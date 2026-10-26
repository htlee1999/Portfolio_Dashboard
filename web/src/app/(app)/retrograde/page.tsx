"use client";

import { ChevronDown, ChevronLeft, ChevronRight, ExternalLink, LineChart, Orbit } from "lucide-react";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

import { Legend } from "@/components/charts/charts";
import { PageHeader } from "@/components/shell/page-header";
import { PageGuide } from "@/components/shell/page-guide";
import { Button } from "@/components/ui/button";
import { Badge, Card, CardHeader } from "@/components/ui/card";
import { cn } from "@/components/ui/cn";
import { Banner, EmptyState, LoadingBlock } from "@/components/ui/feedback";
import { Stat, StatGrid } from "@/components/ui/stat";
import { useApi } from "@/lib/api";
import { dateTime, shortDate } from "@/lib/format";
import { GENERAL_NOTES, MEANINGS, MEANING_SOURCES, type MeaningSource } from "@/lib/retrograde-meanings";
import type { RetroPeriod, RetroSourceId, RetrogradeCalendar } from "@/lib/types";

const DAY = 86_400_000;
const DEFAULT_PLANETS = ["mercury", "venus", "mars"];
const WEEKDAYS = ["M", "T", "W", "T", "F", "S", "S"];
const SOURCE_SHORT: Record<RetroSourceId, string> = { horizons: "JPL Horizons", swisseph: "Swiss Ephemeris", local: "Astronomy Engine" };

/** Planet colors follow the planet's fixed order, so toggling planets never repaints the others. */
const planetColor = (index: number) => `var(--series-${index + 1})`;

type Span = { planet: string; start: number; end: number; shadowStart: number; shadowEnd: number; period: RetroPeriod };
type Overlap = { start: number; end: number; planets: string[] };

const ms = (iso: string | null, fallback: number) => (iso ? new Date(iso).getTime() : fallback);
const days = (a: number, b: number) => (b - a) / DAY;

function spread(hours: number) {
  return hours < 1 ? `${Math.max(1, Math.round(hours * 60))} min` : `${hours.toFixed(1)} h`;
}

function degrees(deg: number) {
  const total = Math.round(deg * 60);
  return `${Math.floor(total / 60)}°${String(total % 60).padStart(2, "0")}′`;
}

/** Stretches where two or more of the given planets are retrograde at once. */
function overlaps(spans: Span[]): Overlap[] {
  const cuts = [...new Set(spans.flatMap((s) => [s.start, s.end]))].sort((a, b) => a - b);
  const out: Overlap[] = [];
  for (let i = 0; i < cuts.length - 1; i++) {
    const mid = (cuts[i] + cuts[i + 1]) / 2;
    const active = [...new Set(spans.filter((s) => s.start <= mid && mid < s.end).map((s) => s.planet))];
    if (active.length < 2) continue;
    const last = out.at(-1);
    if (last && last.end === cuts[i] && last.planets.join() === active.join()) last.end = cuts[i + 1];
    else out.push({ start: cuts[i], end: cuts[i + 1], planets: active });
  }
  return out;
}

