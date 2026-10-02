"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef } from "react";
import { motion } from "motion/react";

import { spring } from "@/lib/motion";
import { cn } from "../ui/cn";
import { usePageTitle } from "./app-shell";
import { RESEARCH, isActive } from "./nav";

export function PageHeader({
  title,
  subtitle,
  actions,
  eyebrow,
}: {
  title: string;
  subtitle?: React.ReactNode;
  actions?: React.ReactNode;
  eyebrow?: React.ReactNode;
}) {
  const ref = useRef<HTMLHeadingElement>(null);
  const { set } = usePageTitle();

  useEffect(() => {
    document.title = `${title} · Portfolio`;
    const el = ref.current;
    if (!el) return;
    const io = new IntersectionObserver(([entry]) => set(title, !entry.isIntersecting), { rootMargin: "-48px 0px 0px 0px" });
    io.observe(el);
    return () => {
      io.disconnect();
      set("", false);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [title]);

  return (
    <header className="mb-6 flex flex-col gap-4 pt-1 sm:mb-8 sm:flex-row sm:items-end sm:justify-between">
      <div className="min-w-0">
        {eyebrow && <div className="mb-1 text-footnote font-semibold text-label-2">{eyebrow}</div>}
        <h1 ref={ref} className="text-large-title">
          {title}
        </h1>
        {subtitle && <p className="mt-1 text-body text-label-2">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </header>
  );
}

/** Research sub-navigation for phones, where the sidebar is hidden. */
export function ResearchTabs() {
  const pathname = usePathname();
  return (
    <nav aria-label="Research" className="-mx-4 mb-5 overflow-x-auto px-4 lg:hidden [&::-webkit-scrollbar]:hidden">
      <div className="inline-flex gap-1.5">
        {RESEARCH.map((r) => {
          const active = isActive(pathname, r.href);
          return (
            <Link
              key={r.href}
              href={r.href}
              aria-current={active ? "page" : undefined}
              className={cn("relative flex h-9 items-center rounded-full px-4 text-footnote font-semibold whitespace-nowrap", active ? "text-white" : "bg-fill text-label")}
            >
              {active && <motion.span layoutId="research-tab" transition={spring.snappy} className="absolute inset-0 rounded-full bg-tint" />}
              <span className="relative">{r.label}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
