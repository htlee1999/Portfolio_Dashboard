"use client";

import { History } from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";

import { MUTED, SERIES, TimeSeries } from "@/components/charts/charts";
import { PageHeader } from "@/components/shell/page-header";
import { PageGuide } from "@/components/shell/page-guide";
import { Button } from "@/components/ui/button";
import { Badge, Card, CardHeader } from "@/components/ui/card";
import { Segmented, Select } from "@/components/ui/controls";
import { Banner, EmptyState, LoadingBlock } from "@/components/ui/feedback";
import { Disclosure } from "@/components/ui/overlay";
import { Delta, Stat, StatGrid } from "@/components/ui/stat";
import { useApi } from "@/lib/api";
import { dateTime, money, pct, shortDate } from "@/lib/format";
import { ScheduledCard } from "./scheduled-card";
import type { Calibration, ModelComparison, RuleComparison, Signal, TrackRecord } from "@/lib/types";

const REC_TONE = { BUY: "positive", SELL: "negative", HOLD: "tint" } as const;
const OUTCOME_TONE = { Correct: "positive", Wrong: "negative", Flat: "neutral", Neutral: "neutral", Pending: "neutral" } as const;

const HORIZONS = [
  { value: "5", label: "1W" },
  { value: "21", label: "1M" },
  { value: "63", label: "3M" },
  { value: "126", label: "6M" },
  { value: "252", label: "1Y" },
  { value: "stated", label: "Stated" },
];
const HORIZON_TEXT: Record<string, string> = { "5": "1 week", "21": "1 month", "63": "3 months", "126": "6 months", "252": "1 year", stated: "each call’s stated horizon" };

// Below this many scored calls a win rate is mostly noise.
const MIN_SCORED = 30;

/** 95% Wilson interval for a win rate, in percent. */
function wilson(wins: number, n: number): [number, number] | null {
  if (!n) return null;
  const z = 1.96;
  const p = wins / n;
  const centre = (p + (z * z) / (2 * n)) / (1 + (z * z) / n);
  const half = (z * Math.sqrt((p * (1 - p)) / n + (z * z) / (4 * n * n))) / (1 + (z * z) / n);
  return [Math.max(0, centre - half) * 100, Math.min(1, centre + half) * 100];
}

/** $1,000 into each BUY at its entry close, held to today, against the same money in the S&P 500 on the same days. */
function followBuys(signals: Signal[]) {
  const paths = signals.filter((s) => s.recommendation === "BUY" && s.path?.length).map((s) => s.path!);
  const dates = [...new Set(paths.flatMap((p) => p.map((r) => r[0])))].sort();
  const at = paths.map(() => -1);
  return dates.map((date) => {
    let invested = 0, value = 0, bench = 0;
    paths.forEach((p, k) => {
      while (at[k] + 1 < p.length && p[at[k] + 1][0] <= date) at[k]++;
      if (at[k] < 0) return;
      invested += 1000;
      value += 1000 * p[at[k]][1];
      bench += 1000 * p[at[k]][2];
    });
    return { date, invested, value, bench, ret: (value / invested - 1) * 100, benchRet: (bench / invested - 1) * 100 };
  });
}

/** Your position at the call, sold at the entry close vs held to today. Dividends and tax are left out. */
function soldVsHeld(s: Signal) {
  if (!s.portfolio_context || s.entry_price == null || s.return_pct == null) return null;
  const shares = s.portfolio_context.total_quantity * s.split_factor;
  const sold = shares * s.entry_price;
  const held = sold * (1 + s.return_pct / 100);
  // Following a SELL means selling; following a BUY or HOLD means keeping the shares.
  return { shares, sold, held, following: s.recommendation === "SELL" ? sold - held : held - sold };
}

function stats(signals: Signal[]) {
  const directional = signals.filter((s) => s.recommendation !== "HOLD" && s.score_return != null);
  const wins = directional.filter((s) => s.outcome === "Correct").length;
  const losses = directional.filter((s) => s.outcome === "Wrong").length;
  const returns = directional.map((s) => s.score_return as number);
  return {
    wins,
    scored: wins + losses,
    flat: directional.length - wins - losses,
    winRate: wins + losses ? (wins / (wins + losses)) * 100 : null,
    avg: returns.length ? returns.reduce((a, b) => a + b, 0) / returns.length : null,
    returns,
  };
}

