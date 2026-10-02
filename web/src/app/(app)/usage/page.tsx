"use client";

import { Download, Gauge, Trash2 } from "lucide-react";
import { motion } from "motion/react";
import { useState } from "react";

import { HBars, SERIES, TimeSeries } from "@/components/charts/charts";
import { PageHeader } from "@/components/shell/page-header";
import { Button } from "@/components/ui/button";
import { Badge, Card, CardHeader } from "@/components/ui/card";
import { Segmented } from "@/components/ui/controls";
import { Banner, EmptyState, LoadingBlock } from "@/components/ui/feedback";
import { Stat, StatGrid } from "@/components/ui/stat";
import { useToast } from "@/components/ui/toast";
import { api, download, useApi } from "@/lib/api";
import { compact, dateTime, number, pct } from "@/lib/format";
import { spring } from "@/lib/motion";
import { useSession } from "@/lib/session";
import type { Usage } from "@/lib/types";

const RANGES = [
  { value: "7", label: "7D" },
  { value: "30", label: "30D" },
  { value: "90", label: "90D" },
  { value: "3650", label: "All" },
] as const;

const usd = (v: number) => `$${v < 1 ? v.toFixed(4) : v.toFixed(2)}`;

export default function UsagePage() {
  const toast = useToast();
  const { user } = useSession();
  const [days, setDays] = useState<string>("30");
  const { data, error, isLoading, mutate } = useApi<Usage>(`/usage?days=${days}`);

  async function clearOld() {
    try {
      const r = await api<{ removed: number }>("/usage/old?days=90", { method: "DELETE" });
      toast(`Removed ${r.removed} records older than 90 days`);
      mutate();
    } catch (e) {
      toast((e as Error).message, "error");
    }
  }

  return (
    <>
      <PageHeader
        title="API Usage"
        subtitle="Gemini calls, tokens and estimated cost"
        actions={<Segmented label="Range" options={RANGES} value={days} onChange={setDays} />}
      />

      {error && <Banner tone="error" title="Couldn't load usage">{error.message}</Banner>}

      {isLoading && !data ? (
        <LoadingBlock />
      ) : data && data.total_calls === 0 ? (
        <Card>
          <EmptyState icon={<Gauge className="size-7" />} title="No API calls in this range">
            Generate an AI assessment and its token usage will appear here.
          </EmptyState>
        </Card>
      ) : data ? (
        <div className="space-y-5">
          <StatGrid>
            <Stat label="Calls" value={number(data.total_calls, 0)} detail={<span className="text-label-2">{data.failed_calls ? `${data.failed_calls} failed` : "all succeeded"}</span>} />
            <Stat label="Tokens" value={compact(data.total_tokens)} detail={<span className="text-label-2">{number(data.avg_tokens_per_call, 0)} per call</span>} />
            <Stat label="Est. cost" value={usd(data.total_cost)} detail={<span className="text-label-2">{usd(data.total_calls ? data.total_cost / data.total_calls : 0)} per call</span>} />
            <Stat label="Success rate" value={pct((data.successful_calls / data.total_calls) * 100, 1, false)} />
          </StatGrid>

          <Card>
            <CardHeader title="Rate limits" subtitle="Gemini free-tier defaults · set in backend/usage.py" />
            <div className="grid gap-5 sm:grid-cols-3">
              <Meter label="Requests, last minute" used={data.rate.minute} limit={data.rate.limits.minute} />
              <Meter label="Requests, last hour" used={data.rate.hour} limit={data.rate.limits.hour} />
              <Meter label="Tokens today" used={data.rate.day_tokens} limit={data.rate.limits.day_tokens} />
            </div>
          </Card>

          <div className="grid gap-5 lg:grid-cols-2">
            <Card>
              <CardHeader title="Tokens per day" />
              <TimeSeries data={data.daily} height={200} lines={[{ key: "tokens", label: "Tokens", color: SERIES[0], area: true }]} format={(v) => compact(v)} ariaLabel="Tokens per day" />
            </Card>
            <Card>
              <CardHeader title="Cost per day" subtitle="USD, estimated" />
              <TimeSeries data={data.daily} height={200} lines={[{ key: "cost", label: "Cost", color: SERIES[1], area: true }]} format={(v) => usd(v)} ariaLabel="Estimated cost per day" />
            </Card>
          </div>

          <div className="grid gap-5 lg:grid-cols-2">
            <Card>
              <CardHeader title="Calls by symbol" />
              <HBars data={data.symbols.slice(0, 10)} labelKey="name" valueKey="calls" format={(v) => number(v, 0)} ariaLabel="API calls by symbol" />
            </Card>
            <Card>
              <CardHeader title="Recent calls" />
              <ul className="-my-2">
                {data.recent.slice(0, 8).map((r) => (
                  <li key={r.timestamp} className="flex items-center gap-3 border-t-[0.5px] border-separator py-2.5 text-footnote first:border-t-0">
                    <Badge tone={r.success ? "positive" : "negative"}>{r.success ? "OK" : "Failed"}</Badge>
                    <span className="min-w-0 flex-1 truncate">
                      <span className="font-semibold">{r.symbol ?? r.operation}</span> <span className="text-label-2">· {dateTime(r.timestamp)}</span>
                    </span>
                    <span className="tabular text-label-2">{compact(r.total_tokens)} tok</span>
                  </li>
                ))}
              </ul>
            </Card>
          </div>

          <div className="flex flex-wrap justify-end gap-2">
            {user?.role === "admin" && (
              <Button variant="destructive" icon={<Trash2 className="size-[18px]" />} onClick={clearOld}>
                Clear Records Older Than 90 Days
              </Button>
            )}
            <Button variant="gray" icon={<Download className="size-[18px]" />} onClick={() => download(`/usage/export?days=${days}`)}>
              Export CSV
            </Button>
          </div>
        </div>
      ) : null}
    </>
  );
}

function Meter({ label, used, limit }: { label: string; used: number; limit: number }) {
  const ratio = Math.min(1, used / limit);
  const tone = ratio > 0.8 ? "var(--negative)" : ratio > 0.5 ? "var(--warning)" : "var(--positive)";
  return (
    <div>
      <div className="flex items-baseline justify-between text-footnote">
        <span className="text-label-2">{label}</span>
        <span className="tabular font-semibold">
          {number(used, 0)} <span className="font-normal text-label-2">/ {compact(limit)}</span>
        </span>
      </div>
      <div className="mt-2 h-2 overflow-hidden rounded-full bg-fill" role="meter" aria-valuenow={used} aria-valuemin={0} aria-valuemax={limit} aria-label={label}>
        <motion.div className="h-full rounded-full" style={{ background: tone }} initial={{ width: 0 }} animate={{ width: `${Math.max(ratio * 100, used ? 2 : 0)}%` }} transition={spring.smooth} />
      </div>
    </div>
  );
}
