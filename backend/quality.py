"""Measures computed from the annual statements: earnings quality, financial risk and
the earnings record. Yahoo's statements list the newest fiscal year first."""

import pandas as pd

from .utils import num


def _get(frame: pd.DataFrame | None, row: str, year: int = 0) -> float | None:
    if frame is None or row not in frame.index or year >= frame.shape[1]:
        return None
    return num(frame.loc[row].iloc[year])


def _div(a: float | None, b: float | None) -> float | None:
    return None if a is None or b is None or b == 0 else a / b


def _metric(key: str, label: str, value: float | None, unit: str, tone: str | None,
            hint: str, note: str | None = None) -> dict:
    return {"key": key, "label": label, "value": value, "unit": unit, "tone": tone, "hint": hint, "note": note}


def _na(key: str, label: str, unit: str, hint: str, note: str) -> dict:
    return _metric(key, label, None, unit, None, hint, note)


def _shares(bal: pd.DataFrame | None, year: int) -> float | None:
    return _get(bal, "Ordinary Shares Number", year) or _get(bal, "Share Issued", year)


def _share_change(bal: pd.DataFrame | None) -> float | None:
    change = _div(_shares(bal, 0), _shares(bal, 1))
    # A jump this size is a stock split or merger, not ordinary issuance or buybacks.
    return None if change is None or not 0.67 < change < 1.5 else change - 1


def piotroski(inc: pd.DataFrame | None, bal: pd.DataFrame | None, cf: pd.DataFrame | None) -> dict | None:
    """Piotroski (2000) F-score: nine pass/fail tests on profitability, funding and efficiency,
    comparing the latest fiscal year with the one before."""
    def assets(year: int) -> float | None:
        # Piotroski scales by assets at the start of the year; fall back to year-end if older data is missing.
        return _get(bal, "Total Assets", year + 1) or _get(bal, "Total Assets", year)

    def roa(year: int) -> float | None:
        return _div(_get(inc, "Net Income", year), assets(year))

    def leverage(year: int) -> float | None:
        total = _get(bal, "Total Assets", year)
        return None if total is None else _div(_get(bal, "Long Term Debt", year) or 0.0, total)

    def current(year: int) -> float | None:
        return _div(_get(bal, "Current Assets", year), _get(bal, "Current Liabilities", year))

    def gross_margin(year: int) -> float | None:
        return _div(_get(inc, "Gross Profit", year), _get(inc, "Total Revenue", year))

    def turnover(year: int) -> float | None:
        return _div(_get(inc, "Total Revenue", year), assets(year))

    def gt(a: float | None, b: float | None) -> bool | None:
        return None if a is None or b is None else a > b

    cfo, roa0 = _get(cf, "Operating Cash Flow"), roa(0)
    lev0, lev1 = leverage(0), leverage(1)
    shares = _share_change(bal)
    tests = [
        ("Profitable (return on assets > 0)", gt(roa0, 0), "profitability"),
        ("Positive operating cash flow", gt(cfo, 0), "profitability"),
        ("Return on assets improved", gt(roa0, roa(1)), "profitability"),
        ("Cash flow exceeds net income", gt(_div(cfo, assets(0)), roa0), "profitability"),
        ("Long-term debt / assets fell", None if lev0 is None or lev1 is None else lev0 < lev1 or lev0 == lev1 == 0,
         "funding"),
        ("Current ratio improved", gt(current(0), current(1)), "funding"),
        ("No new shares issued", None if shares is None else shares <= 0, "funding"),
        ("Gross margin improved", gt(gross_margin(0), gross_margin(1)), "efficiency"),
        ("Asset turnover improved", gt(turnover(0), turnover(1)), "efficiency"),
    ]
    tested = [passed for _, passed, _ in tests if passed is not None]
    if len(tested) < 6:
        return None
    score = sum(tested)
    return {
        "score": score,
        "tested": len(tested),
        # Piotroski's buy and sell groups were 8-9 and 0-1; scale when some tests lack data.
        "state": "strong" if score >= len(tested) - 1 else "weak" if score <= len(tested) * 2 / 9 + 0.5 else "middle",
        "tests": [{"label": label, "passed": passed, "group": group} for label, passed, group in tests],
    }


