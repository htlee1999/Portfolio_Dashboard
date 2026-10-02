"use client";

import { BookOpen, ExternalLink, Gauge, Newspaper } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useState } from "react";

import { SignedBars } from "@/components/charts/charts";
import { PageHeader, ResearchTabs } from "@/components/shell/page-header";
import { ResearchPage } from "@/components/shell/research-page";
import { SymbolPicker, useSymbol } from "@/components/shell/symbol-picker";
import { Button } from "@/components/ui/button";
import { Badge, Card, CardHeader } from "@/components/ui/card";
import { Segmented } from "@/components/ui/controls";
import { EvidenceDot, EvidenceGuide } from "@/components/ui/evidence";
import { Banner, EmptyState, LoadingBlock } from "@/components/ui/feedback";
import { Disclosure } from "@/components/ui/overlay";
import { Delta } from "@/components/ui/stat";
import { api, useApi } from "@/lib/api";
import { number, pct, relative, shortDate } from "@/lib/format";
import { spring, stagger, staggerItem } from "@/lib/motion";
import { GUIDE_SECTIONS, SENTIMENT } from "@/lib/sentiment-evidence";
import type { Article, ArticleStatus, Features, Sentiment, Tone } from "@/lib/types";

type Account = { plan: string | null; searches_left: number | null; used_this_month: number | null };
type Days = 7 | 30;

const TONE = { Positive: "positive", Negative: "negative", Neutral: "neutral" } as const satisfies Record<Tone, string>;

const LEFT_OUT: Record<Exclude<ArticleStatus, "scored">, { label: string; info?: keyof typeof SENTIMENT }> = {
  old: { label: "Older than the window", info: "window" },
  duplicate: { label: "Duplicate", info: "duplicates" },
  routine: { label: "Routine filing", info: "routine" },
  off_topic: { label: "Not about the company", info: "firm_specific" },
  undated: { label: "Undated" },
};

const leftOutLabel = (status: Exclude<ArticleStatus, "scored">, days: number) =>
  status === "old" ? `Older than ${days} days` : LEFT_OUT[status].label;

const signed = (v: number, digits = 2) => `${v >= 0 ? "+" : "−"}${number(Math.abs(v), digits)}`;

export default function Page() {
  return (
    <ResearchPage>
      <SentimentView />
    </ResearchPage>
  );
}

function SentimentView() {
  const [symbol, setSymbol] = useSymbol();
  const { data: features, isLoading } = useApi<Features>("/features");
  const [days, setDays] = useState<Days>(7);
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
      const r = await api<Sentiment>(`/stocks/${encodeURIComponent(symbol)}/sentiment`, { method: "POST", json: { days, source } });
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
  const scorer = features?.sentiment.scorer;

  return (
    <>
      <ResearchTabs />
      <PageHeader
        title="Sentiment"
        eyebrow="Research"
        subtitle="The tone of recent firm-specific headlines, read by a model trained on financial news"
        actions={<SymbolPicker symbol={symbol} onChange={(s) => { setSymbol(s); setResult(null); }} />}
      />

      {isLoading ? (
        <LoadingBlock />
      ) : !enabled ? (
        <Card>
          <EmptyState icon={<Newspaper className="size-7" />} title="Sentiment analysis isn't set up">
            {!features?.sentiment.libraries
              ? "Install the packages with pip install -r requirements.txt, then restart the API."
              : "Add SERP_API_KEY to your .env file (free keys at serpapi.com), then restart the API."}
          </EmptyState>
        </Card>
      ) : (
        <div className="space-y-5">
          <Card>
            <div className="grid gap-5 md:grid-cols-[1fr_auto] md:items-end">
              <div className="grid gap-5 sm:grid-cols-[auto_1fr]">
                <div>
                  <div className="mb-1.5 px-1 text-footnote font-medium text-label-2">Window</div>
                  <Segmented
                    label="Window"
                    value={String(days)}
                    onChange={(v) => setDays(Number(v) as Days)}
                    equal
                    className="[&>button]:px-4"
                    options={[
                      { value: "7", label: "7 days" },
                      { value: "30", label: "30 days" },
                    ]}
                  />
                </div>
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
                <span>Each analysis uses up to {source === "both" ? 2 : 1} SERPapi search{source === "both" ? "es" : ""}.</span>
              )}
              <Button variant="plain" size="sm" loading={checking} onClick={checkAccount}>
                {account ? "Refresh" : "Check Quota"}
              </Button>
            </div>
          </Card>

          {scorer && !scorer.finance && (
            <Banner tone="warning" title="Scoring with VADER, a general-purpose word list">
              {scorer.note}. VADER misreads much financial language; see Method & evidence.
            </Banner>
          )}
          {error && <Banner tone="error" title="Sentiment analysis failed">{error}</Banner>}
          {running && !result && <LoadingBlock label="Fetching and scoring headlines…" />}
          {result && <Results r={result} />}

          <Card>
            <Disclosure
              title="Method & evidence"
              subtitle="Why this model reads the headlines, which headlines count, and sources"
              leading={<BookOpen className="size-5 text-tint" />}
            >
              <EvidenceGuide
                sections={GUIDE_SECTIONS.map((g) => ({ title: g.title, items: g.keys.map((k) => SENTIMENT[k]) }))}
                intro="Scorer ratings summarise the evidence that each method reads the tone of financial text accurately. The rating on news tone as a return signal summarises the evidence that tone predicts returns. Strong means the result has held across many studies; mixed means it has worked in some settings, usually with far more news than one stock's headlines; weak means little or no support. Filtering and reading methods have no rating; they decide which headlines count and how far to trust the result."
                outro="Sentiment here describes how the news reads. It doesn't measure whether the news was already expected, and prices usually absorb it within days. Read the headlines behind the score, and use it alongside technicals and fundamentals."
              />
            </Disclosure>
          </Card>
        </div>
      )}
    </>
  );
}

