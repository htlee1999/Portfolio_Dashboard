"use client";

import { ChevronDown, Search } from "lucide-react";
import { motion } from "motion/react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import { useStoredValue } from "@/lib/storage";

import { useApi } from "@/lib/api";
import { spring } from "@/lib/motion";
import type { Holding } from "@/lib/types";
import { Button } from "../ui/button";
import { Sheet } from "../ui/overlay";

const KEY = "pd-symbol";
const SYMBOL_RE = /^[A-Z0-9.\-^=]{1,20}$/;

/** The research symbol lives in the URL (?symbol=), remembered across pages. */
export function useSymbol(): [string, (s: string) => void] {
  const params = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const fromUrl = params.get("symbol")?.toUpperCase();
  const [remembered, remember] = useStoredValue(KEY);
  const { data } = useApi<{ holdings: Holding[] }>("/holdings");

  const symbol = fromUrl || remembered || data?.holdings[0]?.Symbol || "AAPL";

  useEffect(() => {
    if (fromUrl) remember(fromUrl);
  }, [fromUrl, remember]);

  const setSymbol = useCallback(
    (s: string) => {
      const next = new URLSearchParams(params.toString());
      next.set("symbol", s.toUpperCase());
      router.replace(`${pathname}?${next.toString()}`, { scroll: false });
    },
    [params, pathname, router],
  );

  return [symbol, setSymbol];
}

export function SymbolPicker({ symbol, onChange }: { symbol: string; onChange: (s: string) => void }) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const { data } = useApi<{ holdings: Holding[] }>("/holdings");
  const owned = useMemo(() => [...new Set((data?.holdings ?? []).map((h) => h.Symbol))].sort(), [data]);
  const q = query.trim().toUpperCase();
  const matches = owned.filter((s) => s.includes(q));
  const canUseQuery = q && SYMBOL_RE.test(q) && !owned.includes(q);

  const choose = (s: string) => {
    onChange(s);
    setOpen(false);
    setQuery("");
  };

  return (
    <>
      <motion.button
        whileTap={{ scale: 0.96 }}
        transition={spring.snappy}
        onClick={() => setOpen(true)}
        aria-label={`Symbol: ${symbol}. Change symbol`}
        className="squircle flex h-11 cursor-pointer items-center gap-2 rounded-[12px] bg-elevated pr-3 pl-4 text-headline shadow-[var(--shadow-card)] hover:bg-fill-2"
      >
        {symbol}
        <ChevronDown className="size-4 text-label-2" strokeWidth={2.4} />
      </motion.button>

      <Sheet open={open} onClose={() => setOpen(false)} title="Choose a symbol">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (canUseQuery || owned.includes(q)) choose(q);
          }}
        >
          <label className="relative block">
            <span className="sr-only">Search or enter a ticker</span>
            <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-label-2" />
            <input
              autoFocus
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search or enter a ticker"
              autoCapitalize="characters"
              autoCorrect="off"
              spellCheck={false}
              className="squircle h-11 w-full rounded-[12px] bg-fill-2 pr-3 pl-9 text-body outline-none placeholder:text-label-3 focus:shadow-[0_0_0_3.5px_color-mix(in_srgb,var(--tint)_35%,transparent)]"
            />
          </label>
        </form>

        {canUseQuery && (
          <Button variant="tinted" className="mt-3 w-full" onClick={() => choose(q)}>
            Analyze {q}
          </Button>
        )}

        {matches.length > 0 && (
          <>
            <div className="mt-5 mb-2 px-1 text-footnote font-medium text-label-2">In your portfolio</div>
            <div className="grid grid-cols-3 gap-2 sm:grid-cols-4">
              {matches.map((s) => (
                <motion.button
                  key={s}
                  whileTap={{ scale: 0.94 }}
                  transition={spring.snappy}
                  onClick={() => choose(s)}
                  className={`squircle h-11 cursor-pointer rounded-[12px] text-callout font-semibold ${s === symbol ? "bg-tint text-white" : "bg-fill-2 hover:bg-fill"}`}
                >
                  {s}
                </motion.button>
              ))}
            </div>
          </>
        )}
      </Sheet>
    </>
  );
}
