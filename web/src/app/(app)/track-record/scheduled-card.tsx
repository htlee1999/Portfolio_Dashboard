"use client";

import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { Badge, Card, CardHeader } from "@/components/ui/card";
import { Banner, Spinner } from "@/components/ui/feedback";
import { useToast } from "@/components/ui/toast";
import { api } from "@/lib/api";
import { dateTime } from "@/lib/format";
import { useScheduled } from "@/lib/scheduled";
import { useSession } from "@/lib/session";

const PROVIDER = { local: "Local", gemini: "Gemini" } as const;

/** Twice-weekly runs over the fixed stock list: live progress, the next run, and recent runs. */
export function ScheduledCard({ onFinished }: { onFinished: () => void }) {
  const { data, mutate } = useScheduled();
  const { user } = useSession();
  const toast = useToast();
  const [starting, setStarting] = useState(false);
  const s = data?.status?.user === user?.username ? data?.status : null;
  const running = s?.state === "running";

  // Reload the signals once a run this page watched finishes, so its calls appear.
  const wasRunning = useRef(false);
  useEffect(() => {
    if (wasRunning.current && !running) onFinished();
    wasRunning.current = running;
  }, [running, onFinished]);

  if (!data) return null;

  const start = async () => {
    setStarting(true);
    try {
      await api("/scheduled/run", { method: "POST" });
      toast("Scheduled run started", "info");
      await mutate();
    } catch (e) {
      toast((e as Error).message, "error");
    } finally {
      setStarting(false);
    }
  };

  return (
    <Card>
      <div id="scheduled" className="scroll-mt-16" />
      <CardHeader
        title="Scheduled runs"
        subtitle="A fixed list of stocks, assessed on Mondays and Fridays at 09:00"
        action={
          user?.role === "admin" && (
            <Button size="sm" variant="tinted" onClick={start} loading={starting} disabled={running}>
              Run now
            </Button>
          )
        }
      />

      {!data.installed && (
        <Banner tone="warning" title="Not scheduled">
          Run <code>./schedule.sh install</code> in the project folder to schedule the runs.
        </Banner>
      )}
      {data.local_problem && (
        <Banner tone="warning" title="Local model unavailable">
          {data.local_problem}. Runs skip the local model until it’s fixed.
        </Banner>
      )}

      {running && s ? (
        <div className="mb-4 space-y-2">
          <div className="flex items-center gap-2 text-callout">
            <Spinner className="size-4" />
            <span>
              Running: {s.done} of {s.total} stocks{s.current && <>, assessing <span className="font-semibold">{s.current}</span></>}
            </span>
            <span className="ml-auto flex gap-1">
              {s.providers.map((p) => (
                <Badge key={p} tone="tint">{PROVIDER[p]}</Badge>
              ))}
            </span>
          </div>
          <div className="h-1.5 overflow-hidden rounded-full bg-fill" role="progressbar" aria-valuemin={0} aria-valuemax={s.total} aria-valuenow={s.done}>
            <div className="h-full rounded-full bg-tint transition-[width] duration-500" style={{ width: `${s.total ? (s.done / s.total) * 100 : 0}%` }} />
          </div>
          <p className="text-footnote text-label-2">
            Started {dateTime(s.started)} · {s.ok} calls saved{s.failed > 0 && `, ${s.failed} failed`}. About a minute per stock on the local model.
          </p>
        </div>
      ) : (
        <p className="mb-4 text-callout">
          Next run {dateTime(data.next_run)}: {data.next_compare ? "local model and Gemini (comparison week)" : `local model (${data.model})`}.
          {s?.state === "interrupted" && <span className="text-negative"> The last run stopped at {s.done} of {s.total}.</span>}
        </p>
      )}

      {data.runs.length > 0 && (
        <table className="w-full text-callout tabular">
          <thead className="text-caption text-label-2">
            <tr>
              <th className="py-1 text-left font-normal">Run</th>
              <th className="py-1 text-left font-normal">Models</th>
              <th className="py-1 text-right font-normal">Calls saved</th>
              <th className="py-1 text-right font-normal">Failed</th>
            </tr>
          </thead>
          <tbody>
            {data.runs.map((r) => (
              <tr key={r.run} className="border-t-[0.5px] border-separator" title={r.errors.map((e) => `${e.symbol}: ${e.error}`).join("\n") || undefined}>
                <td className="py-1.5">{dateTime(r.started)}</td>
                <td className="py-1.5">
                  {r.providers.map((p) => PROVIDER[p]).join(" + ") || "—"}
                  {r.skipped.length > 0 && <span className="text-label-2"> · skipped {r.skipped.map((x) => x.split(":")[0]).join(", ")}</span>}
                </td>
                <td className="py-1.5 text-right">{r.ok}</td>
                <td className={`py-1.5 text-right ${r.failed ? "text-negative" : ""}`}>{r.failed}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Card>
  );
}
