"use client";

import { MotionConfig } from "motion/react";

import { ToastProvider } from "@/components/ui/toast";
import { ThemeProvider } from "@/lib/theme";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    // Honors the OS "Reduce Motion" setting for every animation.
    <MotionConfig reducedMotion="user">
      <ThemeProvider>
        <ToastProvider>{children}</ToastProvider>
      </ThemeProvider>
    </MotionConfig>
  );
}