function verdict(r: Sentiment) {
  if (r.overall == null) return { title: "Too few headlines", tone: "neutral" as const };
  if (r.overall === "Neutral") return { title: "No clear tilt", tone: "neutral" as const };
  return { title: r.overall, tone: TONE[r.overall] };
}

function Results({ r }: { r: Sentiment }) {
  const leftOut = Object.values(r.excluded).reduce((a, b) => a + b, 0);

  if (!r.articles.length)
    return <Banner tone="warning" title={`No headlines found for ${r.symbol}`}>{r.errors.join(" · ") || "Try another source or symbol."}</Banner>;

  return (
    <motion.div variants={stagger(0.05)} initial="initial" animate="animate" className="space-y-5">
      {r.errors.length > 0 && (
        <motion.div variants={staggerItem}>
          <Banner tone="warning" title="Some sources failed">{r.errors.join(" · ")}</Banner>
        </motion.div>
      )}
      {r.scorer_note && (
        <motion.div variants={staggerItem}>
          <Banner tone="warning" title="Scored with VADER">{r.scorer_note}</Banner>
        </motion.div>
      )}

      <motion.div variants={staggerItem} className="grid gap-5 lg:grid-cols-5">
        <ToneCard r={r} />
        <Card className="lg:col-span-2">
          <CardHeader title="Which headlines count" subtitle={`${r.articles.length} found · ${r.n} scored · ${leftOut} left out`} />
          <dl className="space-y-2.5 text-callout">
            {(Object.keys(LEFT_OUT) as (keyof typeof LEFT_OUT)[]).filter((k) => r.excluded[k] > 0 || k !== "undated").map((k) => (
              <div key={k} className="flex items-center justify-between gap-3">
                <dt className="flex items-center gap-2 text-label-2">
                  {leftOutLabel(k, r.days)}
                  {LEFT_OUT[k].info && <EvidenceDot info={SENTIMENT[LEFT_OUT[k].info!]} />}
                </dt>
                <dd className="tabular">{r.excluded[k]}</dd>
              </div>
            ))}
          </dl>
          <p className="mt-4 border-t-[0.5px] border-separator pt-3 text-footnote text-label-2">
            Searched {r.query.google_finance ? <>Google Finance for <span className="font-medium text-label">{r.query.google_finance}</span> and </> : null}
            Google News for <span className="font-medium text-label">“{r.query.google_news}”</span>
            {r.query.keywords && <>; a headline counts if it mentions {[...r.query.keywords, r.query.ticker].join(", ")}</>}.
          </p>
        </Card>
      </motion.div>

      {r.daily.length >= 2 && (
        <motion.div variants={staggerItem}>
          <Card>
            <CardHeader title="Tone by day" subtitle="Average net tone of each day's scored headlines. Days with one or two headlines swing to the extremes." />
            <SignedBars
              data={r.daily}
              xKey="date"
              yKey="mean"
              name="Net tone"
              dateAxis
              height={200}
              format={(v) => signed(v)}
              ariaLabel={`Daily net tone of ${r.symbol} headlines`}
            />
          </Card>
        </motion.div>
      )}

      <motion.div variants={staggerItem}>
        <ArticleList r={r} />
      </motion.div>

      <p className="text-center text-caption text-label-2">Automated scoring misreads some headlines. This is not investment advice.</p>
    </motion.div>
  );
}

