import { ExternalLink } from "lucide-react";

import { Badge } from "@/components/ui/card";
import { cn } from "@/components/ui/cn";
import { EVIDENCE_LABEL, EVIDENCE_TONE, type Evidence, type EvidenceInfo } from "@/lib/evidence";

const EVIDENCE_DOT = { strong: "bg-positive", mixed: "bg-warning", weak: "bg-label-3", risk: "bg-tint" } as const satisfies Record<Evidence, string>;

/** A coloured dot for an evidence rating; the label is read by screen readers and shown on hover. */
export function EvidenceDot({ info, className }: { info: EvidenceInfo; className?: string }) {
  if (!info.evidence) return null;
  return (
    <span title={`${EVIDENCE_LABEL[info.evidence]}: ${info.verdict}`} className={cn("inline-flex shrink-0", className)}>
      <span aria-hidden className={`size-1.5 rounded-full ${EVIDENCE_DOT[info.evidence]}`} />
      <span className="sr-only">{EVIDENCE_LABEL[info.evidence]}</span>
    </span>
  );
}

/** A dot with its label, for card footers. */
export function EvidenceTag({ info, className }: { info: EvidenceInfo; className?: string }) {
  if (!info.evidence) return null;
  return (
    <div className={cn("flex items-center gap-1.5 text-caption text-label-2", className)} title={info.verdict}>
      <span aria-hidden className={`size-1.5 shrink-0 rounded-full ${EVIDENCE_DOT[info.evidence]}`} />
      {EVIDENCE_LABEL[info.evidence]}
    </div>
  );
}

export function EvidenceLegend({ className }: { className?: string }) {
  return (
    <div className={cn("flex flex-wrap gap-x-3 gap-y-1 text-caption text-label-2", className)} aria-hidden>
      {(Object.keys(EVIDENCE_DOT) as Evidence[]).map((e) => (
        <span key={e} className="flex items-center gap-1.5">
          <span className={`size-1.5 rounded-full ${EVIDENCE_DOT[e]}`} />
          {EVIDENCE_LABEL[e]}
        </span>
      ))}
    </div>
  );
}

export function SourceLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <a href={href} target="_blank" rel="noreferrer" className="inline-flex items-baseline gap-1 text-tint hover:underline">
      {children}
      <ExternalLink aria-hidden className="size-3 shrink-0 self-center" />
    </a>
  );
}

/** How to read each measure, its evidence rating and verdict, and sources, optionally in titled sections. */
export function EvidenceGuide({
  sections,
  intro,
  outro,
}: {
  sections: { title?: string; items: EvidenceInfo[] }[];
  intro: React.ReactNode;
  outro?: React.ReactNode;
}) {
  return (
    <div className="space-y-5">
      <p className="text-callout text-label-2">{intro}</p>
      {sections.map((section, i) => (
        <section key={section.title ?? i}>
          {section.title && <h4 className="mb-3 text-footnote font-semibold uppercase tracking-wide text-label-2">{section.title}</h4>}
          <dl className="divide-y divide-separator">
            {section.items.map((info) => (
              <div key={info.name} className="space-y-2 py-4 first:pt-0">
                <dt className="flex flex-wrap items-center gap-2">
                  <span className="text-callout font-semibold">{info.name}</span>
                  {info.evidence && <Badge tone={EVIDENCE_TONE[info.evidence]}>{EVIDENCE_LABEL[info.evidence]}</Badge>}
                </dt>
                <dd className="space-y-2 text-callout">
                  <p className="text-label-2">{info.read}</p>
                  <p>
                    <span className="font-semibold">{info.evidence ? "Evidence: " : "Why it's used: "}</span>
                    <span className="text-label-2">{info.verdict}</span>
                  </p>
                  <ul className="space-y-1 text-footnote text-label-2">
                    {info.learn && (
                      <li>
                        <SourceLink href={info.learn.url}>How it works: {info.learn.site}</SourceLink>
                      </li>
                    )}
                    {info.sources.map((src) => (
                      <li key={src.cite}>{src.url ? <SourceLink href={src.url}>{src.cite}</SourceLink> : src.cite}</li>
                    ))}
                  </ul>
                </dd>
              </div>
            ))}
          </dl>
        </section>
      ))}
      {outro && <p className="text-footnote text-label-2">{outro}</p>}
    </div>
  );
}
