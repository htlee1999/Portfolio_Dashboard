"use client";

import { ExternalLink, Gauge, Newspaper } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useMemo, useState } from "react";

import { PageHeader, ResearchTabs } from "@/components/shell/page-header";
import { ResearchPage } from "@/components/shell/research-page";
import { SymbolPicker, useSymbol } from "@/components/shell/symbol-picker";
import { Button } from "@/components/ui/button";
import { Badge, Card, CardHeader } from "@/components/ui/card";
import { Segmented, Slider } from "@/components/ui/controls";
import { Banner, EmptyState, LoadingBlock } from "@/components/ui/feedback";
import { Disclosure } from "@/components/ui/overlay";
import { api, useApi } from "@/lib/api";
import { number, pct } from "@/lib/format";
import { spring, stagger, staggerItem } from "@/lib/motion";
import type { Article, Features, Sentiment } from "@/lib/types";

type Account = { plan: string | null; searches_left: number | null; used_this_month: number | null };

export default function Page() {
  return (
    <ResearchPage>
      <SentimentView />
    </ResearchPage>
  );
}

const TONE = { Positive: "positive", Negative: "negative", Neutral: "neutral" } as const;

function SentimentView() {
  const [symbol, setSymbol] = useSymbol();
  const { data: features, isLoading } = useApi<Features>("/features");
  const [count, setCount] = useState(20);
  const [source, setSource] = useState<"both" | "finance" | "news">("both");
  const [result, setResult] = useState<Sentiment | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [account, setAccount] = useState<Account | null>(null);
  const [checking, setChecking] = useState(false);

  async function analyze() {
    setRunning(true);
    setError(null);
    try {
      const r = await api<Sentiment>(`/stocks/${encodeURIComponent(symbol)}/sentiment`, { method: "POST", json: { num_articles: count, source } });
      setResult(r);
      setAccount((a) => (a && a.searches_left != null ? { ...a, searches_left: Math.max(0, a.searches_left - r.searches_used) } : a));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setRunning(false);
    }
  }

  async function checkAccount() {
    setChecking(true);
    try {
      setAccount(await api<Account>("/sentiment/account"));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setChecking(false);
    }
  }

  const enabled = features?.sentiment.enabled;

  return (
    <>
      <ResearchTabs />
      <PageHeader
        title="Sentiment"
        eyebrow="Research"
        subtitle="News headlines scored with VADER and TextBlob"
        actions={<SymbolPicker symbol={symbol} onChange={(s) => { setSymbol(s); setResult(null); }} />}
      />

      {isLoading ? (
        <LoadingBlock />
      ) : !enabled ? (
        <Card>
          <EmptyState icon={<Newspaper className="size-7" />} title="Sentiment analysis isn't set up">
            {!features?.sentiment.libraries
              ? "Install the NLP packages with pip install -r requirements.txt, then restart the API."
              : "Add SERP_API_KEY to your .env file (free keys at serpapi.com), then restart the API."}
          </EmptyState>
        </Card>
      ) : (
        <div className="space-y-5">
          <Card>
            <div className="grid gap-5 md:grid-cols-[1fr_auto] md:items-end">
              <div className="grid gap-5 sm:grid-cols-2">
                <Slider label="Articles per source" min={5} max={50} step={5} value={count} onChange={setCount} />
                <div>
                  <div className="mb-1.5 px-1 text-footnote font-medium text-label-2">News source</div>
                  <Segmented
                    label="News source"
                    value={source}
                    onChange={setSource}
                    className="w-full"
                    options={[
                      { value: "both", label: "Both" },
                      { value: "finance", label: "Google Finance" },
                      { value: "news", label: "Google News" },
                    ]}
                  />
                </div>
              </div>
              <Button size="lg" loading={running} onClick={analyze}>
                Analyze Sentiment
              </Button>
            </div>
            <div className="mt-4 flex flex-wrap items-center gap-3 border-t-[0.5px] border-separator pt-4 text-footnote text-label-2">
              <Gauge className="size-4" />
              {account ? (
                <span>
                  <span className="font-semibold text-label tabular">{account.searches_left ?? "—"}</span> searches left
                  {account.plan && ` · ${account.plan}`}
                  {account.used_this_month != null && ` · ${account.used_this_month} used this month`}
                </span>
              ) : (
                <span>Each analysis uses {source === "both" ? 2 : 1} SERPapi search{source === "both" ? "es" : ""}.</span>
              )}
              <Button variant="plain" size="sm" loading={checking} onClick={checkAccount}>
                {account ? "Refresh" : "Check Quota"}
              </Button>
            </div>
          </Card>

          {error && <Banner tone="error" title="Sentiment analysis failed">{error}</Banner>}
          {running && !result && <LoadingBlock label="Fetching and scoring headlines…" />}
          {result && <Results r={result} />}

          <Card>
            <Disclosure title="About these scores">
              <dl className="space-y-3 text-callout">
                <div><dt className="font-semibold">VADER compound</dt><dd className="text-label-2">−1 (very negative) to +1 (very positive). Tuned for short text like headlines. ≥ 0.05 counts as positive, ≤ −0.05 as negative.</dd></div>
                <div><dt className="font-semibold">TextBlob polarity and subjectivity</dt><dd className="text-label-2">A second, general-purpose opinion. Subjectivity runs 0 (factual) to 1 (opinion); highly subjective pieces deserve less weight.</dd></div>
                <div><dt className="font-semibold">Limits</dt><dd className="text-label-2">Automated scoring misses sarcasm and context. Read the articles, and use sentiment alongside technicals and fundamentals, not instead of them.</dd></div>
              </dl>
            </Disclosure>
          </Card>
        </div>
      )}
    </>
  );
}

