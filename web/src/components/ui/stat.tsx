"use client";

import { animate, motion, useMotionValue, useTransform } from "motion/react";
import { ArrowDownRight, ArrowUpRight } from "lucide-react";
import { useEffect } from "react";

import { tone as toneOf } from "@/lib/format";
import { cn } from "./cn";

/** A number that springs to its new value instead of jumping. */
export function AnimatedNumber({ value, format }: { value: number; format: (v: number) => string }) {
  const mv = useMotionValue(value);
  const text = useTransform(mv, format);
  useEffect(() => {
    const controls = animate(mv, value, { type: "spring", stiffness: 120, damping: 24, mass: 1 });
    return controls.stop;
  }, [mv, value]);
  return <motion.span>{text}</motion.span>;
}

/** Signed change with arrow + sign so it never relies on color alone. */
export function Delta({ value, children, className }: { value: number | null | undefined; children: React.ReactNode; className?: string }) {
  const t = toneOf(value);
  const Icon = t === "negative" ? ArrowDownRight : ArrowUpRight;
  return (
    <span
      className={cn(
        "tabular inline-flex items-center gap-0.5 font-semibold",
        t === "positive" && "text-positive",
        t === "negative" && "text-negative",
        t === "neutral" && "text-label-2",
        className,
      )}
    >
      {t !== "neutral" && <Icon className="size-[1.05em] shrink-0" strokeWidth={2.5} aria-hidden />}
      {children}
    </span>
  );
}

export function Stat({
  label,
  value,
  detail,
  className,
}: {
  label: string;
  value: React.ReactNode;
  detail?: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("min-w-0", className)}>
      <div className="text-footnote font-medium text-label-2">{label}</div>
      <div className="mt-1 truncate text-title-2 tabular">{value}</div>
      {detail && <div className="mt-0.5 text-footnote">{detail}</div>}
    </div>
  );
}

/** A grid of stats sharing one card, separated by hairlines. */
export function StatGrid({ children, cols = 4 }: { children: React.ReactNode; cols?: 2 | 3 | 4 }) {
  return (
    <div
      className={cn(
        "squircle grid grid-cols-2 gap-px overflow-hidden rounded-[20px] bg-separator shadow-[var(--shadow-card)]",
        cols === 3 && "lg:grid-cols-3",
        cols === 4 && "lg:grid-cols-4",
        "[&>*]:bg-elevated [&>*]:p-5",
      )}
    >
      {children}
    </div>
  );
}
