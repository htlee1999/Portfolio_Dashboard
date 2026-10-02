"use client";

import { History } from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";

import { SERIES, TimeSeries } from "@/components/charts/charts";
import { PageHeader } from "@/components/shell/page-header";
import { Button } from "@/components/ui/button";
import { Badge, Card, CardHeader } from "@/components/ui/card";
import { Segmented, Select } from "@/components/ui/controls";
import { Banner, EmptyState, LoadingBlock } from "@/components/ui/feedback";
import { Disclosure } from "@/components/ui/overlay";
import { Delta, Stat, StatGrid } from "@/components/ui/stat";
import { useApi } from "@/lib/api";
import { dateTime, money, pct, shortDate } from "@/lib/format";
import type { Signal } from "@/lib/types";

const REC_TONE = { BUY: "positive", SELL: "negative", HOLD: "tint" } as const;
const OUTCOME_TONE = { Correct: "positive", Wrong: "negative", Neutral: "neutral", Pending: "neutral" } as const;

export default function TrackRecordPage() {
  const { data, error, isLoading } = useApi<{ signals: Signal[]; symbols: string[] }>("/track-record");
  const [rec, setRec] = useState<"ALL" | "BUY" | "SELL" | "HOLD">("ALL");
  const [symbol, setSymbol] = useState("ALL");

  const filtered = useMemo(
    () => (data?.signals ?? []).filter((s) => (rec === "ALL" || s.recommendation === rec) && (symbol === "ALL" || s.symbol === symbol)),
    [data, rec, symbol],
  );

  const scored = filtered.filter((s) => s.outcome === "Correct" || s.outcome === "Wrong");
  const winRate = scored.length ? (scored.filter((s) => s.outcome === "Correct").length / scored.length) * 100 : null;
  const returns = filtered.map((s) => s.return_pct).filter((r): r is number => r != null);
  const avg = returns.length ? returns.reduce((a, b) => a + b, 0) / returns.length : null;

  // "$1,000 on every BUY signal", cumulative in chronological order.
  const sim = useMemo(() => {
    const buys = filtered.filter((s) => s.recommendation === "BUY" && s.return_pct != null).sort((a, b) => a.timestamp.localeCompare(b.timestamp));
    const profits = buys.map((s) => (1000 * (s.return_pct as number)) / 100);
    const points = buys.map((s, i) => {
      const profit = profits.slice(0, i + 1).reduce((a, b) => a + b, 0);
      return { date: s.timestamp.slice(0, 10), ret: (profit / (1000 * (i + 1))) * 100 };
    });
    const invested = 1000 * buys.length;
    return { points, invested, value: invested + profits.reduce((a, b) => a + b, 0) };
  }, [filtered]);

  return (
    <>
      <PageHeader title="Track Record" subtitle="How past AI recommendations have played out" />

      {error && <Banner tone="error" title="Couldn't load history">{error.message}</Banner>}

      {isLoading && !data ? (
        <LoadingBlock />
      ) : data && data.signals.length === 0 ? (
        <Card>
          <EmptyState
            icon={<History className="size-7" />}
            title="No recommendations yet"
            action={
              <Link href="/assessment">
                <Button>Run an AI Assessment</Button>
              </Link>
            }
          >
            Each AI assessment you generate is recorded here and scored against today’s price.
          </EmptyState>
        </Card>
      ) : data ? (
        <div className="space-y-5">
          <div className="flex flex-wrap items-end gap-3">
            <Segmented
              label="Signal type"
              value={rec}
              onChange={setRec}
              options={[
                { value: "ALL", label: "All" },
                { value: "BUY", label: "Buy" },
                { value: "HOLD", label: "Hold" },
                { value: "SELL", label: "Sell" },
              ]}
            />
            <Select className="w-40" aria-label="Symbol" value={symbol} onChange={(e) => setSymbol(e.target.value)} options={[{ value: "ALL", label: "All symbols" }, ...data.symbols]} />
          </div>

          <StatGrid>
            <Stat label="Signals" value={filtered.length} />
            <Stat label="Win rate" value={winRate != null ? pct(winRate, 0, false) : "—"} detail={<span className="text-label-2">{scored.length} scored BUY/SELL</span>} />
            <Stat label="Avg return" value={<Delta value={avg}>{pct(avg, 1)}</Delta>} detail={<span className="text-label-2">per signal</span>} />
            <Stat
              label="Best / worst"
              value={returns.length ? <span className="flex flex-wrap items-baseline gap-x-1 text-headline sm:text-title-3"><Delta value={Math.max(...returns)}>{pct(Math.max(...returns), 0)}</Delta> <span className="text-label-3">/</span> <Delta value={Math.min(...returns)}>{pct(Math.min(...returns), 0)}</Delta></span> : "—"}
            />
          </StatGrid>

          <Card>
            <CardHeader title="What if you followed every BUY?" subtitle="$1,000 invested at each BUY signal, valued at today’s price" />
            {sim.points.length ? (
              <>
                <div className="mb-4 flex flex-wrap gap-x-8 gap-y-2">
                  <Stat label="Invested" value={money(sim.invested, "USD", { compact: true })} />
                  <Stat label="Worth now" value={money(sim.value, "USD")} />
                  <Stat label="Return" value={<Delta value={sim.value - sim.invested}>{pct(((sim.value - sim.invested) / sim.invested) * 100)}</Delta>} />
                </div>
                {sim.points.length > 1 && (
                  <TimeSeries data={sim.points} height={220} refLines={[{ y: 0 }]} lines={[{ key: "ret", label: "Cumulative return", color: SERIES[0], area: true }]} format={(v) => pct(v, 0)} ariaLabel="Cumulative return from following BUY signals" />
                )}
              </>
            ) : (
              <p className="text-callout text-label-2">No BUY signals in this filter.</p>
            )}
          </Card>

          <Card>
            <CardHeader title="Signals" subtitle="Newest first" />
            {filtered.map((s) => (
              <Disclosure
                key={s.id}
                title={
                  <span className="flex items-center gap-2">
                    {s.symbol}
                    <Badge tone={REC_TONE[s.recommendation]}>{s.recommendation}</Badge>
                  </span>
                }
                subtitle={`${shortDate(s.timestamp, true)} · confidence ${s.confidence ?? "—"}/10`}
                trailing={
                  <span className="flex flex-col items-end gap-0.5">
                    <Delta value={s.return_pct} className="text-callout">{pct(s.return_pct, 1)}</Delta>
                    <Badge tone={OUTCOME_TONE[s.outcome]}>{s.outcome}</Badge>
                  </span>
                }
              >
                <div className="space-y-4 text-callout">
                  <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                    <Field k="At signal" v={money(s.price_at_signal)} />
                    <Field k="Now" v={money(s.current_price)} />
                    <Field k="Target" v={s.price_target ? money(s.price_target) : "—"} />
                    <Field k="Horizon" v={s.time_horizon ?? "—"} />
                  </dl>
                  {s.portfolio_context && (
                    <p className="text-footnote text-label-2">
                      Held {s.portfolio_context.total_quantity} shares at {money(s.portfolio_context.avg_purchase_price)} ({pct(s.portfolio_context.unrealized_pct, 1)} unrealized) when generated · {dateTime(s.timestamp)}
                    </p>
                  )}
                  {s.position_advice && <p>{s.position_advice}</p>}
                  {(s.strengths.length > 0 || s.risks.length > 0) && (
                    <div className="grid gap-4 sm:grid-cols-2">
                      <List title="Strengths" items={s.strengths} />
                      <List title="Risks" items={s.risks} />
                    </div>
                  )}
                  {s.reasoning && (
                    <div>
                      <div className="mb-1 font-semibold">Reasoning</div>
                      <p className="line-clamp-[12] whitespace-pre-line text-label-2">{s.reasoning}</p>
                    </div>
                  )}
                </div>
              </Disclosure>
            ))}
            {filtered.length === 0 && <p className="py-4 text-callout text-label-2">No signals match these filters.</p>}
          </Card>
        </div>
      ) : null}
    </>
  );
}

function Field({ k, v }: { k: string; v: string }) {
  return (
    <div>
      <dt className="text-caption text-label-2">{k}</dt>
      <dd className="font-medium tabular">{v}</dd>
    </div>
  );
}

function List({ title, items }: { title: string; items: string[] }) {
  if (!items.length) return null;
  return (
    <div>
      <div className="mb-1 font-semibold">{title}</div>
      <ul className="list-disc space-y-1 pl-5 text-label-2">
        {items.map((i) => (
          <li key={i}>{i}</li>
        ))}
      </ul>
    </div>
  );
}
