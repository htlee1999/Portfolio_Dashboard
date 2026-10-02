import type { Transition } from "motion/react";

/**
 * Spring presets. Everything animates with mass/stiffness/damping rather than
 * duration curves, so motion is interruptible and carries momentum.
 */
export const spring = {
  /** Snappy UI feedback: presses, toggles, selection indicators. */
  snappy: { type: "spring", stiffness: 520, damping: 38, mass: 0.8 } as Transition,
  /** Default for content entering and layout shifts. */
  smooth: { type: "spring", stiffness: 300, damping: 32, mass: 1 } as Transition,
  /** Sheets and larger surfaces: a touch more mass, gentle settle. */
  sheet: { type: "spring", stiffness: 260, damping: 30, mass: 1.1 } as Transition,
  /** Playful bounce for confirmations. */
  bouncy: { type: "spring", stiffness: 400, damping: 18, mass: 0.9 } as Transition,
};

export const fadeUp = {
  initial: { opacity: 0, y: 12 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -6 },
  transition: spring.smooth,
};

/** Staggered children for lists and grids. */
export const stagger = (step = 0.035) => ({
  animate: { transition: { staggerChildren: step } },
});

export const staggerItem = {
  initial: { opacity: 0, y: 10, scale: 0.985 },
  animate: { opacity: 1, y: 0, scale: 1, transition: spring.smooth },
};
