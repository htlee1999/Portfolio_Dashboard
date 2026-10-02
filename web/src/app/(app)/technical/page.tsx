"use client";

import { BookOpen, Download, ExternalLink, SlidersHorizontal } from "lucide-react";
import { useState } from "react";

import { SERIES, SignedBars, TimeSeries } from "@/components/charts/charts";
import { PageHeader, ResearchTabs } from "@/components/shell/page-header";
import { ResearchPage, useDebounced } from "@/components/shell/research-page";
import { SymbolPicker, useSymbol } from "@/components/shell/symbol-picker";
import { Button } from "@/components/ui/button";
import { Badge, Card, CardHeader } from "@/components/ui/card";
import { Segmented, Slider } from "@/components/ui/controls";
import { Banner, LoadingBlock } from "@/components/ui/feedback";
import { Disclosure } from "@/components/ui/overlay";
import { Delta } from "@/components/ui/stat";
import { useToast } from "@/components/ui/toast";
import { download, useApi } from "@/lib/api";
import { EVIDENCE_LABEL, EVIDENCE_TONE, INDICATORS, type IndicatorKey } from "@/lib/indicator-evidence";
import { PERIODS, compact, money, number, pct, shortDate } from "@/lib/format";
import type { SignalBacktest, Technical } from "@/lib/types";

const DEFAULTS = { rsi: 14, fast: 12, slow: 26, bb: 20, std: 2 };

export default function Page() {
  return (
    <ResearchPage>
      <TechnicalView />
    </ResearchPage>
  );
}

