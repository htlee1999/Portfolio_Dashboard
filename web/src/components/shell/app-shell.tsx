"use client";

import { LogOut, TrendingUp } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { createContext, useContext, useEffect, useState } from "react";

import { useSession } from "@/lib/session";
import { spring } from "@/lib/motion";
import { cn } from "../ui/cn";
import { NAV, RESEARCH, SETTINGS, TABS, isActive, type NavItem } from "./nav";

/* Compact title shown in the toolbar once the page's large title scrolls away. */
const TitleContext = createContext<{ title: string; compact: boolean; set: (title: string, compact: boolean) => void }>({
  title: "",
  compact: false,
  set: () => {},
});
export const usePageTitle = () => useContext(TitleContext);

function SidebarLink({ item, active }: { item: NavItem; active: boolean }) {
  const Icon = item.icon;
  return (
    <Link
      href={item.href}
      aria-current={active ? "page" : undefined}
      className={cn(
        "relative flex h-9 items-center gap-2.5 rounded-[9px] px-2.5 text-callout transition-colors",
        active ? "font-semibold text-label" : "text-label hover:bg-fill-2",
      )}
    >
      {active && (
        <motion.span layoutId="sidebar-active" transition={spring.snappy} className="squircle absolute inset-0 rounded-[9px] bg-fill" />
      )}
      <Icon className={cn("relative size-[18px]", active ? "text-tint" : "text-tint/90")} strokeWidth={1.9} aria-hidden />
      <span className="relative">{item.label}</span>
    </Link>
  );
}

function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useSession();
  return (
    <aside className="material-chrome fixed inset-y-0 left-0 z-30 hidden w-[248px] flex-col shadow-[inset_-0.5px_0_0_var(--separator)] lg:flex">
      <div className="flex h-16 items-center gap-2.5 px-5">
        <span className="squircle flex size-8 items-center justify-center rounded-[9px] bg-gradient-to-b from-[#3d9bff] to-[#0068e6] text-white shadow-sm">
          <TrendingUp className="size-[18px]" strokeWidth={2.4} />
        </span>
        <span className="text-headline">Portfolio</span>
      </div>
      <nav aria-label="Primary" className="flex-1 space-y-5 overflow-y-auto px-3 pb-4">
        {NAV.map((group, i) => (
          <div key={i}>
            {group.heading && <div className="mb-1 px-2.5 text-caption font-semibold text-label-2">{group.heading}</div>}
            <div className="space-y-0.5">
              {group.items.map((item) => (
                <SidebarLink key={item.href} item={item} active={isActive(pathname, item.href)} />
              ))}
            </div>
          </div>
        ))}
      </nav>
      <div className="hairline-t space-y-0.5 px-3 py-3">
        <SidebarLink item={SETTINGS} active={isActive(pathname, SETTINGS.href)} />
        <div className="flex items-center gap-2.5 px-2.5 pt-2">
          <span className="flex size-8 items-center justify-center rounded-full bg-fill text-footnote font-semibold uppercase text-label-2">
            {user?.username.slice(0, 1)}
          </span>
          <div className="min-w-0 flex-1">
            <div className="truncate text-footnote font-semibold">{user?.username}</div>
            <div className="text-caption text-label-2 capitalize">{user?.role}</div>
          </div>
          <button
            onClick={logout}
            aria-label="Sign out"
            title="Sign out"
            className="flex size-11 cursor-pointer items-center justify-center rounded-full text-label-2 hover:bg-fill-2 hover:text-label"
          >
            <LogOut className="size-[18px]" />
          </button>
        </div>
      </div>
    </aside>
  );
}

function TabBar() {
  const pathname = usePathname();
  const researchActive = RESEARCH.some((r) => r.href !== "/assessment" && isActive(pathname, r.href));
  return (
    <nav
      aria-label="Primary"
      className="material-chrome hairline-t fixed inset-x-0 bottom-0 z-30 flex pb-[env(safe-area-inset-bottom)] lg:hidden"
    >
      {TABS.map((tab) => {
        const active =
          tab.label === "Research"
            ? researchActive
            : tab.label === "More"
              ? ["/settings", "/performance", "/track-record", "/usage"].some((h) => isActive(pathname, h))
              : isActive(pathname, tab.href);
        const Icon = tab.icon;
        return (
          <Link
            key={tab.href}
            href={tab.href}
            aria-current={active ? "page" : undefined}
            className={cn("flex h-[52px] flex-1 flex-col items-center justify-center gap-0.5 text-[10px] font-medium", active ? "text-tint" : "text-label-2")}
          >
            <motion.span animate={{ scale: active ? 1.06 : 1 }} transition={spring.bouncy}>
              <Icon className="size-6" strokeWidth={active ? 2.2 : 1.8} aria-hidden />
            </motion.span>
            {tab.label}
          </Link>
        );
      })}
    </nav>
  );
}

function Toolbar() {
  const { title, compact } = usePageTitle();
  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 4);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);
  return (
    <div
      className={cn(
        "sticky top-0 z-20 flex h-12 items-center justify-center transition-[background-color,box-shadow,backdrop-filter] duration-200",
        scrolled ? "material-chrome hairline-b" : "bg-transparent",
      )}
    >
      <AnimatePresence>
        {compact && (
          <motion.span
            key={title}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 6 }}
            transition={spring.snappy}
            className="text-headline"
          >
            {title}
          </motion.span>
        )}
      </AnimatePresence>
    </div>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const [title, setTitle] = useState({ title: "", compact: false });
  const pathname = usePathname();
  return (
    <TitleContext.Provider value={{ ...title, set: (t, c) => setTitle({ title: t, compact: c }) }}>
      <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50 focus:rounded-lg focus:bg-elevated focus:px-3 focus:py-2">
        Skip to content
      </a>
      <Sidebar />
      <div className="lg:pl-[248px]">
        <Toolbar />
        <main id="main" className="mx-auto w-full max-w-[1200px] px-4 pb-[calc(88px+env(safe-area-inset-bottom))] sm:px-6 lg:px-10 lg:pb-16">
          <motion.div key={pathname} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={spring.smooth}>
            {children}
          </motion.div>
        </main>
      </div>
      <TabBar />
    </TitleContext.Provider>
  );
}
