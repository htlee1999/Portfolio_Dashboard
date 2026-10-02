"use client";

import { ExternalLink } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useState } from "react";

import { SERIES } from "@/components/charts/charts";
import { PageHeader, ResearchTabs } from "@/components/shell/page-header";
import { ResearchPage } from "@/components/shell/research-page";
import { SymbolPicker, useSymbol } from "@/components/shell/symbol-picker";
import { Badge, Card, CardHeader } from "@/components/ui/card";
import { Segmented } from "@/components/ui/controls";
import { Banner, LoadingBlock } from "@/components/ui/feedback";
import { Delta, Stat, StatGrid } from "@/components/ui/stat";
import { useApi } from "@/lib/api";
import { compact, money, number, pct } from "@/lib/format";
import { spring } from "@/lib/motion";
import type { Fundamentals, Ratio } from "@/lib/types";

export default function Page() {
  return (
    <ResearchPage>
      <FundamentalsView />
    </ResearchPage>
  );
}

function ratioText(r: Ratio) {
  if (r.value == null) return "—";
  if (r.unit === "fraction") return pct(r.value * 100, 1, false);
  if (r.unit === "percent") return `${number(r.value / 100, 2)}×`;
  return `${number(r.value, 2)}×`;
}

function FundamentalsView() {
  const [symbol, setSymbol] = useSymbol();
  const { data, error, isLoading, isValidating } = useApi<Fundamentals>(`/stocks/${encodeURIComponent(symbol)}/fundamentals`);
  const groups = Object.keys(data?.ratios ?? {});
  const [group, setGroup] = useState("Valuation");
  const [statement, setStatement] = useState<"income" | "balance" | "cashflow">("income");
  const ccy = data?.profile.currency ?? "USD";

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
            {data.profile.summary && <Summary text={data.profile.summary} />}
          </Card>

          <StatGrid>
            <Stat label="Price" value={money(data.headline.price, ccy)} detail={<span className="text-label-2">52w {money(data.headline.week52_low, ccy)} – {money(data.headline.week52_high, ccy)}</span>} />
            <Stat label="Market cap" value={money(data.headline.market_cap, ccy, { compact: true })} detail={<span className="text-label-2">EV {money(data.headline.enterprise_value, ccy, { compact: true })}</span>} />
            <Stat label="P/E" value={data.headline.pe ? `${number(data.headline.pe, 1)}×` : "—"} detail={<span className="text-label-2">Forward {data.headline.forward_pe ? `${number(data.headline.forward_pe, 1)}×` : "—"}</span>} />
            <Stat label="Dividend yield" value={data.analyst.dividend_yield_pct ? pct(data.analyst.dividend_yield_pct, 2, false) : "—"} detail={<span className="text-label-2">Payout {data.analyst.payout_ratio != null ? pct(data.analyst.payout_ratio * 100, 0, false) : "—"}</span>} />
          </StatGrid>

          <div className="grid gap-5 lg:grid-cols-5">
            <Card className="lg:col-span-3">
              <CardHeader title="Ratios" />
              <div className="-mx-1 mb-4 overflow-x-auto px-1">
                <Segmented size="sm" className="[&>button]:px-3.5" label="Ratio group" value={group} onChange={setGroup} options={groups.map((g) => ({ value: g, label: g }))} />
              </div>
              <AnimatePresence mode="wait">
                <motion.dl key={group} initial={{ opacity: 0, x: 8 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -8 }} transition={spring.snappy} className="grid grid-cols-2 gap-x-6 gap-y-4 sm:grid-cols-3">
                  {(data.ratios[group] ?? []).map((r) => (
                    <div key={r.label}>
                      <dt className="text-footnote text-label-2">{r.label}</dt>
                      <dd className="text-title-3 tabular">{ratioText(r)}</dd>
                    </div>
                  ))}
                </motion.dl>
              </AnimatePresence>
            </Card>

            <Card className="lg:col-span-2">
              <CardHeader
                title="Analyst view"
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

          <Card padded={false}>
            <div className="flex flex-wrap items-center justify-between gap-3 px-5 pt-5 sm:px-6 sm:pt-6">
              <h3 className="text-headline">Financial statements</h3>
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
            <StatementTable data={data.statements[statement]} ccy={ccy} />
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
    <div className="mt-3 overflow-x-auto">
      <table className="w-full min-w-[560px] text-callout">
        <thead>
          <tr className="text-caption text-label-2 [&>th]:px-3 [&>th]:pb-2 [&>th]:font-medium [&>th:first-child]:pl-6 [&>th:last-child]:pr-6">
            <th className="text-left">{ccy}</th>
            {data.years.map((y) => (
              <th key={y} className="text-right">
                FY{y}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="tabular">
          {data.rows.map((r) => (
            <tr key={r.label} className="border-t-[0.5px] border-separator [&>td]:px-3 [&>td]:py-2.5 [&>td:first-child]:pl-6 [&>td:last-child]:pr-6">
              <td className="font-medium">{r.label}</td>
              {r.values.map((v, i) => (
                <td key={i} className={`text-right ${v != null && v < 0 ? "text-negative" : ""}`}>
                  {r.label.includes("EPS") ? number(v, 2) : compact(v)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
