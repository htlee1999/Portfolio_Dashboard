"use client";

import { AlertTriangle, BellRing, CalendarClock, CheckCircle2, Info, Plus, Trash2, X } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { mutate as globalMutate } from "swr";

import { CurrencyMenu } from "@/components/shell/currency-menu";
import { PageGuide } from "@/components/shell/page-guide";
import { PageHeader } from "@/components/shell/page-header";
import { Button, IconButton } from "@/components/ui/button";
import { Badge, Card, CardHeader } from "@/components/ui/card";
import { Select, TextField } from "@/components/ui/controls";
import { Banner, LoadingBlock } from "@/components/ui/feedback";
import { Disclosure } from "@/components/ui/overlay";
import { Delta } from "@/components/ui/stat";
import { useToast } from "@/components/ui/toast";
import { api, useApi } from "@/lib/api";
import { money, number, pct, relative, shortDate } from "@/lib/format";
import { useSession } from "@/lib/session";
import type { AlertKind, LastCall, PlanStatus, Thesis, Triggered } from "@/lib/types";

const refreshPlan = () => globalMutate((k) => typeof k === "string" && k.startsWith("/plan"));

const CALL_TONE = { BUY: "positive", HOLD: "neutral", SELL: "negative" } as const;

export default function PlanPage() {
  const { baseCurrency: base } = useSession();
  const { data, error, isLoading, isValidating } = useApi<PlanStatus>(`/plan/status?base=${base}`);

  return (
    <>
      <PageHeader title="Plan" subtitle="Why you own each stock, what would make you sell, and what needs attention" actions={<CurrencyMenu />} />
      <PageGuide page="plan" />
      {error && <Banner tone="error" title="Couldn't load your plan">{error.message}</Banner>}
      {isLoading && !data ? (
        <LoadingBlock label="Checking prices, earnings dates and your alerts…" />
      ) : data ? (
        <div className={`space-y-5 transition-opacity ${isValidating ? "opacity-60" : ""}`}>
          <AttentionCard items={data.triggered} asOf={data.as_of} />
          <ThesesCard data={data} />
          <div className="grid items-start gap-5 lg:grid-cols-5">
            <div className="min-w-0 lg:col-span-3">
              <TargetsCard key={data.as_of} data={data} base={base} />
            </div>
            <div className="min-w-0 lg:col-span-2">
              <CalendarCard data={data} />
            </div>
          </div>
          <WatchlistCard data={data} />
        </div>
      ) : null}
    </>
  );
}

