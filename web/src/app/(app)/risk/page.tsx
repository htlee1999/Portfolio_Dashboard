"use client";

import { AlertTriangle, Info, Minus, Plus, ShieldAlert } from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";

import { Legend, MUTED, SERIES, TimeSeries } from "@/components/charts/charts";
import { CurrencyMenu } from "@/components/shell/currency-menu";
import { PageGuide } from "@/components/shell/page-guide";
import { PageHeader } from "@/components/shell/page-header";
import { Button, IconButton } from "@/components/ui/button";
import { Badge, Card, CardHeader } from "@/components/ui/card";
import { Segmented, Select, Slider, TextField } from "@/components/ui/controls";
import { Banner, EmptyState, LoadingBlock } from "@/components/ui/feedback";
import { Disclosure } from "@/components/ui/overlay";
import { Delta, Stat, StatGrid } from "@/components/ui/stat";
import { api, useApi } from "@/lib/api";
import { money, number, pct, shortDate } from "@/lib/format";
import { useSession } from "@/lib/session";
import type { Exposure, Risk, RiskHolding, WhatIf, WhatIfSide } from "@/lib/types";

export default function RiskPage() {
  const { baseCurrency: base } = useSession();
  const { data, error, isLoading, isValidating } = useApi<Risk>(`/portfolio/risk?base=${base}`);
  const p = data?.portfolio;

  return (
    <>
      <PageHeader title="Risk" subtitle="How your holdings move together, what drives the risk, and how much it could lose" actions={<CurrencyMenu />} />
      <PageGuide page="risk" />

      {error && <Banner tone="error" title="Couldn't load risk">{error.message}</Banner>}

      {isLoading && !data ? (
        <LoadingBlock label="Fetching ten years of prices for every holding…" />
      ) : data && (data.empty || !p) ? (
        <Card>
          <EmptyState icon={<ShieldAlert className="size-7" />} title="Nothing to measure yet" action={<Link href="/holdings"><Button>Add Holdings</Button></Link>}>
            Risk needs at least one holding with a few months of price history.
          </EmptyState>
        </Card>
      ) : data && p ? (
        <div className={`space-y-5 transition-opacity ${isValidating ? "opacity-60" : ""}`}>
          {data.flags.length > 0 && (
            <Card>
              <CardHeader title="What stands out" subtitle="Rules of thumb: above 20% in one stock, 30% in one industry, or fewer than 4 independent bets" />
              <ul className="space-y-2.5">
                {data.flags.map((f) => (
                  <li key={f.message} className="flex gap-2.5 text-callout">
                    {f.severity === "warning" ? <AlertTriangle className="mt-0.5 size-4 shrink-0 text-warning" aria-label="Warning" /> : <Info className="mt-0.5 size-4 shrink-0 text-tint" aria-label="Note" />}
                    {f.message}
                  </li>
                ))}
              </ul>
            </Card>
          )}
          {data.excluded.length > 0 && (
            <Banner tone="warning" title={`Left out of the statistics: ${data.excluded.join(", ")}`}>Fewer than 60 trading days of price history.</Banner>
          )}

          <StatGrid>
            <Stat label="Volatility" value={`${number(p.vol, 1)}%`} detail={<span className="text-label-2">a year · S&P 500 {number(p.bench_vol, 1)}%</span>} />
            <Stat label="Beta" value={number(p.beta, 2)} detail={<span className="text-label-2">moves vs the S&P 500 (1 = the same)</span>} />
            <Stat
              label="Independent bets"
              value={number(p.effective_bets, 1)}
              detail={<span className="text-label-2">from {p.holdings_used} holdings · average correlation {number(p.avg_corr, 2)}</span>}
            />
            <Stat
              label="Bad day (1 in 20)"
              value={<span className="text-negative">−{money(p.var95_amount, base, { compact: true })}</span>}
              detail={<span className="text-label-2">−{number(p.var95, 1)}% · worst 5% average −{number(p.cvar95, 1)}%</span>}
            />
          </StatGrid>

          <div className="grid items-start gap-5 lg:grid-cols-5">
            <Card padded={false} className="lg:col-span-3">
              <div className="px-5 pt-5 sm:px-6 sm:pt-6">
                <CardHeader title="Weight vs share of risk" subtitle="A holding whose risk share is far above its weight drives the portfolio's swings" />
                <Legend items={[{ label: "Weight", color: SERIES[0] }, { label: "Share of risk", color: SERIES[1] }]} className="mb-3" />
              </div>
              <RiskTable holdings={data.holdings} />
            </Card>
            <Card className="lg:col-span-2">
              <CardHeader title="Worst stretch" subtitle={`Today's weights over 3 years: ${shortDate(p.drawdown_from, true)} to ${shortDate(p.drawdown_to, true)}`} />
              <div className="mb-4 grid grid-cols-3 gap-3">
                <Mini label="Max drawdown" value={<span className="text-negative">{pct(p.max_drawdown, 0)}</span>} />
                <Mini label="S&P 500" value={pct(p.bench_max_drawdown, 0)} />
                <Mini label="Below peak now" value={pct(p.current_drawdown, 0)} />
              </div>
              {data.drawdown && (
                <TimeSeries
                  data={data.drawdown}
                  lines={[
                    { key: "portfolio", label: "Portfolio", color: SERIES[0], width: 2, area: true },
                    { key: "benchmark", label: "S&P 500", color: MUTED, dashed: true },
                  ]}
                  height={200}
                  format={(v) => `${number(v, 0)}%`}
                  ariaLabel="Drawdown of the portfolio and the S&P 500"
                />
              )}
            </Card>
          </div>

          {data.exposure && <ExposureCard exposure={data.exposure} />}

          <div className="grid items-start gap-5 lg:grid-cols-2">
            {data.correlation && data.correlation.symbols.length > 1 && <CorrelationCard c={data.correlation} />}
            <StressCard data={data} base={base} />
          </div>

          <WhatIfCard base={base} holdings={data.holdings} />

          <p className="px-1 pt-2 text-center text-caption text-label-2">
            Daily dividend-adjusted returns in {base} over the last {data.window_days} trading days, so currency moves count. History describes risk; it doesn&apos;t bound it.
          </p>
        </div>
      ) : null}
    </>
  );
}

