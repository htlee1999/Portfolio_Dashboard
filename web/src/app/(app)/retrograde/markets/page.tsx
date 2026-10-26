"use client";

import { CalendarDays, FlaskConical, Plus, X } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Legend, SERIES, TimeSeries } from "@/components/charts/charts";
import { PageHeader } from "@/components/shell/page-header";
import { PageGuide } from "@/components/shell/page-guide";
import { Button } from "@/components/ui/button";
import { Badge, Card, CardHeader } from "@/components/ui/card";
import { cn } from "@/components/ui/cn";
import { Segmented, TextField } from "@/components/ui/controls";
import { Banner, EmptyState, LoadingBlock } from "@/components/ui/feedback";
import { Stat, StatGrid } from "@/components/ui/stat";
import { useApi } from "@/lib/api";
import { number, shortDate } from "@/lib/format";
import type { RetroCompare, RetroMarkets } from "@/lib/types";

const PLANETS = [
  ["mercury", "Mercury"], ["venus", "Venus"], ["mars", "Mars"], ["jupiter", "Jupiter"],
  ["saturn", "Saturn"], ["uranus", "Uranus"], ["neptune", "Neptune"], ["pluto", "Pluto"],
] as const;
const PLANET_INDEX: Record<string, number> = Object.fromEntries(PLANETS.map(([id], i) => [id, i]));
const PLANET_NAME: Record<string, string> = Object.fromEntries(PLANETS);
const planetColor = (id: string) => `var(--series-${PLANET_INDEX[id] + 1})`;

const SINCE = [
  { value: "2000", label: "2000" },
  { value: "2010", label: "2010" },
  { value: "2015", label: "2015" },
  { value: "2020", label: "2020" },
] as const;
const WINDOWS = [
  { value: "retrograde", label: "Retrograde" },
  { value: "shadow", label: "Incl. shadow" },
] as const;
const MEASURES = [
  { value: "absolute", label: "ETF return" },
  { value: "excess", label: "vs S&P 500" },
] as const;

type Measure = (typeof MEASURES)[number]["value"];
type EtfList = { etfs: { symbol: string; name: string; group: string }[]; benchmark: string };

const signed = (v: number, digits = 1) => `${v > 0 ? "+" : ""}${v.toFixed(digits)}`;
const pFmt = (p: number) => (p < 0.001 ? "<0.001" : p.toFixed(3));

/** Diverging fill: green for higher inside the windows, red for lower, fading to nothing at zero. */
function cellFill(diff: number) {
  const strength = Math.min(Math.abs(diff) / 30, 1) * 34;
  return `color-mix(in srgb, var(${diff >= 0 ? "--positive" : "--negative"}) ${strength.toFixed(0)}%, transparent)`;
}