export default function TrackRecordPage() {
  const [horizon, setHorizon] = useState("21");
  const { data, error, isLoading, isValidating, mutate } = useApi<TrackRecord>(`/track-record?horizon=${horizon}`);
  const [rec, setRec] = useState<"ALL" | "BUY" | "SELL" | "HOLD">("ALL");
  const [symbol, setSymbol] = useState("ALL");
  const [version, setVersion] = useState("ALL");
  const [source, setSource] = useState("ALL");
  const [model, setModel] = useState("ALL");
  const versions = [...new Set((data?.signals ?? []).map((s) => s.prompt_version))].sort((a, b) => a - b);

  const filtered = useMemo(
    () =>
      (data?.signals ?? []).filter(
        (s) => (rec === "ALL" || s.recommendation === rec) && (symbol === "ALL" || s.symbol === symbol) && (version === "ALL" || String(s.prompt_version) === version) &&
          (source === "ALL" || s.source === source) &&
          (model === "ALL" || s.model === model),
      ),
    [data, rec, symbol, version, source, model],
  );

  const st = stats(filtered);
  const range = wilson(st.wins, st.scored);
  const pending = filtered.filter((s) => s.recommendation !== "HOLD" && s.outcome === "Pending").length;
  const targets = filtered.filter((s) => s.target);
  const targetsHit = targets.filter((s) => s.target!.hit === true).length;
  const targetsMissed = targets.filter((s) => s.target!.hit === false).length;
  const curve = useMemo(() => followBuys(filtered), [filtered]);
  const positions = filtered.flatMap((s) => {
    const p = soldVsHeld(s);
    return p ? [{ s, ...p }] : [];
  });
  const end = curve.at(-1);

  const bySymbol = useMemo(() => {
    const rows = (data?.signals ?? []).filter((s) => rec === "ALL" || s.recommendation === rec);
    return [...new Set(rows.map((s) => s.symbol))]
      .map((sym) => ({ symbol: sym, calls: rows.filter((s) => s.symbol === sym).length, ...stats(rows.filter((s) => s.symbol === sym)) }))
      .sort((a, b) => b.calls - a.calls);
  }, [data, rec]);

  return (
    <>
      <PageHeader
        title="Track Record"
        subtitle="How past AI recommendations did against the S&P 500"
        actions={<Segmented label="Score at" options={HORIZONS} value={horizon} onChange={setHorizon} />}
      />
      <PageGuide page="trackRecord" />

      {error && <Banner tone="error" title="Couldn't load history">{error.message}</Banner>}

      {isLoading && !data ? (
        <LoadingBlock label="Fetching price history…" />
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
            Each AI assessment you generate is recorded here and scored against the S&P 500 once enough time has passed.
          </EmptyState>
        </Card>
      ) : data ? (
        <div className={`space-y-5 transition-opacity ${isValidating ? "opacity-60" : ""}`}>
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
            <Select
              className="w-40"
              aria-label="Source"
              value={source}
              onChange={(e) => setSource(e.target.value)}
              options={[
                { value: "ALL", label: "All sources" },
                { value: "manual", label: "Run by you" },
                { value: "scheduled", label: "Scheduled" },
              ]}
            />
            {data.models.models.length > 1 && (
              <Select
                className="w-48"
                aria-label="Model"
                value={model}
                onChange={(e) => setModel(e.target.value)}
                options={[{ value: "ALL", label: "All models" }, ...data.models.models]}
              />
            )}
            {versions.length > 1 && (
              <Select
                className="w-40"
                aria-label="Prompt version"
                value={version}
                onChange={(e) => setVersion(e.target.value)}
                options={[{ value: "ALL", label: "All prompt versions" }, ...versions.map((v) => ({ value: String(v), label: `Prompt v${v}` }))]}
              />
            )}
          </div>

          {!data.benchmark_available && (
            <Banner tone="warning" title="Price history unavailable">
              Couldn’t load S&P 500 history, so no call can be scored right now. Try again in a few minutes.
            </Banner>
          )}
          {data.benchmark_available && st.scored < MIN_SCORED && (
            <Banner tone="info" title={`${st.scored} scored call${st.scored === 1 ? "" : "s"} at ${HORIZON_TEXT[horizon]}`}>
              Too few to judge: treat these numbers as anecdotes until there are at least {MIN_SCORED}.
              {pending > 0 && ` ${pending} more BUY/SELL call${pending === 1 ? " is" : "s are"} waiting for ${HORIZON_TEXT[horizon]} to pass.`}
            </Banner>
          )}

          <StatGrid>
            <Stat label="Signals" value={filtered.length} detail={<span className="text-label-2">{pending} pending</span>} />
            <Stat
              label="Win rate"
              value={st.winRate != null ? pct(st.winRate, 0, false) : "—"}
              detail={
                <span className="text-label-2">
                  {st.scored} scored{st.flat > 0 && `, ${st.flat} flat`}
                  {range && ` · likely ${pct(range[0], 0, false)}–${pct(range[1], 0, false)}`}
                </span>
              }
            />
            <Stat
              label="Avg vs S&P 500"
              value={<Delta value={st.avg}>{pct(st.avg, 1)}</Delta>}
              detail={
                <span className="text-label-2">
                  {st.returns.length ? `best ${pct(Math.max(...st.returns), 0)} · worst ${pct(Math.min(...st.returns), 0)}` : `per BUY/SELL at ${HORIZONS.find((h) => h.value === horizon)?.label}`}
                </span>
              }
            />
            <Stat
              label="Targets reached"
              value={targetsHit + targetsMissed ? `${targetsHit} of ${targetsHit + targetsMissed}` : "—"}
              detail={<span className="text-label-2">{targets.length - targetsHit - targetsMissed} still within 12 months</span>}
            />
          </StatGrid>

          <Card>
            <CardHeader title="What if you followed every BUY?" subtitle="$1,000 at the first close after each BUY, held to today, vs the same money in the S&P 500 on the same days" />
            {end ? (
              <>
                <div className="mb-4 flex flex-wrap gap-x-8 gap-y-2">
                  <Stat label="Invested" value={money(end.invested, "USD", { compact: true })} />
                  <Stat label="Worth now" value={<Delta value={end.ret}>{money(end.value, "USD")}</Delta>} detail={<span className="text-label-2">{pct(end.ret)}</span>} />
                  <Stat label="In the S&P 500" value={money(end.bench, "USD")} detail={<span className="text-label-2">{pct(end.benchRet)}</span>} />
                  <Stat label="Difference" value={<Delta value={end.value - end.bench}>{money(end.value - end.bench, "USD", { sign: true })}</Delta>} />
                </div>
                {curve.length > 1 && (
                  <TimeSeries
                    data={curve}
                    height={220}
                    refLines={[{ y: 0 }]}
                    lines={[
                      { key: "ret", label: "Following BUYs", color: SERIES[0], width: 2.5 },
                      { key: "benchRet", label: "S&P 500", color: MUTED, dashed: true },
                    ]}
                    format={(v) => pct(v, 0)}
                    ariaLabel="Return from following BUY signals against the S&P 500 over the same days"
                  />
                )}
              </>
            ) : (
              <p className="text-callout text-label-2">No BUY signals with price history in this filter.</p>
            )}
          </Card>

          <ScheduledCard onFinished={() => mutate()} />

          <RulesCard r={data.rules} horizon={HORIZON_TEXT[horizon]} />

          {data.models.models.length > 1 && <ModelsCard m={data.models} horizon={HORIZON_TEXT[horizon]} />}

          {positions.length > 0 && (
            <Card>
              <CardHeader title="Sold or held?" subtitle="The shares you held at each call, sold at the first close after it vs held to today" />
              <div className="overflow-x-auto">
                <table className="w-full text-callout tabular">
                  <thead className="text-caption text-label-2">
                    <tr>
                      <th className="py-1 text-left font-normal">Call</th>
                      <th className="hidden py-1 text-right font-normal sm:table-cell">Shares</th>
                      <th className="py-1 text-right font-normal">If sold</th>
                      <th className="py-1 text-right font-normal">If held</th>
                      <th className="py-1 text-right font-normal">Following the call</th>
                    </tr>
                  </thead>
                  <tbody>
                    {positions.map(({ s, shares, sold, held, following }) => (
                      <tr key={s.id} className="border-t-[0.5px] border-separator">
                        <td className="py-1.5">
                          <span className="flex items-center gap-2 whitespace-nowrap">
                            {s.symbol} <Badge tone={REC_TONE[s.recommendation]}>{s.recommendation}</Badge>
                            <span className="text-label-2">{shortDate(s.timestamp)}</span>
                          </span>
                        </td>
                        <td className="hidden py-1.5 text-right sm:table-cell">{shares.toLocaleString()}</td>
                        <td className="py-1.5 text-right">{money(sold, "USD", { compact: true })}</td>
                        <td className="py-1.5 text-right">{money(held, "USD", { compact: true })}</td>
                        <td className="py-1.5 text-right">
                          <Delta value={following}>{money(following, "USD", { sign: true, compact: true })}</Delta>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="mt-3 text-footnote text-label-2">
                Following a SELL means selling; following a BUY or HOLD means keeping the shares. Calls on the same stock cover the same shares, so
                don’t add the rows up. Dividends and tax are left out.
              </p>
            </Card>
          )}

          {data.calibration.evaluated > 0 && <SecondLookCard c={data.calibration} horizon={HORIZON_TEXT[horizon]} />}

          {bySymbol.length > 1 && (
            <Card>
              <CardHeader title="By symbol" subtitle="Repeated calls on one stock move together, so one symbol can carry the whole record" />
              <table className="w-full text-callout tabular">
                <thead className="text-caption text-label-2">
                  <tr>
                    <th className="py-1 text-left font-normal">Symbol</th>
                    <th className="py-1 text-right font-normal">Calls</th>
                    <th className="py-1 text-right font-normal">Scored</th>
                    <th className="py-1 text-right font-normal">Win rate</th>
                    <th className="py-1 text-right font-normal">Avg vs S&P</th>
                  </tr>
                </thead>
                <tbody>
                  {bySymbol.map((r) => (
                    <tr key={r.symbol} className="border-t-[0.5px] border-separator">
                      <td className="py-1.5 font-medium">{r.symbol}</td>
                      <td className="py-1.5 text-right">{r.calls}</td>
                      <td className="py-1.5 text-right">{r.scored}</td>
                      <td className="py-1.5 text-right">{r.winRate != null ? pct(r.winRate, 0, false) : "—"}</td>
                      <td className="py-1.5 text-right">{r.avg != null ? <Delta value={r.avg}>{pct(r.avg, 1)}</Delta> : "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>
          )}

          <Card>
            <CardHeader title="Signals" subtitle={`Newest first · scored vs the S&P 500 at ${HORIZON_TEXT[horizon]}`} />
            {filtered.map((s) => (
              <Disclosure
                key={s.id}
                title={
                  <span className="flex items-center gap-2">
                    {s.symbol}
                    <Badge tone={REC_TONE[s.recommendation]}>{s.recommendation}</Badge>
                  </span>
                }
                subtitle={`${shortDate(s.timestamp, true)} · confidence ${s.confidence ?? "—"}/10${
                  s.evaluation ? ` · second look: ${EVAL_LABEL[s.evaluation.verdict].toLowerCase()}, ${s.evaluation.confidence_adjusted}/10` : ""
                }`}
                trailing={
                  <span className="flex flex-col items-end gap-0.5">
                    {s.score_return != null ? (
                      <Delta value={s.score_return} className="text-callout">{pct(s.score_return, 1)}</Delta>
                    ) : (
                      <span className="text-callout tabular text-label-2" title="Since the call, vs the S&P 500">{pct(s.excess_pct ?? s.return_pct, 1)} so far</span>
                    )}
                    <Badge tone={OUTCOME_TONE[s.outcome]}>{s.outcome}</Badge>
                  </span>
                }
              >
                <div className="space-y-4 text-callout">
                  <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                    <Field k={s.quote_date ? `Quoted, ${shortDate(s.quote_date)} price` : "Quoted at signal"} v={money(s.price_at_signal)} />
                    <Field k={s.entry_date ? `Entry close, ${shortDate(s.entry_date)}` : "Entry close"} v={money(s.entry_price)} />
                    <Field k="Now" v={money(s.current_price)} />
                    <Field k="Horizon" v={s.time_horizon ?? "—"} />
                    <Field k="Since entry" v={pct(s.return_pct, 1)} />
                    <Field k="S&P 500 since" v={pct(s.benchmark_pct, 1)} />
                    <Field k="Difference" v={pct(s.excess_pct, 1)} />
                    <Field
                      k="12-month target"
                      v={
                        s.target
                          ? `${money(s.target.price)} · ${s.target.hit ? `reached ${shortDate(s.target.date)}` : s.target.hit === false ? "missed" : "open"}`
                          : s.price_target
                            ? money(s.price_target)
                            : "—"
                      }
                    />
                  </dl>
                  {s.checkpoints.length > 0 && <Checkpoints s={s} />}
                  <SoldVsHeld s={s} />
                  {s.portfolio_context && (
                    <p className="text-footnote text-label-2">
                      Held {s.portfolio_context.total_quantity} shares at {money(s.portfolio_context.avg_purchase_price)} ({pct(s.portfolio_context.unrealized_pct, 1)} unrealized) when generated · {dateTime(s.timestamp)}
                    </p>
                  )}
                  {s.position_advice && <p>{s.position_advice}</p>}
                  <p className="text-footnote text-label-2">
                    {s.model ?? "Model not recorded"} · prompt v{s.prompt_version} · {s.source === "scheduled" ? "scheduled run" : "run by you"}
                    {s.momentum != null && ` · 12-1 month momentum ${pct(s.momentum * 100, 0)} at entry`}
                  </p>
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
                  {s.evaluation && (
                    <div>
                      <div className="mb-1 flex items-center gap-2 font-semibold">
                        Second look <Badge tone={EVAL_TONE[s.evaluation.verdict]}>{EVAL_LABEL[s.evaluation.verdict]}</Badge>
                      </div>
                      <p className="text-label-2">{s.evaluation.summary}</p>
                      <List
                        title="Challenges"
                        items={s.evaluation.findings.filter((f) => f.stance === "challenges" && f.severity !== "info").map((f) => `${f.severity === "major" ? "Major" : "Minor"}: ${f.finding}`)}
                      />
                      <List title="What would show the call is wrong" items={s.evaluation.invalidation} />
                    </div>
                  )}
                </div>
              </Disclosure>
            ))}
            {filtered.length === 0 && <p className="py-4 text-callout text-label-2">No signals match these filters.</p>}
          </Card>

          <p className="text-footnote text-label-2">
            Each call starts from the first close after it was made, the first price you could have traded at, and is compared with the S&P 500 over
            the same days. A BUY wins if the stock beat the index by more than {data.flat_band} point; a SELL if it lagged by more than that. Smaller
            gaps are flat and left out of the win rate. HOLDs are shown but not scored. Prices are adjusted for splits but not dividends.
          </p>
        </div>
      ) : null}
    </>
  );
}

function SoldVsHeld({ s }: { s: Signal }) {
  const p = soldVsHeld(s);
  if (!p) return null;
  const more = p.held - p.sold;
  return (
    <p>
      With your {p.shares.toLocaleString()} shares: selling at the {shortDate(s.entry_date)} close would have raised {money(p.sold)}; holding them,
      they’re worth {money(p.held)} now, {money(Math.abs(more))} {more >= 0 ? "more" : "less"}. Following the {s.recommendation}{" "}
      <Delta value={p.following}>{p.following >= 0 ? "gained" : "cost"} you {money(Math.abs(p.following))}</Delta>.
    </p>
  );
}

const RULE_NOTE: Record<string, string> = {
  always_buy: "BUY on every call",
  momentum: "BUY if the past year’s return, skipping the last month, is positive; otherwise SELL",
  analyst: "The analysts’ consensus at the call. Saved from prompt v2 on",
  app_score: "BUY if the app’s radar scores average 55 or more, SELL at 45 or less. Saved from prompt v2 on",
};

/** The AI against simple rules on the same stocks and dates. All signals, not the filters. */
function RulesCard({ r, horizon }: { r: RuleComparison; horizon: string }) {
  return (
    <Card>
      <CardHeader title="Against simple rules" subtitle={`The same stocks and dates as the AI’s calls scored at ${horizon}, all symbols`} />
      {r.checked < MIN_SCORED && (
        <Banner tone="info" title={`${r.checked} call${r.checked === 1 ? "" : "s"} to compare so far`}>
          Too few to tell the AI from a simple rule until there are at least {MIN_SCORED}.
        </Banner>
      )}
      <table className="mt-3 w-full text-callout tabular">
        <thead className="text-caption text-label-2">
          <tr>
            <th className="py-1 text-left font-normal">Strategy</th>
            <th className="py-1 text-right font-normal">BUY/SELL calls</th>
            <th className="py-1 text-right font-normal">Win rate</th>
            <th className="py-1 text-right font-normal">Avg vs S&P</th>
          </tr>
        </thead>
        <tbody>
          {r.rows.map((row) => (
            <tr key={row.key} className="border-t-[0.5px] border-separator">
              <td className="py-1.5">
                <div className={row.key === "ai" ? "font-semibold" : ""}>{row.label}</div>
                {RULE_NOTE[row.key] && <div className="text-caption text-label-2">{RULE_NOTE[row.key]}</div>}
              </td>
              <td className="py-1.5 text-right">{row.calls}</td>
              <td className="py-1.5 text-right">{row.win_rate != null ? pct(row.win_rate, 0, false) : "—"}</td>
              <td className="py-1.5 text-right">{row.avg_return != null ? <Delta value={row.avg_return}>{pct(row.avg_return, 1)}</Delta> : "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="mt-3 text-footnote text-label-2">
        If the AI doesn’t beat these, it isn’t adding accuracy. HOLDs and rules without data for a call are left out, so compare the call counts too;
        a coin flip would win about half the time.
      </p>
    </Card>
  );
}

/** Gemini against the local model. All signals, not the filters. */
function ModelsCard({ m, horizon }: { m: ModelComparison; horizon: string }) {
  const table = (rows: ModelComparison["all"]) => (
    <table className="w-full text-callout tabular">
      <thead className="text-caption text-label-2">
        <tr>
          <th className="py-1 text-left font-normal">Model</th>
          <th className="py-1 text-right font-normal">BUY/SELL calls</th>
          <th className="py-1 text-right font-normal">Win rate</th>
          <th className="py-1 text-right font-normal">Avg vs S&P</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((r) => (
          <tr key={r.model} className="border-t-[0.5px] border-separator">
            <td className="py-1.5 font-medium">{r.model}</td>
            <td className="py-1.5 text-right">{r.calls}</td>
            <td className="py-1.5 text-right">{r.win_rate != null ? pct(r.win_rate, 0, false) : "—"}</td>
            <td className="py-1.5 text-right">{r.avg_return != null ? <Delta value={r.avg_return}>{pct(r.avg_return, 1)}</Delta> : "—"}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
  return (
    <Card>
      <CardHeader title="Gemini vs local model" subtitle={`Calls scored at ${horizon}, all symbols`} />
      {m.pairs > 0 ? (
        <>
          <div className="mb-3 flex flex-wrap gap-x-8 gap-y-2">
            <Stat label="Paired calls" value={m.pairs} detail={<span className="text-label-2">{m.pairs_checked} scored</span>} />
            <Stat label="Same call" value={m.agreement != null ? pct(m.agreement, 0, false) : "—"} detail={<span className="text-label-2">of pairs</span>} />
          </div>
          <div className="mb-1 text-footnote font-semibold">Head to head</div>
          <p className="mb-2 text-footnote text-label-2">
            Comparison runs in the last week of each month give both models the same stock and the same data, so only the model differs.
          </p>
          {table(m.paired)}
        </>
      ) : (
        <p className="mb-3 text-callout text-label-2">No comparison runs yet. They happen on the scheduled runs in the last week of each month.</p>
      )}
      <div className="mt-4 mb-1 text-footnote font-semibold">All calls</div>
      <p className="mb-2 text-footnote text-label-2">Each model on every call it made. The two cover different stocks and dates, so the head-to-head is the fairer test.</p>
      {table(m.all)}
    </Card>
  );
}

/** Return after each checkpoint, vs the S&P 500. */
function Checkpoints({ s }: { s: Signal }) {
  return (
    <table className="w-full text-footnote tabular">
      <thead className="text-caption text-label-2">
        <tr>
          <th className="py-1 text-left font-normal">After</th>
          <th className="py-1 text-right font-normal">{s.symbol}</th>
          <th className="py-1 text-right font-normal">S&P 500</th>
          <th className="py-1 text-right font-normal">Difference</th>
        </tr>
      </thead>
      <tbody>
        {s.checkpoints.map((c) => (
          <tr key={c.days} className={`border-t-[0.5px] border-separator ${c.days === s.score_days ? "font-semibold" : ""}`}>
            <td className="py-1">{c.label}</td>
            <td className="py-1 text-right">{pct(c.stock, 1)}</td>
            <td className="py-1 text-right">{pct(c.benchmark, 1)}</td>
            <td className="py-1 text-right">{c.excess != null ? <Delta value={c.excess}>{pct(c.excess, 1)}</Delta> : <span className="text-label-3">not yet</span>}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

const EVAL_LABEL = { stands: "Stands", weakened: "Weakened", contradicted: "Contradicted" } as const;
const EVAL_TONE = { stands: "positive", weakened: "warning", contradicted: "negative" } as const;

// Below this many evaluated calls the comparison is mostly noise.
const MIN_EVALUATED = 30;

// Brier score of always saying 50%.
const BRIER_COIN = 0.25;

/** Whether the second look's verdicts and lowered confidence match how calls turned out. All signals, not the filters. */
function SecondLookCard({ c, horizon }: { c: Calibration; horizon: string }) {
  const skill = (b: number | null) => (b != null ? (1 - b / BRIER_COIN) * 100 : null);
  const better = c.brier_original != null && c.brier_adjusted != null ? c.brier_original - c.brier_adjusted : null;
  return (
    <Card>
      <CardHeader title="Is the second look right?" subtitle={`BUY and SELL calls scored at ${horizon}, all symbols, by evaluation verdict`} />
      {c.evaluated < MIN_EVALUATED && (
        <Banner tone="info" title={`${c.evaluated} evaluated call${c.evaluated === 1 ? "" : "s"} so far`}>
          Too few to judge: treat these numbers as anecdotes until there are at least {MIN_EVALUATED}.
        </Banner>
      )}
      <table className="mt-3 w-full text-callout tabular">
        <thead className="text-caption text-label-2">
          <tr>
            <th className="py-1 text-left font-normal">Verdict</th>
            <th className="py-1 text-right font-normal">Calls</th>
            <th className="py-1 text-right font-normal">Win rate</th>
            <th className="py-1 text-right font-normal">Avg vs S&P</th>
          </tr>
        </thead>
        <tbody>
          {c.groups.map((g) => (
            <tr key={g.verdict} className="border-t-[0.5px] border-separator">
              <td className="py-1.5">{g.verdict === "not_evaluated" ? <span className="text-label-2">Not evaluated</span> : <Badge tone={EVAL_TONE[g.verdict]}>{EVAL_LABEL[g.verdict]}</Badge>}</td>
              <td className="py-1.5 text-right">{g.n}</td>
              <td className="py-1.5 text-right">{g.win_rate != null ? pct(g.win_rate, 0, false) : "—"}</td>
              <td className="py-1.5 text-right">{g.avg_return != null ? <Delta value={g.avg_return}>{pct(g.avg_return, 1)}</Delta> : "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="mt-4 flex flex-wrap gap-x-8 gap-y-2">
        <Stat label="Confidence lowered" value={`${c.lowered} of ${c.evaluated}`} />
        <Stat
          label="Brier, original"
          value={c.brier_original?.toFixed(3) ?? "—"}
          detail={<span className="text-label-2">{pct(skill(c.brier_original), 0)} vs a coin flip</span>}
        />
        <Stat
          label="Brier, adjusted"
          value={c.brier_adjusted?.toFixed(3) ?? "—"}
          detail={
            <span className="text-label-2">
              {pct(skill(c.brier_adjusted), 0)} vs a coin flip{better != null && better !== 0 && ` · ${better > 0 ? "better" : "worse"} than original`}
            </span>
          }
        />
      </div>
      <p className="mt-3 text-footnote text-label-2">
        The Brier score treats confidence n/10 as the chance the call is right; lower is better, and always saying 50% scores 0.25 (shown as
        skill vs a coin flip; above 0% beats it). If lowering confidence was warranted, the adjusted score is lower. You choose which calls to
        evaluate, so read the groups with care.
      </p>
    </Card>
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
