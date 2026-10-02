"use client";

import { BookOpen, Check, ExternalLink, Minus, X } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useState } from "react";

import { SERIES } from "@/components/charts/charts";
import { PageHeader, ResearchTabs } from "@/components/shell/page-header";
import { ResearchPage } from "@/components/shell/research-page";
import { SymbolPicker, useSymbol } from "@/components/shell/symbol-picker";
import { Badge, Card, CardHeader } from "@/components/ui/card";
import { Segmented } from "@/components/ui/controls";
import { EvidenceDot, EvidenceGuide, EvidenceLegend } from "@/components/ui/evidence";
import { Banner, LoadingBlock } from "@/components/ui/feedback";
import { Disclosure } from "@/components/ui/overlay";
import { Delta, Stat, StatGrid } from "@/components/ui/stat";
import { useApi } from "@/lib/api";
import { compact, money, number, pct, shortDate } from "@/lib/format";
import { EVIDENCE_FOR, FUNDAMENTALS, GUIDE_SECTIONS } from "@/lib/fundamental-evidence";
import { spring } from "@/lib/motion";
import type { EarningsRecord, Fundamentals, HistoryRow, Metric, Piotroski, Ratio } from "@/lib/types";

export default function Page() {
  return (
    <ResearchPage>
      <FundamentalsView />
    </ResearchPage>
  );
}

function ratioText(r: Ratio) {
  if (r.value == null) return r.note?.startsWith("n/m") ? "n/m" : "—";
  if (r.unit === "fraction") return pct(r.value * 100, 1, false);
  if (r.unit === "percent") return `${number(r.value / 100, 2)}×`;
  return `${number(r.value, 2)}×`;
}

function multiple(value: number | null, lossMaking: boolean) {
  if (value != null) return `${number(value, 1)}×`;
  return lossMaking ? "n/m" : "—";
}

