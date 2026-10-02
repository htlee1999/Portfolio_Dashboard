"use client";

import { Plus, X } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useMemo, useState } from "react";

import { Donut, MUTED, SERIES, TimeSeries, type LineSpec } from "@/components/charts/charts";
import { CurrencyMenu } from "@/components/shell/currency-menu";
import { PageHeader } from "@/components/shell/page-header";
import { Card, CardHeader } from "@/components/ui/card";
import { Segmented } from "@/components/ui/controls";
import { Banner, LoadingBlock } from "@/components/ui/feedback";
import { Delta, Stat, StatGrid } from "@/components/ui/stat";
import { useApi } from "@/lib/api";
import { PERIODS, money, number, pct } from "@/lib/format";
import { spring } from "@/lib/motion";
import { useSession } from "@/lib/session";
import type { Performance } from "@/lib/types";

const MAX_PINNED = 6;

export default function PerformancePage() {
  const { baseCurrency } = useSession();
  const [period, setPeriod] = useState<string>("1y");
  const { data, error, isLoading, isValidating } = useApi<Performance>(`/portfolio/performance?base=${baseCurrency}&period=${period}`);
  // Pinned symbols keep the color slot they were given, so adding or removing one never repaints the others.
  const [pinned, setPinned] = useState<{ symbol: string; slot: number }[]>([]);

  const holdings = useMemo(() => (data?.series_keys ?? []).filter((k) => k !== "Portfolio" && k !== "S&P 500"), [data]);

  const togglePin = (symbol: string) =>
    setPinned((cur) => {
      if (cur.some((p) => p.symbol === symbol)) return cur.filter((p) => p.symbol !== symbol);
      if (cur.length >= MAX_PINNED) return cur;
      const used = new Set(cur.map((p) => p.slot));
      const slot = [1, 2, 3, 4, 5, 6, 7].find((s) => !used.has(s))!;
      return [...cur, { symbol, slot }];
    });

  const lines: LineSpec[] = [
    { key: "Portfolio", label: "Portfolio", color: SERIES[0], width: 2.5 },
    { key: "S&P 500", label: "S&P 500", color: MUTED, dashed: true },
    ...pinned.map((p) => ({ key: p.symbol, label: p.symbol, color: SERIES[p.slot] })),
  ];

  const last = data?.series.at(-1);
  const portfolioReturn = last?.Portfolio != null ? Number(last.Portfolio) - 100 : null;
  const benchReturn = last?.["S&P 500"] != null ? Number(last["S&P 500"]) - 100 : null;
  const sectorColors = data?.sectors.map((s, i) => ({ label: s.sector, value: s.value, color: i < 7 ? SERIES[i] : MUTED })) ?? [];

  return (
    <>
      <PageHeader
        title="Performance"
        subtitle="How your current allocation has performed against the market"
        actions={
          <>
            <Segmented label="Period" options={PERIODS} value={period} onChange={setPeriod} />
            <CurrencyMenu />
          </>
        }
      />

      {error && <Banner tone="error" title="Couldn't load performance">{error.message}</Banner>}

      {isLoading && !data ? (
        <LoadingBlock label="Fetching price history…" />
      ) : data ? (
        <div className={`space-y-5 transition-opacity ${isValidating ? "opacity-60" : ""}`}>
          <StatGrid>
            <Stat label="Portfolio" value={<Delta value={portfolioReturn}>{pct(portfolioReturn)}</Delta>} detail={<span className="text-label-2">over {PERIODS.find((p) => p.value === period)?.label}</span>} />
            <Stat label="S&P 500" value={<Delta value={benchReturn}>{pct(benchReturn)}</Delta>} detail={<span className="text-label-2">benchmark</span>} />
            <Stat
              label="Relative"
              value={<Delta value={portfolioReturn != null && benchReturn != null ? portfolioReturn - benchReturn : null}>{portfolioReturn != null && benchReturn != null ? `${pct(portfolioReturn - benchReturn)}` : "—"}</Delta>}
              detail={<span className="text-label-2">vs benchmark</span>}
            />
            <Stat label="Unrealized" value={money(data.summary.total_gain, baseCurrency, { compact: true, sign: true })} detail={<span className="text-label-2">{pct(data.summary.total_gain_pct)} all time</span>} />
          </StatGrid>

          <Card>
            <CardHeader title="Growth of 100" subtitle="Current weights held constant over the period · rebased to 100" />
            <TimeSeries data={data.series} lines={lines} height={320} format={(v) => number(v, 0)} refLines={[{ y: 100 }]} ariaLabel="Portfolio and benchmark performance rebased to 100" />
            <div className="mt-5 border-t-[0.5px] border-separator pt-4">
              <div className="mb-2 text-footnote text-label-2">
                Compare holdings <span className="text-label-3">· up to {MAX_PINNED}</span>
              </div>
              <div className="flex flex-wrap gap-2">
                {holdings.map((s) => {
                  const pin = pinned.find((p) => p.symbol === s);
                  const full = !pin && pinned.length >= MAX_PINNED;
                  return (
                    <motion.button
                      key={s}
                      layout
                      whileTap={{ scale: 0.94 }}
                      transition={spring.snappy}
                      onClick={() => togglePin(s)}
                      disabled={full}
                      aria-pressed={!!pin}
                      className={`relative flex h-9 cursor-pointer items-center gap-1.5 rounded-full px-3.5 text-footnote font-semibold transition-colors before:absolute before:-inset-y-1 before:inset-x-0 disabled:cursor-default disabled:opacity-35 ${pin ? "bg-fill-strong" : "bg-fill-2 hover:bg-fill"}`}
                    >
                      <AnimatePresence initial={false}>
                        {pin && (
                          <motion.span initial={{ scale: 0 }} animate={{ scale: 1 }} exit={{ scale: 0 }} transition={spring.bouncy} className="size-2.5 rounded-full" style={{ background: SERIES[pin.slot] }} />
                        )}
                      </AnimatePresence>
                      {s}
                      {pin ? <X className="size-3.5 text-label-2" /> : <Plus className="size-3.5 text-label-2" />}
                    </motion.button>
                  );
                })}
              </div>
            </div>
          </Card>

          <div className="grid items-start gap-5 lg:grid-cols-2">
            <Card>
              <CardHeader title="Sectors" subtitle={`By current value in ${baseCurrency}`} />
              <Donut data={sectorColors} format={(v) => money(v, baseCurrency)} ariaLabel="Portfolio by sector" size={180} />
            </Card>

            <Card padded={false}>
              <div className="px-5 pt-5 sm:px-6 sm:pt-6">
                <CardHeader title="Risk" subtitle="Trailing 12 months of daily returns" />
              </div>
              <table className="w-full text-callout">
                <thead>
                  <tr className="text-left text-caption text-label-2 [&>th]:px-3 [&>th]:pb-2 [&>th]:font-medium [&>th:first-child]:pl-6 [&>th:last-child]:pr-6">
                    <th>Symbol</th>
                    <th className="text-right">Volatility (ann.)</th>
                    <th className="text-right">Avg daily return</th>
                  </tr>
                </thead>
                <tbody className="tabular">
                  {[...data.risk]
                    .sort((a, b) => b.volatility - a.volatility)
                    .map((r) => (
                      <tr key={r.symbol} className="border-t-[0.5px] border-separator [&>td]:px-3 [&>td]:py-2.5 [&>td:first-child]:pl-6 [&>td:last-child]:pr-6">
                        <td className="font-semibold">{r.symbol}</td>
                        <td className="text-right">
                          <div className="flex items-center justify-end gap-2">
                            <span className="hidden h-1.5 w-20 overflow-hidden rounded-full bg-fill-2 sm:block">
                              <span className="block h-full rounded-full bg-[var(--series-1)]" style={{ width: `${Math.min(100, r.volatility)}%` }} />
                            </span>
                            {number(r.volatility, 1)}%
                          </div>
                        </td>
                        <td className="text-right">
                          <Delta value={r.avg_daily_return}>{pct(r.avg_daily_return, 3)}</Delta>
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </Card>
          </div>
        </div>
      ) : null}
    </>
  );
}
