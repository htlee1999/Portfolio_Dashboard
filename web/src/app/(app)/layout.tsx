"use client";

import { AppShell } from "@/components/shell/app-shell";
import { LoadingBlock } from "@/components/ui/feedback";
import { SessionProvider, useSession } from "@/lib/session";

function Gate({ children }: { children: React.ReactNode }) {
  const { user, loading } = useSession();
  if (!user) return loading ? <LoadingBlock /> : null;
  return <AppShell>{children}</AppShell>;
}

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <SessionProvider>
      <Gate>{children}</Gate>
    </SessionProvider>
  );
}
