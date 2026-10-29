"use client";

import { Card, CardHeader } from "@/components/ui/card";
import { Banner, Skeleton } from "@/components/ui/feedback";
import { useApi } from "@/lib/api";
import { compact, number, pct } from "@/lib/format";
import type { PeerRow, Valuation } from "@/lib/types";

function show(unit: PeerRow["unit"], v: number | null) {
  if (v == null) return "—";
  return unit === "fraction" ? pct(v * 100, 1, false) : `${number(v, 1)}×`;
}

/** The company against its industry peers, and the growth today's price assumes. */
export function ValuationCard({ symbol }: { symbol: string }) {
  const { data, error, isLoading } = useApi<Valuation>(`/stocks/${encodeURIComponent(symbol)}/valuation`);

  if (error) return <Banner tone="warning" title="Couldn't load peers and the reverse DCF">{error.message}</Banner>;
  if (isLoading && !data) {
    return (
      <Card>
        <Skeleton className="h-40" />
      </Card>
    );
  }
  if (!data) return null;
  const { peers, anchor: a } = data;
  const h = a.history;
  // Revenue growth is the steadier yardstick; free cash flow swings with investment cycles.
  const past = h.revenue_cagr ?? h.fcf_cagr;
  const pastLabel = h.revenue_cagr != null ? "revenue" : "free cash flow";
  const stretch = a.implied_growth != null && past != null ? a.implied_growth - past : null;

  return (
    <div className="grid items-start gap-5 lg:grid-cols-5">
      <Card padded={false} className="lg:col-span-3">
        <div className="px-5 pt-5 sm:px-6 sm:pt-6">
          <CardHeader
            title="Against its peers"
            subtitle={
              peers.peers.length
                ? `${peers.peers.length} companies in ${peers.industry ?? "its industry"}${peers.source === "portfolio" ? " that you hold or watch" : ""}: ${peers.peers.map((p) => p.symbol).join(", ")}`
                : "No peers found. Finnhub lists peers for US listings; add same-industry stocks to your watchlist to compare against those."
            }
          />
        </div>
        {peers.peers.length > 0 && (
          <table className="w-full text-callout tabular">
            <thead>
              <tr className="text-left text-caption text-label-2 [&>th]:px-3 [&>th]:pb-2 [&>th]:font-medium [&>th:first-child]:pl-6 [&>th:last-child]:pr-6">
                <th>Measure</th>
                <th className="text-right">{symbol}</th>
                <th className="text-right">Peer median</th>
                <th className="w-36">Beats peers</th>
              </tr>
            </thead>
            <tbody>
              {peers.rows.filter((r) => r.value != null || r.median != null).map((r) => (
                <tr key={r.key} className="border-t-[0.5px] border-separator [&>td]:px-3 [&>td]:py-2 [&>td:first-child]:pl-6 [&>td:last-child]:pr-6">
                  <td>
                    {r.label}
                    <span className="ml-1.5 text-caption text-label-2">{r.better === "lower" ? "lower is cheaper" : "higher is better"}</span>
                  </td>
                  <td className="text-right font-semibold">{show(r.unit, r.value)}</td>
                  <td className="text-right text-label-2">{show(r.unit, r.median)}</td>
                  <td>
                    {r.rank != null ? (
                      <div className="flex items-center gap-2" title={`Better than ${number(r.rank, 0)}% of ${r.n} peers`}>
                        <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-fill-2">
                          <div className="h-full rounded-full bg-[var(--series-1)]" style={{ width: `${Math.max(2, r.rank)}%` }} />
                        </div>
                        <span className="w-9 text-right text-caption text-label-2">{number(r.rank, 0)}%</span>
                      </div>
                    ) : (
                      <span className="text-caption text-label-3">—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <p className="px-6 pt-3 pb-5 text-footnote text-label-2">
          Beats peers is the share of peers this company is cheaper than, or more profitable or faster growing than. Negative multiples are left out, and so are
          sales and EBITDA multiples where Yahoo mixes currencies.
        </p>
      </Card>

      <Card className="lg:col-span-2">
        <CardHeader title="What the price assumes" subtitle="Reverse DCF: the cash-flow growth that would justify today's enterprise value" />
        {a.implied_growth != null ? (
          <>
            <div className="text-title-2 tabular">{pct(a.implied_growth, 1)} a year</div>
            <p className="mt-1 text-footnote text-label-2">
              Free cash flow growth for five years, fading to {number(a.terminal_growth, 1)}% by year ten, discounted at {number(a.discount_rate, 1)}% ({number(a.discount_inputs.risk_free, 2)}% Treasury + beta{" "}
              {number(a.discount_inputs.beta, 2)} × {number(a.discount_inputs.premium, 0)}%{a.discount_inputs.clamped ? ", capped at 6–14%" : ""}). Starting from {compact(a.fcf)} {a.currency} of free cash flow.
            </p>
            <dl className="mt-4 space-y-1.5 border-t-[0.5px] border-separator pt-3 text-footnote tabular">
              <Row k="Revenue growth, past years" v={h.revenue_cagr != null ? `${pct(h.revenue_cagr, 1)} a year` : "—"} />
              <Row k="Free cash flow growth, past years" v={h.fcf_cagr != null ? `${pct(h.fcf_cagr, 1)} a year` : "—"} />
              <Row k="Analysts' EPS growth, next year" v={h.eps_growth_next_year != null ? pct(h.eps_growth_next_year, 1) : "—"} />
              {a.sensitivity.length === 3 && (
                <Row
                  k="At a discount rate 1 point lower / higher"
                  v={`${pct(a.sensitivity[0].growth, 1)} / ${pct(a.sensitivity[2].growth, 1)}`}
                />
              )}
            </dl>
            {stretch != null && (
              <p className="mt-3 text-callout">
                {stretch > 5
                  ? `The price needs faster growth than the company has delivered: ${number(stretch, 0)} points a year above its past ${pastLabel} growth.`
                  : stretch < -5
                    ? `The price asks for slower growth than the company's past ${pastLabel} growth, so some slowdown is already assumed.`
                    : `The price asks for about the ${pastLabel} growth the company has delivered.`}
              </p>
            )}
          </>
        ) : (
          <p className="text-callout text-label-2">{a.note}</p>
        )}

        <h4 className="mt-5 mb-2 text-footnote font-semibold text-label-2">Yields against the 10-year Treasury ({number(a.yields.treasury_10y, 2)}%)</h4>
        <dl className="space-y-1.5 text-footnote tabular">
          <Row k="Earnings yield (forward)" v={a.yields.forward_earnings != null ? `${number(a.yields.forward_earnings, 1)}%` : a.yields.earnings != null ? `${number(a.yields.earnings, 1)}% (trailing)` : "—"} />
          <Row k="Free cash flow yield (cash flow statement)" v={a.yields.fcf != null ? `${number(a.yields.fcf, 1)}%` : "—"} />
          <Row k="Shareholder yield (dividends + net buybacks)" v={a.yields.shareholder != null ? `${number(a.yields.shareholder, 1)}%` : "—"} />
        </dl>
        {a.yield_gap != null && (
          <p className="mt-3 text-footnote text-label-2">
            Earnings yield is {number(Math.abs(a.yield_gap), 1)} points {a.yield_gap >= 0 ? "above" : "below"} the Treasury yield
            {a.yield_gap < 0 ? ": you're paying for growth, since bonds pay more today." : "."}
          </p>
        )}
      </Card>
    </div>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex justify-between gap-3">
      <dt className="text-label-2">{k}</dt>
      <dd className="font-semibold">{v}</dd>
    </div>
  );
}