def quality(stmts: dict, kind: str) -> dict:
    inc, bal, cf = stmts.get("income"), stmts.get("balance"), stmts.get("cashflow")
    financial = kind == "financial"
    note = "n/a for banks & insurers"
    total_assets = _get(bal, "Total Assets")
    avg_assets = _div((total_assets or 0) + (_get(bal, "Total Assets", 1) or total_assets or 0), 2) if total_assets else None

    gpa = _div(_get(inc, "Gross Profit"), total_assets)
    accruals = None
    net_income, cfo = _get(inc, "Net Income"), _get(cf, "Operating Cash Flow")
    if net_income is not None and cfo is not None:
        accruals = _div(net_income - cfo, avg_assets)
    asset_growth = _div(total_assets, _get(bal, "Total Assets", 1))
    asset_growth = None if asset_growth is None else asset_growth - 1
    shares = _share_change(bal)

    def tone(value, good, bad, higher_is_good=True):
        if value is None:
            return None
        if higher_is_good:
            return "good" if value >= good else "bad" if value < bad else "neutral"
        return "good" if value <= good else "bad" if value > bad else "neutral"

    metrics = [
        _na("gross_profitability", "Gross profit / assets", "fraction", "", note) if financial else
        _metric("gross_profitability", "Gross profit / assets", gpa, "fraction", tone(gpa, 0.30, 0.10),
                "Above 30% is high, below 10% low"),
        _na("accruals", "Accruals / assets", "fraction", "", note) if financial else
        _metric("accruals", "Accruals / assets", accruals, "fraction", tone(accruals, 0.0, 0.05, False),
                "Net income minus operating cash flow. Negative means profits are backed by cash"),
        _na("asset_growth", "Asset growth", "fraction", "", note) if financial else
        _metric("asset_growth", "Asset growth", asset_growth, "fraction", tone(asset_growth, 0.05, 0.20, False),
                "Last fiscal year. Above 20% has historically preceded weak returns"),
        _metric("share_change", "Change in share count", shares, "fraction", tone(shares, -0.01, 0.02, False),
                "Negative means buybacks; above 2% means dilution",
                None if shares is not None or _shares(bal, 1) is None else "Skipped: share split"),
    ]
    return {"piotroski": None if financial else piotroski(inc, bal, cf), "metrics": metrics}


def risk(stmts: dict, kind: str) -> dict:
    inc, bal = stmts.get("income"), stmts.get("balance")
    if kind == "financial":
        note = "n/a for banks & insurers"
        return {"metrics": [_na("altman_z", "Altman Z″-score", "number", "", note),
                            _na("interest_coverage", "Interest coverage", "x", "", note),
                            _na("net_debt_ebitda", "Net debt / EBITDA", "x", "", note)]}
    altman = _na("altman_z", "Altman Z″-score", "number", "", "Not designed for REITs") if kind == "reit" else _altman(inc, bal)
    return {"metrics": [altman, _coverage(inc), _net_debt(inc, bal)]}


def _altman(inc: pd.DataFrame | None, bal: pd.DataFrame | None) -> dict:
    """Altman's Z″ for non-manufacturers (1995), which uses book rather than market equity
    and leaves out sales/assets, so it suits service and non-US companies."""
    label, hint = "Altman Z″-score", "Above 2.6 safe, 1.1–2.6 grey zone, below 1.1 distress"
    ta = _get(bal, "Total Assets")
    wc = _get(bal, "Working Capital")
    if wc is None:
        ca, cl = _get(bal, "Current Assets"), _get(bal, "Current Liabilities")
        wc = None if ca is None or cl is None else ca - cl
    re_, ebit = _get(bal, "Retained Earnings"), _get(inc, "EBIT")
    equity, liabilities = _get(bal, "Stockholders Equity"), _get(bal, "Total Liabilities Net Minority Interest")
    parts = [_div(wc, ta), _div(re_, ta), _div(ebit, ta), _div(equity, liabilities)]
    if any(p is None for p in parts):
        return _na("altman_z", label, "number", hint, "Not enough data")
    z = 6.56 * parts[0] + 3.26 * parts[1] + 6.72 * parts[2] + 1.05 * parts[3]
    note = "Buybacks shrink retained earnings and equity, understating Z" if (re_ < 0 or equity < 0) and ebit > 0 else None
    return _metric("altman_z", label, z, "number", "good" if z > 2.6 else "bad" if z < 1.1 else "neutral", hint, note)


