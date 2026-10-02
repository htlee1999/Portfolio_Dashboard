// Shared shape for the research-evidence notes behind the Technicals, Fundamentals and Forecast pages.
// Ratings describe how well peer-reviewed research supports each measure as a return signal;
// testing methods carry no rating, and their verdict explains why the method is used.

export type Evidence = "strong" | "mixed" | "weak" | "risk";

export type Source = { cite: string; url?: string };

export type EvidenceInfo = {
  name: string;
  evidence?: Evidence;
  read: string;
  verdict: string;
  learn?: { site: string; url: string };
  sources: Source[];
};

export const EVIDENCE_LABEL: Record<Evidence, string> = {
  strong: "Strong evidence",
  mixed: "Mixed evidence",
  weak: "Weak evidence",
  risk: "Risk measure",
};

export const EVIDENCE_TONE = {
  strong: "positive",
  mixed: "warning",
  weak: "neutral",
  risk: "tint",
} as const satisfies Record<Evidence, string>;

export const doi = (id: string) => `https://doi.org/${id}`;