export default function RetroMarketsPage() {
  const router = useRouter();
  const etfList = useApi<EtfList>("/retrograde/etfs");
  const [planets, setPlanets] = useState<string[]>(["mercury", "venus", "mars"]);
  const [win, setWin] = useState<(typeof WINDOWS)[number]["value"]>("retrograde");
  const [since, setSince] = useState<(typeof SINCE)[number]["value"]>("2000");
  const [measure, setMeasure] = useState<Measure>("absolute");
  const [removed, setRemoved] = useState<string[]>([]);
  const [custom, setCustom] = useState<string[]>([]);
  const [draft, setDraft] = useState("");
  const [focus, setFocus] = useState<{ symbol: string; test: string } | null>(null);

  const symbols = [...(etfList.data?.etfs.map((e) => e.symbol) ?? []).filter((s) => !removed.includes(s)), ...custom];
  const path = etfList.data && planets.length
    ? `/retrograde/markets?planets=${planets.join(",")}&symbols=${symbols.join(",")}&since=${since}&window=${win}`
    : null;
  const { data, error, isLoading } = useApi<RetroMarkets>(path);

  const togglePlanet = (id: string) =>
    setPlanets((p) => (p.includes(id) ? p.filter((x) => x !== id) : [...p, id].sort((a, b) => PLANET_INDEX[a] - PLANET_INDEX[b])));
  const toggleEtf = (s: string) => setRemoved((r) => (r.includes(s) ? r.filter((x) => x !== s) : [...r, s]));
  const addCustom = () => {
    const s = draft.trim().toUpperCase();
    if (s && /^[A-Z0-9.\-^=]{1,20}$/.test(s) && !symbols.includes(s)) setCustom((c) => [...c, s]);
    setDraft("");
  };

  const pick = (r: RetroMarkets["results"][number], test: string) => r.tests[test]?.[measure] ?? null;
  const all = data?.results.flatMap((r) => data.tests.map((t) => pick(r, t.id))).filter((c): c is RetroCompare => !!c) ?? [];
  const significant = all.filter((c) => c.q < 0.05).length;
  const rawHits = all.filter((c) => c.p < 0.05).length;

  const active = data && focus && data.results.some((r) => r.symbol === focus.symbol) && data.tests.some((t) => t.id === focus.test)
    ? focus
    : data
      ? { symbol: data.results.find((r) => r.symbol !== data.benchmark)?.symbol ?? data.benchmark, test: data.tests[0].id }
      : null;

  return (
    <>
      <PageHeader
        title="Retrograde vs Markets"
        subtitle="Do sector ETFs behave differently while planets are retrograde?"
        actions={
          <Button variant="gray" size="sm" icon={<CalendarDays className="size-4" />} onClick={() => router.push("/retrograde")}>
            Calendar
          </Button>
        }
      />
      <PageGuide page="retroMarkets" />

      <div className="space-y-5">
        <Card>
          <div className="space-y-4">
            <div className="flex flex-wrap gap-2" role="group" aria-label="Planets">
              {PLANETS.map(([id, name]) => {
                const on = planets.includes(id);
                return (
                  <button key={id} aria-pressed={on} onClick={() => togglePlanet(id)} className={cn("flex h-8 cursor-pointer items-center gap-2 rounded-full px-3 text-footnote font-semibold transition-colors", on ? "bg-fill-strong text-label" : "bg-fill text-label-2 hover:text-label")}>
                    <span className="size-2.5 rounded-full" style={{ background: on ? planetColor(id) : "var(--label-tertiary)" }} aria-hidden />
                    {name}
                  </button>
                );
              })}
            </div>
            <div className="flex flex-wrap items-center gap-x-5 gap-y-3">
              <label className="flex items-center gap-2 text-footnote text-label-2">Window <Segmented label="Window" size="sm" options={WINDOWS} value={win} onChange={setWin} /></label>
              <label className="flex items-center gap-2 text-footnote text-label-2">Since <Segmented label="Since" size="sm" options={SINCE} value={since} onChange={setSince} /></label>
              <label className="flex items-center gap-2 text-footnote text-label-2">Measure <Segmented label="Measure" size="sm" options={MEASURES} value={measure} onChange={setMeasure} /></label>
            </div>
            {etfList.data && (
              <div className="flex flex-wrap items-center gap-1.5" role="group" aria-label="ETFs">
                {etfList.data.etfs.map((e) => {
                  const on = !removed.includes(e.symbol);
                  const locked = e.symbol === etfList.data!.benchmark;
                  return (
                    <button key={e.symbol} aria-pressed={on} disabled={locked} title={`${e.name} · ${e.group}${locked ? " (benchmark, always included)" : ""}`} onClick={() => toggleEtf(e.symbol)} className={cn("h-7 cursor-pointer rounded-full px-2.5 text-caption font-semibold transition-colors disabled:cursor-default", on ? "bg-tint-fill text-tint" : "bg-fill text-label-3 line-through hover:text-label-2")}>
                      {e.symbol}
                    </button>
                  );
                })}
                {custom.map((s) => (
                  <button key={s} onClick={() => setCustom((c) => c.filter((x) => x !== s))} className="flex h-7 cursor-pointer items-center gap-1 rounded-full bg-tint-fill px-2.5 text-caption font-semibold text-tint" aria-label={`Remove ${s}`}>
                    {s} <X className="size-3" aria-hidden />
                  </button>
                ))}
                <form onSubmit={(e) => { e.preventDefault(); addCustom(); }} className="ml-1 flex items-center gap-1.5">
                  <TextField aria-label="Add a ticker" placeholder="Add ticker" value={draft} onChange={(e) => setDraft(e.target.value)} className="h-7 w-28 text-caption" />
                  <Button type="submit" variant="gray" size="sm" aria-label="Add ticker" icon={<Plus className="size-4" />} />
                </form>
              </div>
            )}
          </div>
        </Card>

        {error && <Banner tone="error" title="Couldn't run the comparison">{error.message}</Banner>}
        {data && data.missing.length > 0 && <Banner tone="warning" title="No price data">{data.missing.join(", ")} returned no prices from Yahoo Finance and were skipped.</Banner>}

        {planets.length === 0 ? (
          <Card><EmptyState icon={<FlaskConical className="size-7" />} title="Pick a planet">Choose at least one planet to compare against the market.</EmptyState></Card>
        ) : (isLoading && !data) || etfList.isLoading ? (
          <LoadingBlock label="Loading prices and retrograde history (the first run can take a minute)" />
        ) : data && active ? (
          <>
            <Banner tone={significant ? "warning" : "info"} title={significant ? `${significant} of ${all.length} comparisons pass the multiple-testing check` : `No reliable link in ${all.length} comparisons`}>
              {significant
                ? "These differences are unlikely to be timing luck. Before acting on one, check that it holds in the later Since ranges and when you include the shadow."
                : `${rawHits} comparison${rawHits === 1 ? "" : "s"} would look significant on its own (p < 0.05), but with this many tests about ${Math.round(all.length * 0.05)} would by chance alone. None survives the correction (q < 0.05, adjusted across all ${data.method.tests_run} tests on both measures).`}
            </Banner>

            <Heatmap data={data} measure={measure} active={active} onPick={setFocus} />
            <Detail data={data} measure={measure} symbol={active.symbol} test={active.test} />
            <Method data={data} />
          </>
        ) : null}
      </div>
    </>
  );
}

