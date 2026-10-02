"use client";

import { AnimatePresence, motion, useDragControls } from "motion/react";
import { ChevronDown, X } from "lucide-react";
import { useEffect, useId, useRef, useState } from "react";

import { spring } from "@/lib/motion";
import { cn } from "./cn";

/**
 * Modal sheet. Rises from the bottom on small screens (drag down to dismiss,
 * with rubber-banding) and floats centered on larger screens.
 */
export function Sheet({
  open,
  onClose,
  title,
  children,
  footer,
  wide,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
  wide?: boolean;
}) {
  const titleId = useId();
  const drag = useDragControls();
  const panel = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    panel.current?.querySelector<HTMLElement>("input,select,textarea,button")?.focus();
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
    };
  }, [open, onClose]);

  return (
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-50 flex items-end justify-center sm:items-center sm:p-6">
          <motion.div
            className="absolute inset-0 bg-black/30 dark:bg-black/55"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            onClick={onClose}
          />
          <motion.div
            ref={panel}
            role="dialog"
            aria-modal="true"
            aria-labelledby={titleId}
            initial={{ y: "100%", opacity: 0.6, scale: 1 }}
            animate={{ y: 0, opacity: 1, scale: 1 }}
            exit={{ y: "100%", opacity: 0.6 }}
            transition={spring.sheet}
            drag="y"
            dragListener={false}
            dragControls={drag}
            dragConstraints={{ top: 0, bottom: 0 }}
            dragElastic={{ top: 0.05, bottom: 0.6 }}
            onDragEnd={(_, info) => (info.offset.y > 120 || info.velocity.y > 600) && onClose()}
            className={cn(
              "squircle relative flex max-h-[92dvh] w-full flex-col overflow-hidden rounded-t-[22px] bg-elevated shadow-[var(--shadow-raised)] sm:rounded-[22px]",
              wide ? "sm:max-w-2xl" : "sm:max-w-md",
            )}
          >
            <div className="flex cursor-grab touch-none justify-center pt-2 sm:hidden" onPointerDown={(e) => drag.start(e)}>
              <span className="h-[5px] w-9 rounded-full bg-fill-strong" />
            </div>
            <header className="flex items-center justify-between px-5 pt-3 pb-2 sm:pt-5">
              <h2 id={titleId} className="text-title-3">
                {title}
              </h2>
              <button
                onClick={onClose}
                aria-label="Close"
                className="-mr-2 flex size-11 cursor-pointer items-center justify-center rounded-full text-label-2 hover:text-label"
              >
                <span className="flex size-[30px] items-center justify-center rounded-full bg-fill">
                  <X className="size-4" strokeWidth={2.5} />
                </span>
              </button>
            </header>
            <div className="overflow-y-auto px-5 pb-5">{children}</div>
            {footer && <div className="hairline-t flex justify-end gap-2 px-5 py-3 pb-[max(12px,env(safe-area-inset-bottom))]">{footer}</div>}
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}

/** Expand/collapse row whose height animates on a spring. */
export function Disclosure({
  title,
  subtitle,
  leading,
  trailing,
  defaultOpen = false,
  children,
}: {
  title: React.ReactNode;
  subtitle?: React.ReactNode;
  leading?: React.ReactNode;
  trailing?: React.ReactNode;
  defaultOpen?: boolean;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  const id = useId();
  return (
    <div className="border-t-[0.5px] border-separator first:border-t-0">
      <button
        aria-expanded={open}
        aria-controls={id}
        onClick={() => setOpen((o) => !o)}
        className="flex min-h-11 w-full cursor-pointer items-center gap-3 py-3 text-left"
      >
        {leading}
        <div className="min-w-0 flex-1">
          <div className="text-body font-medium">{title}</div>
          {subtitle && <div className="text-footnote text-label-2">{subtitle}</div>}
        </div>
        {trailing}
        <motion.span animate={{ rotate: open ? 180 : 0 }} transition={spring.snappy} className="text-label-3">
          <ChevronDown className="size-4" />
        </motion.span>
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            id={id}
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={spring.smooth}
            className="overflow-hidden"
          >
            <div className="pb-4">{children}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
