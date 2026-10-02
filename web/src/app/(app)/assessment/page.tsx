"use client";

import { ArrowDownCircle, ArrowUpCircle, CheckCircle2, FileDown, MinusCircle, Sparkles, TriangleAlert } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import Link from "next/link";
import { useState } from "react";

import { ScoreRadar } from "@/components/charts/charts";
import { PageHeader, ResearchTabs } from "@/components/shell/page-header";
import { ResearchPage } from "@/components/shell/research-page";
import { SymbolPicker, useSymbol } from "@/components/shell/symbol-picker";
import { Button } from "@/components/ui/button";
import { Badge, Card, CardHeader } from "@/components/ui/card";
import { Segmented, Switch } from "@/components/ui/controls";
import { Banner, EmptyState, Spinner } from "@/components/ui/feedback";
import { Disclosure } from "@/components/ui/overlay";
import { Delta } from "@/components/ui/stat";
import { useToast } from "@/components/ui/toast";
import { api, download } from "@/lib/api";
import { PERIODS, money, number, pct } from "@/lib/format";
import { spring, stagger, staggerItem } from "@/lib/motion";
import type { AIResult, AssessmentContext } from "@/lib/types";

export default function Page() {
  return (
    <ResearchPage>
      <AssessmentView />
    </ResearchPage>
  );
}

function AssessmentView() {
  const toast = useToast();
  const [symbol, setSymbol] = useSymbol();
  const [period, setPeriod] = useState<string>("1y");
  const [withSentiment, setWithSentiment] = useState(true);
  const [ctx, setCtx] = useState<AssessmentContext | null>(null);
  const [ai, setAi] = useState<AIResult | null>(null);
  const [step, setStep] = useState<"idle" | "context" | "ai">("idle");
  const [error, setError] = useState<string | null>(null);

  async function gather() {
    setStep("context");
    setError(null);
    setAi(null);
    try {
      setCtx(await api<AssessmentContext>(`/stocks/${encodeURIComponent(symbol)}/assessment`, { method: "POST", json: { period, include_sentiment: withSentiment } }));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setStep("idle");
    }
  }

  async function generate() {
    if (!ctx) return;
    setStep("ai");
    setError(null);
    try {
      setAi(await api<AIResult>(`/stocks/${encodeURIComponent(ctx.symbol)}/assessment/ai`, { method: "POST", json: ctx }));
      toast("Assessment saved to your track record");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setStep("idle");
    }
  }

  return (
    <>
      <ResearchTabs />
      <PageHeader
        title="AI Assessment"
        eyebrow="Research"
        subtitle="Technicals, fundamentals, sentiment and ML forecasts, weighed by Gemini"
        actions={<SymbolPicker symbol={symbol} onChange={(s) => { setSymbol(s); setCtx(null); setAi(null); }} />}
      />

      <div className="space-y-5">
        <Card>
          <div className="grid gap-5 md:grid-cols-[auto_1fr_auto] md:items-center">
            <div>
              <div className="mb-1.5 px-1 text-footnote font-medium text-label-2">Lookback</div>
              <Segmented label="Lookback" options={PERIODS.filter((p) => p.value !== "1mo")} value={period} onChange={setPeriod} />
            </div>
            <div className="md:px-4">
              <Switch checked={withSentiment} onChange={setWithSentiment} label="Include news sentiment" description="Uses 2 SERPapi searches" />
            </div>
            <Button size="lg" variant={ctx ? "gray" : "filled"} loading={step === "context"} onClick={gather}>
              {ctx ? "Re-run Analysis" : "Run Analysis"}
            </Button>
          </div>
        </Card>

        {error && <Banner tone="error" title="Something went wrong">{error}</Banner>}

        {step === "context" && !ctx && (
          <Card>
            <div className="flex flex-col items-center gap-3 py-12 text-center">
              <Spinner className="size-7" />
              <div className="text-headline">Analyzing {symbol}</div>
              <p className="max-w-sm text-footnote text-label-2">Fetching prices and financials, training a forecast model{withSentiment ? ", and scoring news" : ""}. This can take 10–30 seconds.</p>
            </div>
          </Card>
        )}

        {!ctx && step === "idle" && !error && (
          <Card>
            <EmptyState icon={<Sparkles className="size-7" />} title={`Assess ${symbol}`}>
              Run the analysis to gather every signal, then ask Gemini for a recommendation that accounts for your position.
            </EmptyState>
          </Card>
        )}

        {ctx && (
          <div className={`transition-opacity ${step === "context" ? "opacity-55" : ""}`}>
            <Snapshot ctx={ctx} />
            <div className="mt-5">
              <AnimatePresence mode="wait">
                {ai ? (
                  <AIPanel key="ai" ai={ai} ctx={ctx} onRegenerate={generate} regenerating={step === "ai"} />
                ) : (
                  <motion.div key="cta" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, scale: 0.98 }} transition={spring.smooth}>
                    <Card className="relative overflow-hidden">
                      <div aria-hidden className="pointer-events-none absolute -top-24 -right-24 size-72 rounded-full bg-[radial-gradient(circle,color-mix(in_srgb,var(--tint)_18%,transparent),transparent_70%)]" />
                      <div className="relative flex flex-col items-start gap-4 sm:flex-row sm:items-center sm:justify-between">
                        <div>
                          <h3 className="text-title-3">Ready for an AI recommendation</h3>
                          <p className="mt-1 text-callout text-label-2">
                            {ctx.ai_available ? "Gemini will weigh the signals above and explain its reasoning step by step." : "Add GEMINI_API_KEY to .env and restart the API to enable AI assessments."}
                          </p>
                        </div>
                        <Button size="lg" disabled={!ctx.ai_available} loading={step === "ai"} icon={<Sparkles className="size-5" />} onClick={generate}>
                          Generate Assessment
                        </Button>
                      </div>
                    </Card>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>
        )}
      </div>
    </>
  );
}