def _coverage(inc: pd.DataFrame | None) -> dict:
    label, hint = "Interest coverage", "Operating profit / interest expense. Below 1.5× is strained, above 5× comfortable"
    ebit, interest = _get(inc, "EBIT"), _get(inc, "Interest Expense")
    if ebit is None:
        return _na("interest_coverage", label, "x", hint, "Not enough data")
    if ebit <= 0:
        return _metric("interest_coverage", label, None, "x", "bad", hint, "n/m: operating loss")
    if not interest:
        # Yahoo omits the line for some large borrowers (e.g. Apple), so don't read it as debt-free.
        return _na("interest_coverage", label, "x", hint, "Interest expense not reported")
    cover = ebit / abs(interest)
    return _metric("interest_coverage", label, cover, "x", "good" if cover >= 5 else "bad" if cover < 1.5 else "neutral", hint)


def _net_debt(inc: pd.DataFrame | None, bal: pd.DataFrame | None) -> dict:
    label, hint = "Net debt / EBITDA", "Years of cash profit to repay debt. Negative is net cash; above 3× is high"
    debt = _get(bal, "Total Debt") or 0.0
    cash = _get(bal, "Cash Cash Equivalents And Short Term Investments") or _get(bal, "Cash And Cash Equivalents")
    ebitda = _get(inc, "EBITDA")
    if cash is None or ebitda is None:
        return _na("net_debt_ebitda", label, "x", hint, "Not enough data")
    if ebitda <= 0:
        return _na("net_debt_ebitda", label, "x", hint, "n/m: negative EBITDA")
    ratio = (debt - cash) / ebitda
    return _metric("net_debt_ebitda", label, ratio, "x", "good" if ratio <= 1 else "bad" if ratio > 3 else "neutral",
                   hint, "Net cash" if ratio < 0 else None)


_PERIODS = {"0q": "This quarter", "+1q": "Next quarter", "0y": "This year", "+1y": "Next year"}


def earnings(raw: dict | None, next_epoch) -> dict:
    raw = raw or {}
    history, trend, revisions = raw.get("history"), raw.get("trend"), raw.get("revisions")

    surprises = []
    if history is not None and not history.empty:
        for quarter, row in history.sort_index().tail(4).iterrows():
            actual, estimate = num(row.get("epsActual")), num(row.get("epsEstimate"))
            surprises.append({
                "quarter": pd.Timestamp(quarter).strftime("%Y-%m-%d"),
                "actual": actual,
                "estimate": estimate,
                "surprise_pct": None if actual is None or not estimate else (actual - estimate) / abs(estimate) * 100,
            })

    estimates = []
    for period, label in _PERIODS.items():
        if trend is None or period not in trend.index:
            continue
        row = trend.loc[period]
        current, d30, d90 = num(row.get("current")), num(row.get("30daysAgo")), num(row.get("90daysAgo"))
        rev = revisions.loc[period] if revisions is not None and period in revisions.index else {}
        estimates.append({
            "period": period, "label": label, "current": current,
            "change_30d": None if current is None or not d30 else (current - d30) / abs(d30) * 100,
            "change_90d": None if current is None or not d90 else (current - d90) / abs(d90) * 100,
            "up_30d": num(rev.get("upLast30days")) if len(rev) else None,
            "down_30d": num(rev.get("downLast30days")) if len(rev) else None,
        })

    next_date = None
    if isinstance(next_epoch, (int, float)) and next_epoch > pd.Timestamp.now().timestamp():
        next_date = pd.Timestamp(next_epoch, unit="s").strftime("%Y-%m-%d")
    return {
        "surprises": surprises,
        "beats": sum(1 for s in surprises if s["surprise_pct"] is not None and s["surprise_pct"] > 0),
        "estimates": estimates,
        "next_date": next_date,
    }
