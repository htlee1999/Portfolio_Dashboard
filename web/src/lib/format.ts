const NO_DECIMALS = new Set(["JPY", "KRW", "IDR", "VND"]);

export function money(value: number | null | undefined, currency = "USD", opts: { compact?: boolean; sign?: boolean } = {}) {
  if (value == null || Number.isNaN(value)) return "—";
  const digits = NO_DECIMALS.has(currency) ? 0 : 2;
  try {
    return new Intl.NumberFormat(undefined, {
      style: "currency",
      currency,
      notation: opts.compact ? "compact" : "standard",
      minimumFractionDigits: opts.compact ? 0 : digits,
      maximumFractionDigits: opts.compact ? 1 : digits,
      signDisplay: opts.sign ? "exceptZero" : "auto",
    }).format(value);
  } catch {
    return `${currency} ${value.toFixed(digits)}`;
  }
}

export function pct(value: number | null | undefined, digits = 2, sign = true) {
  if (value == null || Number.isNaN(value)) return "—";
  return new Intl.NumberFormat(undefined, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
    signDisplay: sign ? "exceptZero" : "auto",
  }).format(value) + "%";
}

export function number(value: number | null | undefined, digits = 2) {
  if (value == null || Number.isNaN(value)) return "—";
  return new Intl.NumberFormat(undefined, { minimumFractionDigits: digits, maximumFractionDigits: digits }).format(value);
}

export function compact(value: number | null | undefined) {
  if (value == null || Number.isNaN(value)) return "—";
  return new Intl.NumberFormat(undefined, { notation: "compact", maximumFractionDigits: 1 }).format(value);
}

export function shortDate(iso: string | null | undefined, withYear = false) {
  if (!iso) return "—";
  const d = new Date(iso.length === 10 ? `${iso}T00:00:00` : iso);
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric", ...(withYear ? { year: "numeric" } : {}) });
}

export function dateTime(iso: string | null | undefined) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString(undefined, { month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit" });
}

export function relative(iso: string | null | undefined) {
  if (!iso) return "never";
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  const rtf = new Intl.RelativeTimeFormat(undefined, { numeric: "auto" });
  if (diff < 60) return "just now";
  if (diff < 3600) return rtf.format(-Math.round(diff / 60), "minute");
  if (diff < 86400) return rtf.format(-Math.round(diff / 3600), "hour");
  return rtf.format(-Math.round(diff / 86400), "day");
}

export function bytes(n: number) {
  if (n < 1024) return `${n} B`;
  if (n < 1024 ** 2) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 ** 2).toFixed(1)} MB`;
}

/** Semantic tone for a signed value. */
export function tone(value: number | null | undefined): "positive" | "negative" | "neutral" {
  if (value == null || value === 0 || Number.isNaN(value)) return "neutral";
  return value > 0 ? "positive" : "negative";
}

export const PERIODS = [
  { value: "1mo", label: "1M" },
  { value: "3mo", label: "3M" },
  { value: "6mo", label: "6M" },
  { value: "1y", label: "1Y" },
  { value: "2y", label: "2Y" },
  { value: "5y", label: "5Y" },
] as const;