function Snapshot({ ctx }: { ctx: AssessmentContext }) {
  const t = ctx.technical;
  const f = ctx.fundamental;
  const p = ctx.predictive;
  const s = ctx.sentiment;
  const pos = ctx.position;
  const ccy = f.profile.currency;
  return (
    <motion.div variants={stagger(0.05)} initial="initial" animate="animate" className="space-y-5">
      <motion.div variants={staggerItem} className="grid gap-5 lg:grid-cols-5">
        <Card className="lg:col-span-3">
          <div className="text-footnote font-medium text-label-2">{f.profile.name}</div>
          <div className="flex flex-wrap items-baseline gap-x-3">
            <span className="text-hero tabular">{money(t.quote.price, ccy)}</span>
            <Delta value={t.quote.change_pct} className="text-callout">{pct(t.quote.change_pct)} today</Delta>
          </div>
          {pos ? (
            <div className="mt-5 grid grid-cols-2 gap-4 border-t-[0.5px] border-separator pt-4 sm:grid-cols-4">
              <Mini label="Your shares" value={number(pos.quantity, pos.quantity % 1 ? 2 : 0)} />
              <Mini label="Avg cost" value={money(pos.avg_cost, pos.currency)} />
              <Mini label="Value" value={money(pos.value, pos.currency, { compact: true })} />
              <Mini label="Unrealized" value={<Delta value={pos.unrealized_pct}>{pct(pos.unrealized_pct, 1)}</Delta>} />
            </div>
          ) : (
            <p className="mt-4 border-t-[0.5px] border-separator pt-4 text-footnote text-label-2">You don’t hold {ctx.symbol}. The assessment will consider it as a new position.</p>
          )}
        </Card>
        <Card className="lg:col-span-2">
          <CardHeader title="Signal profile" subtitle="0–100, where 50 is neutral or unknown" />
          <ScoreRadar data={ctx.scores} ariaLabel={`${ctx.symbol} score profile`} />
          <ul className="sr-only">
            {ctx.scores.map((x) => (
              <li key={x.axis}>{x.axis}: {x.score.toFixed(0)}</li>
            ))}
          </ul>
        </Card>
      </motion.div>

      <motion.div variants={staggerItem} className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <SignalCard
          title="Technical"
          lines={[
            ["RSI", `${number(t.signals.rsi.value, 0)} · ${t.signals.rsi.state ?? "—"}`],
            ["MACD", t.signals.macd.state ?? "—"],
            ["Trend", t.signals.trend.sma50.price_above ? "Above 50-day" : "Below 50-day"],
          ]}
        />
        <SignalCard
          title="Fundamental"
          lines={[
            ["P/E", f.headline.pe ? `${number(f.headline.pe, 1)}×` : f.headline.loss_making ? "n/m · loss-making" : "—"],
            ["Analysts", f.analyst.recommendation_key?.replace("_", " ") ?? "—"],
            ["Target", f.analyst.upside_pct != null ? pct(f.analyst.upside_pct, 1) : "—"],
          ]}
        />
        <SignalCard
          title="ML forecast"
          empty={!p ? "Not enough history" : undefined}
          lines={p ? [
            ["Next close", money(p.next_close, ccy)],
            ["Direction acc.", p.directional_accuracy != null ? pct(p.directional_accuracy * 100, 0, false) : "—"],
            ["RMSE", number(p.rmse, 2)],
          ] : []}
        />
        <SignalCard
          title="Sentiment"
          empty={!s ? (ctx.sentiment_status.error ?? (ctx.sentiment_status.requested ? (ctx.sentiment_status.enabled ? "No articles found" : "Not configured") : "Not included")) : undefined}
          lines={s ? [
            ["Overall", s.overall ?? "—"],
            ["VADER", `${s.avg_vader >= 0 ? "+" : ""}${number(s.avg_vader, 3)}`],
            ["Articles", String(s.total)],
          ] : []}
        />
      </motion.div>
    </motion.div>
  );
}

