"use client";

import { BrainCircuit, Trophy } from "lucide-react";
import { motion } from "motion/react";
import { useState } from "react";

import { HBars, SERIES, TimeSeries } from "@/components/charts/charts";
import { PageHeader, ResearchTabs } from "@/components/shell/page-header";
import { ResearchPage } from "@/components/shell/research-page";
import { SymbolPicker, useSymbol } from "@/components/shell/symbol-picker";
import { Button } from "@/components/ui/button";
import { Badge, Card, CardHeader } from "@/components/ui/card";
import { Segmented, Select, Slider } from "@/components/ui/controls";
import { Banner, EmptyState } from "@/components/ui/feedback";
import { Disclosure } from "@/components/ui/overlay";
import { Delta } from "@/components/ui/stat";
import { api } from "@/lib/api";
import { PERIODS, number, pct } from "@/lib/format";
import { spring, stagger, staggerItem } from "@/lib/motion";
import type { Prediction } from "@/lib/types";

const DEFAULTS = { rf_estimators: 100, rf_depth: 10, svm_c: 1, svm_gamma: "scale", test_size: 20 };

export default function Page() {
  return (
    <ResearchPage>
      <ForecastView />
    </ResearchPage>
  );
}

function ForecastView() {
  const [symbol, setSymbol] = useSymbol();
  const [period, setPeriod] = useState<string>("2y");
  const [params, setParams] = useState(DEFAULTS);
  const [result, setResult] = useState<Prediction | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);

  async function run() {
    setRunning(true);
    setError(null);
    try {
      setResult(await api<Prediction>(`/stocks/${encodeURIComponent(symbol)}/predict`, { method: "POST", json: { period, ...params } }));
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
        subtitle="Machine-learning models trained on technical features to predict the next close"
        actions={
          <>
            <SymbolPicker symbol={symbol} onChange={(s) => { setSymbol(s); setResult(null); }} />
            <Segmented label="Training period" options={PERIODS.filter((p) => p.value !== "1mo")} value={period} onChange={setPeriod} />
          </>
        }
      />

      <div className="space-y-5">
        <Card>
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <h3 className="text-headline">Random Forest and SVM</h3>
              <p className="text-footnote text-label-2">Chronological split: models are tested only on data after their training window.</p>
            </div>
            <Button size="lg" loading={running} icon={<BrainCircuit className="size-5" />} onClick={run}>
              {result ? "Retrain" : "Train Models"}
            </Button>
          </div>
          <div className="mt-2">
            <Disclosure title="Model parameters">
              <div className="grid gap-x-8 gap-y-1 sm:grid-cols-2 lg:grid-cols-3">
                <Slider label="Trees" min={50} max={200} step={10} value={params.rf_estimators} onChange={set("rf_estimators")} />
                <Slider label="Max depth" min={3} max={20} value={params.rf_depth} onChange={set("rf_depth")} />
                <Slider label="Test size" min={10} max={40} value={params.test_size} onChange={set("test_size")} format={(v) => `${v}%`} />
                <Slider label="SVM C" min={0.1} max={20} step={0.1} value={params.svm_c} onChange={set("svm_c")} format={(v) => v.toFixed(1)} />
                <div className="pt-2">
                  <Select label="SVM gamma" value={params.svm_gamma} onChange={(e) => set("svm_gamma")(e.target.value)} options={["scale", "auto", "0.001", "0.01", "0.1", "1.0"]} />
                </div>
              </div>
            </Disclosure>
            <Disclosure title="How to read the results">
              <dl className="space-y-3 text-callout">
                <div><dt className="font-semibold">RMSE and MAE</dt><dd className="text-label-2">Average prediction error in price units on the test window. Lower is better. Compare to the share price: under 2% of price is strong.</dd></div>
                <div><dt className="font-semibold">Directional accuracy</dt><dd className="text-label-2">How often the model called the day-to-day direction correctly. 50% is a coin flip; consistently above 60% is meaningful. Above 80% usually means overfitting.</dd></div>
                <div><dt className="font-semibold">Feature importance</dt><dd className="text-label-2">Which inputs the Random Forest relied on most. A single dominant moving average means the model is mostly echoing recent price.</dd></div>
              </dl>
            </Disclosure>
          </div>
        </Card>

        {error && <Banner tone="error" title="Training failed">{error}</Banner>}

        {!result && !running && !error && (
          <Card>
            <EmptyState icon={<BrainCircuit className="size-7" />} title={`Forecast ${symbol}`}>
              Train both models on {PERIODS.find((p) => p.value === period)?.label} of history to see backtest accuracy and a next-session estimate.
            </EmptyState>
          </Card>
        )}

        {result && <Results r={result} />}
      </div>
    </>
  );
}

