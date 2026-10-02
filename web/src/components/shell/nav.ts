import {
  Activity,
  BarChart3,
  BrainCircuit,
  Briefcase,
  CandlestickChart,
  Gauge,
  History,
  LayoutGrid,
  Newspaper,
  ScrollText,
  Settings,
  Sparkles,
  type LucideIcon,
} from "lucide-react";

export type NavItem = { href: string; label: string; icon: LucideIcon; research?: boolean };

export const NAV: { heading?: string; items: NavItem[] }[] = [
  {
    items: [
      { href: "/", label: "Overview", icon: LayoutGrid },
      { href: "/holdings", label: "Holdings", icon: Briefcase },
      { href: "/performance", label: "Performance", icon: Activity },
    ],
  },
  {
    heading: "Research",
    items: [
      { href: "/technical", label: "Technicals", icon: CandlestickChart, research: true },
      { href: "/fundamentals", label: "Fundamentals", icon: ScrollText, research: true },
      { href: "/forecast", label: "Forecast", icon: BrainCircuit, research: true },
      { href: "/sentiment", label: "Sentiment", icon: Newspaper, research: true },
      { href: "/assessment", label: "AI Assessment", icon: Sparkles, research: true },
    ],
  },
  {
    heading: "Insights",
    items: [
      { href: "/track-record", label: "Track Record", icon: History },
      { href: "/usage", label: "API Usage", icon: Gauge },
    ],
  },
];

export const SETTINGS: NavItem = { href: "/settings", label: "Settings", icon: Settings };

/** Phone tab bar: the five most-used destinations. */
export const TABS: NavItem[] = [
  { href: "/", label: "Overview", icon: LayoutGrid },
  { href: "/holdings", label: "Holdings", icon: Briefcase },
  { href: "/technical", label: "Research", icon: BarChart3 },
  { href: "/assessment", label: "AI", icon: Sparkles },
  { href: "/settings", label: "More", icon: Settings },
];

export const RESEARCH = NAV[1].items;

export function isActive(pathname: string, href: string) {
  return href === "/" ? pathname === "/" : pathname === href || pathname.startsWith(`${href}/`);
}
