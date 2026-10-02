"use client";

import { motion } from "motion/react";
import { ChevronDown } from "lucide-react";
import { forwardRef, useId } from "react";

import { spring } from "@/lib/motion";
import { cn } from "./cn";

/* ── Segmented control: the selection pill slides between segments on a spring ── */
export function Segmented<T extends string>({
  options,
  value,
  onChange,
  label,
  className,
  size = "md",
}: {
  options: readonly { value: T; label: React.ReactNode }[];
  value: T;
  onChange: (v: T) => void;
  label: string;
  className?: string;
  size?: "md" | "sm";
}) {
  const id = useId();
  return (
    <div
      role="radiogroup"
      aria-label={label}
      className={cn("squircle relative inline-flex rounded-[10px] bg-fill p-[2px]", size === "md" ? "h-9" : "h-8", className)}
    >
      {options.map((o) => {
        const active = o.value === value;
        return (
          <button
            key={o.value}
            role="radio"
            aria-checked={active}
            onClick={() => onChange(o.value)}
            className={cn(
              "relative min-w-11 flex-1 cursor-pointer px-3 text-footnote font-medium whitespace-nowrap transition-colors",
              "before:absolute before:-inset-y-1 before:inset-x-0 before:content-['']",
              active ? "text-label" : "text-label-2 hover:text-label",
            )}
          >
            {active && (
              <motion.span
                layoutId={`seg-${id}`}
                transition={spring.snappy}
                className="squircle absolute inset-0 rounded-[8px] bg-elevated shadow-[0_3px_8px_rgba(0,0,0,0.12),0_3px_1px_rgba(0,0,0,0.04)] dark:bg-[#636366]"
              />
            )}
            <span className="relative">{o.label}</span>
          </button>
        );
      })}
    </div>
  );
}

/* ── Text field ── */
type FieldProps = React.InputHTMLAttributes<HTMLInputElement> & { label?: string; hint?: string; error?: string | null };

export const TextField = forwardRef<HTMLInputElement, FieldProps>(function TextField(
  { label, hint, error, className, id, ...props },
  ref,
) {
  const auto = useId();
  const fieldId = id ?? auto;
  return (
    <label htmlFor={fieldId} className="block">
      {label && <span className="mb-1.5 block px-1 text-footnote font-medium text-label-2">{label}</span>}
      <input
        ref={ref}
        id={fieldId}
        aria-invalid={!!error}
        className={cn(
          "squircle h-11 w-full rounded-[12px] bg-fill-2 px-3.5 text-body text-label transition-shadow outline-none placeholder:text-label-3",
          "focus:bg-elevated focus:shadow-[0_0_0_3.5px_color-mix(in_srgb,var(--tint)_35%,transparent),inset_0_0_0_1px_var(--tint)]",
          error && "shadow-[inset_0_0_0_1px_var(--negative)]",
          className,
        )}
        {...props}
      />
      {(error || hint) && <span className={cn("mt-1.5 block px-1 text-caption", error ? "text-negative" : "text-label-2")}>{error || hint}</span>}
    </label>
  );
});

/* ── Select (native, so it gets the platform picker on touch devices) ── */
export function Select({
  label,
  options,
  className,
  ...props
}: React.SelectHTMLAttributes<HTMLSelectElement> & { label?: string; options: readonly (string | { value: string; label: string })[] }) {
  const id = useId();
  return (
    <label htmlFor={id} className={cn("block", className)}>
      {label && <span className="mb-1.5 block px-1 text-footnote font-medium text-label-2">{label}</span>}
      <span className="relative block">
        <select
          id={id}
          className="squircle h-11 w-full cursor-pointer appearance-none rounded-[12px] bg-fill-2 pr-9 pl-3.5 text-body text-label outline-none focus:shadow-[0_0_0_3.5px_color-mix(in_srgb,var(--tint)_35%,transparent)]"
          {...props}
        >
          {options.map((o) => {
            const v = typeof o === "string" ? o : o.value;
            return (
              <option key={v} value={v}>
                {typeof o === "string" ? o : o.label}
              </option>
            );
          })}
        </select>
        <ChevronDown className="pointer-events-none absolute top-1/2 right-3 size-4 -translate-y-1/2 text-label-2" aria-hidden />
      </span>
    </label>
  );
}

/* ── Switch: thumb travels on a spring ── */
export function Switch({ checked, onChange, label, description }: { checked: boolean; onChange: (v: boolean) => void; label: string; description?: string }) {
  return (
    <label className="flex min-h-11 cursor-pointer items-center justify-between gap-4">
      <span>
        <span className="block text-body">{label}</span>
        {description && <span className="block text-footnote text-label-2">{description}</span>}
      </span>
      <button
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className={cn("relative h-[31px] w-[51px] shrink-0 cursor-pointer rounded-full transition-colors duration-200", checked ? "bg-positive" : "bg-fill-strong")}
      >
        <motion.span
          layout
          transition={spring.snappy}
          className="absolute top-[2px] size-[27px] rounded-full bg-white shadow-[0_3px_8px_rgba(0,0,0,0.15),0_3px_1px_rgba(0,0,0,0.06)]"
          style={{ left: checked ? 22 : 2 }}
        />
      </button>
    </label>
  );
}

/* ── Slider with value readout ── */
export function Slider({
  label,
  value,
  min,
  max,
  step = 1,
  onChange,
  format = (v) => String(v),
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step?: number;
  onChange: (v: number) => void;
  format?: (v: number) => string;
}) {
  const id = useId();
  const fill = ((value - min) / (max - min)) * 100;
  return (
    <div>
      <div className="flex items-baseline justify-between px-1">
        <label htmlFor={id} className="text-footnote font-medium text-label-2">
          {label}
        </label>
        <span className="tabular text-footnote font-semibold">{format(value)}</span>
      </div>
      <input
        id={id}
        type="range"
        className="slider w-full"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        style={{ "--fill-pct": `${fill}%` } as React.CSSProperties}
      />
    </div>
  );
}