function Results({ r }: { r: Prediction }) {
  const drift = Math.max(...r.models.map((m) => Math.abs(m.next_close - r.last_close) / r.last_close));
  return (
    <motion.div variants={stagger(0.06)} initial="initial" animate="animate" className="space-y-5">
      {drift > 0.08 && (
        <motion.div variants={staggerItem}>
          <Banner tone="warning" title="Treat this forecast with caution">
            A model’s estimate is {pct(drift * 100, 0, false)} away from the last close. Tree-based models can’t predict beyond the price range they were trained on, so they lag after strong rallies or sell-offs.
          </Banner>
        </motion.div>
      )}

      <div className="grid gap-5 md:grid-cols-2">
        {r.models.map((m, i) => {
          const change = ((m.next_close - r.last_close) / r.last_close) * 100;
          const best = m.name === r.best_model;
          return (
            <motion.div key={m.name} variants={staggerItem}>
              <Card className="h-full">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="size-2.5 rounded-full" style={{ background: SERIES[i + 1] }} />
                    <h3 className="text-headline">{m.name}</h3>
                  </div>
                  {best && (
                    <motion.span initial={{ scale: 0.5, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} transition={spring.bouncy}>
                      <Badge tone="positive"><Trophy className="size-3" /> Lowest error</Badge>
                    </motion.span>
                  )}
                </div>
                <div className="mt-4 text-footnote text-label-2">Next-session estimate</div>
                <div className="flex items-baseline gap-2">
                  <span className="text-title-1 tabular">{number(m.next_close, 2)}</span>
                  <Delta value={change} className="text-callout">{pct(change)}</Delta>
                </div>
                <dl className="mt-5 grid grid-cols-3 gap-3 border-t-[0.5px] border-separator pt-4 text-center">
                  <div><dt className="text-caption text-label-2">RMSE</dt><dd className="text-headline tabular">{number(m.metrics.rmse, 2)}</dd></div>
                  <div><dt className="text-caption text-label-2">MAE</dt><dd className="text-headline tabular">{number(m.metrics.mae, 2)}</dd></div>
                  <div><dt className="text-caption text-label-2">Direction</dt><dd className="text-headline tabular">{m.metrics.directional_accuracy != null ? pct(m.metrics.directional_accuracy * 100, 0, false) : "—"}</dd></div>
                </dl>
              </Card>
            </motion.div>
          );
        })}
      </div>

      <motion.div variants={staggerItem}>
        <Card>
          <CardHeader title="Backtest" subtitle={`Predicted vs actual close over the ${r.samples.test}-day test window · trained on ${r.samples.train} days, ${r.samples.features} features · last close ${number(r.last_close, 2)}`} />
          <TimeSeries
            data={r.series}
            height={300}
            format={(v) => number(v, 2)}
            ariaLabel="Model predictions versus actual closing price"
            lines={[
              { key: "actual", label: "Actual", color: SERIES[0], width: 2.5 },
              { key: "rf", label: "Random Forest", color: SERIES[1], width: 1.5 },
              { key: "svm", label: "SVM", color: SERIES[2], width: 1.5 },
            ]}
          />
        </Card>
      </motion.div>

      <motion.div variants={staggerItem}>
        <Card>
          <CardHeader title="What drives the Random Forest" subtitle="Top 10 features by importance" />
          <HBars data={r.feature_importance.slice(0, 10)} labelKey="feature" valueKey="importance" format={(v) => pct(v * 100, 1, false)} ariaLabel="Feature importance" />
        </Card>
      </motion.div>

      <p className="text-center text-caption text-label-2">Model outputs are statistical estimates, not investment advice.</p>
    </motion.div>
  );
}
