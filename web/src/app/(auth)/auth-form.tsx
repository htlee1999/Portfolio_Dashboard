"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { TextField } from "@/components/ui/controls";
import { Banner } from "@/components/ui/feedback";
import { api } from "@/lib/api";
import { AuthShell } from "./auth-shell";

export function AuthForm({ mode }: { mode: "login" | "signup" }) {
  const router = useRouter();
  const params = useSearchParams();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const signup = mode === "signup";

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (signup && password !== confirm) return setError("Passwords do not match.");
    setBusy(true);
    try {
      await api(`/auth/${mode}`, { method: "POST", json: { username, password } });
      const next = params.get("next");
      router.replace(next && next.startsWith("/") && !next.startsWith("//") ? next : "/");
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  }

  return (
    <AuthShell
      title={signup ? "Create your account" : "Welcome back"}
      subtitle={signup ? "Track holdings and research stocks in one place." : "Sign in to your portfolio."}
      footer={
        <>
          {signup ? "Already have an account? " : "New here? "}
          <Link href={signup ? "/login" : "/signup"} className="inline-flex min-h-11 items-center font-semibold text-tint">
            {signup ? "Sign in" : "Create an account"}
          </Link>
        </>
      }
    >
      <form onSubmit={submit} className="space-y-4">
        {error && <Banner tone="error" title={error} />}
        <TextField
          label="Username"
          autoComplete="username"
          autoCapitalize="none"
          autoCorrect="off"
          required
          value={username}
          onChange={(e) => setUsername(e.target.value)}
        />
        <div>
          <TextField
            label="Password"
            type="password"
            autoComplete={signup ? "new-password" : "current-password"}
            required
            minLength={signup ? 10 : undefined}
            hint={signup ? "At least 10 characters." : undefined}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          {!signup && (
            <div className="flex justify-end">
              <Link
                href={username ? `/forgot?u=${encodeURIComponent(username)}` : "/forgot"}
                className="inline-flex min-h-11 items-center px-1 text-footnote font-semibold text-tint"
              >
                Forgot password?
              </Link>
            </div>
          )}
        </div>
        {signup && (
          <TextField
            label="Confirm password"
            type="password"
            autoComplete="new-password"
            required
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
          />
        )}
        <Button type="submit" size="lg" className="w-full" loading={busy}>
          {signup ? "Create Account" : "Sign In"}
        </Button>
      </form>
    </AuthShell>
  );
}
