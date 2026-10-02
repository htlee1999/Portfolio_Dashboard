"use client";

import { KeyRound, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";

import { Button } from "@/components/ui/button";
import { TextField } from "@/components/ui/controls";
import { Banner, LoadingBlock } from "@/components/ui/feedback";
import { api, useApi } from "@/lib/api";
import { AuthShell } from "../auth-shell";

export default function Page() {
  return (
    <Suspense>
      <ResetForm />
    </Suspense>
  );
}

function ResetForm() {
  const router = useRouter();
  const token = useSearchParams().get("token") ?? "";
  // Validate the link up front so an expired one says so before you type anything.
  const { data, error: linkError, isLoading } = useApi<{ username: string }>(token ? `/auth/reset?token=${encodeURIComponent(token)}` : null);
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (password !== confirm) return setError("Passwords do not match.");
    setBusy(true);
    try {
      await api("/auth/reset", { method: "POST", json: { token, new_password: password } });
      setDone(true);
      setTimeout(() => router.replace("/login"), 1800);
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  }

  const backToForgot = (
    <Link href="/forgot" className="inline-flex min-h-11 items-center font-semibold text-tint">
      Request a New Link
    </Link>
  );

  if (!token || linkError) {
    return (
      <AuthShell title="Link not valid" subtitle="Reset links work once and expire after 30 minutes." icon={<KeyRound strokeWidth={2.1} />} footer={backToForgot}>
        <Banner tone="error" title={linkError?.message ?? "This reset link is missing its token."} />
      </AuthShell>
    );
  }

  if (done) {
    return (
      <AuthShell title="Password updated" subtitle="Taking you to sign in…" icon={<ShieldCheck strokeWidth={2.1} />}>
        <p className="text-callout">
          Sign in as <span className="font-semibold">{data?.username}</span> with your new password. Other devices have been signed out.
        </p>
      </AuthShell>
    );
  }

  return (
    <AuthShell
      title="Choose a new password"
      subtitle={data ? <>For <span className="font-semibold text-label">{data.username}</span></> : " "}
      icon={<KeyRound strokeWidth={2.1} />}
      footer={backToForgot}
    >
      {isLoading ? (
        <LoadingBlock label="Checking link…" />
      ) : (
        <form onSubmit={submit} className="space-y-4">
          {error && <Banner tone="error" title={error} />}
          {/* Hidden username helps password managers save the new password to the right account. */}
          <input type="text" name="username" autoComplete="username" value={data?.username ?? ""} readOnly hidden />
          <TextField label="New password" type="password" autoComplete="new-password" required minLength={10} hint="At least 10 characters." value={password} onChange={(e) => setPassword(e.target.value)} />
          <TextField label="Confirm new password" type="password" autoComplete="new-password" required value={confirm} onChange={(e) => setConfirm(e.target.value)} />
          <Button type="submit" size="lg" className="w-full" loading={busy}>
            Update Password
          </Button>
        </form>
      )}
    </AuthShell>
  );
}
