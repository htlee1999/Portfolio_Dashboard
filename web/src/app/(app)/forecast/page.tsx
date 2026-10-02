"use client";

import { BookOpen, BrainCircuit, Trophy } from "lucide-react";
import { motion } from "motion/react";
import { useState } from "react";

import { HBars, Legend, MUTED, SERIES, TimeSeries } from "@/components/charts/charts";
import { PageHeader, ResearchTabs } from "@/components/shell/page-header";
import { ResearchPage } from "@/components/shell/research-page";
import { SymbolPicker, useSymbol } from "@/components/shell/symbol-picker";
import { Button } from "@/components/ui/button";
import { Badge, Card, CardHeader } from "@/components/ui/card";
import { Segmented, Slider, Switch } from "@/components/ui/controls";
import { EvidenceDot, EvidenceGuide } from "@/components/ui/evidence";
import { Banner, EmptyState } from "@/components/ui/feedback";
import { Disclosure } from "@/components/ui/overlay";
import { Delta } from "@/components/ui/stat";
import { api, useApi } from "@/lib/api";
import { FORECAST, GUIDE_SECTIONS, MODEL_EVIDENCE } from "@/lib/forecast-evidence";
import { number, pct, shortDate } from "@/lib/format";
import { spring, stagger, staggerItem } from "@/lib/motion";
import type { Coverage, Features, ModelMetrics, ModelResult, Prediction } from "@/lib/types";

const DEFAULTS = { rf_estimators: 200, rf_depth: 6, test_size: 30 };
const PERIODS = [
  { value: "1y", label: "1Y" },
  { value: "2y", label: "2Y" },
  { value: "5y", label: "5Y" },
] as const;
type Period = (typeof PERIODS)[number]["value"];

const VERDICT = {
  skill: { tone: "positive", label: "Beats no change" },
  "no edge": { tone: "neutral", label: "No edge" },
  worse: { tone: "negative", label: "Worse than no change" },
} as const satisfies Record<ModelMetrics["verdict"], { tone: string; label: string }>;

export default function Page() {
  return (
    <ResearchPage>
      <ForecastView />
    </ResearchPage>
  );
}