function FundamentalsView() {
  const [symbol, setSymbol] = useSymbol();
  const { data, error, isLoading, isValidating } = useApi<Fundamentals>(`/stocks/${encodeURIComponent(symbol)}/fundamentals`);
  const groups = Object.keys(data?.ratios ?? {});
  const [group, setGroup] = useState("Valuation");
  const [statement, setStatement] = useState<"income" | "balance" | "cashflow">("income");
  const ccy = data?.profile.currency ?? "USD";
  const reportCcy = data?.profile.financial_currency ?? ccy;

  return (
    <>
      <ResearchTabs />
      <PageHeader title="Fundamentals" eyebrow="Research" actions={<SymbolPicker symbol={symbol} onChange={setSymbol} />} />

      {error && <Banner tone="error" title={`Couldn't load fundamentals for ${symbol}`}>{error.message}</Banner>}

      {isLoading && !data ? (
        <LoadingBlock label={`Loading ${symbol} financials…`} />
      ) : data ? (
        <div className={`space-y-5 transition-opacity ${isValidating || data.symbol !== symbol ? "opacity-55" : ""}`}>
          <Card>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0">
                <h2 className="text-title-2">{data.profile.name}</h2>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {data.profile.sector && <Badge tone="tint">{data.profile.sector}</Badge>}
                  {data.profile.industry && <Badge>{data.profile.industry}</Badge>}
                  {data.profile.country && <Badge>{data.profile.country}</Badge>}
                </div>
              </div>
              {data.profile.website && (
                <a href={data.profile.website} target="_blank" rel="noreferrer" className="flex min-h-11 items-center gap-1 text-callout font-semibold text-tint">
                  Website <ExternalLink className="size-3.5" />
                </a>
              )}
            </div>
            {data.profile.kind_note && (
              <p className="mt-4 rounded-xl bg-fill px-4 py-3 text-footnote text-label-2">{data.profile.kind_note}</p>
            )}
            {data.profile.summary && <Summary text={data.profile.summary} />}
          </Card>

          <StatGrid>
            <Stat label="Price" value={money(data.headline.price, ccy)} detail={<span className="text-label-2">52w {money(data.headline.week52_low, ccy)} – {money(data.headline.week52_high, ccy)}</span>} />
            <Stat label="Market cap" value={money(data.headline.market_cap, ccy, { compact: true })} detail={<span className="text-label-2">EV {money(data.headline.enterprise_value, ccy, { compact: true })}</span>} />
            <Stat
              label="P/E"
              value={multiple(data.headline.pe, data.headline.loss_making)}
              detail={
                <span className="text-label-2">
                  {data.headline.loss_making ? "Loss-making · " : ""}Forward {multiple(data.headline.forward_pe, data.headline.loss_making)}
                </span>
              }
            />
            <Stat label="Dividend yield" value={data.analyst.dividend_yield_pct ? pct(data.analyst.dividend_yield_pct, 2, false) : "—"} detail={<span className="text-label-2">Payout {data.analyst.payout_ratio != null ? pct(data.analyst.payout_ratio * 100, 0, false) : "—"}</span>} />
          </StatGrid>

          <div className="grid gap-5 lg:grid-cols-5">
            <Card className="lg:col-span-3">
              <CardHeader title="Ratios" subtitle={data.as_of.ratios ? `Trailing 12 months to ${shortDate(data.as_of.ratios, true)}` : undefined} />
              <div className="-mx-1 mb-4 overflow-x-auto px-1">
                <Segmented size="sm" className="[&>button]:px-3.5" label="Ratio group" value={group} onChange={setGroup} options={groups.map((g) => ({ value: g, label: g }))} />
              </div>
              <AnimatePresence mode="wait">
                <motion.dl key={group} initial={{ opacity: 0, x: 8 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -8 }} transition={spring.snappy} className="grid grid-cols-2 gap-x-6 gap-y-4 sm:grid-cols-3">
                  {(data.ratios[group] ?? []).map((r) => (
                    <div key={r.label}>
                      <dt className="flex items-center gap-1.5 text-footnote text-label-2">
                        {r.label}
                        {EVIDENCE_FOR[r.key] && <EvidenceDot info={FUNDAMENTALS[EVIDENCE_FOR[r.key]]} />}
                      </dt>
                      <dd className="text-title-3 tabular">{ratioText(r)}</dd>
                      {r.note && <dd className={`mt-0.5 text-caption ${r.value == null ? "text-label-2" : "text-warning"}`}>{r.note.replace(/^n\/m: /, "")}</dd>}
                    </div>
                  ))}
                </motion.dl>
              </AnimatePresence>
              <EvidenceLegend className="mt-5 border-t-[0.5px] border-separator pt-3" />
            </Card>

            <Card className="lg:col-span-2">
              <CardHeader
                title={<TitleWithEvidence title="Analyst view" info={FUNDAMENTALS.analysts} />}
                subtitle={data.analyst.analyst_count ? `${data.analyst.analyst_count} analysts` : undefined}
                action={data.analyst.recommendation_key && <Badge tone="tint" className="capitalize">{data.analyst.recommendation_key.replace("_", " ")}</Badge>}
              />
              <div className="text-footnote text-label-2">Mean price target</div>
              <div className="flex items-baseline gap-2">
                <span className="text-title-1 tabular">{money(data.analyst.target_mean, ccy)}</span>
                <Delta value={data.analyst.upside_pct} className="text-callout">
                  {pct(data.analyst.upside_pct, 1)}
                </Delta>
              </div>
              <TargetRange low={data.analyst.target_low} high={data.analyst.target_high} mean={data.analyst.target_mean} price={data.headline.price} ccy={ccy} />
              {data.analyst.recommendation_mean != null && (
                <p className="mt-4 text-footnote text-label-2">
                  Consensus score {number(data.analyst.recommendation_mean, 2)} on a 1 (strong buy) to 5 (sell) scale.
                </p>
              )}
            </Card>
          </div>

          {data.history.rows.length > 0 && <HistoryCard history={data.history} />}

          <div className="grid gap-5 lg:grid-cols-3">
            <QualityCard piotroski={data.quality.piotroski} metrics={data.quality.metrics} financial={data.profile.kind === "financial"} />
            <Card>
              <CardHeader title="Financial risk" subtitle="Latest fiscal year" />
              <MetricList metrics={data.risk.metrics} />
            </Card>
            <EarningsCard earnings={data.earnings} />
          </div>

          <Card padded={false}>
            <div className="flex flex-wrap items-center justify-between gap-3 px-5 pt-5 sm:px-6 sm:pt-6">
              <div>
                <h3 className="text-headline">Financial statements</h3>
                <p className="mt-0.5 text-footnote text-label-2">
                  Annual, in {reportCcy}
                  {reportCcy !== ccy && ` (shares trade in ${ccy})`}
                  {data.as_of.statements && ` · latest fiscal year ended ${shortDate(data.as_of.statements, true)}`}
                </p>
              </div>
              <Segmented
                size="sm"
                label="Statement"
                value={statement}
                onChange={setStatement}
                options={[
                  { value: "income", label: "Income" },
                  { value: "balance", label: "Balance" },
                  { value: "cashflow", label: "Cash Flow" },
                ]}
              />
            </div>
            <StatementTable data={data.statements[statement]} ccy={reportCcy} />
          </Card>

          <Card>
            <Disclosure
              title="Metric guide & evidence"
              subtitle="How to read each measure, how well research supports it, and sources"
              leading={<BookOpen className="size-5 text-tint" />}
            >
              <EvidenceGuide
                sections={GUIDE_SECTIONS.map((g) => ({ title: g.title, items: g.keys.map((k) => FUNDAMENTALS[k]) }))}
                intro="Evidence ratings summarise peer-reviewed research on whether each measure has predicted future stock returns. Strong means the effect has held across decades and markets; mixed means it worked historically but has weakened or depends on context; risk measures describe danger rather than expected return. Thresholds marked Good, Fair or Watch are rules of thumb, not research findings."
                outro="Fundamental signals work slowly, over months to years, and are best compared with industry peers and the company's own history. Studies rank many stocks against each other; a single stock's score is a weaker guide."
              />
            </Disclosure>
          </Card>
        </div>
      ) : null}
    </>
  );
}