function TechnicalView() {
  const toast = useToast();
  const [symbol, setSymbol] = useSymbol();
  const [period, setPeriod] = useState<string>("1y");
  const [params, setParams] = useState(DEFAULTS);
  const [overlay, setOverlay] = useState<"bands" | "averages">("bands");
  const p = useDebounced(params);
  const query = `/stocks/${encodeURIComponent(symbol)}/technical?period=${period}&rsi_period=${p.rsi}&macd_fast=${p.fast}&macd_slow=${p.slow}&bb_period=${p.bb}&bb_std=${p.std}`;
  const { data, error, isLoading, isValidating } = useApi<Technical>(query);
  const stale = data && data.symbol !== symbol;

  const set = (k: keyof typeof DEFAULTS) => (v: number) =>
    setParams((cur) => {
      const next = { ...cur, [k]: v };
      if (k === "fast" && v >= next.slow) next.slow = Math.min(50, v + 1);
      if (k === "slow" && v <= next.fast) next.fast = Math.max(5, v - 1);
      return next;
    });

  return (
    <>
      <ResearchTabs />
      <PageHeader
        title="Technicals"
        eyebrow="Research"
        actions={
          <>
            <SymbolPicker symbol={symbol} onChange={setSymbol} />
            <Segmented label="Period" options={PERIODS} value={period} onChange={setPeriod} />
          </>
        }
      />

      {error && <Banner tone="error" title={`Couldn't analyze ${symbol}`}>{error.message}</Banner>}

      {isLoading && !data ? (
        <LoadingBlock label={`Analyzing ${symbol}…`} />
      ) : data ? (
        <div className={`space-y-5 transition-opacity duration-200 ${isValidating || stale ? "opacity-55" : ""}`}>
          {/* Quote */}
          <Card>
            <div className="flex flex-wrap items-end justify-between gap-4">
              <div>
                <div className="text-footnote font-medium text-label-2">{data.symbol} · last close</div>
                <div className="text-hero tabular">{money(data.quote.price)}</div>
                <Delta value={data.quote.change} className="text-callout">
                  {money(data.quote.change, "USD", { sign: true })} ({pct(data.quote.change_pct)}) today
                </Delta>
              </div>
              <div className="text-right">
                <div className="text-footnote text-label-2">Volume</div>
                <div className="text-title-3 tabular">{compact(data.quote.volume)}</div>
              </div>
            </div>
          </Card>

          <SignalGrid t={data} />

          <Card>
            <CardHeader
              title="Price"
              subtitle={overlay === "bands" ? `Bollinger Bands (${p.bb}, ${p.std}σ)` : "20, 50 and 200-day simple moving averages"}
              action={
                <Segmented
                  size="sm"
                  label="Overlay"
                  value={overlay}
                  onChange={setOverlay}
                  options={[
                    { value: "bands", label: "Bands" },
                    { value: "averages", label: "Averages" },
                  ]}
                />
              }
            />
            <TimeSeries
              data={data.series}
              height={320}
              ariaLabel={`${data.symbol} price with ${overlay}`}
              format={(v) => number(v, v >= 1000 ? 0 : 2)}
              band={overlay === "bands" ? { lower: "bb_lower", upper: "bb_upper", color: SERIES[0] } : undefined}
              lines={
                overlay === "bands"
                  ? [
                      { key: "close", label: "Close", color: SERIES[0] },
                      { key: "bb_middle", label: `SMA ${p.bb}`, color: SERIES[1], width: 1.5, dashed: true },
                    ]
                  : [
                      { key: "close", label: "Close", color: SERIES[0] },
                      { key: "sma20", label: "SMA 20", color: SERIES[1], width: 1.5 },
                      { key: "sma50", label: "SMA 50", color: SERIES[2], width: 1.5 },
                      { key: "sma200", label: "SMA 200", color: SERIES[3], width: 1.5 },
                    ]
              }
            />
          </Card>

          <div className="grid gap-5 lg:grid-cols-2">
            <Card>
              <CardHeader title={`RSI (${p.rsi})`} subtitle="Above 70 overbought · below 30 oversold · can stay extended in strong trends" />
              <TimeSeries
                data={data.series}
                height={200}
                yDomain={[0, 100]}
                refAreas={[{ y1: 30, y2: 70 }]}
                refLines={[{ y: 70, label: "70" }, { y: 30, label: "30" }]}
                lines={[{ key: "rsi", label: "RSI", color: SERIES[6] }]}
                format={(v) => number(v, 0)}
                ariaLabel="Relative strength index"
              />
            </Card>
            <Card>
              <CardHeader title="On-Balance Volume" subtitle="Rising OBV confirms buying pressure" />
              <TimeSeries
                data={data.series}
                height={200}
                lines={[
                  { key: "obv", label: "OBV", color: SERIES[0] },
                  { key: "obv_ema", label: "EMA 10", color: SERIES[1], width: 1.5, dashed: true },
                ]}
                format={(v) => compact(v)}
                ariaLabel="On-balance volume"
              />
            </Card>
          </div>

          <Card>
            <CardHeader title={`MACD (${p.fast}, ${p.slow}, 9)`} subtitle="MACD above its signal line indicates bullish momentum" />
            <TimeSeries
              data={data.series}
              height={200}
              refLines={[{ y: 0 }]}
              lines={[
                { key: "macd", label: "MACD", color: SERIES[0] },
                { key: "signal", label: "Signal", color: SERIES[1] },
              ]}
              format={(v) => number(v, 2)}
              ariaLabel="MACD and signal line"
            />
            <div className="mt-4 text-footnote font-medium text-label-2">Histogram</div>
            <SignedBars data={data.series} xKey="date" yKey="hist" name="Histogram" height={120} dateAxis format={(v) => number(v, 2)} ariaLabel="MACD histogram" />
          </Card>

          <div className="grid gap-5 lg:grid-cols-2">
            <Card>
              <CardHeader title="ADX (14)" subtitle="Above 25 trending · below 20 ranging · +DI vs −DI gives direction" />
              <TimeSeries
                data={data.series}
                height={200}
                refLines={[{ y: 25, label: "25" }, { y: 20, label: "20" }]}
                lines={[
                  { key: "adx", label: "ADX", color: SERIES[0] },
                  { key: "plus_di", label: "+DI", color: SERIES[2], width: 1.5 },
                  { key: "minus_di", label: "−DI", color: SERIES[4], width: 1.5 },
                ]}
                format={(v) => number(v, 0)}
                ariaLabel="Average directional index"
              />
            </Card>
            <Card>
              <CardHeader title="ATR (14)" subtitle="Average daily range as a percent of price" />
              <TimeSeries
                data={data.series}
                height={200}
                lines={[{ key: "atr_pct", label: "ATR %", color: SERIES[6] }]}
                format={(v) => pct(v, 1, false)}
                ariaLabel="Average true range as percent of price"
              />
            </Card>
          </div>

          <BacktestCard symbol={symbol} params={p} />

          <Card>
            <Disclosure title="Indicator settings" subtitle="Adjust periods; charts update as you drag" leading={<SlidersHorizontal className="size-5 text-tint" />}>
              <div className="grid gap-x-8 gap-y-1 sm:grid-cols-2 lg:grid-cols-3">
                <Slider label="RSI period" min={5} max={30} value={params.rsi} onChange={set("rsi")} />
                <Slider label="MACD fast" min={5} max={20} value={params.fast} onChange={set("fast")} />
                <Slider label="MACD slow" min={15} max={50} value={params.slow} onChange={set("slow")} />
                <Slider label="Bollinger period" min={10} max={30} value={params.bb} onChange={set("bb")} />
                <Slider label="Bollinger σ" min={1} max={3} step={0.1} value={params.std} onChange={set("std")} format={(v) => v.toFixed(1)} />
              </div>
              <Button variant="plain" size="sm" className="mt-2" onClick={() => setParams(DEFAULTS)}>
                Reset to Defaults
              </Button>
            </Disclosure>
            <Disclosure
              title="Indicator guide & evidence"
              subtitle="How to read each indicator, how well research supports it, and sources"
              leading={<BookOpen className="size-5 text-tint" />}
            >
              <Guide />
            </Disclosure>
          </Card>

          <div className="flex justify-end">
            <Button
              variant="gray"
              icon={<Download className="size-[18px]" />}
              onClick={() => download(`/stocks/${encodeURIComponent(symbol)}/technical.csv?period=${period}`).catch((e) => toast(e.message, "error"))}
            >
              Export Indicator Data
            </Button>
          </div>
        </div>
      ) : null}
    </>
  );
}