/* ── ETF × retrograde grid of annualized differences ── */
function Heatmap({ data, measure, active, onPick }: { data: RetroMarkets; measure: Measure; active: { symbol: string; test: string }; onPick: (f: { symbol: string; test: string }) => void }) {
  const rows = data.results.filter((r) => measure === "absolute" || r.symbol !== data.benchmark);
  return (
    <Card padded={false}>
      <div className="p-5 pb-0 sm:p-6 sm:pb-0">
        <CardHeader
          title="Inside minus outside, annualized"
          subtitle={
            measure === "absolute"
              ? "Each ETF's annualized return during the windows minus its return at other times, in percentage points"
              : "The same, for the ETF's return in excess of the S&P 500 (SPY)"
          }
        />
        <p className="-mt-2 mb-3 text-caption text-label-2">
          <span className="font-semibold text-label">*</span> p &lt; 0.05 on its own · <span className="font-semibold text-label">**</span> still significant after correcting for every test on the page (q &lt; 0.05) · select a cell for details
        </p>
      </div>
      <div className="overflow-x-auto px-2 pb-4 sm:px-3">
        <table className="w-full min-w-[640px] border-separate border-spacing-0.5 text-footnote">
          <thead>
            <tr>
              <th className="px-2 py-1.5 text-left font-medium text-label-2">ETF</th>
              {data.tests.map((t) => (
                <th key={t.id} className="px-2 py-1.5 text-center font-medium text-label-2">
                  <span className="flex items-center justify-center gap-1.5">
                    {t.planets.length === 1 && <span className="size-2 rounded-full" style={{ background: planetColor(t.planets[0]) }} aria-hidden />}
                    {t.label}
                  </span>
                  <span className="block text-caption font-normal text-label-3">{t.share_of_days != null ? `${t.share_of_days}% of days` : ""}</span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.symbol}>
                <th className="px-2 py-1 text-left font-normal" title={`${r.name} · since ${r.first_date}`}>
                  <span className="font-semibold">{r.symbol}</span> <span className="hidden text-label-2 lg:inline">{r.name}</span>
                </th>
                {data.tests.map((t) => {
                  const c = r.tests[t.id]?.[measure];
                  const on = active.symbol === r.symbol && active.test === t.id;
                  return (
                    <td key={t.id} className="p-0">
                      <button
                        onClick={() => onPick({ symbol: r.symbol, test: t.id })}
                        aria-pressed={on}
                        disabled={!c}
                        title={c ? `${r.symbol}, ${t.label}: ${signed(c.ann_in)}% inside vs ${signed(c.ann_out)}% outside a year · p ${pFmt(c.p)} · q ${pFmt(c.q)} · ${c.days_in} days inside` : "Too few trading days to test"}
                        className={cn("h-9 w-full cursor-pointer rounded-[6px] px-2 tabular transition-shadow disabled:cursor-default", on && "ring-2 ring-tint", c && c.q < 0.05 && "font-semibold")}
                        style={{ background: c ? cellFill(c.diff) : "var(--fill-secondary)" }}
                      >
                        {c ? (
                          <>
                            {signed(c.diff)}
                            <span className="text-label-2">{c.q < 0.05 ? "**" : c.p < 0.05 ? "*" : ""}</span>
                          </>
                        ) : (
                          <span className="text-label-3">—</span>
                        )}
                      </button>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

/* ── One ETF against one retrograde: stats, shaded price chart, every period ── */
function Detail({ data, measure, symbol, test }: { data: RetroMarkets; measure: Measure; symbol: string; test: string }) {
  const row = data.results.find((r) => r.symbol === symbol)!;
  const t = data.tests.find((x) => x.id === test)!;
  const c = row.tests[test]?.[measure] ?? row.tests[test]?.absolute ?? null;
  const bench = data.benchmark;
  const isBench = symbol === bench;

  const growth = (() => {
    // Rebase both lines to 1 at the ETF's first week, so a late-starting ETF lines up with SPY.
    const first = data.growth.find((g) => g[symbol] != null);
    if (!first) return [];
    const base = Number(first[bench]);
    return data.growth
      .filter((g) => g.date >= first.date)
      .map((g) => ({ date: g.date, etf: g[symbol] as number | null, spy: g[bench] != null ? Number(g[bench]) / base : null }));
  })();

  const periods = data.periods.filter((p) => t.planets.includes(p.planet) && p.returns[symbol] && p.returns[bench]);
  const areas = (() => {
    const dates = growth.map((g) => g.date);
    const snap = (iso: string, up: boolean) => {
      const d = iso.slice(0, 10);
      const i = dates.findIndex((x) => x >= d);
      return up ? dates[i === -1 ? dates.length - 1 : i] : dates[Math.max(0, (i === -1 ? dates.length : i) - 1)];
    };
    return periods
      .filter((p) => growth.length && p.end.slice(0, 10) >= growth[0].date)
      .map((p) => {
        const x1 = snap(p.start, false);
        let x2 = snap(p.end, true);
        if (x2 === x1) x2 = dates[Math.min(dates.indexOf(x1) + 1, dates.length - 1)];
        return { x1, x2, color: planetColor(p.planet) };
      });
  })();

  const done = periods.filter((p) => p.complete);
  const beat = done.filter((p) => p.returns[symbol].ret > p.returns[bench].ret).length;
  const avg = (xs: number[]) => (xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : 0);
  const rets = done.map((p) => p.returns[symbol].ret).sort((a, b) => a - b);
  const avgRet = avg(rets);
  const avgTypical = avg(done.map((p) => p.returns[symbol].typical ?? 0));
  const fell = rets.filter((r) => r < 0).length;
  const baseDown = avg(done.map((p) => p.returns[symbol].typical_down ?? 0));
  const median = rets.length ? (rets[Math.floor((rets.length - 1) / 2)] + rets[Math.ceil((rets.length - 1) / 2)]) / 2 : 0;
  const trimmed = avg(rets.slice(Math.min(5, Math.floor(rets.length / 4))));

  return (
    <Card>
      <CardHeader
        title={`${symbol} during ${t.label === "Any selected" ? "any selected retrograde" : t.label === "Overlap (2+)" ? "overlapping retrogrades" : `${t.label} retrograde`}${data.window === "shadow" ? " (incl. shadow)" : ""}`}
        subtitle={`${row.name} · data since ${shortDate(row.first_date, true)}`}
        action={c && <Badge className="whitespace-nowrap" tone={c.q < 0.05 ? "warning" : "neutral"}>{c.q < 0.05 ? "Significant after correction" : c.p < 0.05 ? "Nominal only" : "No evidence"}</Badge>}
      />
      {c ? (
        <>
          <p className="mb-4 text-callout text-label-2">
            {measure === "excess" && !isBench ? `Return in excess of the S&P 500. ` : ""}
            Annualized, {symbol} {measure === "excess" && !isBench ? "beat SPY by" : "returned"} <span className="font-semibold text-label">{signed(c.ann_in)}%</span> inside the windows and{" "}
            <span className="font-semibold text-label">{signed(c.ann_out)}%</span> outside them. A gap at least this large turned up in{" "}
            <span className="font-semibold text-label">{Math.round(c.p * 100)}%</span> of {number(c.shifts, 0)} random placements of the same calendar.
          </p>
          <StatGrid>
            <Stat label="Difference" value={`${signed(c.diff)} pts`} detail={<span className="text-label-2">{signed(c.daily_diff_bp, 1)} bp a day</span>} />
            <Stat label="p-value" value={pFmt(c.p)} detail={<span className="text-label-2">q {pFmt(c.q)} after {data.method.tests_run} tests</span>} />
            <Stat label="Volatility inside" value={`${c.vol_in.toFixed(1)}%`} detail={<span className="text-label-2">vs {c.vol_out.toFixed(1)}% outside, annualized</span>} />
            <Stat label="Up days inside" value={`${c.up_in}%`} detail={<span className="text-label-2">vs {c.up_out}% outside · {number(c.days_in, 0)} days</span>} />
          </StatGrid>
        </>
      ) : (
        <p className="text-callout text-label-2">Too few trading days inside these windows to test.</p>
      )}

      <div className="mt-6">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <h4 className="text-headline">Growth of $1, windows shaded</h4>
          <Legend items={[
            { label: symbol, color: SERIES[0] },
            ...(isBench ? [] : [{ label: `${bench} (S&P 500)`, color: "var(--series-muted)", dashed: true }]),
            ...t.planets.map((p) => ({ label: `${PLANET_NAME[p]} window`, color: planetColor(p) })),
          ]} />
        </div>
        <TimeSeries
          data={growth}
          height={300}
          legend={false}
          lines={[{ key: "etf", label: symbol, color: SERIES[0] }, ...(isBench ? [] : [{ key: "spy", label: bench, color: "var(--series-muted)", dashed: true, width: 1.5 }])]}
          xAreas={areas}
          format={(v) => `$${v.toFixed(2)}`}
          ariaLabel={`Growth of ${symbol} and SPY with retrograde windows shaded`}
        />
      </div>

      <div className="mt-6">
        <h4 className="mb-3 text-headline">Each window</h4>
        {done.length > 0 && (
          <div className="mb-4">
            <StatGrid>
              <Stat label="Fell in" value={`${fell} of ${done.length}`} detail={<span className="text-label-2">{Math.round((fell / done.length) * 100)}% vs {baseDown.toFixed(0)}% of any stretch this long</span>} />
              <Stat label="Median window" value={`${signed(median, 2)}%`} detail={<span className="text-label-2">the middle result</span>} />
              <Stat label="Average window" value={`${signed(avgRet, 2)}%`} detail={<span className="text-label-2">vs {signed(avgTypical, 2)}% typical{!isBench && <> · beat SPY {beat}/{done.length}</>}</span>} />
              <Stat label={`Without worst ${Math.min(5, Math.floor(rets.length / 4))}`} value={`${signed(trimmed, 2)}%`} detail={<span className="text-label-2">average, if a few crashes drive it</span>} />
            </StatGrid>
          </div>
        )}
        <div className="max-h-[420px] overflow-auto rounded-[12px] border-[0.5px] border-separator">
          <table className="w-full min-w-[560px] text-left text-footnote">
            <thead className="sticky top-0 bg-elevated text-label-2">
              <tr className="border-b-[0.5px] border-separator">
                {["Window", "Trading days", symbol, ...(isBench ? [] : [bench, "Difference"]), "Typical"].map((h) => (
                  <th key={h} className="px-3 py-2 font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="tabular">
              {[...periods].reverse().map((p) => {
                const r = p.returns[symbol];
                const s = p.returns[bench];
                return (
                  <tr key={`${p.planet}${p.start}`} className="border-b-[0.5px] border-separator last:border-b-0">
                    <td className="px-3 py-2">
                      <span className="flex items-center gap-2">
                        <span className="size-2 shrink-0 rounded-full" style={{ background: planetColor(p.planet) }} aria-hidden />
                        {shortDate(p.start, true)} – {shortDate(p.end, true)}
                        {!p.complete && <Badge>so far</Badge>}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-label-2">{p.trading_days}</td>
                    <td className={cn("px-3 py-2 font-semibold", r.ret >= 0 ? "text-positive" : "text-negative")}>{signed(r.ret, 2)}%</td>
                    {!isBench && <td className="px-3 py-2">{signed(s.ret, 2)}%</td>}
                    {!isBench && <td className={cn("px-3 py-2", r.ret - s.ret >= 0 ? "text-positive" : "text-negative")}>{signed(r.ret - s.ret, 2)}</td>}
                    <td className="px-3 py-2 text-label-2">{r.typical != null ? `${signed(r.typical, 2)}%` : "—"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </Card>
  );
}

function Method({ data }: { data: RetroMarkets }) {
  return (
    <Card>
      <CardHeader title="How this is tested" subtitle={`Prices from Yahoo Finance (dividend-adjusted) · retrograde dates from the cross-checked calendar · run ${shortDate(data.generated_at, true)}`} />
      <dl className="grid gap-4 text-footnote md:grid-cols-2">
        <div>
          <dt className="font-semibold">Inside vs outside</dt>
          <dd className="text-label-2">A trading day counts as inside if the window covers that day&apos;s US market close. Each ETF&apos;s average daily return inside is compared with outside and annualized. The S&amp;P 500 view uses the ETF&apos;s daily return minus SPY&apos;s, which removes moves the whole market shared.</dd>
        </div>
        <div>
          <dt className="font-semibold">Random-placement test (p)</dt>
          <dd className="text-label-2">The whole retrograde calendar is slid along the price history to every other start date, keeping the real lengths and spacing of the windows. p is the share of those placements with a gap at least as large. Shifts under {data.method.exclude_shift_days} trading days are skipped because they mostly overlap the real dates. Unlike a t-test, this isn&apos;t fooled by calm and volatile markets coming in runs.</dd>
        </div>
        <div>
          <dt className="font-semibold">Many tests (q)</dt>
          <dd className="text-label-2">This page runs {data.method.tests_run} comparisons, so about one in twenty would look significant at p &lt; 0.05 by chance. q is the Benjamini–Hochberg adjustment for that; judge results by q &lt; 0.05. Comparisons need at least {data.method.min_days} days inside and outside.</dd>
        </div>
        <div>
          <dt className="font-semibold">Caveats</dt>
          <dd className="text-label-2">Newer ETFs (DTCR from 2020, SRVR and XLC from 2018, XLRE from 2015) have few windows, so their numbers swing widely. A few big shocks inside a window, such as March 2020 or late 2008, can dominate a result; check whether it holds across the Since ranges. ETFs also move together, so a column of same-coloured cells is mostly one market-wide effect counted many times; the vs S&amp;P 500 view strips that out. Correlation isn&apos;t cause, and none of this is investment advice.</dd>
        </div>
      </dl>
    </Card>
  );
}