function Mini({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="min-w-0">
      <div className="text-caption text-label-2">{label}</div>
      <div className="text-headline tabular">{value}</div>
    </div>
  );
}

function Pair({ a, b, max }: { a: number; b: number | null; max: number }) {
  return (
    <div className="space-y-1" aria-hidden>
      <span className="block h-1.5 rounded-full bg-[var(--series-1)]" style={{ width: `${Math.max(1, (a / max) * 100)}%` }} />
      <span className="block h-1.5 rounded-full bg-[var(--series-2)]" style={{ width: `${Math.max(1, ((b ?? 0) / max) * 100)}%` }} />
    </div>
  );
}

function RiskTable({ holdings }: { holdings: RiskHolding[] }) {
  const max = Math.max(...holdings.map((h) => Math.max(h.weight, h.risk_share ?? 0)), 1);
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[560px] text-callout tabular">
        <thead>
          <tr className="text-left text-caption text-label-2 [&>th]:px-3 [&>th]:pb-2 [&>th]:font-medium [&>th:first-child]:pl-6 [&>th:last-child]:pr-6">
            <th>Holding</th>
            <th className="w-40" />
            <th className="text-right">Weight</th>
            <th className="text-right">Risk</th>
            <th className="text-right">Beta</th>
            <th className="text-right" title="Correlation with the rest of the portfolio">Corr.</th>
          </tr>
        </thead>
        <tbody>
          {holdings.map((h) => (
            <tr key={h.symbol} className="border-t-[0.5px] border-separator [&>td]:px-3 [&>td]:py-2.5 [&>td:first-child]:pl-6 [&>td:last-child]:pr-6">
              <td>
                <div className="font-semibold">{h.symbol}</div>
                <div className="max-w-44 truncate text-caption text-label-2">{h.industry}</div>
              </td>
              <td>
                <Pair a={h.weight} b={h.risk_share} max={max} />
              </td>
              <td className="text-right">{number(h.weight, 1)}%</td>
              <td className={`text-right ${h.risk_share != null && h.risk_share > h.weight * 1.5 && h.risk_share > 5 ? "font-semibold" : ""}`}>
                {h.risk_share != null ? `${number(h.risk_share, 1)}%` : "—"}
              </td>
              <td className="text-right">{number(h.beta, 2)}</td>
              <td className="text-right">{number(h.corr_to_rest, 2)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const EXPOSURES = [
  { value: "sector", label: "Sector" },
  { value: "industry", label: "Industry" },
  { value: "currency", label: "Currency" },
  { value: "country", label: "Country" },
] as const;

function ExposureCard({ exposure }: { exposure: NonNullable<Risk["exposure"]> }) {
  const [by, setBy] = useState<(typeof EXPOSURES)[number]["value"]>("sector");
  const rows: Exposure[] = exposure[by].filter((r) => r.weight > 0.05 || (r.benchmark ?? 0) > 0.5);
  const max = Math.max(...rows.map((r) => Math.max(r.weight, r.benchmark ?? 0)), 1);
  const withBench = by === "sector" && rows.some((r) => r.benchmark != null);
  return (
    <Card>
      <CardHeader
        title="Exposure"
        subtitle={
          by === "sector"
            ? "Funds are looked through to their sectors · against the S&P 500"
            : by === "currency"
              ? "By the currency each holding trades in; an ADR trades in USD but its business may not"
              : by === "country"
                ? "Where each company is based"
                : "By Yahoo's industry for each company"
        }
        action={<Segmented size="sm" label="Exposure by" options={EXPOSURES} value={by} onChange={setBy} />}
      />
      {withBench && <Legend items={[{ label: "Your portfolio", color: SERIES[0] }, { label: "S&P 500", color: MUTED }]} className="mb-3" />}
      <ul className="space-y-2.5">
        {rows.map((r) => (
          <li key={r.name} className="grid grid-cols-[minmax(0,10rem)_1fr_auto] items-center gap-3 text-footnote">
            <span className="truncate text-label-2" title={r.name}>{r.name}</span>
            <span className="space-y-1">
              <span className="block h-2.5 rounded-r-[4px] bg-[var(--series-1)]" style={{ width: `${Math.max(0.5, (r.weight / max) * 100)}%` }} />
              {withBench && <span className="block h-1.5 rounded-r-[4px] bg-[var(--series-muted)]" style={{ width: `${Math.max(0.5, ((r.benchmark ?? 0) / max) * 100)}%` }} />}
            </span>
            <span className="tabular w-24 text-right">
              <span className="font-semibold">{number(r.weight, 1)}%</span>
              {withBench && <span className="text-label-2"> / {r.benchmark != null ? number(r.benchmark, 0) : "—"}%</span>}
            </span>
          </li>
        ))}
      </ul>
    </Card>
  );
}

/** Diverging fill: warm for holdings that move together, cool for ones that offset, neutral at zero. */
function cellColor(v: number) {
  const strength = Math.round(Math.min(1, Math.abs(v)) * 80);
  return `color-mix(in srgb, ${v >= 0 ? "var(--series-2)" : "var(--series-1)"} ${strength}%, var(--fill-secondary))`;
}

function CorrelationCard({ c }: { c: NonNullable<Risk["correlation"]> }) {
  return (
    <Card>
      <CardHeader title="Correlation" subtitle="How daily returns move together: 1 in lockstep, 0 unrelated, below 0 offsetting" />
      <div className="overflow-x-auto">
        <table className="mx-auto border-separate border-spacing-[2px] text-[11px] tabular" aria-label="Correlation matrix">
          <thead>
            <tr>
              <th />
              {c.symbols.map((s) => (
                <th key={s} className="h-14 w-9 align-bottom font-medium text-label-2">
                  <span className="inline-block origin-bottom-left translate-x-3 -rotate-60 whitespace-nowrap">{s}</span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {c.matrix.map((row, i) => (
              <tr key={c.symbols[i]}>
                <th className="pr-1.5 text-right font-medium text-label-2">{c.symbols[i]}</th>
                {row.map((v, j) => (
                  <td
                    key={j}
                    title={`${c.symbols[i]} × ${c.symbols[j]}: ${v.toFixed(2)}`}
                    className="size-9 rounded-[4px] text-center text-label"
                    style={{ background: i === j ? "var(--fill)" : cellColor(v) }}
                  >
                    {i === j ? "" : v.toFixed(1).replace("0.", ".")}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="mt-3 flex items-center justify-center gap-2 text-caption text-label-2">
        <span>−1 offsetting</span>
        <span className="h-2 w-28 rounded-full" style={{ background: `linear-gradient(90deg, ${cellColor(-1)}, ${cellColor(0)}, ${cellColor(1)})` }} />
        <span>+1 together</span>
      </div>
    </Card>
  );
}

function StressCard({ data, base }: { data: Risk; base: string }) {
  const [shock, setShock] = useState(-20);
  const industries = useMemo(() => (data.exposure?.industry ?? []).filter((x) => !x.name.startsWith("Fund")).map((x) => x.name), [data]);
  const [industry, setIndustry] = useState<string>("");
  const [industryShock, setIndustryShock] = useState(-30);
  const ind = industry || industries[0] || "";
  const total = data.total_value;
  // Beta-implied: each holding moves its beta times the market.
  const marketLoss = data.holdings.reduce((sum, h) => sum + (h.weight / 100) * (h.beta ?? 1) * shock, 0);
  const industryLoss = data.holdings.reduce((sum, h) => sum + (h.industry === ind ? (h.weight / 100) * industryShock : 0), 0);

  return (
    <Card>
      <CardHeader title="Stress tests" subtitle="Today's holdings through past selloffs, peak to trough of the S&P 500" />
      <div>
        {data.scenarios.map((s) => (
          <Disclosure
            key={s.name}
            title={s.name}
            subtitle={`${shortDate(s.start, true)} – ${shortDate(s.end, true)} · S&P 500 ${pct(s.benchmark, 0)}${s.estimated ? ` · ${s.estimated} estimated from beta` : ""}`}
            trailing={
              <span className="text-right tabular">
                <span className="block text-callout font-semibold text-negative">{pct(s.portfolio, 0)}</span>
                <span className="block text-caption text-label-2">{money(s.loss, base, { compact: true })}</span>
              </span>
            }
          >
            <ul className="grid grid-cols-2 gap-x-4 gap-y-1 text-footnote tabular sm:grid-cols-3">
              {[...s.rows].sort((a, b) => a.return - b.return).map((r) => (
                <li key={r.symbol} className="flex justify-between gap-2">
                  <span className="text-label-2">
                    {r.symbol}
                    {r.estimated && <span title="Not listed then: its beta times the S&P 500's move"> *</span>}
                  </span>
                  <Delta value={r.return}>{pct(r.return, 0)}</Delta>
                </li>
              ))}
            </ul>
            {s.estimated > 0 && <p className="mt-2 text-caption text-label-2">* not trading then: beta × the S&P 500&apos;s move.</p>}
          </Disclosure>
        ))}
      </div>

      <div className="mt-4 space-y-4 border-t-[0.5px] border-separator pt-4">
        <div>
          <Slider label="If the S&P 500 moves" value={shock} min={-50} max={20} onChange={setShock} format={(v) => `${v > 0 ? "+" : ""}${v}%`} />
          <p className="mt-1 px-1 text-callout">
            Your portfolio: about <Delta value={marketLoss}>{pct(marketLoss, 0)}</Delta>{" "}
            <span className="text-label-2">({money((marketLoss / 100) * total, base, { compact: true, sign: true })}, from each holding&apos;s beta)</span>
          </p>
        </div>
        {industries.length > 0 && (
          <div className="grid gap-3 sm:grid-cols-[1fr_1fr]">
            <Select label="If one industry" options={industries} value={ind} onChange={(e) => setIndustry(e.target.value)} />
            <Slider label="moves" value={industryShock} min={-60} max={30} onChange={setIndustryShock} format={(v) => `${v > 0 ? "+" : ""}${v}%`} />
            <p className="px-1 text-callout sm:col-span-2">
              Your portfolio: <Delta value={industryLoss}>{pct(industryLoss, 1)}</Delta>{" "}
              <span className="text-label-2">({money((industryLoss / 100) * total, base, { compact: true, sign: true })}; the rest held flat)</span>
            </p>
          </div>
        )}
      </div>
    </Card>
  );
}

type TradeRow = { symbol: string; side: "buy" | "sell"; amount: string };

function WhatIfCard({ base, holdings }: { base: string; holdings: RiskHolding[] }) {
  const [rows, setRows] = useState<TradeRow[]>([{ symbol: "", side: "buy", amount: "" }]);
  const [result, setResult] = useState<WhatIf | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const update = (i: number, patch: Partial<TradeRow>) => setRows(rows.map((r, j) => (j === i ? { ...r, ...patch } : r)));

  async function run(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const trades = rows
        .filter((r) => r.symbol.trim() && Number(r.amount) > 0)
        .map((r) => ({ symbol: r.symbol.trim(), amount: (r.side === "buy" ? 1 : -1) * Number(r.amount) }));
      if (!trades.length) throw new Error("Enter a symbol and an amount");
      setResult(await api<WhatIf>(`/portfolio/whatif?base=${base}`, { method: "POST", json: { trades } }));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <CardHeader title="What if?" subtitle={`Check a trade before you make it: the portfolio's risk before and after, in ${base}`} />
      <form onSubmit={run} className="space-y-3">
        {rows.map((r, i) => (
          <div key={i} className="grid grid-cols-[1fr_auto] items-end gap-2 sm:grid-cols-[minmax(0,10rem)_auto_minmax(0,12rem)_auto]">
            <TextField label={i === 0 ? "Symbol" : undefined} placeholder={i === 0 ? "KO" : holdings[0]?.symbol} value={r.symbol} onChange={(e) => update(i, { symbol: e.target.value.toUpperCase() })} autoCapitalize="characters" spellCheck={false} />
            <Segmented label="Buy or sell" className="mb-1" options={[{ value: "buy", label: "Buy" }, { value: "sell", label: "Sell" }]} value={r.side} onChange={(v) => update(i, { side: v })} />
            <TextField label={i === 0 ? `Amount (${base})` : undefined} type="number" inputMode="decimal" min="0" step="any" placeholder="5000" value={r.amount} onChange={(e) => update(i, { amount: e.target.value })} />
            <div className="flex gap-1">
              {rows.length > 1 && (
                <IconButton type="button" label="Remove trade" onClick={() => setRows(rows.filter((_, j) => j !== i))}>
                  <Minus className="size-[18px]" />
                </IconButton>
              )}
              {i === rows.length - 1 && rows.length < 4 && (
                <IconButton type="button" label="Add another trade" onClick={() => setRows([...rows, { symbol: "", side: "sell", amount: "" }])}>
                  <Plus className="size-[18px]" />
                </IconButton>
              )}
            </div>
          </div>
        ))}
        {error && <Banner tone="error" title={error} />}
        <Button type="submit" loading={busy}>Compare</Button>
      </form>
      {result?.after && <WhatIfResult r={result} base={base} />}
    </Card>
  );
}

function WhatIfResult({ r, base }: { r: WhatIf; base: string }) {
  const b = r.before;
  const a = r.after!;
  /** ``lowerIsBetter`` null: the change is shown without judging it. */
  const row = (label: string, get: (x: WhatIfSide) => number | null | undefined, fmt: (v: number) => string, lowerIsBetter: boolean | null = true) => {
    const before = b ? get(b) : null;
    const after = get(a);
    const diff = before != null && after != null ? after - before : null;
    const better = diff == null || Math.abs(diff) < 1e-9 || lowerIsBetter == null ? null : lowerIsBetter ? diff < 0 : diff > 0;
    return (
      <tr key={label} className="border-t-[0.5px] border-separator">
        <td className="py-2 text-label-2">{label}</td>
        <td className="py-2 text-right">{before != null ? fmt(before) : "—"}</td>
        <td className="py-2 text-right font-semibold">{after != null ? fmt(after) : "—"}</td>
        <td className="py-2 text-right">
          {better == null ? <span className="text-label-3">—</span> : <Badge tone={better ? "positive" : "negative"}>{better ? "Better" : "Worse"}</Badge>}
        </td>
      </tr>
    );
  };
  return (
    <div className="mt-5 border-t-[0.5px] border-separator pt-4">
      <table className="w-full text-callout tabular">
        <thead className="text-caption text-label-2">
          <tr>
            <th className="py-1 text-left font-normal" />
            <th className="py-1 text-right font-normal">Now</th>
            <th className="py-1 text-right font-normal">After</th>
            <th className="w-20" />
          </tr>
        </thead>
        <tbody>
          {row("Volatility", (x) => x.vol, (v) => `${number(v, 1)}%`)}
          {row("Beta", (x) => x.beta, (v) => number(v, 2))}
          {row("Independent bets", (x) => x.effective_bets, (v) => number(v, 1), false)}
          {row("Max drawdown (3 yr)", (x) => x.max_drawdown, (v) => pct(v, 0), false)}
          {row("Bad day (1 in 20)", (x) => x.var95, (v) => `−${number(v, 1)}%`)}
          {row("Worst stress test", (x) => x.worst_scenario?.portfolio, (v) => pct(v, 0), false)}
          {row(`Largest industry`, (x) => x.top_industry?.weight, (v) => `${number(v, 0)}%`)}
          {r.symbols.map((s) => row(`${s} weight`, (x) => x.holdings[s]?.weight ?? 0, (v) => `${number(v, 1)}%`, null))}
          {r.symbols.map((s) => row(`${s} share of risk`, (x) => x.holdings[s]?.risk_share ?? 0, (v) => `${number(v, 1)}%`, null))}
        </tbody>
      </table>
      <p className="mt-3 text-footnote text-label-2">
        Largest industry after: {a.top_industry?.name ?? "—"}. Portfolio value after: {money(a.total_value, base)}. A trade can lower risk and still leave you
        concentrated; check the warnings below.
      </p>
      {a.flags.length > 0 && (
        <ul className="mt-3 space-y-1.5">
          {a.flags.map((f) => (
            <li key={f.message} className="flex gap-2 text-footnote">
              <AlertTriangle className="mt-0.5 size-3.5 shrink-0 text-warning" aria-hidden />
              {f.message}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