type Tone = "positive" | "negative" | "neutral" | "warning";

type Item = { id: IndicatorKey; name: string; value: string; badge: { tone: Tone; text: string } };

function SignalGrid({ t }: { t: Technical }) {
  const s = t.signals;
  const thin = { tone: "neutral" as const, text: "Needs more history" };
  const shortTerm: Item[] = [
    {
      id: "rsi",
      name: "RSI",
      value: number(s.rsi.value, 1),
      badge: s.rsi.state === "overbought" ? { tone: "warning", text: "Overbought" } : s.rsi.state === "oversold" ? { tone: "warning", text: "Oversold" } : { tone: "neutral", text: "Neutral" },
    },
    {
      id: "macd",
      name: "MACD",
      value: number(s.macd.macd, 2),
      badge: s.macd.state === "bullish" ? { tone: "positive", text: "Bullish ↑" } : { tone: "negative", text: "Bearish ↓" },
    },
    {
      id: "bollinger",
      name: "Bollinger %B",
      value: number(s.bollinger.percent_b, 2),
      badge: s.bollinger.state === "above" ? { tone: "warning", text: "Above upper" } : s.bollinger.state === "below" ? { tone: "warning", text: "Below lower" } : { tone: "neutral", text: "Within bands" },
    },
    {
      id: "trend",
      name: "Trend",
      value: s.trend.sma50.price_above ? "Above SMA 50" : "Below SMA 50",
      badge: s.trend.sma50.price_above && s.trend.sma20.price_above ? { tone: "positive", text: "Uptrend ↑" } : !s.trend.sma50.price_above && !s.trend.sma20.price_above ? { tone: "negative", text: "Downtrend ↓" } : { tone: "neutral", text: "Mixed" },
    },
    {
      id: "obv",
      name: "On-Balance Volume",
      value: compact(s.obv.value),
      badge: s.obv.state === "rising" ? { tone: "positive", text: "Rising ↑" } : { tone: "negative", text: "Falling ↓" },
    },
  ];
  const longTerm: Item[] = [
    {
      id: "momentum",
      name: "12-1 Momentum",
      value: s.momentum.return_12_1 == null ? "—" : pct(s.momentum.return_12_1 * 100, 1),
      badge: s.momentum.state === "positive" ? { tone: "positive", text: "Positive ↑" } : s.momentum.state === "negative" ? { tone: "negative", text: "Negative ↓" } : thin,
    },
    {
      id: "high52w",
      name: "52-Week High",
      value: s.high_52w.distance == null ? "—" : pct(s.high_52w.distance * 100, 1),
      badge: s.high_52w.state === "near" ? { tone: "positive", text: "Near high" } : s.high_52w.state === "far" ? { tone: "negative", text: "Far below" } : s.high_52w.state === "below" ? { tone: "neutral", text: "Below high" } : thin,
    },
    {
      id: "sma200",
      name: "Long-Term Trend",
      value: s.trend.sma200.value == null ? "—" : s.trend.sma200.price_above ? "Above SMA 200" : "Below SMA 200",
      badge: s.trend.golden_cross == null ? thin : s.trend.golden_cross ? { tone: "positive", text: "SMA 50 > 200" } : { tone: "negative", text: "SMA 50 < 200" },
    },
    {
      id: "adx",
      name: "ADX",
      value: number(s.adx.value, 1),
      badge:
        s.adx.state === "strong"
          ? s.adx.direction === "up" ? { tone: "positive", text: "Strong uptrend" } : { tone: "negative", text: "Strong downtrend" }
          : s.adx.state === "developing" ? { tone: "neutral", text: "Developing" } : s.adx.state === "weak" ? { tone: "neutral", text: "Ranging" } : thin,
    },
    {
      id: "atr",
      name: "ATR",
      value: number(s.atr.value, 2),
      badge: { tone: "neutral", text: s.atr.pct == null ? "—" : `${pct(s.atr.pct, 1, false)} of price` },
    },
  ];
  return (
    <div className="space-y-4">
      <SignalRow label="Short-term momentum & trend" items={shortTerm} />
      <SignalRow label="Long-term trend, strength & volatility" items={longTerm} />
    </div>
  );
}