function ToneCard({ r }: { r: Sentiment }) {
  const v = verdict(r);
  const at = (x: number) => `${((Math.max(-1, Math.min(1, x)) + 1) / 2) * 100}%`;
  const segments = [
    { k: "Positive" as const, color: "var(--positive)" },
    { k: "Neutral" as const, color: "var(--series-muted)" },
    { k: "Negative" as const, color: "var(--negative)" },
  ];

  return (
    <Card className="lg:col-span-3">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="text-footnote font-medium text-label-2">News tone for {r.symbol} · last {r.days} days</div>
          <div className={`mt-1 text-title-1 ${v.tone === "positive" ? "text-positive" : v.tone === "negative" ? "text-negative" : ""}`}>{v.title}</div>
          <div className="flex items-center gap-1.5 text-footnote text-label-2">
            {r.n} headlines scored by {r.scorer.name}
            <EvidenceDot info={r.scorer.finance ? SENTIMENT.finance_model : SENTIMENT.vader} />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-6 text-right">
          <div>
            <div className="flex items-center justify-end gap-1.5 text-caption text-label-2">Net tone <EvidenceDot info={SENTIMENT.net_tone} /></div>
            <div className="text-title-3 tabular">{r.index != null ? signed(r.index) : "—"}</div>
            {r.ci && <div className="text-caption text-label-2 tabular">95% CI {signed(r.ci[0])} to {signed(r.ci[1])}</div>}
          </div>
          <div>
            <div className="text-caption text-label-2">Price, same {r.days} days</div>
            <div className="text-title-3 tabular">{r.price ? <Delta value={r.price.change_pct}>{pct(r.price.change_pct, 1)}</Delta> : "—"}</div>
            {r.price && <div className="text-caption text-label-2">{shortDate(r.price.from)} – {shortDate(r.price.to)}</div>}
          </div>
        </div>
      </div>

      {r.overall == null && (
        <p className="mt-3 text-footnote text-label-2">At least {r.min_articles} scored headlines are needed to judge the tone. Try the 30-day window.</p>
      )}

      {/* Net tone on −1 … +1, with the 95% interval shaded */}
      {r.index != null && (
        <div
          className="mt-6"
          aria-label={`Net tone ${r.index.toFixed(2)}${r.ci ? `, 95% interval ${r.ci[0].toFixed(2)} to ${r.ci[1].toFixed(2)}` : ""}, on a scale from −1 to +1`}
        >
          <div className="relative h-2 rounded-full bg-[linear-gradient(to_right,var(--negative),var(--fill-strong)_50%,var(--positive))] opacity-80">
            {r.ci && (
              <motion.span
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="absolute -top-1 h-4 rounded-full border-[1.5px] border-label/50 bg-label/10"
                style={{ left: at(r.ci[0]), width: `calc(${at(r.ci[1])} - ${at(r.ci[0])})` }}
              />
            )}
            <span className="absolute left-1/2 top-1/2 h-4 w-px -translate-y-1/2 bg-label/40" />
            <motion.span
              initial={{ left: "50%" }}
              animate={{ left: at(r.index) }}
              transition={spring.bouncy}
              className="absolute top-1/2 size-5 -translate-x-1/2 -translate-y-1/2 rounded-full border-[3px] border-[var(--bg-elevated)] bg-label shadow"
            />
          </div>
          <div className="mt-1.5 flex justify-between text-caption text-label-2"><span>−1 Negative</span><span>0</span><span>Positive +1</span></div>
        </div>
      )}

      {r.n > 0 && (
        <>
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
        </>
      )}

      {r.price_move_share != null && r.price && (
        <p className="mt-4 flex items-start gap-1.5 border-t-[0.5px] border-separator pt-3 text-footnote text-label-2">
          <span>
            {pct(r.price_move_share * 100, 0, false)} of the scored headlines report a price move, so the tone partly restates the {pct(r.price.change_pct, 1)} the price already moved.
          </span>
          <EvidenceDot info={SENTIMENT.price_moves} className="mt-0.5" />
        </p>
      )}
    </Card>
  );
}

