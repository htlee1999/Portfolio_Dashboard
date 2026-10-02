"use client";

import { motion } from "motion/react";
import { ChevronRight } from "lucide-react";
import Link from "next/link";

import { spring } from "@/lib/motion";
import { cn } from "./cn";

/** Rounded content group on the grouped background (inset-grouped style). */
export function Card({
  className,
  children,
  padded = true,
  ...props
}: React.HTMLAttributes<HTMLDivElement> & { padded?: boolean }) {
  return (
    <div
      className={cn(
        "squircle rounded-[20px] bg-elevated shadow-[var(--shadow-card)]",
        padded && "p-5 sm:p-6",
        className,
      )}
      {...props}
    >
      {children}
    </div>
  );
}

export function Section({
  title,
  description,
  action,
  children,
  className,
}: {
  title?: React.ReactNode;
  description?: React.ReactNode;
  action?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section className={cn("space-y-3", className)}>
      {(title || action) && (
        <div className="flex items-end justify-between gap-4 px-1">
          <div className="min-w-0">
            {title && <h2 className="text-title-3">{title}</h2>}
            {description && <p className="mt-0.5 text-footnote text-label-2">{description}</p>}
          </div>
          {action}
        </div>
      )}
      {children}
    </section>
  );
}

export function CardHeader({ title, subtitle, action }: { title: React.ReactNode; subtitle?: React.ReactNode; action?: React.ReactNode }) {
  return (
    <div className="mb-4 flex items-start justify-between gap-3">
      <div className="min-w-0">
        <h3 className="text-headline">{title}</h3>
        {subtitle && <p className="mt-0.5 text-footnote text-label-2">{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}

/** A list inside a card: rows separated by inset hairlines. */
export function List({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <ul className={cn("squircle overflow-hidden rounded-[20px] bg-elevated shadow-[var(--shadow-card)]", className)}>{children}</ul>
  );
}

export function ListRow({
  title,
  subtitle,
  leading,
  trailing,
  href,
  onClick,
  chevron,
}: {
  title: React.ReactNode;
  subtitle?: React.ReactNode;
  leading?: React.ReactNode;
  trailing?: React.ReactNode;
  href?: string;
  onClick?: () => void;
  chevron?: boolean;
}) {
  const body = (
    <>
      {leading}
      {/* The hairline starts after the leading icon, as in inset-grouped lists. */}
      <div className="flex min-h-11 min-w-0 flex-1 items-center gap-3 border-t-[0.5px] border-separator pr-4 [li:first-child_&]:border-t-0">
        <div className="min-w-0 flex-1 py-2.5">
          <div className="truncate text-body">{title}</div>
          {subtitle && <div className="truncate text-footnote text-label-2">{subtitle}</div>}
        </div>
        {trailing && <div className="shrink-0 text-right">{trailing}</div>}
        {(chevron || href) && <ChevronRight className="size-4 shrink-0 text-label-3" aria-hidden />}
      </div>
    </>
  );
  const cls = "flex w-full items-center gap-3 pl-4 text-left";
  return (
    <li>
      {href ? (
        <Link href={href} className={cn(cls, "transition-colors hover:bg-fill-2")}>
          {body}
        </Link>
      ) : onClick ? (
        <motion.button whileTap={{ scale: 0.99 }} transition={spring.snappy} onClick={onClick} className={cn(cls, "cursor-pointer transition-colors hover:bg-fill-2")}>
          {body}
        </motion.button>
      ) : (
        <div className={cls}>{body}</div>
      )}
    </li>
  );
}

export function Badge({
  tone = "neutral",
  children,
  className,
}: {
  tone?: "neutral" | "positive" | "negative" | "warning" | "tint";
  children: React.ReactNode;
  className?: string;
}) {
  const tones = {
    neutral: "bg-fill text-label-2",
    positive: "bg-positive-fill text-positive",
    negative: "bg-negative-fill text-negative",
    warning: "bg-warning-fill text-warning",
    tint: "bg-tint-fill text-tint",
  };
  return (
    <span className={cn("inline-flex h-6 items-center gap-1 rounded-full px-2.5 text-caption font-semibold", tones[tone], className)}>
      {children}
    </span>
  );
}
