"use client";

import { createContext, useCallback, useContext } from "react";
import { mutate as globalMutate } from "swr";

import { api, useApi } from "./api";
import type { User } from "./types";

type Session = {
  user: User | null;
  loading: boolean;
  baseCurrency: string;
  setBaseCurrency: (code: string) => Promise<void>;
  logout: () => Promise<void>;
};

const SessionContext = createContext<Session | null>(null);

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const { data: user, isLoading } = useApi<User>("/auth/me");
  const { data: settings, mutate: mutateSettings } = useApi<{ base_currency: string }>(user ? "/settings" : null);

  const setBaseCurrency = useCallback(
    async (code: string) => {
      await mutateSettings(api("/settings", { method: "PUT", json: { base_currency: code } }), {
        optimisticData: { base_currency: code },
      });
      // Every currency-dependent query refetches in the new base.
      globalMutate((key) => typeof key === "string" && key.startsWith("/portfolio/"));
    },
    [mutateSettings],
  );

  const logout = useCallback(async () => {
    await api("/auth/logout", { method: "POST" });
    // Full navigation on purpose: clears every cached query from the signed-out session.
    // eslint-disable-next-line @next/next/no-location-assign-relative-destination
    window.location.href = "/login";
  }, []);

  return (
    <SessionContext.Provider
      value={{ user: user ?? null, loading: isLoading, baseCurrency: settings?.base_currency ?? "USD", setBaseCurrency, logout }}
    >
      {children}
    </SessionContext.Provider>
  );
}

export function useSession() {
  const ctx = useContext(SessionContext);
  if (!ctx) throw new Error("useSession must be used inside SessionProvider");
  return ctx;
}
