"use client";

import { TrendingUp } from "lucide-react";
import { motion } from "motion/react";

import { spring } from "@/lib/motion";

/** Shared frame for the signed-out screens: soft backdrop, app icon, title and a glass card. */
export function AuthShell({
  title,
  subtitle,
  icon,
  children,
  footer,
}: {
  title: string;
  subtitle: React.ReactNode;
  icon?: React.ReactNode;
  children: React.ReactNode;
  footer?: React.ReactNode;
}) {
  return (
    <main className="relative flex min-h-dvh items-center justify-center overflow-hidden px-4 py-12">
      {/* Soft depth behind the glass card */}
      <div aria-hidden className="pointer-events-none absolute inset-0">
        <div className="absolute -top-32 left-1/2 size-[560px] -translate-x-1/2 rounded-full bg-[radial-gradient(circle,color-mix(in_srgb,var(--tint)_22%,transparent),transparent_65%)] blur-2xl" />
        <div className="absolute right-[-120px] bottom-[-160px] size-[420px] rounded-full bg-[radial-gradient(circle,color-mix(in_srgb,var(--series-3)_16%,transparent),transparent_65%)] blur-2xl" />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 24, scale: 0.97 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={spring.sheet}
        className="relative w-full max-w-[380px]"
      >
        <div className="mb-8 flex flex-col items-center text-center">
          <motion.span
            initial={{ scale: 0.6, rotate: -12 }}
            animate={{ scale: 1, rotate: 0 }}
            transition={{ ...spring.bouncy, delay: 0.08 }}
            className="squircle mb-5 flex size-16 items-center justify-center rounded-[18px] bg-gradient-to-b from-[#3d9bff] to-[#0068e6] text-white shadow-[0_8px_24px_rgba(0,104,230,0.35)] [&_svg]:size-8"
          >
            {icon ?? <TrendingUp strokeWidth={2.3} />}
          </motion.span>
          <h1 className="text-title-1">{title}</h1>
          <p className="mt-1.5 text-body text-label-2">{subtitle}</p>
        </div>

        <div className="material-thick squircle rounded-[22px] p-6">{children}</div>

        {footer && <div className="mt-6 text-center text-callout text-label-2">{footer}</div>}
      </motion.div>
    </main>
  );
}
