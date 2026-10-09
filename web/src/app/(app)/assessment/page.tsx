"use client";

import { ArrowDownCircle, ArrowUpCircle, CheckCircle2, CircleDot, FileDown, Info, MinusCircle, ShieldCheck, Sparkles, TriangleAlert, XCircle } from "lucide-react";
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
import { EvidenceGuide } from "@/components/ui/evidence";
import { Disclosure } from "@/components/ui/overlay";
import { Delta } from "@/components/ui/stat";
import { useToast } from "@/components/ui/toast";
import { api, download } from "@/lib/api";
import { PERIODS, money, number, pct } from "@/lib/format";
import { spring, stagger, staggerItem } from "@/lib/motion";
import type { AIResult, AssessmentContext, EntryPlan, Evaluation, EvaluationFinding } from "@/lib/types";

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
  const [evaluation, setEvaluation] = useState<Evaluation | null>(null);
  const [step, setStep] = useState<"idle" | "context" | "ai" | "evaluate">("idle");
  const [error, setError] = useState<string | null>(null);

  async function gather() {
    setStep("context");
    setError(null);
    setAi(null);
    setEvaluation(null);
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
      setEvaluation(null);
      toast("Assessment saved to your track record");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setStep("idle");
    }
  }

  async function evaluate() {
    if (!ctx || !ai) return;
    setStep("evaluate");
    setError(null);
    try {
      const result = await api<Evaluation>(`/stocks/${encodeURIComponent(ctx.symbol)}/assessment/evaluate`, { method: "POST", json: { context: ctx, ai } });
      setEvaluation(result);
      if (result.saved) toast("Evaluation added to your track record");
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
        actions={<SymbolPicker symbol={symbol} onChange={(s) => { setSymbol(s); setCtx(null); setAi(null); setEvaluation(null); }} />}
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
                  <AIPanel
                    key="ai"
                    ai={ai}
                    ctx={ctx}
                    onRegenerate={generate}
                    regenerating={step === "ai"}
                    evaluation={evaluation}
                    onEvaluate={evaluate}
                    evaluating={step === "evaluate"}
                  />
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
          title="Forecast"
          empty={!p ? "Not enough history" : undefined}
          lines={p ? [
            ["Models", p.any_skill ? `${p.best?.name} beats no change` : "No edge over no change"],
            ["Best skill", p.best?.skill != null ? pct(p.best.skill * 100, 2) : "—"],
            ["80% range", `${number(p.range.next["80"].low, 2)}–${number(p.range.next["80"].high, 2)}`],
          ] : []}
        />
        <SignalCard
          title="Sentiment"
          empty={!s ? (ctx.sentiment_status.error ?? (ctx.sentiment_status.requested ? (ctx.sentiment_status.enabled ? "No headlines found" : "Not configured") : "Not included")) : undefined}
          lines={s ? [
            ["Tone", s.overall === "Neutral" ? "No clear tilt" : s.overall ?? "Too few articles"],
            ["Net tone", s.index != null ? `${s.index >= 0 ? "+" : ""}${number(s.index, 2)}` : "—"],
            ["Headlines", `${s.n} in ${s.days} days`],
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

function AIPanel({
  ai,
  ctx,
  onRegenerate,
  regenerating,
  evaluation,
  onEvaluate,
  evaluating,
}: {
  ai: AIResult;
  ctx: AssessmentContext;
  onRegenerate: () => void;
  regenerating: boolean;
  evaluation: Evaluation | null;
  onEvaluate: () => void;
  evaluating: boolean;
}) {
  const toast = useToast();
  const [pdfBusy, setPdfBusy] = useState(false);
  const rec = REC[ai.recommendation];
  const Icon = rec.icon;
  const ccy = ctx.fundamental.profile.currency;
  const price = ctx.technical.quote.price;

  async function pdf() {
    setPdfBusy(true);
    try {
      await download("/reports/assessment.pdf", { method: "POST", json: { context: ctx, ai, evaluation } });
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
        <AnimatePresence mode="wait">
          {evaluation ? (
            <EvaluationPanel key="evaluation" ev={evaluation} />
          ) : (
            <motion.div key="evaluate-cta" exit={{ opacity: 0, scale: 0.98 }} transition={spring.smooth}>
              <Card>
                <div className="flex flex-col items-start gap-4 sm:flex-row sm:items-center sm:justify-between">
                  <div className="flex gap-3">
                    <ShieldCheck className="mt-0.5 size-6 shrink-0 text-tint" aria-hidden />
                    <div>
                      <h3 className="text-headline">Get a second look</h3>
                      <p className="mt-0.5 text-callout text-label-2">
                        Checks this recommendation against the data with research-based skills: claims, the case against it, valuation, earnings timing, and an entry plan. It flags problems and can lower confidence, but doesn’t change the call.
                      </p>
                    </div>
                  </div>
                  <Button variant="tinted" loading={evaluating} icon={<ShieldCheck className="size-[18px]" />} onClick={onEvaluate} className="shrink-0">
                    Evaluate
                  </Button>
                </div>
              </Card>
            </motion.div>
          )}
        </AnimatePresence>
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

const VERDICT = {
  stands: { label: "Stands", tone: "positive", text: "The recommendation holds up against the data." },
  weakened: { label: "Weakened", tone: "warning", text: "Parts of the argument don’t hold up." },
  contradicted: { label: "Contradicted", tone: "negative", text: "The main argument rests on claims that are wrong or unreliable." },
} as const;

const APPROACH: Record<EntryPlan["approach"], string> = { all_at_once: "All at once", staged: "Staged", wait: "Wait" };

function EvaluationPanel({ ev }: { ev: Evaluation }) {
  const v = VERDICT[ev.verdict];
  const titles = Object.fromEntries(ev.skills.map((s) => [s.name, s.title]));
  const failed = ev.checks.filter((c) => !c.passed);
  // Problems first, worst first; supporting findings after.
  const rank = (f: EvaluationFinding) => (f.stance === "challenges" ? { major: 0, minor: 1, info: 2 }[f.severity] : f.stance === "neutral" ? 3 : 4);
  const findings = [...ev.findings].sort((a, b) => rank(a) - rank(b));
  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={spring.smooth} className="space-y-5">
      <Card>
        <CardHeader
          title="Second look"
          subtitle={`${ev.skills.length} skills · ${ev.model}`}
          action={<Badge tone={v.tone}>{v.label}</Badge>}
        />
        <div className="grid gap-5 md:grid-cols-[auto_1fr] md:items-start">
          <div className="flex items-baseline gap-2" aria-label={`Confidence ${ev.original_confidence} out of 10, adjusted to ${ev.confidence_adjusted}`}>
            <span className="text-caption text-label-2">Confidence</span>
            <span className="text-headline tabular">
              {ev.confidence_adjusted < ev.original_confidence ? (
                <>
                  <span className="text-label-3 line-through">{ev.original_confidence}</span> {ev.confidence_adjusted}/10
                </>
              ) : (
                `${ev.confidence_adjusted}/10`
              )}
            </span>
          </div>
          <div className="space-y-1">
            <p className="text-callout font-medium">{v.text}</p>
            <p className="text-callout text-label-2">{ev.summary}</p>
          </div>
        </div>

        <ul className="mt-5 space-y-3 border-t-[0.5px] border-separator pt-4">
          {findings.map((f, i) => (
            <FindingRow key={i} f={f} skill={titles[f.skill] ?? f.skill} />
          ))}
        </ul>
      </Card>

      <div className={`grid gap-5 ${ev.entry_plan ? "md:grid-cols-2" : ""}`}>
        <Card>
          <CardHeader title="The case against" />
          <p className="text-callout">{ev.counter_case}</p>
          {ev.invalidation.length > 0 && (
            <>
              <h4 className="mt-4 mb-2 text-footnote font-semibold text-label-2">What would show the call is wrong</h4>
              <ul className="space-y-2">
                {ev.invalidation.map((x) => (
                  <li key={x} className="flex gap-2.5 text-callout">
                    <CircleDot className="mt-0.5 size-4 shrink-0 text-label-2" aria-hidden />
                    {x}
                  </li>
                ))}
              </ul>
            </>
          )}
        </Card>
        {ev.entry_plan && (
          <Card>
            <CardHeader title="Entry plan" action={<Badge tone="tint">{APPROACH[ev.entry_plan.approach]}</Badge>} />
            <dl className="space-y-3 text-callout">
              <div>
                <dt className="text-footnote font-semibold text-label-2">How</dt>
                <dd>{ev.entry_plan.detail}</dd>
              </div>
              <div>
                <dt className="text-footnote font-semibold text-label-2">Size</dt>
                <dd>{ev.entry_plan.size}</dd>
              </div>
              <div>
                <dt className="text-footnote font-semibold text-label-2">Review</dt>
                <dd>{ev.entry_plan.review_when}</dd>
              </div>
            </dl>
            <p className="mt-4 text-caption text-label-2">Plans the size and pace of buying, not the price: timing the market hasn’t worked reliably.</p>
          </Card>
        )}
      </div>

      <Card className="!py-2">
        <Disclosure title="Automatic checks" subtitle={failed.length ? `${failed.length} of ${ev.checks.length} flagged` : `${ev.checks.length} passed`}>
          <p className="mb-3 text-footnote text-label-2">
            Rule checks run in code before Gemini reviews. They read wording with simple patterns, so Gemini confirms or dismisses each flag in the findings above.
          </p>
          {ev.checks.length ? (
            <ul className="space-y-2 pb-2">
              {ev.checks.map((c, i) => (
                <li key={i} className="flex gap-2.5 text-footnote">
                  {c.passed ? <CheckCircle2 className="mt-px size-4 shrink-0 text-positive" aria-label="Passed" /> : <TriangleAlert className="mt-px size-4 shrink-0 text-warning" aria-label="Flagged" />}
                  <span>
                    <span className="font-semibold">{c.check}</span> <span className="text-label-2">· {titles[c.skill] ?? c.skill}</span>
                    <br />
                    <span className="text-label-2">{c.detail}</span>
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="pb-2 text-footnote text-label-2">No rule checks applied to this recommendation.</p>
          )}
        </Disclosure>
        <Disclosure title="Skills & evidence" subtitle="Why each check is used">
          <div className="pb-3">
            <EvidenceGuide
              intro="Each skill is a set of instructions with facts computed in code, so Gemini judges from given numbers rather than doing arithmetic. Skills are chosen by rules: claims and the counter-case always run; the others when they apply. Ratings describe how well research supports each check."
              outro="Language models reviewing their own work tend to agree with it, so the review is tied to computed facts, may only lower confidence, and can’t change the recommendation."
              sections={[{
                items: ev.skills.map((s) => ({
                  name: s.title,
                  evidence: s.evidence,
                  read: `${s.description} Runs when: ${s.applies_when.charAt(0).toLowerCase()}${s.applies_when.slice(1)}`,
                  verdict: s.rationale,
                  sources: s.sources,
                })),
              }]}
            />
          </div>
        </Disclosure>
      </Card>
    </motion.div>
  );
}

function FindingRow({ f, skill }: { f: EvaluationFinding; skill: string }) {
  const icon =
    f.stance === "supports" ? <CheckCircle2 className="mt-0.5 size-[18px] shrink-0 text-positive" aria-label="Supports" />
    : f.stance === "neutral" ? <Info className="mt-0.5 size-[18px] shrink-0 text-label-2" aria-label="Note" />
    : f.severity === "major" ? <XCircle className="mt-0.5 size-[18px] shrink-0 text-negative" aria-label="Major challenge" />
    : <TriangleAlert className="mt-0.5 size-[18px] shrink-0 text-warning" aria-label="Challenge" />;
  return (
    <li className="flex gap-2.5 text-callout">
      {icon}
      <div className="min-w-0">
        <div className="mb-0.5 flex flex-wrap items-center gap-1.5 text-caption text-label-2">
          {skill}
          {f.stance === "challenges" && f.severity !== "info" && <Badge tone={f.severity === "major" ? "negative" : "warning"} className="!h-5 !px-2">{f.severity}</Badge>}
        </div>
        {f.finding}
      </div>
    </li>
  );
}
