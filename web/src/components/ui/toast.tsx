"use client";

import { AnimatePresence, motion } from "motion/react";
import { CheckCircle2, AlertCircle, Info } from "lucide-react";
import { createContext, useCallback, useContext, useRef, useState } from "react";

import { spring } from "@/lib/motion";

type Tone = "success" | "error" | "info";
type Toast = { id: number; message: string; tone: Tone };

const ToastContext = createContext<(message: string, tone?: Tone) => void>(() => {});

const ICONS = {
  success: <CheckCircle2 className="size-5 text-positive" strokeWidth={2} aria-hidden />,
  error: <AlertCircle className="size-5 text-negative" strokeWidth={2} aria-hidden />,
  info: <Info className="size-5 text-tint" strokeWidth={2} aria-hidden />,
};

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const nextId = useRef(0);

  const push = useCallback((message: string, tone: Tone = "success") => {
    const id = nextId.current++;
    setToasts((t) => [...t.slice(-2), { id, message, tone }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), tone === "error" ? 6000 : 3200);
  }, []);

  return (
    <ToastContext.Provider value={push}>
      {children}
      <div
        aria-live="polite"
        className="pointer-events-none fixed inset-x-0 top-3 z-[100] flex flex-col items-center gap-2 px-4 sm:top-5"
      >
        <AnimatePresence initial={false}>
          {toasts.map((t) => (
            <motion.div
              key={t.id}
              layout
              initial={{ opacity: 0, y: -24, scale: 0.92 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -12, scale: 0.96 }}
              transition={spring.bouncy}
              drag="y"
              dragConstraints={{ top: 0, bottom: 0 }}
              dragElastic={0.4}
              onDragEnd={(_, info) => info.offset.y < -24 && setToasts((all) => all.filter((x) => x.id !== t.id))}
              className="material-thick squircle pointer-events-auto flex max-w-md items-center gap-2.5 rounded-full py-2.5 pr-5 pl-3.5 text-callout font-medium"
              role={t.tone === "error" ? "alert" : "status"}
            >
              {ICONS[t.tone]}
              <span>{t.message}</span>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  );
}

export const useToast = () => useContext(ToastContext);
