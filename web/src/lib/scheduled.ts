import { useApi } from "./api";
import type { ScheduledRuns } from "./types";

/** Scheduled-run status, polled every 10 seconds while a run is going and every minute otherwise. */
export function useScheduled() {
  return useApi<ScheduledRuns>("/scheduled", {
    refreshInterval: (data) => (data?.status?.state === "running" ? 10_000 : 60_000),
  });
}