function Results({ r }: { r: Sentiment }) {
  const [sort, setSort] = useState<"recent" | "positive" | "negative" | "subjective">("recent");
  const articles = useMemo(() => {
    const a = [...r.articles];
    if (sort === "positive") a.sort((x, y) => y.vader - x.vader);
    if (sort === "negative") a.sort((x, y) => x.vader - y.vader);
    if (sort === "subjective") a.sort((x, y) => y.subjectivity - x.subjectivity);
    return a;
  }, [r, sort]);

  if (!r.total) return <Banner tone="warning" title={`No recent articles found for ${r.symbol}`}>{r.errors.join(" · ") || "Try another source or symbol."}</Banner>;

  const segments = [
    { k: "Positive" as const, color: "var(--positive)" },
    { k: "Neutral" as const, color: "var(--series-muted)" },
    { k: "Negative" as const, color: "var(--negative)" },
  ];
  const marker = ((r.avg_vader + 1) / 2) * 100;

  return (
    <motion.div variants={stagger(0.05)} initial="initial" animate="animate" className="space-y-5">
      {r.errors.length > 0 && <Banner tone="warning" title="Some sources failed">{r.errors.join(" · ")}</Banner>}
      <motion.div variants={staggerItem}>
        <Card>
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <div className="text-footnote font-medium text-label-2">Overall sentiment for {r.symbol}</div>
              <div className="mt-1 text-title-1">{r.overall}</div>
              <div className="text-footnote text-label-2">{r.total} unique articles</div>
            </div>
            <div className="grid grid-cols-2 gap-6 text-right">
              <div><div className="text-caption text-label-2">VADER</div><div className="text-title-3 tabular">{r.avg_vader >= 0 ? "+" : ""}{number(r.avg_vader, 3)}</div></div>
              <div><div className="text-caption text-label-2">TextBlob</div><div className="text-title-3 tabular">{r.avg_polarity >= 0 ? "+" : ""}{number(r.avg_polarity, 3)}</div></div>
            </div>
          </div>

          {/* VADER gauge: −1 … +1 with a neutral midpoint */}
          <div className="mt-6" aria-label={`Average VADER score ${r.avg_vader.toFixed(3)} on a scale from −1 to +1`}>
            <div className="relative h-2 rounded-full bg-[linear-gradient(to_right,var(--negative),var(--fill-strong)_50%,var(--positive))] opacity-80">
              <motion.span
                initial={{ left: "50%" }}
                animate={{ left: `${marker}%` }}
                transition={spring.bouncy}
                className="absolute top-1/2 size-5 -translate-x-1/2 -translate-y-1/2 rounded-full border-[3px] border-[var(--bg-elevated)] bg-label shadow"
              />
            </div>
            <div className="mt-1.5 flex justify-between text-caption text-label-2"><span>−1 Negative</span><span>0</span><span>Positive +1</span></div>
          </div>

          {/* Distribution: one stacked bar with 2px surface gaps */}
          <div className="mt-6 flex h-3 gap-[2px] overflow-hidden rounded-full">
            {segments.map((s) =>
              r.pct[s.k] > 0 ? (
                <motion.span key={s.k} initial={{ flexGrow: 0 }} animate={{ flexGrow: r.pct[s.k] }} transition={spring.smooth} style={{ background: s.color, flexBasis: 0 }} />
              ) : null,
            )}
          </div>
          <ul className="mt-2 flex flex-wrap gap-x-5 gap-y-1 text-footnote">
            {segments.map((s) => (
              <li key={s.k} className="flex items-center gap-1.5">
                <span className="size-2.5 rounded-[3px]" style={{ background: s.color }} />
                {s.k} <span className="tabular text-label-2">{r.counts[s.k]} · {pct(r.pct[s.k], 0, false)}</span>
              </li>
            ))}
          </ul>
        </Card>
      </motion.div>

      <motion.div variants={staggerItem}>
        <Card padded={false}>
          <div className="flex flex-wrap items-center justify-between gap-3 px-5 pt-5 sm:px-6 sm:pt-6">
            <CardHeader title="Articles" />
            <Segmented
              size="sm"
              label="Sort articles"
              value={sort}
              onChange={setSort}
              options={[
                { value: "recent", label: "Recent" },
                { value: "positive", label: "Positive" },
                { value: "negative", label: "Negative" },
                { value: "subjective", label: "Subjective" },
              ]}
            />
          </div>
          <motion.ul layout className="mt-1">
            <AnimatePresence initial={false}>
              {articles.map((a) => (
                <ArticleRow key={a.title} a={a} />
              ))}
            </AnimatePresence>
          </motion.ul>
        </Card>
      </motion.div>
    </motion.div>
  );
}

function ArticleRow({ a }: { a: Article }) {
  return (
    <motion.li layout transition={spring.smooth} className="border-t-[0.5px] border-separator px-5 py-4 sm:px-6">
      <div className="flex items-start gap-3">
        <div className="min-w-0 flex-1">
          <a href={a.link} target="_blank" rel="noreferrer" className="group text-body font-semibold hover:text-tint">
            {a.title}
            <ExternalLink className="ml-1 inline size-3.5 opacity-0 transition-opacity group-hover:opacity-100" />
          </a>
          {a.snippet && <p className="mt-1 line-clamp-2 text-callout text-label-2">{a.snippet}</p>}
          <div className="mt-2 text-caption text-label-2">
            {a.source} · {a.date || "undated"} · {a.origin}
          </div>
        </div>
        <div className="flex shrink-0 flex-col items-end gap-1">
          <Badge tone={TONE[a.sentiment]}>{a.sentiment}</Badge>
          <span className="text-caption text-label-2 tabular">
            {a.vader >= 0 ? "+" : ""}
            {number(a.vader, 2)}
          </span>
        </div>
      </div>
    </motion.li>
  );
}