export default function RetrogradePage() {
  const router = useRouter();
  const [now] = useState(() => Date.now());
  const thisYear = new Date(now).getFullYear();
  const [year, setYear] = useState(thisYear);
  const [selected, setSelected] = useState<string[]>(DEFAULT_PLANETS);
  const [day, setDay] = useState<number | null>(null);
  // The following year comes too, so "next station" still works late in the year.
  const { data, error, isLoading } = useApi<RetrogradeCalendar>(`/retrograde?start_year=${year}&end_year=${year + 1}`);

  const planets = useMemo(() => data?.planets ?? [], [data]);
  const order = useMemo(() => Object.fromEntries(planets.map((p, i) => [p.id, i])), [planets]);
  const names = useMemo(() => Object.fromEntries(planets.map((p) => [p.id, p.name])), [planets]);

  const spans = useMemo<Span[]>(
    () =>
      (data?.periods ?? [])
        .filter((p) => selected.includes(p.planet))
        .map((p) => {
          const start = ms(p.start, 0);
          const end = ms(p.end, 0);
          return { planet: p.planet, start, end, shadowStart: ms(p.shadow_start, start), shadowEnd: ms(p.shadow_end, end), period: p };
        }),
    [data, selected],
  );

  const yearStart = new Date(year, 0, 1).getTime();
  const yearEnd = new Date(year + 1, 0, 1).getTime();
  const inYear = spans.filter((s) => s.shadowEnd > yearStart && s.shadowStart < yearEnd);
  const yearOverlaps = overlaps(spans)
    .filter((o) => o.end > yearStart && o.start < yearEnd)
    .map((o) => ({ ...o, start: Math.max(o.start, yearStart), end: Math.min(o.end, yearEnd) }));

  const retroNow = spans.filter((s) => s.start <= now && now < s.end);
  const shadowNow = spans.filter((s) => s.shadowStart <= now && now < s.shadowEnd && !(s.start <= now && now < s.end));
  const nextStation = spans
    .flatMap((s) => [
      { planet: s.planet, kind: "retrograde", at: s.start },
      { planet: s.planet, kind: "direct", at: s.end },
    ])
    .filter((e) => e.at > now)
    .sort((a, b) => a.at - b.at)[0];
  const overlapDays = new Set<number>();
  for (const o of yearOverlaps) for (let t = new Date(o.start).setHours(0, 0, 0, 0); t < o.end; t += DAY) overlapDays.add(new Date(t).setHours(0, 0, 0, 0));

  const toggle = (id: string) => setSelected((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id].sort((a, b) => order[a] - order[b])));

  return (
    <>
      <PageHeader
        title="Retrograde"
        subtitle="When planets appear to move backwards, cross-checked across three ephemerides"
        actions={
          <div className="flex items-center gap-1">
            <Button variant="tinted" size="sm" className="mr-2" icon={<LineChart className="size-4" />} onClick={() => router.push("/retrograde/markets")}>
              vs Markets
            </Button>
            <Button variant="gray" size="sm" aria-label="Previous year" icon={<ChevronLeft className="size-4" />} disabled={year <= 1950} onClick={() => { setYear(year - 1); setDay(null); }} />
            <span className="w-14 text-center text-headline tabular">{year}</span>
            <Button variant="gray" size="sm" aria-label="Next year" icon={<ChevronRight className="size-4" />} disabled={year >= 2099} onClick={() => { setYear(year + 1); setDay(null); }} />
            {year !== thisYear && (
              <Button variant="plain" size="sm" onClick={() => { setYear(thisYear); setDay(null); }}>
                Today
              </Button>
            )}
          </div>
        }
      />
      <PageGuide page="retrograde" />

      {error && <Banner tone="error" title="Couldn't load the retrograde calendar">{error.message}</Banner>}

      {isLoading && !data ? (
        <LoadingBlock label="Fetching ephemerides from JPL Horizons, Swiss Ephemeris and Astronomy Engine" />
      ) : data ? (
        <div className="space-y-5">
          {data.sources.some((s) => s.status !== "ok") && (
            <Banner tone="warning" title="A source is unavailable">
              {data.sources.filter((s) => s.status !== "ok").map((s) => `${s.name}: ${s.error}`).join(" · ")}. Dates are checked against the remaining
              sources; the page retries within the hour.
            </Banner>
          )}

          <div className="flex flex-wrap gap-2" role="group" aria-label="Planets">
            {planets.map((p, i) => {
              const on = selected.includes(p.id);
              return (
                <button
                  key={p.id}
                  aria-pressed={on}
                  onClick={() => toggle(p.id)}
                  className={cn("flex h-8 cursor-pointer items-center gap-2 rounded-full px-3 text-footnote font-semibold transition-colors", on ? "bg-fill-strong text-label" : "bg-fill text-label-2 hover:text-label")}
                >
                  <span className="size-2.5 rounded-full" style={{ background: on ? planetColor(i) : "var(--label-tertiary)" }} aria-hidden />
                  {p.name}
                </button>
              );
            })}
          </div>

          {year === thisYear && (
            <StatGrid>
              <Stat label="Retrograde now" value={retroNow.length ? retroNow.map((s) => names[s.planet]).join(", ") : "None"} detail={retroNow.length ? <span className="text-label-2">{retroNow.map((s) => `${names[s.planet]} to ${shortDate(s.period.end)}`).join(" · ")}</span> : <span className="text-label-2">of the selected planets</span>} />
              <Stat label="In shadow" value={shadowNow.length ? shadowNow.map((s) => names[s.planet]).join(", ") : "None"} detail={<span className="text-label-2">before or after a retrograde</span>} />
              <Stat
                label="Next station"
                value={nextStation ? `${names[nextStation.planet]} ${nextStation.kind === "retrograde" ? "Rx" : "D"}` : "—"}
                detail={nextStation && <span className="text-label-2">{shortDate(new Date(nextStation.at).toISOString(), true)} · in {Math.ceil(days(now, nextStation.at))} days</span>}
              />
              <Stat label={`Overlap days in ${year}`} value={overlapDays.size} detail={<span className="text-label-2">2+ selected planets retrograde</span>} />
            </StatGrid>
          )}

          {selected.length === 0 ? (
            <Card>
              <EmptyState icon={<Orbit className="size-7" />} title="No planets selected">Pick one or more planets above to see their retrograde periods.</EmptyState>
            </Card>
          ) : (
            <>
              <Timeline now={now} year={year} spans={inYear} overlaps={yearOverlaps} order={order} names={names} selected={selected} />
              <YearCalendar now={now} year={year} spans={inYear} overlapDays={overlapDays} order={order} names={names} day={day} onDay={setDay} />
              <OverlapList year={year} overlaps={yearOverlaps} order={order} names={names} />
              <Meanings selected={selected} order={order} names={names} />
              <PeriodTable year={year} spans={inYear} order={order} sources={data.sources.filter((s) => s.status === "ok").map((s) => s.id)} />
            </>
          )}

          <Sources data={data} />
        </div>
      ) : null}
    </>
  );
}

