"use client";

import { motion, type HTMLMotionProps } from "motion/react";
import { forwardRef } from "react";

import { spring } from "@/lib/motion";
import { cn } from "./cn";
import { Spinner } from "./feedback";

type Variant = "filled" | "tinted" | "gray" | "plain" | "destructive";
type Size = "md" | "lg" | "sm";

const VARIANTS: Record<Variant, string> = {
  filled: "bg-tint text-white hover:brightness-110 active:brightness-95",
  tinted: "bg-tint-fill text-tint hover:bg-[color-mix(in_srgb,var(--tint)_18%,transparent)]",
  gray: "bg-fill text-label hover:bg-fill-strong",
  plain: "text-tint hover:bg-fill-2",
  destructive: "bg-negative-fill text-negative hover:bg-[color-mix(in_srgb,var(--negative)_20%,transparent)]",
};

// Every size keeps a 44pt hit area; "sm" pads its hit area with an invisible inset.
const SIZES: Record<Size, string> = {
  sm: "h-8 px-3 text-footnote font-semibold rounded-full relative before:absolute before:-inset-y-1.5 before:inset-x-0 before:content-['']",
  md: "h-11 px-5 text-body font-semibold rounded-[12px]",
  lg: "h-[50px] px-6 text-headline rounded-[14px]",
};

export type ButtonProps = Omit<HTMLMotionProps<"button">, "children"> & {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  icon?: React.ReactNode;
  children?: React.ReactNode;
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = "filled", size = "md", loading, icon, className, children, disabled, ...props },
  ref,
) {
  return (
    <motion.button
      ref={ref}
      whileTap={disabled || loading ? undefined : { scale: 0.96 }}
      transition={spring.snappy}
      disabled={disabled || loading}
      className={cn(
        "squircle inline-flex shrink-0 cursor-pointer items-center justify-center gap-2 whitespace-nowrap transition-[background-color,filter,opacity] duration-150 select-none disabled:cursor-default disabled:opacity-40",
        VARIANTS[variant],
        SIZES[size],
        className,
      )}
      {...props}
    >
      {loading ? <Spinner className={variant === "filled" ? "text-white" : undefined} /> : icon}
      {children}
    </motion.button>
  );
});

export function IconButton({
  label,
  className,
  children,
  ...props
}: Omit<HTMLMotionProps<"button">, "children"> & { label: string; children: React.ReactNode }) {
  return (
    <motion.button
      whileTap={{ scale: 0.9 }}
      transition={spring.snappy}
      aria-label={label}
      title={label}
      className={cn(
        "inline-flex size-11 shrink-0 cursor-pointer items-center justify-center rounded-full text-tint transition-colors hover:bg-fill-2 disabled:opacity-40",
        className,
      )}
      {...props}
    >
      {children}
    </motion.button>
  );
}
