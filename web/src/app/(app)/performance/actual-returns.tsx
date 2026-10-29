"use client";

import { useState } from "react";

import { HBars, MUTED, SERIES, TimeSeries, type LineSpec } from "@/components/charts/charts";
import { Card, CardHeader } from "@/components/ui/card";
import { Segmented } from "@/components/ui/controls";
import { Banner, LoadingBlock } from "@/components/ui/feedback";
import { Delta, Stat, StatGrid } from "@/components/ui/stat";
import { useApi } from "@/lib/api";
import { money, number, pct, shortDate } from "@/lib/format";
import type { Returns } from "@/lib/types";

type Live = Extract<Returns, { empty: false }>;

/** What your money actually did: purchases, sales and dividends, against the same trades made in the S&P 500. */
export function ActualReturns({ base }: { base: string }) {
  const { data, error, isLoading } = useApi<Returns>(`/portfolio/returns?base=${base}`);
  const [view, setView] = useState<"value" | "return">("value");

  if (error) return <Banner tone="error" title="Couldn't rebuild your returns">{error.message}</Banner>;
  if (isLoading && !data) return <Card><LoadingBlock label="Rebuilding your returns from every purchase, sale and dividend…" /></Card>;
  if (!data || data.empty) return null;
  const d = data as Live;
  const s = d.summary;
  const fmt = (v: number) => money(v, base, { compact: true });

  const lines: LineSpec[] =
    view === "value"
      ? [
          { key: "with_income", label: "Your holdings + dividends received", color: SERIES[0], width: 2.5 },
          { key: "benchmark_value", label: "Same trades in the S&P 500", color: MUTED, dashed: true },
          { key: "net_invested", label: "Net money put in", color: SERIES[3] },
        ]
      : [
          { key: "twr", label: "You (time-weighted)", color: SERIES[0], width: 2.5 },
          { key: "benchmark_twr", label: "S&P 500 (SPY, dividends reinvested)", color: MUTED, dashed: true },
        ];

  return (
    <div className="space-y-5">
      <div className="px-1">
        <h2 className="text-title-3">Actual returns</h2>
        <p className="mt-0.5 text-footnote text-label-2">
          Since your first purchase on {shortDate(d.start, true)}, from every purchase, sale and dividend · in {base}
        </p>
      </div>

      <StatGrid>
        <Stat
          label="Money-weighted (IRR)"
          value={<Delta value={s.irr_pct}>{pct(s.irr_pct, 1)}</Delta>}
          detail={<span className="text-label-2">a year · S&P 500 on the same trades {pct(s.benchmark_irr_pct, 1)}</span>}
        />
        <Stat
          label="Time-weighted"
          value={<Delta value={s.twr_pct}>{pct(s.twr_pct, 1)}</Delta>}
          detail={<span className="text-label-2">{s.twr_annual_pct != null ? `${pct(s.twr_annual_pct, 1)} a year · ` : ""}S&P 500 {pct(s.benchmark_twr_pct, 1)}</span>}
        />
        <Stat
          label="Vs the same trades in SPY"
          value={<Delta value={s.value_added}>{money(s.value_added, base, { compact: true, sign: true })}</Delta>}
          detail={<span className="text-label-2">what your picks and timing added</span>}
        />
        <Stat
          label="Total gain"
          value={<Delta value={s.total_gain}>{money(s.total_gain, base, { compact: true, sign: true })}</Delta>}
          detail={
            <span className="text-label-2">
              {money(s.unrealized, base, { compact: true })} unrealized · {money(s.realized, base, { compact: true })} realized · {money(s.dividends, base, { compact: true })} dividends
            </span>
          }
        />
      </StatGrid>

      {d.missing.length > 0 && (
        <Banner tone="warning" title={`No price history for ${d.missing.join(", ")}`}>These are left out of the daily values until Yahoo Finance returns their history.</Banner>
      )}

      <Card>
        <CardHeader
          title={view === "value" ? "Your money vs the same trades in the S&P 500" : "Time-weighted return"}
          subtitle={
            view === "value"
              ? "Each purchase also bought SPY on the same day, and each sale sold the same amount of it"
              : "Each day's return chained together, so when and how much you invested doesn't count"
          }
          action={<Segmented size="sm" label="Chart" value={view} onChange={setView} options={[{ value: "value", label: "Value" }, { value: "return", label: "Return" }]} />}
        />
        <TimeSeries
          data={d.series}
          lines={lines}
          height={300}
          format={view === "value" ? fmt : (v) => `${number(v, 0)}%`}
          refLines={view === "return" ? [{ y: 0 }] : []}
          ariaLabel="Actual portfolio value against the same trades in the S&P 500"
        />
      </Card>

      <div className="grid items-start gap-5 lg:grid-cols-2">
        <Card>
          <CardHeader title="Dividends received" subtitle={`${money(s.dividends, base)} in all · ${money(s.dividends_ttm, base)} in the last 12 months · before withholding tax`} />
          {d.dividends.by_symbol.length ? (
            <HBars data={d.dividends.by_symbol} labelKey="symbol" valueKey="amount" format={(v) => money(v, base)} ariaLabel="Dividends received by holding" />
          ) : (
            <p className="text-callout text-label-2">None of your holdings has paid a dividend while you held it.</p>
          )}
          {d.dividends.by_year.length > 1 && (
            <div className="mt-4 flex flex-wrap gap-x-5 gap-y-1 border-t-[0.5px] border-separator pt-3 text-footnote text-label-2 tabular">
              {d.dividends.by_year.map((y) => (
                <span key={y.year}>
                  {y.year} <span className="font-semibold text-label">{money(y.amount, base)}</span>
                </span>
              ))}
            </div>
          )}
        </Card>

        <Card padded={false}>
          <div className="px-5 pt-5 sm:px-6 sm:pt-6">
            <CardHeader title="Realized gains" subtitle="From sales recorded on Holdings, oldest lots first" />
          </div>
          {d.realized.length ? (
            <table className="w-full text-callout tabular">
              <thead>
                <tr className="text-left text-caption text-label-2 [&>th]:px-3 [&>th]:pb-2 [&>th]:font-medium [&>th:first-child]:pl-6 [&>th:last-child]:pr-6">
                  <th>Sale</th>
                  <th className="text-right">Proceeds</th>
                  <th className="text-right">Gain</th>
                  <th className="text-right">In {base}</th>
                </tr>
              </thead>
              <tbody>
                {d.realized.map((r) => (
                  <tr key={r.id} className="border-t-[0.5px] border-separator [&>td]:px-3 [&>td]:py-2.5 [&>td:first-child]:pl-6 [&>td:last-child]:pr-6">
                    <td>
                      <div className="font-semibold">{r.symbol}</div>
                      <div className="text-caption text-label-2">
                        {shortDate(r.date, true)}
                        {r.held_days != null && ` · held ${r.held_days >= 365 ? `${number(r.held_days / 365, 1)} yr` : `${r.held_days} d`}`}
                      </div>
                    </td>
                    <td className="text-right">{money(r.proceeds, r.currency)}</td>
                    <td className="text-right">
                      <Delta value={r.gain}>{r.gain_pct != null ? pct(r.gain_pct, 1) : money(r.gain, r.currency)}</Delta>
                    </td>
                    <td className="text-right">
                      <Delta value={r.gain_base}>{money(r.gain_base, base, { sign: true })}</Delta>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="px-6 pb-6 text-callout text-label-2">No sales yet. Record one on Holdings when you sell, so realized gains and these returns stay accurate.</p>
          )}
        </Card>
      </div>
    </div>
  );
}