function AttentionCard({ items, asOf }: { items: Triggered[]; asOf: string }) {
  return (
    <Card>
      <CardHeader title="Needs attention" subtitle={`Checked ${relative(asOf)} · your alert rules, earnings within a week, reviews due and drift from targets`} />
      {items.length ? (
        <ul className="space-y-2.5">
          {items.map((t, i) => (
            <li key={i} className="flex gap-2.5 text-callout">
              {t.severity === "warning" ? (
                <AlertTriangle className="mt-0.5 size-4 shrink-0 text-warning" aria-label="Warning" />
              ) : t.kind === "earnings" ? (
                <CalendarClock className="mt-0.5 size-4 shrink-0 text-tint" aria-label="Earnings" />
              ) : (
                <Info className="mt-0.5 size-4 shrink-0 text-tint" aria-label="Note" />
              )}
              <span>
                {t.message}
                {t.symbol && (
                  <Link href={`/assessment?symbol=${t.symbol}`} className="ml-2 text-footnote font-semibold text-tint">
                    Assess
                  </Link>
                )}
              </span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="flex items-center gap-2 text-callout text-label-2">
          <CheckCircle2 className="size-4 text-positive" aria-hidden /> Nothing right now.
        </p>
      )}
    </Card>
  );
}

function CallBadge({ call }: { call: LastCall | null }) {
  if (!call) return null;
  return (
    <Badge tone={CALL_TONE[call.recommendation]}>
      {call.recommendation}
      {call.confidence != null && ` ${call.confidence}/10`} · {shortDate(call.timestamp)}
    </Badge>
  );
}

function ThesesCard({ data }: { data: PlanStatus }) {
  const missing = data.holdings.filter((h) => !h.thesis).length;
  return (
    <Card>
      <CardHeader
        title="Why you own it"
        subtitle={
          missing
            ? `${missing} of ${data.holdings.length} holdings have no written thesis. Writing down what would make you sell, before it happens, guards against anchoring on what you paid.`
            : "Your thesis and sell conditions for each holding. Revisit them on the review date, or when an assessment's “what would show the call is wrong” fires."
        }
      />
      <div>
        {data.holdings.map((h) => (
          <Disclosure
            key={h.symbol}
            title={
              <span className="flex flex-wrap items-center gap-2">
                {h.symbol}
                <span className="text-footnote font-normal text-label-2">{number(h.weight, 1)}%</span>
                {!h.thesis && <Badge tone="warning">No thesis</Badge>}
                {h.alerts.length > 0 && (
                  <Badge>
                    <BellRing className="size-3" aria-hidden /> {h.alerts.length}
                  </Badge>
                )}
              </span>
            }
            subtitle={h.thesis?.thesis ? h.thesis.thesis.slice(0, 110) + (h.thesis.thesis.length > 110 ? "…" : "") : h.quote?.name}
            trailing={<CallBadge call={h.last_call} />}
          >
            {/* Remounts when the saved thesis changes, so the form starts from it. */}
            <ThesisEditor key={h.thesis?.updated ?? "new"} symbol={h.symbol} thesis={h.thesis} />
            <AlertsEditor symbol={h.symbol} data={data} />
          </Disclosure>
        ))}
      </div>
    </Card>
  );
}

const textarea =
  "squircle min-h-24 w-full rounded-[12px] bg-fill-2 px-3.5 py-2.5 text-body text-label outline-none placeholder:text-label-3 focus:bg-elevated focus:shadow-[0_0_0_3.5px_color-mix(in_srgb,var(--tint)_35%,transparent),inset_0_0_0_1px_var(--tint)]";

function ThesisEditor({ symbol, thesis }: { symbol: string; thesis: Thesis | null }) {
  const toast = useToast();
  const [text, setText] = useState(thesis?.thesis ?? "");
  const [conditions, setConditions] = useState<string[]>(thesis?.sell_if ?? []);
  const [draft, setDraft] = useState("");
  const [review, setReview] = useState(thesis?.review_date ?? "");
  const [saving, setSaving] = useState(false);

  async function save() {
    setSaving(true);
    try {
      const sell_if = draft.trim() ? [...conditions, draft.trim()] : conditions;
      await api(`/plan/journal/${symbol}`, { method: "PUT", json: { thesis: text, sell_if, review_date: review || null } });
      setDraft("");
      refreshPlan();
      toast(`Saved your ${symbol} thesis`);
    } catch (e) {
      toast((e as Error).message, "error");
    } finally {
      setSaving(false);
    }
  }

  const inThreeMonths = () => {
    const d = new Date();
    d.setMonth(d.getMonth() + 3);
    setReview(d.toISOString().slice(0, 10));
  };

  return (
    <div className="space-y-3">
      <label className="block">
        <span className="mb-1.5 block px-1 text-footnote font-medium text-label-2">Why you own it</span>
        <textarea className={textarea} value={text} onChange={(e) => setText(e.target.value)} placeholder="What has to be true for this to work, and over what time" />
      </label>
      <div>
        <span className="mb-1.5 block px-1 text-footnote font-medium text-label-2">Sell if</span>
        {conditions.length > 0 && (
          <ul className="mb-2 space-y-1.5">
            {conditions.map((c, i) => (
              <li key={i} className="flex items-start gap-2 text-callout">
                <span className="mt-2 size-1.5 shrink-0 rounded-full bg-label-2" aria-hidden />
                <span className="flex-1">{c}</span>
                <IconButton label="Remove condition" onClick={() => setConditions(conditions.filter((_, j) => j !== i))}>
                  <X className="size-4" />
                </IconButton>
              </li>
            ))}
          </ul>
        )}
        <div className="flex gap-2">
          <TextField
            placeholder="e.g. Gross margin falls below 45% for two quarters"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && draft.trim()) {
                e.preventDefault();
                setConditions([...conditions, draft.trim()]);
                setDraft("");
              }
            }}
          />
          <IconButton label="Add condition" disabled={!draft.trim()} onClick={() => { setConditions([...conditions, draft.trim()]); setDraft(""); }}>
            <Plus className="size-[18px]" />
          </IconButton>
        </div>
      </div>
      <div className="flex flex-wrap items-end gap-3">
        <TextField label="Review on" type="date" value={review} onChange={(e) => setReview(e.target.value)} className="w-44" />
        <Button variant="gray" size="sm" onClick={inThreeMonths}>In 3 months</Button>
        <div className="flex-1" />
        <Button onClick={save} loading={saving}>Save</Button>
      </div>
      {thesis && <p className="px-1 text-caption text-label-2">Written {shortDate(thesis.created, true)} · updated {relative(thesis.updated)}</p>}
    </div>
  );
}

