"""Actual returns, risk statistics, the reverse DCF, FIFO sales and the Track Record's ranking, on
synthetic data with known answers (no network)."""

import numpy as np
import pandas as pd
import pytest

from backend import returns, risk, storage, track_record, valuation


# ── Returns ──────────────────────────────────────────────────────────────────

def test_xirr_one_year_ten_percent():
    flows = [(pd.Timestamp("2024-01-01"), -100.0), (pd.Timestamp("2024-12-31"), 110.0)]
    assert returns.xirr(flows) == pytest.approx(0.10, abs=0.002)


def test_xirr_needs_money_in_and_out():
    assert returns.xirr([(pd.Timestamp("2024-01-01"), -100.0)]) is None


def _ledger(prices, purchases, sales=(), divs=None):
    index = prices.index
    ones = np.ones(len(index))
    return returns.rebuild(list(purchases), list(sales), {"X": prices}, {"X": divs if divs is not None else pd.Series(dtype=float)},
                           {"USD": ones}, prices, ones, index)


def test_twr_and_benchmark_on_a_doubling_stock():
    index = pd.bdate_range("2024-01-01", periods=5)
    prices = pd.Series([10, 12, 15, 18, 20.0], index=index)
    out = _ledger(prices, [{"Symbol": "X", "Quantity": 10, "Purchase_Price": 10, "Purchase_Date": "2024-01-01", "Currency": "USD"}])
    assert out["twr"][-1] == pytest.approx(2.0)
    assert out["value"][-1] == pytest.approx(200.0)
    # The benchmark is the same series here, so the same purchase in it ends at the same value.
    assert out["pme"][-1] == pytest.approx(200.0)


def test_twr_ignores_the_size_of_a_later_deposit():
    index = pd.bdate_range("2024-01-01", periods=3)
    prices = pd.Series([10, 10, 20.0], index=index)
    out = _ledger(prices, [
        {"Symbol": "X", "Quantity": 1, "Purchase_Price": 10, "Purchase_Date": "2024-01-01", "Currency": "USD"},
        {"Symbol": "X", "Quantity": 100, "Purchase_Price": 10, "Purchase_Date": "2024-01-02", "Currency": "USD"},
    ])
    assert out["twr"][-1] == pytest.approx(2.0)


def test_dividend_paid_on_shares_held_before_the_ex_date():
    index = pd.bdate_range("2024-01-01", periods=4)
    prices = pd.Series([10, 10, 10, 10.0], index=index)
    divs = pd.Series([0.5], index=[index[2]])
    out = _ledger(prices, [
        {"Symbol": "X", "Quantity": 10, "Purchase_Price": 10, "Purchase_Date": "2024-01-01", "Currency": "USD"},
        # Bought on the ex-date: no dividend on these.
        {"Symbol": "X", "Quantity": 5, "Purchase_Price": 10, "Purchase_Date": str(index[2].date()), "Currency": "USD"},
    ], divs=divs)
    assert out["income"].sum() == pytest.approx(5.0)
    # Money added that day counts from the start of the day (Modified Dietz), so the base is 100 + 50.
    assert out["twr"][-1] == pytest.approx(1 + 5 / 150)


def test_sale_takes_money_out():
    index = pd.bdate_range("2024-01-01", periods=3)
    prices = pd.Series([10, 10, 10.0], index=index)
    out = _ledger(prices,
                  [{"Symbol": "X", "Quantity": 10, "Purchase_Price": 10, "Purchase_Date": "2024-01-01", "Currency": "USD"}],
                  [{"Symbol": "X", "Quantity": 4, "Date": str(index[1].date()), "proceeds": 40.0}])
    assert out["value"][-1] == pytest.approx(60.0)
    assert out["flow"].sum() == pytest.approx(60.0)
    assert out["twr"][-1] == pytest.approx(1.0)


# ── Risk ─────────────────────────────────────────────────────────────────────

def _returns(seed=0, n=500):
    rng = np.random.default_rng(seed)
    index = pd.bdate_range("2023-01-02", periods=n)
    return index, rng.normal(0, 0.01, (n, 3))


def test_identical_holdings_are_one_bet_and_independent_ones_are_many():
    index, z = _returns()
    bench = pd.Series(z[:, 0], index=index)
    same = pd.DataFrame({"A": z[:, 0], "B": z[:, 0]}, index=index)
    apart = pd.DataFrame({"A": z[:, 1], "B": z[:, 2]}, index=index)
    w = pd.Series({"A": 0.5, "B": 0.5})
    assert risk.stats(same, w, bench)["effective_bets"] == pytest.approx(1.0, abs=1e-6)
    assert risk.stats(apart, w, bench)["effective_bets"] == pytest.approx(2.0, abs=0.15)


def test_risk_shares_sum_to_100_and_beta_of_the_benchmark_is_one():
    index, z = _returns(1)
    bench = pd.Series(z[:, 0], index=index)
    R = pd.DataFrame({"A": z[:, 0], "B": z[:, 1] * 3, "C": z[:, 2]}, index=index)
    s = risk.stats(R, pd.Series({"A": 0.2, "B": 0.5, "C": 0.3}), bench)
    assert sum(h["risk_share"] for h in s["holdings"].values()) == pytest.approx(100.0)
    assert s["holdings"]["A"]["beta"] == pytest.approx(1.0)
    # The volatile holding carries more than its weight of the risk.
    assert s["holdings"]["B"]["risk_share"] > 50


