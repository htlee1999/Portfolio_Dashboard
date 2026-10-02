import useSWR, { type SWRConfiguration } from "swr";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function parseError(res: Response): Promise<ApiError> {
  let message = `${res.status} ${res.statusText}`;
  try {
    const body = await res.json();
    if (typeof body.detail === "string") message = body.detail;
    else if (Array.isArray(body.detail)) message = body.detail.map((d: { msg: string }) => d.msg).join(", ");
  } catch {
    /* not JSON */
  }
  return new ApiError(res.status, message);
}

function onUnauthorized() {
  if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
    const next = encodeURIComponent(window.location.pathname + window.location.search);
    // Full navigation on purpose: drops all cached data from the expired session.
    // eslint-disable-next-line @next/next/no-location-assign-relative-destination
    window.location.href = `/login?next=${next}`;
  }
}

// The API rejects state-changing requests without this header (CSRF protection).
const CSRF_HEADER = { "X-Requested-With": "fetch" };

export async function api<T = unknown>(path: string, init: RequestInit & { json?: unknown } = {}): Promise<T> {
  const { json, headers, ...rest } = init;
  const res = await fetch(`/api${path}`, {
    credentials: "same-origin",
    ...rest,
    headers: { ...CSRF_HEADER, ...(json !== undefined && { "Content-Type": "application/json" }), ...headers },
    body: json !== undefined ? JSON.stringify(json) : rest.body,
  });
  if (res.status === 401 && !path.startsWith("/auth/")) onUnauthorized();
  if (!res.ok) throw await parseError(res);
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

/** Download a file response (CSV / PDF) through the browser. */
export async function download(path: string, init: RequestInit & { json?: unknown } = {}) {
  const { json, ...rest } = init;
  const res = await fetch(`/api${path}`, {
    credentials: "same-origin",
    ...rest,
    headers: { ...CSRF_HEADER, ...(json !== undefined && { "Content-Type": "application/json" }) },
    body: json !== undefined ? JSON.stringify(json) : rest.body,
  });
  if (!res.ok) throw await parseError(res);
  const name = res.headers.get("Content-Disposition")?.match(/filename="([^"]+)"/)?.[1] ?? "download";
  const url = URL.createObjectURL(await res.blob());
  const a = Object.assign(document.createElement("a"), { href: url, download: name });
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export function useApi<T>(path: string | null, config?: SWRConfiguration<T>) {
  return useSWR<T>(path, (p: string) => api<T>(p), {
    revalidateOnFocus: false,
    keepPreviousData: true,
    shouldRetryOnError: false,
    ...config,
  });
}