function Summary({ text }: { text: string }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="mt-4">
      <motion.p layout transition={spring.smooth} className={`text-callout text-label-2 ${open ? "" : "line-clamp-3"}`}>
        {text}
      </motion.p>
      <button onClick={() => setOpen((o) => !o)} className="mt-1 min-h-11 cursor-pointer text-callout font-semibold text-tint">
        {open ? "Show less" : "More"}
      </button>
    </div>
  );
}

function TargetRange({ low, high, mean, price, ccy }: { low: number | null; high: number | null; mean: number | null; price: number | null; ccy: string }) {
  if (low == null || high == null || high <= low) return null;
  const pos = (v: number | null) => (v == null ? null : Math.max(0, Math.min(100, ((v - low) / (high - low)) * 100)));
  const marks = [
    { v: pos(price), label: "Price", color: "var(--label)" },
    { v: pos(mean), label: "Mean", color: SERIES[0] },
  ];
  return (
    <div className="mt-6" aria-label={`Analyst targets range from ${money(low, ccy)} to ${money(high, ccy)}`}>
      <div className="relative h-2 rounded-full bg-fill">
        {marks.map((m) =>
          m.v == null ? null : (
            <motion.span
              key={m.label}
              initial={{ left: "50%" }}
              animate={{ left: `${m.v}%` }}
              transition={spring.smooth}
              className="absolute top-1/2 size-4 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-[var(--bg-elevated)]"
              style={{ background: m.color }}
              title={m.label}
            />
          ),
        )}
      </div>
      <div className="mt-2 flex justify-between text-caption text-label-2 tabular">
        <span>Low {money(low, ccy)}</span>
        <span className="flex gap-3">
          <span className="flex items-center gap-1"><span className="size-2 rounded-full bg-label" />Price</span>
          <span className="flex items-center gap-1"><span className="size-2 rounded-full" style={{ background: SERIES[0] }} />Mean</span>
        </span>
        <span>High {money(high, ccy)}</span>
      </div>
    </div>
  );
}