function SignalRow({ label, items }: { label: string; items: Item[] }) {
  return (
    <section>
      <h2 className="mb-2 text-footnote font-medium text-label-2">{label}</h2>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        {items.map((i) => (
          <Card key={i.id} className="flex flex-col !p-4">
            <div className="truncate text-footnote font-medium text-label-2">{i.name}</div>
            <div className="mt-1 truncate text-title-3 tabular">{i.value}</div>
            <Badge tone={i.badge.tone} className="mt-2 self-start">
              {i.badge.text}
            </Badge>
            <EvidenceTag id={i.id} />
          </Card>
        ))}
      </div>
    </section>
  );
}

const VERDICT = {
  worked: { tone: "positive", text: "Worked here" },
  failed: { tone: "negative", text: "Failed here" },
  no_edge: { tone: "neutral", text: "No clear edge" },
  insufficient: { tone: "neutral", text: "Too few" },
} as const;

function BacktestCard({ symbol, params }: { symbol: string; params: typeof DEFAULTS }) {
  const [days, setDays] = useState("20");
  const p = params;
  const { data, error, isLoading } = useApi<SignalBacktest>(
    `/stocks/${encodeURIComponent(symbol)}/technical/backtest?rsi_period=${p.rsi}&macd_fast=${p.fast}&macd_slow=${p.slow}&bb_period=${p.bb}&bb_std=${p.std}`,
  );
  const h = Number(days);
  const base = data?.signals[0]?.horizons.find((x) => x.days === h);

  return (
    <Card padded={false} className="pb-5 sm:pb-6">
      <div className="px-5 pt-5 sm:px-6 sm:pt-6">
        <CardHeader
          title="Signal track record"
          subtitle={
            data
              ? `How ${data.symbol} moved after each signal, ${shortDate(data.start, true)} – ${shortDate(data.end, true)}`
              : "How this stock moved after each signal over the past five years"
          }
          action={
            <Segmented
              size="sm"
              label="Horizon"
              value={days}
              onChange={setDays}
              options={[
                { value: "5", label: "5d" },
                { value: "20", label: "20d" },
                { value: "60", label: "60d" },
              ]}
            />
          }
        />
      </div>
      {error ? (
        <p className="px-5 py-4 text-callout text-label-2 sm:px-6">Couldn’t load the signal history: {error.message}</p>
      ) : isLoading && !data ? (
        <LoadingBlock label="Testing signals…" />
      ) : data ? (
        <>
          {base && (
            <p className="px-5 text-footnote text-label-2 sm:px-6">
              Baseline: over any {h} trading days, {data.symbol} rose {pct(base.baseline_hit * 100, 0, false)} of the time, by{" "}
              {pct((base.baseline_avg ?? 0) * 100, 1)} on average. A signal only adds information if it beats that.
            </p>
          )}
          <div className="mt-3 overflow-x-auto">
            <table className="w-full min-w-[640px] text-callout">
              <thead>
                <tr className="text-caption text-label-2 [&>th]:px-3 [&>th]:pb-2 [&>th]:font-medium [&>th:first-child]:pl-6 [&>th:last-child]:pr-6">
                  <th className="text-left">Signal</th>
                  <th className="text-right">Fired</th>
                  <th className="text-right">Last</th>
                  <th className="text-right">Moved as expected</th>
                  <th className="text-right">Avg return</th>
                  <th className="text-right">Verdict</th>
                </tr>
              </thead>
              <tbody className="tabular">
                {data.signals.map((sig) => {
                  const r = sig.horizons.find((x) => x.days === h);
                  if (!r) return null;
                  const verdict = VERDICT[r.verdict];
                  return (
                    <tr key={sig.id} className="border-t-[0.5px] border-separator [&>td]:px-3 [&>td]:py-2.5 [&>td:first-child]:pl-6 [&>td:last-child]:pr-6">
                      <td>
                        <div className="font-medium">{sig.label}</div>
                        <div className="text-caption text-label-2">Expects {sig.expect === "up" ? "a rise ↑" : "a fall ↓"}</div>
                      </td>
                      <td className="text-right">{r.n}</td>
                      <td className="text-right text-label-2">{sig.last ? shortDate(sig.last, true) : "—"}</td>
                      <td className="text-right">
                        {r.hit_rate == null ? "—" : pct(r.hit_rate * 100, 0, false)}
                        <span className="text-label-2"> vs {pct(r.baseline_hit * 100, 0, false)}</span>
                      </td>
                      <td className={`text-right ${r.avg_return != null && r.avg_return < 0 ? "text-negative" : ""}`}>
                        {r.avg_return == null ? "—" : pct(r.avg_return * 100, 1)}
                      </td>
                      <td className="text-right">
                        <Badge tone={verdict.tone}>{verdict.text}</Badge>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <p className="px-5 pt-3 text-footnote text-label-2 sm:px-6">
            Each signal counts on the day it first triggers, then not again for {data.cooldown_days} trading days. “Worked” means
            the hit rate beat the baseline by more than chance would explain (one-sided z-test, 95%); with fewer than {data.min_events}{" "}
            occurrences there’s too little data to judge. Holding periods overlap, so treat this as a screen, not proof. Past behaviour
            of one stock is a small sample.
          </p>
        </>
      ) : null}
    </Card>
  );
}

const EVIDENCE_DOT = { strong: "bg-positive", mixed: "bg-warning", weak: "bg-label-3", risk: "bg-tint" } as const;

function EvidenceTag({ id }: { id: IndicatorKey }) {
  const evidence = INDICATORS[id].evidence;
  return (
    <div className="mt-auto flex items-center gap-1.5 pt-3 text-caption text-label-2" title={INDICATORS[id].verdict}>
      <span aria-hidden className={`size-1.5 shrink-0 rounded-full ${EVIDENCE_DOT[evidence]}`} />
      {EVIDENCE_LABEL[evidence]}
    </div>
  );
}

function Guide() {
  return (
    <div className="space-y-5">
      <p className="text-callout text-label-2">
        Evidence ratings summarise peer-reviewed research on whether each signal has predicted future returns, as this page uses it.
        Strong means the effect has held across decades and markets; weak means tests found little or no edge after trading costs.
      </p>
      <dl className="divide-y divide-separator">
        {(Object.keys(INDICATORS) as IndicatorKey[]).map((id) => {
          const info = INDICATORS[id];
          return (
            <div key={id} className="space-y-2 py-4 first:pt-0">
              <dt className="flex flex-wrap items-center gap-2">
                <span className="text-callout font-semibold">{info.name}</span>
                <Badge tone={EVIDENCE_TONE[info.evidence]}>{EVIDENCE_LABEL[info.evidence]}</Badge>
              </dt>
              <dd className="space-y-2 text-callout">
                <p className="text-label-2">{info.read}</p>
                <p>
                  <span className="font-semibold">Evidence: </span>
                  <span className="text-label-2">{info.verdict}</span>
                </p>
                <ul className="space-y-1 text-footnote text-label-2">
                  {"learn" in info && info.learn && (
                    <li>
                      <SourceLink href={info.learn}>How it works: StockCharts ChartSchool</SourceLink>
                    </li>
                  )}
                  {info.sources.map((src) => (
                    <li key={src.cite}>
                      {"url" in src && src.url ? <SourceLink href={src.url}>{src.cite}</SourceLink> : src.cite}
                    </li>
                  ))}
                </ul>
              </dd>
            </div>
          );
        })}
      </dl>
      <p className="text-footnote text-label-2">
        No single indicator is reliable on its own. Look for confirmation across several, and weight the ones with stronger evidence more heavily.
      </p>
    </div>
  );
}

function SourceLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <a href={href} target="_blank" rel="noreferrer" className="inline-flex items-baseline gap-1 text-tint hover:underline">
      {children}
      <ExternalLink aria-hidden className="size-3 shrink-0 self-center" />
    </a>
  );
}