/* ── Gantt-style year timeline: one row per planet, plus a row for overlaps ── */
function Timeline({ now, year, spans, overlaps, order, names, selected }: { now: number; year: number; spans: Span[]; overlaps: Overlap[]; order: Record<string, number>; names: Record<string, string>; selected: string[] }) {
  const t0 = new Date(year, 0, 1).getTime();
  const t1 = new Date(year + 1, 0, 1).getTime();
  const x = (t: number) => `${(Math.min(Math.max(t, t0), t1) - t0) / (t1 - t0) * 100}%`;
  const w = (a: number, b: number) => `${(Math.min(b, t1) - Math.max(a, t0)) / (t1 - t0) * 100}%`;
  const today = now >= t0 && now < t1;
  const months = Array.from({ length: 12 }, (_, m) => new Date(year, m, 1));

  const row = (label: string, children: React.ReactNode, key: string) => (
    <div key={key} className="flex items-center gap-3">
      <div className="w-20 shrink-0 truncate text-footnote text-label-2">{label}</div>
      <div className="relative h-6 flex-1 rounded-[6px] bg-fill-2">
        {children}
        {today && <span className="absolute -inset-y-[3px] w-[1.5px] bg-negative" style={{ left: x(now) }} aria-hidden />}
      </div>
    </div>
  );

  return (
    <Card>
      <CardHeader
        title={`${year} at a glance`}
        subtitle="Solid: retrograde · faded: shadow, the stretch of sky the retrograde re-covers"
        action={<Legend items={selected.map((id) => ({ label: names[id], color: planetColor(order[id]) }))} className="hidden sm:flex" />}
      />
      <div className="space-y-1.5">
        {selected.map((id) =>
          row(
            names[id],
            spans
              .filter((s) => s.planet === id)
              .map((s) => (
                <div key={s.start}>
                  <div
                    className="absolute inset-y-1 rounded-[4px] opacity-25"
                    style={{ left: x(s.shadowStart), width: w(s.shadowStart, s.shadowEnd), background: planetColor(order[id]) }}
                    title={`${names[id]} shadow: ${shortDate(s.period.shadow_start, true)} – ${shortDate(s.period.shadow_end, true)}`}
                  />
                  <div
                    className="absolute inset-y-0 rounded-[4px]"
                    style={{ left: x(s.start), width: w(s.start, s.end), background: planetColor(order[id]) }}
                    title={`${names[id]} retrograde: ${dateTime(s.period.start)} – ${dateTime(s.period.end)}`}
                  />
                </div>
              )),
            id,
          ),
        )}
        {selected.length > 1 &&
          row(
            "Overlap",
            overlaps.map((o) => (
              <div
                key={o.start}
                className="absolute inset-y-0 rounded-[4px] bg-label"
                style={{ left: x(o.start), width: w(o.start, o.end) }}
                title={`${o.planets.map((p) => names[p]).join(" + ")}: ${shortDate(new Date(o.start).toISOString())} – ${shortDate(new Date(o.end).toISOString(), true)}`}
              />
            )),
            "overlap",
          )}
        <div className="flex gap-3">
          <div className="w-20 shrink-0" />
          <div className="relative h-5 flex-1 text-caption text-label-2">
            {months.map((m) => (
              <span key={m.getMonth()} className="absolute top-1" style={{ left: x(m.getTime()) }}>
                {m.toLocaleDateString(undefined, { month: "narrow" })}
              </span>
            ))}
          </div>
        </div>
      </div>
    </Card>
  );
}

