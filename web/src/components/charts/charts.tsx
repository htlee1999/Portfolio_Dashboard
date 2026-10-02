"use client";

import {
  Area,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ComposedChart,
  Line,
  Pie,
  PieChart,
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ReferenceArea,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { shortDate } from "@/lib/format";
import { cn } from "../ui/cn";

/** Categorical slots, assigned in fixed order. Never cycled past 8. */
export const SERIES = [1, 2, 3, 4, 5, 6, 7, 8].map((i) => `var(--series-${i})`);
export const MUTED = "var(--series-muted)";

const AXIS = { fontSize: 11, fill: "var(--chart-axis)" };

export type LineSpec = {
  key: string;
  label: string;
  color: string;
  width?: number;
  dashed?: boolean;
  area?: boolean;
};

/* ── Tooltip on a translucent material ── */
function TooltipCard({
  active,
  label,
  payload,
  format,
  labelFormat,
}: {
  active?: boolean;
  label?: string | number;
  payload?: { dataKey?: string | number; name?: string; value?: number; color?: string; payload?: Record<string, unknown> }[];
  format: (v: number, key: string) => string;
  labelFormat?: (l: string) => string;
}) {
  if (!active || !payload?.length) return null;
  const rows = payload.filter((p) => p.value != null && p.name !== "_band");
  return (
    <div className="material-thick squircle min-w-36 rounded-[12px] px-3 py-2 text-caption">
      {label != null && <div className="mb-1 font-semibold text-label">{labelFormat ? labelFormat(String(label)) : String(label)}</div>}
      {rows.map((p) => (
        <div key={String(p.dataKey)} className="flex items-center justify-between gap-4 py-px">
          <span className="flex items-center gap-1.5 text-label-2">
            <span className="size-2 rounded-full" style={{ background: p.color }} />
            {p.name}
          </span>
          <span className="tabular font-semibold text-label">{format(Number(p.value), String(p.dataKey))}</span>
        </div>
      ))}
    </div>
  );
}

export function Legend({ items, className }: { items: { label: string; color: string; dashed?: boolean }[]; className?: string }) {
  return (
    <ul className={cn("flex flex-wrap gap-x-4 gap-y-1.5 text-caption text-label-2", className)}>
      {items.map((i) => (
        <li key={i.label} className="flex items-center gap-1.5">
          {i.dashed ? (
            <span className="h-0 w-3.5 border-t-2 border-dashed" style={{ borderColor: i.color }} />
          ) : (
            <span className="h-[3px] w-3.5 rounded-full" style={{ background: i.color }} />
          )}
          {i.label}
        </li>
      ))}
    </ul>
  );
}

/* ── Time series (line/area), single y-axis ── */
export function TimeSeries({
  data,
  lines,
  height = 280,
  format = (v) => v.toFixed(2),
  yDomain,
  band,
  refLines = [],
  refAreas = [],
  legend = true,
  ariaLabel,
}: {
  data: Record<string, unknown>[];
  lines: LineSpec[];
  height?: number;
  format?: (v: number, key: string) => string;
  yDomain?: [number | "auto" | "dataMin" | "dataMax", number | "auto" | "dataMin" | "dataMax"];
  band?: { lower: string; upper: string; color: string };
  refLines?: { y: number; label?: string }[];
  refAreas?: { y1: number; y2: number }[];
  legend?: boolean;
  ariaLabel: string;
}) {
  const longRange = data.length > 300;
  const banded = band
    ? data.map((d) => ({ ...d, _band: d[band.lower] != null && d[band.upper] != null ? [d[band.lower], d[band.upper]] : null }))
    : data;
  return (
    <figure aria-label={ariaLabel}>
      {legend && lines.length > 1 && <Legend className="mb-3" items={lines.map((l) => ({ label: l.label, color: l.color, dashed: l.dashed }))} />}
      <div style={{ height }}>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={banded} margin={{ top: 6, right: 4, bottom: 0, left: 0 }}>
            <CartesianGrid vertical={false} stroke="var(--chart-grid)" />
            <XAxis
              dataKey="date"
              tick={AXIS}
              tickLine={false}
              axisLine={false}
              minTickGap={42}
              tickFormatter={(d) => shortDate(d, longRange)}
            />
            <YAxis
              tick={AXIS}
              tickLine={false}
              axisLine={false}
              width={52}
              domain={yDomain ?? ["auto", "auto"]}
              tickFormatter={(v) => format(Number(v), "")}
            />
            {refAreas.map((a, i) => (
              <ReferenceArea key={i} y1={a.y1} y2={a.y2} fill="var(--fill)" fillOpacity={0.6} stroke="none" />
            ))}
            {refLines.map((r) => (
              <ReferenceLine
                key={r.y}
                y={r.y}
                stroke="var(--chart-axis)"
                strokeOpacity={0.5}
                label={r.label ? { value: r.label, position: "insideTopRight", fontSize: 10, fill: "var(--chart-axis)" } : undefined}
              />
            ))}
            {band && <Area dataKey="_band" name="_band" stroke="none" fill={band.color} fillOpacity={0.1} isAnimationActive={false} />}
            {lines.map((l) =>
              l.area ? (
                <Area
                  key={l.key}
                  dataKey={l.key}
                  name={l.label}
                  stroke={l.color}
                  strokeWidth={l.width ?? 2}
                  fill={l.color}
                  fillOpacity={0.1}
                  dot={false}
                  activeDot={{ r: 4, strokeWidth: 2, stroke: "var(--bg-elevated)" }}
                  connectNulls
                  animationDuration={700}
                  animationEasing="ease-out"
                />
              ) : (
                <Line
                  key={l.key}
                  dataKey={l.key}
                  name={l.label}
                  stroke={l.color}
                  strokeWidth={l.width ?? 2}
                  strokeDasharray={l.dashed ? "4 4" : undefined}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  dot={false}
                  activeDot={{ r: 4, strokeWidth: 2, stroke: "var(--bg-elevated)" }}
                  connectNulls
                  animationDuration={700}
                  animationEasing="ease-out"
                />
              ),
            )}
            <Tooltip
              cursor={{ stroke: "var(--chart-axis)", strokeWidth: 1 }}
              content={<TooltipCard format={format} labelFormat={(l) => shortDate(l, true)} />}
              isAnimationActive={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </figure>
  );
}

/* ── Signed columns (e.g. MACD histogram, gain by holding) ── */
export function SignedBars({
  data,
  xKey,
  yKey,
  height = 220,
  format = (v) => v.toFixed(2),
  dateAxis,
  ariaLabel,
  name,
}: {
  data: Record<string, unknown>[];
  xKey: string;
  yKey: string;
  height?: number;
  format?: (v: number, key: string) => string;
  dateAxis?: boolean;
  ariaLabel: string;
  name: string;
}) {
  return (
    <figure aria-label={ariaLabel} style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 6, right: 4, bottom: 0, left: 0 }} barCategoryGap="20%">
          <CartesianGrid vertical={false} stroke="var(--chart-grid)" />
          <XAxis
            dataKey={xKey}
            tick={AXIS}
            tickLine={false}
            axisLine={false}
            minTickGap={dateAxis ? 42 : 4}
            interval={dateAxis ? "preserveStartEnd" : 0}
            tickFormatter={dateAxis ? (d) => shortDate(d) : undefined}
          />
          <YAxis tick={AXIS} tickLine={false} axisLine={false} width={52} tickFormatter={(v) => format(Number(v), "")} />
          <ReferenceLine y={0} stroke="var(--chart-axis)" strokeOpacity={0.6} />
          <Tooltip
            cursor={{ fill: "var(--fill-secondary)" }}
            content={<TooltipCard format={format} labelFormat={dateAxis ? (l) => shortDate(l, true) : undefined} />}
            isAnimationActive={false}
          />
          <Bar dataKey={yKey} name={name} maxBarSize={24} radius={[4, 4, 0, 0]} animationDuration={600}>
            {data.map((d, i) => (
              <Cell key={i} fill={Number(d[yKey]) >= 0 ? "var(--positive)" : "var(--negative)"} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </figure>
  );
}

/* ── Horizontal magnitude bars (e.g. feature importance), single hue ── */
export function HBars({
  data,
  labelKey,
  valueKey,
  format = (v) => v.toFixed(2),
  color = SERIES[0],
  ariaLabel,
}: {
  data: Record<string, unknown>[];
  labelKey: string;
  valueKey: string;
  format?: (v: number) => string;
  color?: string;
  ariaLabel: string;
}) {
  const max = Math.max(...data.map((d) => Number(d[valueKey]) || 0), 1e-9);
  return (
    <ul aria-label={ariaLabel} className="space-y-2.5">
      {data.map((d) => {
        const v = Number(d[valueKey]);
        return (
          <li key={String(d[labelKey])} className="grid grid-cols-[minmax(0,9rem)_1fr_auto] items-center gap-3 text-footnote">
            <span className="truncate text-label-2">{String(d[labelKey])}</span>
            <span className="h-3 rounded-r-[4px] bg-fill-2">
              <span className="block h-full rounded-r-[4px] transition-[width] duration-700" style={{ width: `${(v / max) * 100}%`, background: color }} />
            </span>
            <span className="tabular w-14 text-right font-medium">{format(v)}</span>
          </li>
        );
      })}
    </ul>
  );
}

/* ── Donut with a center readout and a legend list ── */
export function Donut({
  data,
  center,
  format,
  ariaLabel,
  size = 200,
}: {
  data: { label: string; value: number; color: string }[];
  center?: React.ReactNode;
  format: (v: number) => string;
  ariaLabel: string;
  size?: number;
}) {
  const total = data.reduce((s, d) => s + d.value, 0) || 1;
  return (
    <figure aria-label={ariaLabel} className="flex flex-col items-center gap-6 sm:flex-row sm:items-center">
      <div className="relative shrink-0" style={{ width: size, height: size }}>
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              dataKey="value"
              nameKey="label"
              innerRadius="68%"
              outerRadius="100%"
              stroke="var(--bg-elevated)"
              strokeWidth={2}
              cornerRadius={4}
              startAngle={90}
              endAngle={-270}
              animationDuration={700}
            >
              {data.map((d) => (
                <Cell key={d.label} fill={d.color} />
              ))}
            </Pie>
            <Tooltip content={<TooltipCard format={(v) => `${format(v)} · ${((v / total) * 100).toFixed(1)}%`} />} isAnimationActive={false} />
          </PieChart>
        </ResponsiveContainer>
        {center && <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center text-center">{center}</div>}
      </div>
      <ul className="w-full min-w-0 flex-1 space-y-1">
        {data.map((d) => (
          <li key={d.label} className="flex min-h-7 items-center gap-2.5 text-footnote">
            <span className="size-2.5 shrink-0 rounded-[3px]" style={{ background: d.color }} />
            <span className="min-w-0 flex-1 truncate">{d.label}</span>
            <span className="tabular text-label-2">{((d.value / total) * 100).toFixed(1)}%</span>
          </li>
        ))}
      </ul>
    </figure>
  );
}

/* ── Radar for 0–100 scores ── */
export function ScoreRadar({ data, ariaLabel }: { data: { axis: string; score: number }[]; ariaLabel: string }) {
  return (
    <figure aria-label={ariaLabel} className="h-[300px]">
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart data={data} outerRadius="72%">
          <PolarGrid stroke="var(--chart-grid)" />
          <PolarAngleAxis dataKey="axis" tick={{ fontSize: 11, fill: "var(--label-secondary)" }} />
          <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
          <Radar dataKey="score" name="Score" stroke={SERIES[0]} strokeWidth={2} fill={SERIES[0]} fillOpacity={0.12} dot={{ r: 3, fill: SERIES[0], strokeWidth: 0 }} animationDuration={700} />
          <Tooltip content={<TooltipCard format={(v) => `${v.toFixed(0)} / 100`} />} isAnimationActive={false} />
        </RadarChart>
      </ResponsiveContainer>
    </figure>
  );
}