function ForecastView() {
  const [symbol, setSymbol] = useSymbol();
  const [period, setPeriod] = useState<Period>("2y");
  const [params, setParams] = useState(DEFAULTS);
  const [useChronos, setUseChronos] = useState(false);
  const [result, setResult] = useState<Prediction | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const { data: features } = useApi<Features>("/features");
  const chronos = features?.chronos;

  async function run() {
    setRunning(true);
    setError(null);
    try {
      setResult(
        await api<Prediction>(`/stocks/${encodeURIComponent(symbol)}/predict`, {
          method: "POST",
          json: { period, ...params, use_chronos: useChronos && !!chronos?.available },
        }),
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setRunning(false);
    }
  }

  const set = <K extends keyof typeof DEFAULTS>(k: K) => (v: (typeof DEFAULTS)[K]) => setParams((p) => ({ ...p, [k]: v }));

  return (
    <>
      <ResearchTabs />
      <PageHeader
        title="Forecast"
        eyebrow="Research"
        subtitle="Next-session return models tested against a no-change forecast, and a volatility range for the next close"
        actions={
          <>
            <SymbolPicker symbol={symbol} onChange={(s) => { setSymbol(s); setResult(null); }} />
            <Segmented label="Training period" options={PERIODS} value={period} onChange={setPeriod} />
          </>
        }
      />

      <div className="space-y-5">
        <Card>
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <h3 className="text-headline">Forecast models</h3>
              <p className="text-footnote text-label-2">Walk-forward test: each model is refitted monthly and scored only on days after its training data.</p>
            </div>
            <Button size="lg" loading={running} icon={<BrainCircuit className="size-5" />} onClick={run}>
              {result ? "Retrain" : "Train Models"}
            </Button>
          </div>
          <div className="mt-2">
            <Disclosure title="Model settings">
              <div className="grid gap-x-8 gap-y-1 sm:grid-cols-3">
                <Slider label="Random forest trees" min={50} max={300} step={10} value={params.rf_estimators} onChange={set("rf_estimators")} />
                <Slider label="Random forest depth" min={2} max={12} value={params.rf_depth} onChange={set("rf_depth")} />
                <Slider label="Test window" min={20} max={40} value={params.test_size} onChange={set("test_size")} format={(v) => `${v}%`} />
              </div>
              <div className="mt-3 border-t-[0.5px] border-separator pt-2">
                <Switch
                  label="Include Chronos-Bolt (pretrained)"
                  description={
                    chronos && !chronos.available
                      ? `${chronos.note}. Requires torch and transformers.`
                      : "Amazon's pretrained time-series transformer, tiny version. About 35 MB download on first use and around 750 MB of memory while it runs."
                  }
                  checked={useChronos && !!chronos?.available}
                  onChange={(v) => chronos?.available && setUseChronos(v)}
                />
              </div>
            </Disclosure>
          </div>
        </Card>

        {error && <Banner tone="error" title="Training failed">{error}</Banner>}

        {!result && !running && !error && (
          <Card>
            <EmptyState icon={<BrainCircuit className="size-7" />} title={`Forecast ${symbol}`}>
              Train the models on {PERIODS.find((p) => p.value === period)?.label} of history to see whether any of them beats a no-change forecast, and the likely range for the next close.
            </EmptyState>
          </Card>
        )}

        {result && <Results r={result} />}

        <Card>
          <Disclosure
            title="Method & evidence"
            subtitle="Why these models were chosen, how they are tested, and sources"
            leading={<BookOpen className="size-5 text-tint" />}
          >
            <EvidenceGuide
              sections={GUIDE_SECTIONS.map((g) => ({ title: g.title, items: g.keys.map((k) => FORECAST[k]) }))}
              intro="Model ratings summarise peer-reviewed evidence that each approach forecasts daily stock returns, or for GARCH, volatility. Strong means the result has held across many studies and markets; mixed means it has worked in some settings, usually with far more data than one stock provides; weak means little or no evidence for this use. Testing methods have no rating; they are there to keep the models honest."
              outro="Daily returns are mostly noise, so even a genuinely useful model will look only slightly better than no change, and the edge can disappear as conditions change. The range is the more dependable output: it describes how far the price is likely to move, not which way."
            />
          </Disclosure>
        </Card>
      </div>
    </>
  );
}

function Results({ r }: { r: Prediction }) {
  const skilled = r.models.filter((m) => m.metrics.verdict === "skill").map((m) => m.name);
  return (
    <motion.div variants={stagger(0.06)} initial="initial" animate="animate" className="space-y-5">
      <motion.div variants={staggerItem}>
        {r.any_skill ? (
          <Banner tone="info" title={`${skilled.join(" and ")} beat the no-change forecast`}>
            The gain over the last {r.samples.test} trading days is statistically significant, but daily edges are small and often fade. Re-check on another training period before relying on it.
          </Banner>
        ) : (
          <Banner tone="info" title="No model beat the no-change forecast">
            Over the last {r.samples.test} trading days, none of the models predicted daily returns reliably better than assuming no change. That is the usual result for daily stock returns, so treat their forecasts as no signal and use the range instead.
          </Banner>
        )}
      </motion.div>

      {r.chronos?.note && (
        <motion.div variants={staggerItem}>
          <Banner tone="warning" title="Chronos-Bolt skipped">{r.chronos.note}</Banner>
        </motion.div>
      )}

      <motion.div variants={staggerItem} className="grid gap-5 lg:grid-cols-5">
        <RangeCard r={r} />
        <Card className="lg:col-span-3" padded={false}>
          <ModelTable r={r} />
        </Card>
      </motion.div>

      <motion.div variants={staggerItem}>
        <Card>
          <CardHeader
            title="Range backtest"
            subtitle={`Each day's 80% range (shaded) and 95% range (dashed), set the evening before, against the actual close · ${r.range.backtest.length} days`}
          />
          <Legend
            className="mb-3"
            items={[
              { label: "Actual close", color: SERIES[0] },
              { label: "80% range", color: SERIES[1] },
              { label: "95% range", color: MUTED, dashed: true },
            ]}
          />
          <TimeSeries
            data={r.range.backtest}
            height={300}
            legend={false}
            format={(v) => number(v, 2)}
            band={{ lower: "lo80", upper: "hi80", color: SERIES[1] }}
            ariaLabel="Next-day price range forecasts against the actual close"
            lines={[
              { key: "actual", label: "Actual close", color: SERIES[0], width: 2 },
              { key: "lo95", label: "95% range, low", color: MUTED, width: 1, dashed: true },
              { key: "hi95", label: "95% range, high", color: MUTED, width: 1, dashed: true },
            ]}
          />
        </Card>
      </motion.div>

      <motion.div variants={staggerItem}>
        <Card>
          <CardHeader
            title="Predicted vs actual daily return"
            subtitle="Forecasts that stay close to zero are what a model with little to go on should produce. Large swings that miss the actual moves are overfitting."
          />
          <TimeSeries
            data={r.series}
            height={280}
            format={(v) => pct(v, 1)}
            ariaLabel="Predicted versus actual daily returns"
            refLines={[{ y: 0 }]}
            lines={[
              { key: "actual", label: "Actual", color: MUTED, width: 1 },
              ...r.models.map((m, i) => ({ key: m.name, label: m.name, color: SERIES[i + 1], width: 1.75 })),
            ]}
          />
        </Card>
      </motion.div>

      <motion.div variants={staggerItem}>
        <Card>
          <CardHeader
            title="What the random forest leans on"
            subtitle="Top 10 inputs by importance. This shows what the model uses, not that it works: without skill, these are patterns in noise."
          />
          <HBars data={r.feature_importance.slice(0, 10)} labelKey="feature" valueKey="importance" format={(v) => pct(v * 100, 1, false)} ariaLabel="Feature importance" />
        </Card>
      </motion.div>

      <p className="text-center text-caption text-label-2">Model outputs are statistical estimates, not investment advice.</p>
    </motion.div>
  );
}

function coverageBadge(c: Coverage) {
  if (c.hit_rate == null || c.p_value == null) return null;
  if (c.p_value >= 0.05) return <Badge tone="positive">Calibrated</Badge>;
  return c.hit_rate < c.target ? <Badge tone="warning">Too narrow</Badge> : <Badge tone="warning">Too wide</Badge>;
}

function RangeCard({ r }: { r: Prediction }) {
  const g = r.range;
  const move = (v: number) => ((v - r.last_close) / r.last_close) * 100;
  return (
    <Card className="lg:col-span-2">
      <div className="flex items-center gap-2">
        <h3 className="text-headline">Next-session range</h3>
        <EvidenceDot info={FORECAST.garch} />
      </div>
      <p className="text-footnote text-label-2">
        {g.model} · from the {shortDate(r.last_date, true)} close of {number(r.last_close, 2)}
      </p>
      <div className="mt-4 space-y-3">
        {(["80", "95"] as const).map((lvl) => (
          <div key={lvl}>
            <div className="text-footnote text-label-2">{lvl}% likely between</div>
            <div className="flex flex-wrap items-baseline gap-x-2">
              <span className={lvl === "80" ? "text-title-1 tabular" : "text-title-3 tabular"}>
                {number(g.next[lvl].low, 2)} – {number(g.next[lvl].high, 2)}
              </span>
              <span className="text-callout tabular">
                <Delta value={move(g.next[lvl].low)}>{pct(move(g.next[lvl].low), 1)}</Delta>
                <span className="text-label-2"> / </span>
                <Delta value={move(g.next[lvl].high)}>{pct(move(g.next[lvl].high), 1)}</Delta>
              </span>
            </div>
          </div>
        ))}
      </div>
      <dl className="mt-5 space-y-2.5 border-t-[0.5px] border-separator pt-4 text-callout">
        <div className="flex items-baseline justify-between gap-3">
          <dt className="text-label-2">Daily volatility</dt>
          <dd className="tabular">
            {pct(g.sigma_pct, 2, false)}
            {g.long_run_sigma_pct != null && <span className="text-label-2"> · long-run {pct(g.long_run_sigma_pct, 2, false)}</span>}
          </dd>
        </div>
        {(["80", "95"] as const).map((lvl) => {
          const c = g.coverage[lvl];
          return (
            <div key={lvl} className="flex items-center justify-between gap-3">
              <dt className="flex items-center gap-2 text-label-2">
                Past {lvl}% ranges held
                {lvl === "80" && <EvidenceDot info={FORECAST.coverage} />}
              </dt>
              <dd className="flex items-center gap-2 tabular">
                {c.hit_rate != null ? pct(c.hit_rate * 100, 0, false) : "—"}
                <span className="text-label-2">of {c.n}</span>
                {coverageBadge(c)}
              </dd>
            </div>
          );
        })}
      </dl>
    </Card>
  );
}

function ModelTable({ r }: { r: Prediction }) {
  const cell = "[&>td]:px-3 [&>td]:py-2.5 [&>td:first-child]:pl-5 sm:[&>td:first-child]:pl-6 [&>td:last-child]:pr-5 sm:[&>td:last-child]:pr-6";
  return (
    <div className="pb-5 sm:pb-6">
      <div className="px-5 pt-5 sm:px-6 sm:pt-6">
        <CardHeader
          title="Models against no change"
          subtitle={`Scored on ${r.samples.test} test days after training on ${r.samples.train} · ${r.samples.features} inputs · refitted every ${r.samples.refit_every} days`}
        />
      </div>
      <div className="overflow-x-auto pb-1">
        <table className="w-full min-w-[640px] text-callout">
          <thead>
            <tr className="text-caption text-label-2 [&>th]:px-3 [&>th]:pb-2 [&>th]:font-medium [&>th:first-child]:pl-5 sm:[&>th:first-child]:pl-6 [&>th:last-child]:pr-5 sm:[&>th:last-child]:pr-6">
              <th className="text-left">Model</th>
              <th className="text-right">Next session</th>
              <th className="text-right">Skill</th>
              <th className="text-right">p-value</th>
              <th className="text-right">Direction right</th>
              <th className="text-right">Verdict</th>
            </tr>
          </thead>
          <tbody className="tabular">
            <tr className={`border-t-[0.5px] border-separator ${cell}`}>
              <td className="font-medium">
                <span className="flex items-center gap-2">No change <EvidenceDot info={FORECAST.no_change} /></span>
                <span className="block text-caption font-normal text-label-2">Benchmark</span>
              </td>
              <td className="text-right text-label-2">{pct(0, 2)}</td>
              <td className="text-right text-label-2">0%</td>
              <td className="text-right text-label-2">—</td>
              <td className="text-right text-label-2">
                {pct(r.baseline.up_share * 100, 0, false)}
                <span className="block text-caption">if always “up”</span>
              </td>
              <td className="text-right"><Badge>Benchmark</Badge></td>
            </tr>
            {r.models.map((m) => (
              <ModelRow key={m.name} m={m} best={m.name === r.best_model && m.metrics.verdict === "skill"} cls={cell} />
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-3 px-5 text-caption text-label-2 sm:px-6">
        Skill is the share of the no-change forecast’s error a model removes (out-of-sample R²). A model counts as better only if its p-value is below{" "}
        {number(r.alpha, 3)}: 0.05 divided across the {r.models.length} models tested.
      </p>
    </div>
  );
}

function ModelRow({ m, best, cls }: { m: ModelResult; best: boolean; cls: string }) {
  const x = m.metrics;
  const info = FORECAST[MODEL_EVIDENCE[m.name] ?? "ridge"];
  return (
    <tr className={`border-t-[0.5px] border-separator ${cls}`}>
      <td className="font-medium">
        <span className="flex items-center gap-2">
          {m.name}
          <EvidenceDot info={info} />
          {best && (
            <motion.span initial={{ scale: 0.5, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} transition={spring.bouncy}>
              <Trophy className="size-3.5 text-positive" aria-label="Best model" />
            </motion.span>
          )}
        </span>
        <span className="block text-caption font-normal text-label-2">
          {m.kind === "pretrained" ? `Pretrained${x.band80_hit != null ? ` · 80% range held ${pct(x.band80_hit * 100, 0, false)}` : ""}` : "Trained on this stock"}
        </span>
      </td>
      <td className="text-right">
        <Delta value={m.next_return}>{pct(m.next_return * 100, 2)}</Delta>
      </td>
      <td className="text-right">{x.skill != null ? pct(x.skill * 100, 1) : "—"}</td>
      <td className="text-right text-label-2">{x.dm_p != null ? number(x.dm_p, 2) : "—"}</td>
      <td className="text-right">
        {x.directional_accuracy != null ? pct(x.directional_accuracy * 100, 0, false) : "—"}
        {x.direction_ci && (
          <span className="block text-caption text-label-2">
            {pct(x.direction_ci[0] * 100, 0, false)}–{pct(x.direction_ci[1] * 100, 0, false)}
          </span>
        )}
      </td>
      <td className="text-right">
        <Badge tone={VERDICT[x.verdict].tone}>{VERDICT[x.verdict].label}</Badge>
      </td>
    </tr>
  );
}
