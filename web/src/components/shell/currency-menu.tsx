"use client";

import { ChevronDown } from "lucide-react";

import { CURRENCIES } from "@/lib/portfolio";
import { useSession } from "@/lib/session";

/** Compact base-currency picker for page toolbars. */
export function CurrencyMenu() {
  const { baseCurrency, setBaseCurrency } = useSession();
  return (
    <label className="squircle relative flex h-11 items-center rounded-[12px] bg-elevated shadow-[var(--shadow-card)] hover:bg-fill-2">
      <span className="sr-only">Base currency</span>
      <select
        value={baseCurrency}
        onChange={(e) => setBaseCurrency(e.target.value)}
        className="h-full cursor-pointer appearance-none bg-transparent pr-9 pl-4 text-callout font-semibold outline-none"
      >
        {CURRENCIES.map((c) => (
          <option key={c}>{c}</option>
        ))}
      </select>
      <ChevronDown className="pointer-events-none absolute right-3 size-4 text-label-2" strokeWidth={2.4} />
    </label>
  );
}
