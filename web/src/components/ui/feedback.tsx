"use client";

import { AlertTriangle, Info, XCircle } from "lucide-react";
import { motion } from "motion/react";

import { spring } from "@/lib/motion";
import { cn } from "./cn";

export function Spinner({ className }: { className?: string }) {
  // Apple-style activity indicator: 8 tapered spokes fading in sequence.
  return (
    <span role="status" aria-label="Loading" className={cn("relative inline-block size-[18px] text-label-2", className)}>
      {Array.from({ length: 8 }).map((_, i) => (
        <span
          key={i}
          className="absolute top-0 left-[calc(50%-1px)] h-[30%] w-[2px] origin-[50%_166%] rounded-full bg-current"
          style={{
            transform: `rotate(${i * 45}deg)`,
            animation: `pd-spoke 0.8s linear ${(i - 8) * 0.1}s infinite`,
          }}
        />
      ))}
      <style>{`@keyframes pd-spoke{0%{opacity:1}100%{opacity:.18}}`}</style>
    </span>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return (
    <span
      aria-hidden
      className={cn("block animate-pulse rounded-[8px] bg-fill-2 motion-reduce:animate-none", className)}
    />
  );
}

export function Banner({
  tone = "info",
  title,
  children,
  action,
}: {
  tone?: "info" | "warning" | "error";
  title?: string;
  children?: React.ReactNode;
  action?: React.ReactNode;
}) {
  const styles = {
    info: { cls: "bg-tint-fill", icon: <Info className="size-5 text-tint" aria-hidden /> },
    warning: { cls: "bg-warning-fill", icon: <AlertTriangle className="size-5 text-warning" aria-hidden /> },
    error: { cls: "bg-negative-fill", icon: <XCircle className="size-5 text-negative" aria-hidden /> },
  }[tone];
  return (
    <motion.div
      initial={{ opacity: 0, y: -6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={spring.smooth}
      role={tone === "error" ? "alert" : "status"}
      className={cn("squircle flex items-start gap-3 rounded-[14px] px-4 py-3", styles.cls)}
    >
      <span className="mt-px">{styles.icon}</span>
      <div className="min-w-0 flex-1 text-callout">
        {title && <p className="font-semibold">{title}</p>}
        {children && <div className="text-label-2">{children}</div>}
      </div>
      {action}
    </motion.div>
  );
}

export function EmptyState({
  icon,
  title,
  children,
  action,
}: {
  icon: React.ReactNode;
  title: string;
  children?: React.ReactNode;
  action?: React.ReactNode;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.97 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={spring.smooth}
      className="flex flex-col items-center px-6 py-16 text-center"
    >
      <div className="squircle mb-4 flex size-16 items-center justify-center rounded-[18px] bg-fill-2 text-label-2">{icon}</div>
      <h2 className="text-title-3">{title}</h2>
      {children && <div className="mt-1.5 max-w-sm text-callout text-label-2">{children}</div>}
      {action && <div className="mt-6">{action}</div>}
    </motion.div>
  );
}

export function LoadingBlock({ label = "Loading" }: { label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-20 text-footnote text-label-2">
      <Spinner className="size-6" />
      {label}
    </div>
  );
}