/* ── Twelve month grids; each day carries one stripe per planet ── */
function YearCalendar({ now, year, spans, overlapDays, order, names, day, onDay }: { now: number; year: number; spans: Span[]; overlapDays: Set<number>; order: Record<string, number>; names: Record<string, string>; day: number | null; onDay: (d: number | null) => void }) {
  const today = new Date(now).setHours(0, 0, 0, 0);

  const stateOn = (t: number) => {
    const end = new Date(t).setDate(new Date(t).getDate() + 1);
    return spans
      .filter((s) => s.shadowStart < end && s.shadowEnd > t)
      .map((s) => ({
        span: s,
        retro: s.start < end && s.end > t,
        station: s.start >= t && s.start < end ? "Rx" : s.end >= t && s.end < end ? "D" : null,
      }))
      .sort((a, b) => order[a.span.planet] - order[b.span.planet]);
  };

  const describe = (t: number) =>
    stateOn(t)
      .map((s) => `${names[s.span.planet]}: ${s.station === "Rx" ? "stations retrograde" : s.station === "D" ? "stations direct" : s.retro ? "retrograde" : "shadow"}`)
      .join("\n");

  const picked = day !== null ? stateOn(day) : [];

  return (
    <Card>
      <CardHeader title="Calendar" subtitle="Solid stripe: retrograde · faded: shadow · ringed days: two or more planets retrograde at once · select a day for details" />
      <div className="grid gap-x-6 gap-y-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {Array.from({ length: 12 }, (_, m) => {
          const first = new Date(year, m, 1);
          const lead = (first.getDay() + 6) % 7; // Monday first
          const count = new Date(year, m + 1, 0).getDate();
          return (
            <div key={m}>
              <h4 className="mb-2 text-callout font-semibold">{first.toLocaleDateString(undefined, { month: "long" })}</h4>
              <div className="grid grid-cols-7 gap-0.5 text-center">
                {WEEKDAYS.map((d, i) => (
                  <div key={i} className="pb-1 text-caption text-label-3">{d}</div>
                ))}
                {Array.from({ length: lead }, (_, i) => <div key={`pad${i}`} />)}
                {Array.from({ length: count }, (_, i) => {
                  const t = new Date(year, m, i + 1).getTime();
                  const states = stateOn(t);
                  const overlap = overlapDays.has(t);
                  const active = day === t;
                  return (
                    <button
                      key={t}
                      onClick={() => onDay(active ? null : t)}
                      title={describe(t) || undefined}
                      aria-pressed={active}
                      aria-label={`${new Date(t).toDateString()}${states.length ? `. ${describe(t).replaceAll("\n", ". ")}` : ""}`}
                      className={cn(
                        "flex h-11 cursor-pointer flex-col items-center rounded-[8px] pt-1 transition-colors hover:bg-fill-2",
                        overlap && "ring-[1.5px] ring-label ring-inset",
                        active && "bg-fill-strong",
                      )}
                    >
                      <span className={cn("flex size-5 items-center justify-center rounded-full text-caption tabular", t === today ? "bg-negative font-semibold text-white" : states.some((s) => s.retro) ? "font-semibold" : "text-label-2")}>{i + 1}</span>
                      <span className="mt-auto mb-1 flex w-full flex-col gap-px px-1">
                        {states.map((s) => (
                          <span
                            key={s.span.planet}
                            className="h-[3px] rounded-full"
                            style={{ background: planetColor(order[s.span.planet]), opacity: s.retro ? 1 : 0.3 }}
                          />
                        ))}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>

      {day !== null && (
        <div className="mt-6 border-t-[0.5px] border-separator pt-4">
          <p className="text-headline">{new Date(day).toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric", year: "numeric" })}</p>
          {picked.length === 0 ? (
            <p className="mt-1 text-callout text-label-2">No selected planet is retrograde or in shadow.</p>
          ) : (
            <ul className="mt-2 space-y-1.5">
              {picked.map((s) => {
                const p = s.span.period;
                return (
                  <li key={p.planet} className="flex items-center gap-2 text-callout">
                    <span className="size-2.5 shrink-0 rounded-full" style={{ background: planetColor(order[p.planet]) }} aria-hidden />
                    <span className="font-semibold">{p.name}</span>
                    <span className="text-label-2">
                      {s.station === "Rx"
                        ? `stations retrograde at ${dateTime(p.start)}, ${degrees(p.station_retrograde.degree)} ${p.station_retrograde.sign}`
                        : s.station === "D"
                          ? `stations direct at ${dateTime(p.end)}, ${degrees(p.station_direct.degree)} ${p.station_direct.sign}`
                          : s.retro
                            ? `retrograde ${shortDate(p.start)} – ${shortDate(p.end, true)}`
                            : `in shadow (retrograde ${shortDate(p.start)} – ${shortDate(p.end, true)})`}
                      {MEANINGS[p.planet] && <> · {MEANINGS[p.planet].theme}</>}
                    </span>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      )}
    </Card>
  );
}

function PlanetDots({ planets, order, names }: { planets: string[]; order: Record<string, number>; names: Record<string, string> }) {
  return (
    <span className="flex flex-wrap items-center gap-x-3 gap-y-1">
      {planets.map((p) => (
        <span key={p} className="flex items-center gap-1.5">
          <span className="size-2.5 rounded-full" style={{ background: planetColor(order[p]) }} aria-hidden />
          <span className="font-semibold">{names[p]}</span>
        </span>
      ))}
    </span>
  );
}

function OverlapList({ year, overlaps, order, names }: { year: number; overlaps: Overlap[]; order: Record<string, number>; names: Record<string, string> }) {
  return (
    <Card>
      <CardHeader title={`Overlaps in ${year}`} subtitle="Times when two or more of the selected planets are retrograde together" />
      {overlaps.length === 0 ? (
        <p className="text-callout text-label-2">No overlapping retrogrades among the selected planets this year.</p>
      ) : (
        <ul className="-my-2">
          {overlaps.map((o) => (
            <li key={o.start} className="flex flex-wrap items-center gap-x-4 gap-y-1 border-t-[0.5px] border-separator py-3 text-callout first:border-t-0">
              <PlanetDots planets={o.planets} order={order} names={names} />
              <span className="text-label-2 tabular">
                {dateTime(new Date(o.start).toISOString())} – {dateTime(new Date(o.end).toISOString())}
              </span>
              <Badge className="ml-auto">{days(o.start, o.end).toFixed(1)} days</Badge>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

function Cites({ ids }: { ids: MeaningSource[] }) {
  return (
    <span className="text-caption text-label-2">
      {ids.map((id, i) => (
        <span key={id}>
          {i > 0 && " · "}
          <a href={MEANING_SOURCES[id].url} target="_blank" rel="noreferrer" className="underline decoration-label-3 underline-offset-2 hover:text-tint">
            {MEANING_SOURCES[id].label}
          </a>
        </span>
      ))}
    </span>
  );
}

/* ── Astrological readings: what each retrograde is said to mean, with sources ── */
function Meanings({ selected, order, names }: { selected: string[]; order: Record<string, number>; names: Record<string, string> }) {
  const [open, setOpen] = useState(false);
  const used = [...new Set([...GENERAL_NOTES.flatMap((n) => n.sources), ...selected.flatMap((id) => MEANINGS[id]?.sources ?? [])])];
  return (
    <Card>
      <CardHeader
        title="What it means in astrology"
        subtitle="Traditional readings from astrology publishers. The dates above are measured astronomy; these interpretations are belief, not scientific prediction."
      />
      <div className="grid gap-4 lg:grid-cols-2">
        {selected.map((id) => {
          const m = MEANINGS[id];
          if (!m) return null;
          return (
            <section key={id} className="squircle rounded-[14px] bg-fill-2 p-4">
              <div className="flex items-center gap-2">
                <span className="size-2.5 rounded-full" style={{ background: planetColor(order[id]) }} aria-hidden />
                <h4 className="text-headline">{names[id]} retrograde</h4>
              </div>
              <p className="mt-0.5 text-footnote text-label-2">{m.cycle}</p>
              <p className="mt-2 text-footnote text-label-2">
                <span className="font-semibold text-label">Governs:</span> {m.rules}
              </p>
              <p className="mt-2 text-callout">{m.reading}</p>
              <div className="mt-3 grid gap-3 sm:grid-cols-2">
                <div>
                  <p className="text-footnote font-semibold text-positive">Said to be good for</p>
                  <ul className="mt-1 list-disc space-y-0.5 pl-4 text-footnote">
                    {m.goodFor.map((g) => <li key={g}>{g}</li>)}
                  </ul>
                </div>
                <div>
                  <p className="text-footnote font-semibold text-warning">Traditionally avoided</p>
                  <ul className="mt-1 list-disc space-y-0.5 pl-4 text-footnote">
                    {m.avoid.map((a) => <li key={a}>{a}</li>)}
                  </ul>
                </div>
              </div>
              <p className="mt-3">
                <span className="text-caption text-label-2">Sources: </span>
                <Cites ids={m.sources} />
              </p>
            </section>
          );
        })}
      </div>

      <button onClick={() => setOpen(!open)} aria-expanded={open} className="mt-4 flex cursor-pointer items-center gap-1 text-footnote font-semibold text-tint">
        Stations, shadows and inner vs outer planets
        <ChevronDown className={cn("size-4 transition-transform", open && "rotate-180")} aria-hidden />
      </button>
      {open && (
        <dl className="mt-3 space-y-3">
          {GENERAL_NOTES.map((n) => (
            <div key={n.title}>
              <dt className="text-footnote font-semibold">{n.title}</dt>
              <dd className="text-footnote text-label-2">
                {n.text} <Cites ids={n.sources} />
              </dd>
            </div>
          ))}
        </dl>
      )}

      <div className="mt-5 border-t-[0.5px] border-separator pt-3">
        <p className="text-caption font-semibold text-label-2">All sources for this section</p>
        <ul className="mt-1 space-y-0.5">
          {used.map((id) => (
            <li key={id}>
              <Cites ids={[id]} />
            </li>
          ))}
        </ul>
      </div>
    </Card>
  );
}

function VerifyBadge({ p }: { p: RetroPeriod }) {
  const v = p.verification;
  const tone = v.status === "verified" ? "positive" : v.status === "conflict" ? "negative" : "warning";
  const label = v.status === "verified" ? "Verified" : v.status === "single" ? "One source" : v.status === "conflict" ? "Conflict" : "Partial";
  return (
    <Badge tone={tone}>
      {label} {v.sources_agreeing}/{v.sources_available}
    </Badge>
  );
}

function PeriodTable({ year, spans, order, sources }: { year: number; spans: Span[]; order: Record<string, number>; sources: RetroSourceId[] }) {
  const [open, setOpen] = useState<string | null>(null);
  return (
    <Card padded={false}>
      <div className="p-5 pb-0 sm:p-6 sm:pb-0">
        <CardHeader title={`Retrograde periods touching ${year}`} subtitle="Times in your timezone, consensus (median) of the sources · select a row to compare sources" />
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[720px] text-left text-footnote">
          <thead className="text-label-2">
            <tr className="border-b-[0.5px] border-separator">
              {["Planet", "Stations retrograde", "Stations direct", "Length", "Shadow", "Check"].map((h) => (
                <th key={h} className="px-3 py-2 font-medium first:pl-5 sm:first:pl-6">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {spans.map((s) => {
              const p = s.period;
              const key = `${p.planet}${p.start}`;
              const expanded = open === key;
              return [
                <tr key={key} onClick={() => setOpen(expanded ? null : key)} className="cursor-pointer border-b-[0.5px] border-separator transition-colors hover:bg-fill-2" aria-expanded={expanded}>
                  <td className="px-3 py-3 pl-5 sm:pl-6">
                    <span className="flex items-center gap-2 font-semibold">
                      <span className="size-2.5 rounded-full" style={{ background: planetColor(order[p.planet]) }} aria-hidden />
                      {p.name}
                      <ChevronDown className={cn("size-3.5 text-label-3 transition-transform", expanded && "rotate-180")} aria-hidden />
                    </span>
                  </td>
                  <td className="px-3 py-3 tabular">
                    {dateTime(p.start)}
                    <div className="text-label-2">{degrees(p.station_retrograde.degree)} {p.station_retrograde.sign}</div>
                  </td>
                  <td className="px-3 py-3 tabular">
                    {dateTime(p.end)}
                    <div className="text-label-2">{degrees(p.station_direct.degree)} {p.station_direct.sign}</div>
                  </td>
                  <td className="px-3 py-3 tabular">{Math.round(days(s.start, s.end))} days</td>
                  <td className="px-3 py-3 tabular text-label-2">{shortDate(p.shadow_start, true)} – {shortDate(p.shadow_end, true)}</td>
                  <td className="px-3 py-3">
                    <VerifyBadge p={p} />
                    <div className="mt-1 text-caption text-label-2">within {spread(p.verification.max_spread_hours)}</div>
                  </td>
                </tr>,
                expanded && (
                  <tr key={`${key}-detail`} className="border-b-[0.5px] border-separator bg-fill-2">
                    <td colSpan={6} className="px-5 py-3 sm:px-6">
                      <table className="text-footnote">
                        <thead className="text-label-2">
                          <tr>
                            <th className="pr-6 pb-1 font-medium">Source</th>
                            <th className="pr-6 pb-1 font-medium">Stations retrograde</th>
                            <th className="pb-1 font-medium">Stations direct</th>
                          </tr>
                        </thead>
                        <tbody className="tabular">
                          {sources.map((id) => (
                            <tr key={id}>
                              <td className="pr-6 py-0.5 font-semibold">{SOURCE_SHORT[id]}</td>
                              <td className="pr-6 py-0.5">{p.station_retrograde.by_source[id] ? dateTime(p.station_retrograde.by_source[id]) : "not found"}</td>
                              <td className="py-0.5">{p.station_direct.by_source[id] ? dateTime(p.station_direct.by_source[id]) : "not found"}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                      <p className="mt-2 text-caption text-label-2">
                        Sources differ by up to {spread(p.station_retrograde.spread_hours)} at the retrograde station and {spread(p.station_direct.spread_hours)} at the direct station.
                      </p>
                    </td>
                  </tr>
                ),
              ];
            })}
          </tbody>
        </table>
      </div>
      {spans.length === 0 && <p className="px-5 py-4 text-callout text-label-2 sm:px-6">No retrograde periods for the selected planets.</p>}
    </Card>
  );
}

function Sources({ data }: { data: RetrogradeCalendar }) {
  return (
    <Card>
      <CardHeader
        title="Sources"
        subtitle={`Each station is matched across sources; a period is verified when every source agrees within ${data.agree_hours} hours. Calculated ${dateTime(data.generated_at)}.`}
      />
      <ul className="-my-2">
        {data.sources.map((s) => (
          <li key={s.id} className="flex flex-wrap items-center gap-x-3 gap-y-1 border-t-[0.5px] border-separator py-3 first:border-t-0">
            <Badge tone={s.status === "ok" ? "positive" : "negative"}>{s.status === "ok" ? "OK" : "Unavailable"}</Badge>
            <div className="min-w-0 flex-1">
              <a href={s.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-callout font-semibold hover:text-tint">
                {s.name} <ExternalLink className="size-3.5" aria-hidden />
              </a>
              <div className="text-footnote text-label-2">
                {s.method}
                {s.id === data.reference && " · reference for shadows"}
              </div>
            </div>
            <span className="text-footnote text-label-2 tabular">{s.status === "ok" ? `${s.stations} stations found` : s.error}</span>
          </li>
        ))}
      </ul>
    </Card>
  );
}