def test_drawdown():
    index = pd.bdate_range("2024-01-01", periods=5)
    dd = risk.drawdown(pd.Series([1.0, 1.2, 0.9, 1.0, 1.1], index=index))
    assert dd["max"] == pytest.approx(-25.0)
    assert dd["from"] == str(index[1].date()) and dd["to"] == str(index[2].date())
    assert dd["current"] == pytest.approx((1.1 / 1.2 - 1) * 100)


def test_scenario_return_needs_history_from_the_start():
    index = pd.bdate_range("2020-03-02", periods=30)
    prices = pd.Series(np.linspace(100, 70, 30), index=index)
    assert risk.scenario_return(prices, "2020-02-19", "2020-03-23") is None
    assert risk.scenario_return(prices, "2020-03-02", str(index[-1].date())) == pytest.approx(-0.3)


# ── Reverse DCF ──────────────────────────────────────────────────────────────

def test_implied_growth_recovers_the_growth_that_set_the_price():
    ev = valuation.dcf_value(100.0, 0.12, 0.09)
    assert valuation.implied_growth(ev, 100.0, 0.09) == pytest.approx(0.12, abs=1e-6)


def test_implied_growth_needs_positive_cash_flow():
    assert valuation.implied_growth(1000.0, -5.0, 0.09) is None


# ── FIFO sales ───────────────────────────────────────────────────────────────

@pytest.fixture
def tmp_data(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    storage.save_holdings("t", [
        {"Symbol": "X", "Quantity": 10, "Purchase_Price": 5, "Purchase_Date": "2022-01-03", "Currency": "USD"},
        {"Symbol": "X", "Quantity": 10, "Purchase_Price": 8, "Purchase_Date": "2023-01-03", "Currency": "USD"},
        {"Symbol": "Y", "Quantity": 1, "Purchase_Price": 1, "Purchase_Date": "2023-01-03", "Currency": "USD"},
    ])
    return "t"


def test_sale_takes_the_oldest_lots_first_and_undo_restores_them(tmp_data):
    t = storage.sell(tmp_data, "X", 15, 10, "2024-01-02", fees=1)
    assert t["cost"] == pytest.approx(10 * 5 + 5 * 8)
    assert t["realized"] == pytest.approx(15 * 10 - 1 - 90)
    left = {(h["Symbol"], h["Purchase_Date"]): h["Quantity"] for h in storage.load_holdings(tmp_data)}
    assert left == {("X", "2023-01-03"): 5, ("Y", "2023-01-03"): 1}
    assert sum(p["Quantity"] for p in storage.all_purchases(tmp_data) if p["Symbol"] == "X") == pytest.approx(20)
    assert storage.undo_sell(tmp_data, t["id"])
    assert sorted(h["Quantity"] for h in storage.load_holdings(tmp_data) if h["Symbol"] == "X") == [10, 10]
    assert storage.load_transactions(tmp_data) == []


def test_cannot_sell_shares_not_yet_bought(tmp_data):
    with pytest.raises(ValueError):
        storage.sell(tmp_data, "X", 15, 10, "2022-06-01")


# ── Ranking ──────────────────────────────────────────────────────────────────

def _signal(symbol, rec, conf, excess, expected=None, run="r1"):
    return {"symbol": symbol, "recommendation": rec, "confidence": conf, "score_excess": excess,
            "expected_excess": expected, "run": run, "model": "m", "outcome": "x"}


def test_perfect_ranking_scores_an_ic_of_one():
    signals = [_signal(s, "HOLD", 5, e, expected=e) for s, e in zip("ABCDEF", [6, 4, 2, 0, -2, -4])]
    r = track_record.ranking(signals)
    assert r["count"] == 1 and r["mean_ic"] == pytest.approx(1.0)
    assert r["runs"][0]["spread"] > 0
    assert not set(r["runs"][0]["top"]) & set(r["runs"][0]["bottom"])


def test_ranking_from_conviction_when_mostly_holds():
    signals = [_signal("A", "BUY", 8, 5.0), _signal("B", "HOLD", 6, 1.0), _signal("C", "HOLD", 6, 0.0),
               _signal("D", "HOLD", 6, -1.0), _signal("E", "HOLD", 7, -2.0)]
    run = track_record.ranking(signals)["runs"][0]
    assert run["top"] == ["A"] and run["spread"] == pytest.approx(5.0 - (-0.5))


def test_confidence_calibration_buckets():
    signals = [{"outcome": "Correct", "confidence": 7}, {"outcome": "Wrong", "confidence": 7},
               {"outcome": "Correct", "confidence": 9}, {"outcome": "Neutral", "confidence": 7}]
    rows = {r["label"]: r for r in track_record.confidence_calibration(signals)["rows"]}
    assert rows["7"]["n"] == 2 and rows["7"]["actual"] == pytest.approx(50.0)
    assert rows["8–10"]["actual"] == pytest.approx(100.0)
