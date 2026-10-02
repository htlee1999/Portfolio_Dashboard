import { useCallback, useSyncExternalStore } from "react";

/** localStorage-backed value that is safe to read during render (null on the server). */
const listeners = new Set<() => void>();

function read(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null; // storage blocked (private mode, previews)
  }
}

export function useStoredValue(key: string): [string | null, (v: string) => void] {
  const subscribe = useCallback((cb: () => void) => {
    listeners.add(cb);
    window.addEventListener("storage", cb);
    return () => {
      listeners.delete(cb);
      window.removeEventListener("storage", cb);
    };
  }, []);
  const value = useSyncExternalStore(subscribe, () => read(key), () => null);
  const set = useCallback(
    (v: string) => {
      try {
        if (read(key) === v) return;
        localStorage.setItem(key, v);
      } catch {
        /* storage blocked */
      }
      listeners.forEach((l) => l());
    },
    [key],
  );
  return [value, set];
}