function Mini({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="min-w-0">
      <div className="text-caption text-label-2">{label}</div>
      <div className="truncate text-headline tabular">{value}</div>
    </div>
  );
}

function SignalCard({ title, lines, empty }: { title: string; lines: [string, string][]; empty?: string }) {
  return (
    <Card className="!p-4">
      <div className="text-footnote font-semibold">{title}</div>
      {empty ? (
        <p className="mt-2 text-footnote text-label-2">{empty}</p>
      ) : (
        <dl className="mt-2 space-y-1 text-footnote">
          {lines.map(([k, v]) => (
            <div key={k} className="flex justify-between gap-2">
              <dt className="text-label-2">{k}</dt>
              <dd className="truncate font-medium capitalize tabular">{v}</dd>
            </div>
          ))}
        </dl>
      )}
    </Card>
  );
}

const REC = {
  BUY: { icon: ArrowUpCircle, cls: "text-positive", fill: "bg-positive-fill" },
  HOLD: { icon: MinusCircle, cls: "text-tint", fill: "bg-tint-fill" },
  SELL: { icon: ArrowDownCircle, cls: "text-negative", fill: "bg-negative-fill" },
};

function AIPanel({ ai, ctx, onRegenerate, regenerating }: { ai: AIResult; ctx: AssessmentContext; onRegenerate: () => void; regenerating: boolean }) {
  const toast = useToast();
  const [pdfBusy, setPdfBusy] = useState(false);
  const rec = REC[ai.recommendation];
  const Icon = rec.icon;
  const ccy = ctx.fundamental.profile.currency;
  const price = ctx.technical.quote.price;

  async function pdf() {
    setPdfBusy(true);
    try {
      await download("/reports/assessment.pdf", { method: "POST", json: { context: ctx, ai } });
    } catch (e) {
      toast((e as Error).message, "error");
    } finally {
      setPdfBusy(false);
    }
  }

  return (
    <motion.div variants={stagger(0.07)} initial="initial" animate="animate" exit={{ opacity: 0 }} className="space-y-5">
      <motion.div variants={staggerItem}>
        <Card className="overflow-hidden !p-0">
          <div className="grid md:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)]">
            <div className={`flex flex-col items-center justify-center gap-2 p-8 text-center ${rec.fill}`}>
              <motion.span initial={{ scale: 0.4, rotate: -20 }} animate={{ scale: 1, rotate: 0 }} transition={spring.bouncy}>
                <Icon className={`size-14 ${rec.cls}`} strokeWidth={1.6} />
              </motion.span>
              <div className={`text-[44px] leading-none font-bold tracking-[-0.03em] ${rec.cls}`}>{ai.recommendation}</div>
              <div className="text-footnote text-label-2">{ai.time_horizon}</div>
            </div>
            <div className="space-y-5 p-6">
              <div>
                <div className="flex items-baseline justify-between">
                  <span className="text-footnote font-medium text-label-2">Confidence</span>
                  <span className="text-headline tabular">{ai.confidence}/10</span>
                </div>
                <div className="mt-2 flex gap-1" role="meter" aria-valuemin={1} aria-valuemax={10} aria-valuenow={ai.confidence} aria-label="Confidence">
                  {Array.from({ length: 10 }).map((_, i) => (
                    <motion.span
                      key={i}
                      initial={{ scaleY: 0.3, opacity: 0 }}
                      animate={{ scaleY: 1, opacity: 1 }}
                      transition={{ ...spring.bouncy, delay: 0.15 + i * 0.03 }}
                      className={`h-2 flex-1 rounded-full ${i < ai.confidence ? "bg-tint" : "bg-fill"}`}
                    />
                  ))}
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <Mini label="Price now" value={money(price, ccy)} />
                <Mini
                  label="Price target"
                  value={ai.price_target ? (
                    <span>
                      {money(ai.price_target, ccy)}{" "}
                      <Delta value={ai.price_target - price} className="text-footnote">{pct(((ai.price_target - price) / price) * 100, 1)}</Delta>
                    </span>
                  ) : "—"}
                />
              </div>
              <p className="text-callout">{ai.summary}</p>
            </div>
          </div>
        </Card>
      </motion.div>

      <motion.div variants={staggerItem}>
        <Card>
          <CardHeader title="Position advice" />
          <p className="text-callout">{ai.position_advice}</p>
        </Card>
      </motion.div>

      <motion.div variants={staggerItem} className="grid gap-5 md:grid-cols-2">
        <Card>
          <CardHeader title="Strengths" />
          <ul className="space-y-2.5">
            {ai.strengths.map((s) => (
              <li key={s} className="flex gap-2.5 text-callout">
                <CheckCircle2 className="mt-0.5 size-[18px] shrink-0 text-positive" aria-hidden />
                {s}
              </li>
            ))}
          </ul>
        </Card>
        <Card>
          <CardHeader title="Risks" />
          <ul className="space-y-2.5">
            {ai.risks.map((s) => (
              <li key={s} className="flex gap-2.5 text-callout">
                <TriangleAlert className="mt-0.5 size-[18px] shrink-0 text-warning" aria-hidden />
                {s}
              </li>
            ))}
          </ul>
        </Card>
      </motion.div>

      <motion.div variants={staggerItem}>
        <Card>
          <CardHeader title="How Gemini reasoned" subtitle={`${ai.model} · step by step`} />
          {ai.steps.map((s, i) => (
            <Disclosure key={i} defaultOpen={i < 2} title={s.title} leading={<span className="flex size-7 shrink-0 items-center justify-center rounded-full bg-fill text-caption font-semibold tabular">{i + 1}</span>}>
              <p className="pl-10 text-callout text-label-2">{s.content}</p>
            </Disclosure>
          ))}
        </Card>
      </motion.div>

      <motion.div variants={staggerItem} className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-footnote text-label-2">
          Analysts say <Badge className="capitalize">{ctx.fundamental.analyst.recommendation_key?.replace("_", " ") ?? "n/a"}</Badge> · Saved to your{" "}
          <Link href="/track-record" className="font-semibold text-tint">
            track record
          </Link>
        </p>
        <div className="flex gap-2">
          <Button variant="gray" loading={regenerating} onClick={onRegenerate}>
            Regenerate
          </Button>
          <Button variant="tinted" loading={pdfBusy} icon={<FileDown className="size-[18px]" />} onClick={pdf}>
            Download PDF
          </Button>
        </div>
      </motion.div>
      <p className="text-center text-caption text-label-2">AI output can be wrong. This is not financial advice.</p>
    </motion.div>
  );
}
