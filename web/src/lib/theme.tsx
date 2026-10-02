"use client";

import { createContext, useCallback, useContext, useEffect, useSyncExternalStore } from "react";

import { useStoredValue } from "./storage";

export type ThemePref = "system" | "light" | "dark";
const KEY = "pd-theme";

/** Inline script run before paint so the first frame is in the right appearance. */
export const themeBootScript = `(function(){try{var p=localStorage.getItem('${KEY}')||'system';var d=p==='dark'||(p==='system'&&matchMedia('(prefers-color-scheme: dark)').matches);document.documentElement.dataset.theme=d?'dark':'light';}catch(e){document.documentElement.dataset.theme=matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light';}})();`;

const DARK_QUERY = "(prefers-color-scheme: dark)";

function useSystemDark() {
  return useSyncExternalStore(
    (cb) => {
      const mq = window.matchMedia(DARK_QUERY);
      mq.addEventListener("change", cb);
      return () => mq.removeEventListener("change", cb);
    },
    () => window.matchMedia(DARK_QUERY).matches,
    () => false,
  );
}

const ThemeContext = createContext<{ pref: ThemePref; resolved: "light" | "dark"; setPref: (p: ThemePref) => void }>({
  pref: "system",
  resolved: "light",
  setPref: () => {},
});

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [stored, store] = useStoredValue(KEY);
  const systemDark = useSystemDark();
  const pref = (stored as ThemePref | null) ?? "system";
  const resolved = pref === "system" ? (systemDark ? "dark" : "light") : pref;

  useEffect(() => {
    document.documentElement.dataset.theme = resolved;
  }, [resolved]);

  const setPref = useCallback((p: ThemePref) => store(p), [store]);

  return <ThemeContext.Provider value={{ pref, resolved, setPref }}>{children}</ThemeContext.Provider>;
}

export const useTheme = () => useContext(ThemeContext);