function AlertsEditor({ symbol, data }: { symbol: string; data: PlanStatus }) {
  const toast = useToast();
  const rules = data.alerts.filter((a) => a.symbol === symbol);
  const kinds = Object.entries(data.kinds) as [AlertKind, { label: string; unit: "price" | "pct" }][];
  const [kind, setKind] = useState<AlertKind>("price_below");
  const [value, setValue] = useState("");
  const unit = data.kinds[kind].unit;

  async function add() {
    try {
      await api("/plan/alerts", { method: "POST", json: { symbol, kind, value: Number(value) } });
      setValue("");
      refreshPlan();
    } catch (e) {
      toast((e as Error).message, "error");
    }
  }
  async function remove(id: string) {
    await api(`/plan/alerts/${id}`, { method: "DELETE" });
    refreshPlan();
  }

  return (
    <div className="mt-5 border-t-[0.5px] border-separator pt-4">
      <h4 className="mb-2 px-1 text-footnote font-semibold text-label-2">Alerts</h4>
      {rules.length > 0 && (
        <ul className="mb-3 space-y-1">
          {rules.map((a) => (
            <li key={a.id} className="flex items-center gap-2 text-callout">
              <BellRing className="size-4 shrink-0 text-label-2" aria-hidden />
              <span className="flex-1">
                {a.label} {a.unit === "price" ? number(a.value, 2) : `${number(a.value, 0)}%`}
              </span>
              <IconButton label="Delete alert" onClick={() => remove(a.id)}>
                <Trash2 className="size-4" />
              </IconButton>
            </li>
          ))}
        </ul>
      )}
      <div className="grid grid-cols-[1fr_7rem_auto] items-end gap-2">
        <Select options={kinds.map(([k, v]) => ({ value: k, label: v.label }))} value={kind} onChange={(e) => setKind(e.target.value as AlertKind)} aria-label="Alert when" />
        <TextField type="number" inputMode="decimal" step="any" min="0" placeholder={unit === "price" ? "Price" : "%"} value={value} onChange={(e) => setValue(e.target.value)} aria-label="Value" />
        <Button variant="tinted" disabled={!value} onClick={add}>Add</Button>
      </div>
      <p className="mt-1.5 px-1 text-caption text-label-2">Checked whenever you open this page, and emailed when a scheduled run starts if email is set up.</p>
    </div>
  );
}

