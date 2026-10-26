"use client";

import { BookOpen, ChevronDown, ChevronLeft, ChevronRight, Lightbulb, TriangleAlert } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useState } from "react";

import { GUIDES, type Guide, type GuideKey } from "@/lib/guides";
import { spring } from "@/lib/motion";
import { Button } from "../ui/button";
import { cn } from "../ui/cn";

const storageKey = (page: string) => `pd-guide-open:${page}`;

function readOpen(page: string): boolean {
  try {
    return localStorage.getItem(storageKey(page)) === "1";
  } catch {
    return false;
  }
}

/** "How to read this page": a step-by-step walkthrough shown under the page header. */
export function PageGuide({ page }: { page: GuideKey }) {
  const guide: Guide = GUIDES[page];
  // Closed by default; once opened it stays open for this page, in this browser, until closed.
  // (App pages render only in the browser, after the session loads, so storage is readable here.)
  const [open, setOpen] = useState(() => readOpen(page));
  const [step, setStep] = useState(0);

  const toggle = () => {
    const next = !open;
    setOpen(next);
    try {
      localStorage.setItem(storageKey(page), next ? "1" : "0");
    } catch {
      /* storage unavailable: the choice just isn't remembered */
    }
  };

  const s = guide.steps[step];
  const last = guide.steps.length - 1;

  return (
    <section aria-label="How to read this page" className="squircle mb-5 overflow-hidden rounded-[20px] bg-tint-fill">
      <button onClick={toggle} aria-expanded={open} className="flex w-full cursor-pointer items-center gap-3 px-5 py-3.5 text-left sm:px-6">
        <BookOpen className="size-5 shrink-0 text-tint" aria-hidden />
        <span className="min-w-0 flex-1">
          <span className="block text-headline">How to read this page</span>
          {!open && <span className="block truncate text-footnote text-label-2">{guide.steps.length} steps · {guide.intro}</span>}
        </span>
        <ChevronDown className={cn("size-5 shrink-0 text-label-2 transition-transform", open && "rotate-180")} aria-hidden />
      </button>

      <AnimatePresence initial={false}>
        {open && (
          <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} transition={spring.smooth}>
            <div className="px-5 pb-5 sm:px-6">
              <p className="mb-4 max-w-3xl text-callout text-label-2">{guide.intro}</p>
              <div className="grid gap-4 md:grid-cols-[220px_1fr]">
                <ol className="flex gap-1.5 overflow-x-auto md:flex-col md:overflow-visible [&::-webkit-scrollbar]:hidden" aria-label="Steps">
                  {guide.steps.map((st, i) => (
                    <li key={st.title} className="shrink-0">
                      <button
                        onClick={() => setStep(i)}
                        aria-current={i === step ? "step" : undefined}
                        className={cn(
                          "flex w-full cursor-pointer items-center gap-2.5 rounded-[10px] px-2.5 py-1.5 text-left text-footnote transition-colors",
                          i === step ? "bg-elevated font-semibold text-label shadow-[var(--shadow-card)]" : "text-label-2 hover:bg-fill-2",
                        )}
                      >
                        <span className={cn("flex size-5 shrink-0 items-center justify-center rounded-full text-caption font-semibold tabular", i === step ? "bg-tint text-white" : i < step ? "bg-tint-fill text-tint" : "bg-fill text-label-2")}>
                          {i + 1}
                        </span>
                        <span className="hidden md:inline">{st.title}</span>
                      </button>
                    </li>
                  ))}
                </ol>

                <div className="squircle min-w-0 rounded-[14px] bg-elevated p-4 shadow-[var(--shadow-card)] sm:p-5">
                  <AnimatePresence mode="wait" initial={false}>
                    <motion.div key={step} initial={{ opacity: 0, x: 8 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -8 }} transition={{ duration: 0.15 }}>
                      <p className="text-caption font-semibold text-tint">Step {step + 1} of {guide.steps.length}</p>
                      <h3 className="mt-0.5 text-headline">{s.title}</h3>
                      <p className="mt-2 text-callout">{s.body}</p>
                      {s.meaning && (
                        <div className="mt-3 flex gap-2.5 rounded-[10px] bg-fill-2 px-3 py-2.5 text-footnote">
                          <Lightbulb className="mt-px size-4 shrink-0 text-tint" aria-hidden />
                          <p><span className="font-semibold">How to read it: </span>{s.meaning}</p>
                        </div>
                      )}
                      {s.caution && (
                        <div className="mt-2 flex gap-2.5 rounded-[10px] bg-warning-fill px-3 py-2.5 text-footnote">
                          <TriangleAlert className="mt-px size-4 shrink-0 text-warning" aria-hidden />
                          <p><span className="font-semibold">Watch out: </span>{s.caution}</p>
                        </div>
                      )}
                    </motion.div>
                  </AnimatePresence>
                  <div className="mt-4 flex items-center justify-between gap-2">
                    <Button variant="gray" size="sm" icon={<ChevronLeft className="size-4" />} disabled={step === 0} onClick={() => setStep(step - 1)}>
                      Back
                    </Button>
                    {step < last ? (
                      <Button size="sm" onClick={() => setStep(step + 1)}>
                        Next <ChevronRight className="size-4" aria-hidden />
                      </Button>
                    ) : (
                      <Button variant="tinted" size="sm" onClick={toggle}>
                        Got it
                      </Button>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </section>
  );
}