function StatementTable({ data, ccy }: { data: Fundamentals["statements"]["income"]; ccy: string }) {
  if (!data.rows.length) return <p className="px-6 py-8 text-callout text-label-2">Statement data isn’t available for this company.</p>;
  return (
    <div className="mt-3 overflow-x-auto pb-1">
      <table className="w-full min-w-[560px] text-callout">
        <thead>
          <tr className="text-caption text-label-2 [&>th]:px-3 [&>th]:pb-2 [&>th]:font-medium [&>th:first-child]:pl-6 [&>th:last-child]:pr-6">
            <th className="text-left">{ccy}</th>
            {data.years.map((y) => (
              <th key={y} className="text-right">
                FY{y}
              </th>
            ))}
            <th className="text-right" title="Compound annual growth from the oldest to the latest year">
              CAGR
            </th>
          </tr>
        </thead>
        <tbody className="tabular">
          {data.rows.map((r) => (
            <tr key={r.label} className="border-t-[0.5px] border-separator [&>td]:px-3 [&>td]:py-2.5 [&>td:first-child]:pl-6 [&>td:last-child]:pr-6">
              <td className="font-medium">{r.label}</td>
              {r.values.map((v, i) => (
                <td key={i} className="text-right align-top">
                  <div className={v != null && v < 0 ? "text-negative" : ""}>{r.label.includes("EPS") ? number(v, 2) : compact(v)}</div>
                  {r.growth[i] != null && <div className="text-caption text-label-2">{pct(r.growth[i]! * 100, 0)}</div>}
                </td>
              ))}
              <td className="text-right align-top font-medium">{r.cagr == null ? "—" : pct(r.cagr * 100, 1)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const TONE = {
  good: { badge: "positive", text: "Good" },
  neutral: { badge: "neutral", text: "Fair" },
  bad: { badge: "negative", text: "Watch" },
} as const;

function metricText(m: Metric) {
  if (m.value == null) return m.note?.startsWith("n/m") ? "n/m" : "—";
  if (m.unit === "fraction") return pct(m.value * 100, 1, m.key === "share_change" || m.key === "asset_growth" || m.key === "accruals");
  if (m.unit === "x") return `${number(m.value, 1)}×`;
  return number(m.value, 2);
}

function MetricList({ metrics }: { metrics: Metric[] }) {
  return (
    <dl className="divide-y-[0.5px] divide-separator">
      {metrics.map((m) => (
        <div key={m.key} className="py-3 first:pt-0 last:pb-0">
          <div className="flex items-baseline justify-between gap-3">
            <dt className="flex items-center gap-1.5 text-callout font-medium">
              {m.label}
              {EVIDENCE_FOR[m.key] && <EvidenceDot info={FUNDAMENTALS[EVIDENCE_FOR[m.key]]} />}
            </dt>
            <dd className="flex items-center gap-2">
              <span className="text-headline tabular">{metricText(m)}</span>
              {m.tone && <Badge tone={TONE[m.tone].badge}>{TONE[m.tone].text}</Badge>}
            </dd>
          </div>
          {m.note && <dd className={`mt-0.5 text-caption ${m.value == null ? "text-label-2" : "text-warning"}`}>{m.note.replace(/^n\/m: /, "")}</dd>}
          {m.hint && m.value != null && <dd className="mt-0.5 text-caption text-label-2">{m.hint}</dd>}
        </div>
      ))}
    </dl>
  );
}

const F_STATE = {
  strong: { tone: "positive", text: "Strong" },
  middle: { tone: "neutral", text: "Middle" },
  weak: { tone: "negative", text: "Weak" },
} as const;

function QualityCard({ piotroski, metrics, financial }: { piotroski: Piotroski | null; metrics: Metric[]; financial: boolean }) {
  return (
    <Card>
      <CardHeader title="Quality" subtitle="Latest fiscal year against the one before" />
      {piotroski ? (
        <div className="mb-4 border-b-[0.5px] border-separator pb-4">
          <div className="flex items-baseline justify-between gap-3">
            <div className="flex items-center gap-1.5 text-callout font-medium">
              Piotroski F-score
              <EvidenceDot info={FUNDAMENTALS.piotroski} />
            </div>
            <div className="flex items-center gap-2">
              <span className="text-title-2 tabular">
                {piotroski.score}
                <span className="text-callout text-label-2">/{piotroski.tested}</span>
              </span>
              <Badge tone={F_STATE[piotroski.state].tone}>{F_STATE[piotroski.state].text}</Badge>
            </div>
          </div>
          <ul className="mt-3 grid gap-1.5 text-footnote">
            {piotroski.tests.map((t) => (
              <li key={t.label} className={`flex items-center gap-2 ${t.passed == null ? "text-label-2" : ""}`}>
                {t.passed == null ? (
                  <Minus className="size-3.5 shrink-0 text-label-2" aria-label="Not tested" />
                ) : t.passed ? (
                  <Check className="size-3.5 shrink-0 text-positive" aria-label="Passed" />
                ) : (
                  <X className="size-3.5 shrink-0 text-negative" aria-label="Failed" />
                )}
                {t.label}
              </li>
            ))}
          </ul>
          {piotroski.tested < 9 && <p className="mt-2 text-caption text-label-2">{9 - piotroski.tested} test(s) skipped for missing data.</p>}
        </div>
      ) : (
        <p className="mb-4 border-b-[0.5px] border-separator pb-4 text-footnote text-label-2">
          {financial ? "The F-score isn't designed for banks and insurers." : "Not enough statement history for an F-score."}
        </p>
      )}
      <MetricList metrics={metrics} />
    </Card>
  );
}

function quarterLabel(iso: string) {
  return new Date(`${iso}T00:00:00`).toLocaleDateString(undefined, { month: "short", year: "numeric" });
}

function EarningsCard({ earnings }: { earnings: EarningsRecord }) {
  const graded = earnings.surprises.filter((x) => x.surprise_pct != null);
  return (
    <Card>
      <CardHeader
        title={<TitleWithEvidence title="Earnings" info={FUNDAMENTALS.surprise} />}
        subtitle={earnings.next_date ? `Next report ${shortDate(earnings.next_date, true)}` : "Reported EPS against estimates"}
        action={graded.length > 0 && <Badge tone={earnings.beats > graded.length / 2 ? "positive" : earnings.beats < graded.length / 2 ? "negative" : "neutral"}>{earnings.beats}/{graded.length} beats</Badge>}
      />
      {earnings.surprises.length ? (
        <table className="w-full text-footnote">
          <thead>
            <tr className="text-caption text-label-2 [&>th]:pb-1.5 [&>th]:font-medium">
              <th className="text-left">Quarter</th>
              <th className="text-right">EPS</th>
              <th className="text-right">Estimate</th>
              <th className="text-right">Surprise</th>
            </tr>
          </thead>
          <tbody className="tabular">
            {earnings.surprises.map((x) => (
              <tr key={x.quarter} className="border-t-[0.5px] border-separator [&>td]:py-2">
                <td>{quarterLabel(x.quarter)}</td>
                <td className="text-right">{number(x.actual, 2)}</td>
                <td className="text-right text-label-2">{number(x.estimate, 2)}</td>
                <td className="text-right font-semibold">
                  <Delta value={x.surprise_pct}>{pct(x.surprise_pct, 1)}</Delta>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p className="text-footnote text-label-2">No earnings-surprise history for this listing.</p>
      )}

      {earnings.estimates.some((e) => e.current != null) && (
        <>
          <h4 className="mt-5 flex items-center gap-1.5 text-footnote font-semibold">
            Analyst estimate revisions
            <EvidenceDot info={FUNDAMENTALS.revisions} />
          </h4>
          <table className="mt-1.5 w-full text-footnote">
            <thead>
              <tr className="text-caption text-label-2 [&>th]:pb-1.5 [&>th]:font-medium">
                <th className="text-left">EPS for</th>
                <th className="text-right">Estimate</th>
                <th className="text-right">90 days</th>
                <th className="text-right">Up / down (30d)</th>
              </tr>
            </thead>
            <tbody className="tabular">
              {earnings.estimates
                .filter((e) => e.current != null)
                .map((e) => (
                  <tr key={e.period} className="border-t-[0.5px] border-separator [&>td]:py-2">
                    <td>{e.label}</td>
                    <td className="text-right">{number(e.current, 2)}</td>
                    <td className="text-right font-semibold">
                      <Delta value={e.change_90d}>{pct(e.change_90d, 1)}</Delta>
                    </td>
                    <td className="text-right text-label-2">
                      {e.up_30d == null ? "—" : `${number(e.up_30d, 0)} / ${number(e.down_30d, 0)}`}
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </>
      )}
    </Card>
  );
}

function TitleWithEvidence({ title, info }: { title: string; info: (typeof FUNDAMENTALS)[keyof typeof FUNDAMENTALS] }) {
  return (
    <span className="flex items-center gap-2">
      {title}
      <EvidenceDot info={info} />
    </span>
  );
}

function historyText(unit: HistoryRow["unit"], v: number | null) {
  if (v == null) return "—";
  return unit === "fraction" ? pct(v * 100, 1, false) : `${number(v, 1)}×`;
}

const VERDICT_TONE = { cheaper: "positive", better: "positive", pricier: "warning", worse: "warning", "in line": "neutral" } as const;

/** Where today's figure sits in the past range: a bar from the lowest to the highest year. */
function RangeBar({ row }: { row: HistoryRow }) {
  if (row.now == null || row.high <= row.low) return null;
  const pos = Math.max(0, Math.min(100, ((row.now - row.low) / (row.high - row.low)) * 100));
  const outside = row.now < row.low ? "below" : row.now > row.high ? "above" : null;
  return (
    <div className="relative h-1.5 w-20 rounded-full bg-fill" aria-hidden title={outside ? `Now ${outside} its past range` : undefined}>
      <span
        className={`absolute top-1/2 size-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full ${outside ? "bg-warning" : "bg-tint"}`}
        style={{ left: `${pos}%` }}
      />
    </div>
  );
}

function HistoryCard({ history }: { history: Fundamentals["history"] }) {
  const groups = [
    { title: "Valuation", rows: history.rows.filter((r) => r.valuation) },
    { title: "Profitability & balance sheet", rows: history.rows.filter((r) => !r.valuation) },
  ].filter((g) => g.rows.length);
  return (
    <Card padded={false} className="pb-5 sm:pb-6">
      <div className="px-5 pt-5 sm:px-6 sm:pt-6">
        <CardHeader
          title="Against its own history"
          subtitle="Each fiscal year-end against today. Cheap or expensive is relative to this company, not a fixed rule."
        />
      </div>
      <div className="overflow-x-auto pb-1">
        <table className="w-full min-w-[720px] text-callout">
          <thead>
            <tr className="text-caption text-label-2 [&>th]:px-3 [&>th]:pb-2 [&>th]:font-medium [&>th:first-child]:pl-5 sm:[&>th:first-child]:pl-6 [&>th:last-child]:pr-5 sm:[&>th:last-child]:pr-6">
              <th className="text-left">Measure</th>
              {history.years.map((y) => (
                <th key={y} className="text-right">FY{y}</th>
              ))}
              <th className="text-right">Now</th>
              <th className="text-left">Past range</th>
              <th className="text-right">Now vs median</th>
            </tr>
          </thead>
          {groups.map((g) => (
            <tbody key={g.title} className="tabular">
              <tr>
                <th colSpan={history.years.length + 4} className="px-5 pb-1 pt-3 text-left text-caption font-semibold uppercase tracking-wide text-label-2 sm:px-6">
                  {g.title}
                </th>
              </tr>
              {g.rows.map((r) => (
                <tr key={r.key} className="border-t-[0.5px] border-separator [&>td]:px-3 [&>td]:py-2.5 [&>td:first-child]:pl-5 sm:[&>td:first-child]:pl-6 [&>td:last-child]:pr-5 sm:[&>td:last-child]:pr-6">
                  <td className="font-medium">
                    {r.label}
                    <span className="block text-caption font-normal text-label-2">{r.better === "lower" ? "Lower is better" : "Higher is better"}</span>
                  </td>
                  {r.values.map((v, i) => (
                    <td key={i} className="text-right text-label-2">{historyText(r.unit, v)}</td>
                  ))}
                  <td className="text-right font-semibold">{historyText(r.unit, r.now)}</td>
                  <td>
                    <RangeBar row={r} />
                  </td>
                  <td className="text-right">
                    {r.verdict ? (
                      <Badge tone={VERDICT_TONE[r.verdict]}>
                        {r.verdict === "in line" ? "In line" : `${pct(r.vs_median! * 100, 0)} · ${r.verdict}`}
                      </Badge>
                    ) : (
                      <span className="text-label-2">—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          ))}
        </table>
      </div>
      <p className="mt-4 px-5 text-caption text-label-2 sm:px-6">
        Past valuations use the price at each fiscal year-end; &ldquo;Now&rdquo; uses the latest trailing 12 months. Four years is a short history, and a business
        that has changed (faster growth, a big acquisition) can deserve a different multiple. Treat a gap from the median as a prompt to ask why, not a verdict.
      </p>
    </Card>
  );
}