function TargetsCard({ data, base }: { data: PlanStatus; base: string }) {
  const toast = useToast();
  const [targets, setTargets] = useState<Record<string, string>>(() =>
    Object.fromEntries(data.rebalance.map((r) => [r.symbol, r.target != null ? String(r.target) : ""])),
  );
  const [band, setBand] = useState(String(data.band));
  const [adding, setAdding] = useState("");
  const [saving, setSaving] = useState(false);

  const sum = Object.values(targets).reduce((s, v) => s + (Number(v) || 0), 0);
  const symbols = [...new Set([...data.rebalance.map((r) => r.symbol), ...Object.keys(targets)])];

  async function save() {
    setSaving(true);
    try {
      const payload = Object.fromEntries(Object.entries(targets).filter(([, v]) => Number(v) > 0).map(([k, v]) => [k, Number(v)]));
      await api("/plan/targets", { method: "PUT", json: { targets: payload, band: Number(band) || 5 } });
      refreshPlan();
      toast("Saved target weights");
    } catch (e) {
      toast((e as Error).message, "error");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Card padded={false}>
      <div className="px-5 pt-5 sm:px-6 sm:pt-6">
        <CardHeader
          title="Target weights"
          subtitle={`Set what each holding should be. Anything more than ${band || 5} points off target shows the trade that restores it.`}
          action={<Badge tone={sum > 100.0001 ? "negative" : "neutral"} className="whitespace-nowrap">{number(sum, 0)}% set</Badge>}
        />
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[520px] text-callout tabular">
          <thead>
            <tr className="text-left text-caption text-label-2 [&>th]:px-3 [&>th]:pb-2 [&>th]:font-medium [&>th:first-child]:pl-6 [&>th:last-child]:pr-6">
              <th>Holding</th>
              <th className="text-right">Now</th>
              <th className="w-24 text-right">Target %</th>
              <th className="text-right">To rebalance</th>
            </tr>
          </thead>
          <tbody>
            {symbols.map((sym) => {
              const r = data.rebalance.find((x) => x.symbol === sym);
              const off = r?.drift != null && Math.abs(r.drift) > data.band;
              return (
                <tr key={sym} className="border-t-[0.5px] border-separator [&>td]:px-3 [&>td]:py-1.5 [&>td:first-child]:pl-6 [&>td:last-child]:pr-6">
                  <td className="font-semibold">{sym}</td>
                  <td className="text-right">{number(r?.weight ?? 0, 1)}%</td>
                  <td className="text-right">
                    <input
                      aria-label={`${sym} target weight`}
                      type="number"
                      min="0"
                      max="100"
                      step="any"
                      value={targets[sym] ?? ""}
                      onChange={(e) => setTargets({ ...targets, [sym]: e.target.value })}
                      placeholder="—"
                      className="squircle h-9 w-20 rounded-[10px] bg-fill-2 px-2 text-right outline-none focus:shadow-[0_0_0_3px_color-mix(in_srgb,var(--tint)_35%,transparent)]"
                    />
                  </td>
                  <td className={`text-right ${off ? "font-semibold" : "text-label-2"}`}>
                    {r?.trade != null && r.target != null ? (
                      <>
                        {r.trade >= 0 ? "Buy" : "Sell"} {money(Math.abs(r.trade), base, { compact: true })}
                        {r.shares != null && <span className="block text-caption font-normal text-label-2">≈ {number(Math.abs(r.shares), Math.abs(r.shares) < 10 ? 2 : 0)} shares</span>}
                      </>
                    ) : "—"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <div className="flex flex-wrap items-end gap-3 px-5 pt-4 pb-5 sm:px-6 sm:pb-6">
        <TextField label="Add a stock to buy" placeholder="KO" value={adding} onChange={(e) => setAdding(e.target.value.toUpperCase())} className="w-32" />
        <Button variant="gray" size="sm" disabled={!adding.trim()} onClick={() => { setTargets({ ...targets, [adding.trim()]: "" }); setAdding(""); }}>Add</Button>
        <TextField label="Band (points)" type="number" min="1" max="50" value={band} onChange={(e) => setBand(e.target.value)} className="w-28" />
        <div className="flex-1" />
        <Button onClick={save} loading={saving} disabled={sum > 100.0001}>Save Targets</Button>
      </div>
      {sum > 0 && sum < 99.5 && <p className="px-6 pb-5 text-footnote text-label-2">{number(100 - sum, 0)}% has no target; it stays as cash or untargeted holdings.</p>}
    </Card>
  );
}

function CalendarCard({ data }: { data: PlanStatus }) {
  return (
    <Card>
      <CardHeader title="Earnings calendar" subtitle="Next reports for your holdings and watchlist" />
      {data.calendar.length ? (
        <ul className="tabular">
          {data.calendar.map((c) => (
            <li key={c.symbol} className="flex items-center justify-between border-t-[0.5px] border-separator py-2 text-callout first:border-t-0">
              <span className="font-semibold">
                {c.symbol} {!c.held && <span className="text-caption font-normal text-label-2">watching</span>}
              </span>
              <span className={c.days <= 7 ? "font-semibold" : "text-label-2"}>
                {shortDate(c.date, true)} <span className="text-caption text-label-2">· {c.days === 0 ? "today" : `in ${c.days} d`}</span>
              </span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-callout text-label-2">No upcoming dates from Yahoo Finance.</p>
      )}
    </Card>
  );
}

function WatchlistCard({ data }: { data: PlanStatus }) {
  const toast = useToast();
  const [symbol, setSymbol] = useState("");
  async function add(e: React.FormEvent) {
    e.preventDefault();
    try {
      await api("/plan/watchlist", { method: "POST", json: { symbol: symbol.trim() } });
      setSymbol("");
      refreshPlan();
    } catch (err) {
      toast((err as Error).message, "error");
    }
  }
  async function remove(s: string) {
    await api(`/plan/watchlist/${s}`, { method: "DELETE" });
    refreshPlan();
  }
  return (
    <Card padded={false}>
      <div className="px-5 pt-5 sm:px-6 sm:pt-6">
        <CardHeader title="Watchlist" subtitle="Stocks you're considering, with what you'd need to decide" />
        <form onSubmit={add} className="mb-4 flex items-end gap-2">
          <TextField placeholder="Add a symbol" value={symbol} onChange={(e) => setSymbol(e.target.value.toUpperCase())} className="w-40" aria-label="Symbol" />
          <Button type="submit" variant="tinted" disabled={!symbol.trim()}>Add</Button>
        </form>
      </div>
      {data.watchlist.length ? (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[680px] text-callout tabular">
            <thead>
              <tr className="text-left text-caption text-label-2 [&>th]:px-3 [&>th]:pb-2 [&>th]:font-medium [&>th:first-child]:pl-6 [&>th:last-child]:pr-6">
                <th>Symbol</th>
                <th className="text-right">Price</th>
                <th className="text-right">From 52w high</th>
                <th className="text-right">Fwd P/E</th>
                <th className="text-right">Analysts</th>
                <th>Next report</th>
                <th>Last AI call</th>
                <th className="w-12" />
              </tr>
            </thead>
            <tbody>
              {data.watchlist.map((w) => (
                <tr key={w.symbol} className="border-t-[0.5px] border-separator [&>td]:px-3 [&>td]:py-2 [&>td:first-child]:pl-6 [&>td:last-child]:pr-6">
                  <td>
                    <Link href={`/fundamentals?symbol=${w.symbol}`} className="font-semibold hover:text-tint">{w.symbol}</Link>
                    <div className="max-w-40 truncate text-caption text-label-2">{w.name}</div>
                  </td>
                  <td className="text-right">
                    {money(w.price, w.currency)}
                    {w.change_pct != null && <Delta value={w.change_pct} className="block text-caption">{pct(w.change_pct, 1)}</Delta>}
                  </td>
                  <td className="text-right">{w.from_high != null ? pct(w.from_high, 0) : "—"}</td>
                  <td className="text-right">{number(w.forward_pe, 1)}</td>
                  <td className="text-right text-label-2">
                    {w.recommendation?.replace("_", " ") ?? "—"}
                    {w.target_mean != null && w.price && <span className="block text-caption">target {pct((w.target_mean / w.price - 1) * 100, 0)}</span>}
                  </td>
                  <td className="text-label-2">{w.next_earnings ? shortDate(w.next_earnings, true) : "—"}</td>
                  <td>{w.last_call ? <CallBadge call={w.last_call} /> : <Link href={`/assessment?symbol=${w.symbol}`} className="text-footnote font-semibold text-tint">Assess</Link>}</td>
                  <td>
                    <IconButton label={`Remove ${w.symbol} from watchlist`} onClick={() => remove(w.symbol)} className="!text-label-2 hover:!text-negative">
                      <Trash2 className="size-[18px]" />
                    </IconButton>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="px-6 pb-6 text-callout text-label-2">Nothing yet. Before buying a stock, add it here and check it on Risk&apos;s What if? card.</p>
      )}
    </Card>
  );
}
