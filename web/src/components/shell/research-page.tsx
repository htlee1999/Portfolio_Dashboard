"use client";

import { Suspense, useEffect, useState } from "react";

import { LoadingBlock } from "../ui/feedback";

/** Research pages read ?symbol= from the URL, which needs a Suspense boundary. */
export function ResearchPage({ children }: { children: React.ReactNode }) {
  return <Suspense fallback={<LoadingBlock />}>{children}</Suspense>;
}

export function useDebounced<T>(value: T, delay = 350): T {
  const [v, setV] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setV(value), delay);
    return () => clearTimeout(t);
  }, [value, delay]);
  return v;
}