function ArticleList({ r }: { r: Sentiment }) {
  const [show, setShow] = useState<"scored" | "left_out">("scored");
  const [sort, setSort] = useState<"recent" | "positive" | "negative">("recent");
  const scored = r.articles.filter((a) => a.status === "scored");
  const leftOut = r.articles.filter((a) => a.status !== "scored");
  const articles = [...(show === "scored" ? scored : leftOut)];
  if (sort === "positive") articles.sort((x, y) => y.score - x.score);
  if (sort === "negative") articles.sort((x, y) => x.score - y.score);

  return (
    <Card padded={false}>
      <div className="flex flex-wrap items-center justify-between gap-3 px-5 pt-5 sm:px-6 sm:pt-6">
        <Segmented
          size="sm"
          label="Which headlines"
          value={show}
          onChange={setShow}
          options={[
            { value: "scored", label: `Scored (${scored.length})` },
            { value: "left_out", label: `Left out (${leftOut.length})` },
          ]}
        />
        <Segmented
          size="sm"
          label="Sort headlines"
          value={sort}
          onChange={setSort}
          options={[
            { value: "recent", label: "Recent" },
            { value: "positive", label: "Positive" },
            { value: "negative", label: "Negative" },
          ]}
        />
      </div>
      {articles.length === 0 ? (
        <p className="px-5 py-6 text-callout text-label-2 sm:px-6">{show === "scored" ? "No headlines passed the filters." : "Nothing was left out."}</p>
      ) : (
        <motion.ul layout className="mt-3">
          <AnimatePresence initial={false}>
            {articles.map((a) => (
              <ArticleRow key={`${a.origin}-${a.link}-${a.title}`} a={a} days={r.days} />
            ))}
          </AnimatePresence>
        </motion.ul>
      )}
    </Card>
  );
}

function ArticleRow({ a, days }: { a: Article; days: number }) {
  const status = a.status;
  const out = status !== "scored";
  return (
    <motion.li layout transition={spring.smooth} className="border-t-[0.5px] border-separator px-5 py-4 sm:px-6">
      <div className="flex items-start gap-3">
        <div className="min-w-0 flex-1">
          <a href={a.link} target="_blank" rel="noreferrer" className={`group text-body font-semibold hover:text-tint ${out ? "text-label-2" : ""}`}>
            {a.title}
            <ExternalLink className="ml-1 inline size-3.5 opacity-0 transition-opacity group-hover:opacity-100" />
          </a>
          <div className="mt-1.5 flex flex-wrap items-center gap-x-1.5 gap-y-1 text-caption text-label-2">
            <span>{a.source}</span>
            <span>·</span>
            <span>{a.published ? relative(a.published) : a.date || "undated"}</span>
            <span>·</span>
            <span>{a.origin}</span>
            {a.price_move && !out && <Badge className="ml-1 !h-5">Price move</Badge>}
          </div>
        </div>
        <div className="flex shrink-0 flex-col items-end gap-1">
          {status !== "scored" ? (
            <Badge>{leftOutLabel(status, days)}</Badge>
          ) : (
            <Badge tone={TONE[a.sentiment]}>{a.sentiment}</Badge>
          )}
          <span className="text-caption text-label-2 tabular">
            {out && `${a.sentiment} `}
            {signed(a.score)}
          </span>
        </div>
      </div>
    </motion.li>
  );
}
