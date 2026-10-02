"use client";

import { KeyRound, MailCheck, Terminal } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";

import { Button } from "@/components/ui/button";
import { TextField } from "@/components/ui/controls";
import { Banner } from "@/components/ui/feedback";
import { api } from "@/lib/api";
import { spring } from "@/lib/motion";
import { AuthShell } from "../auth-shell";

export default function Page() {
  return (
    <Suspense>
      <ForgotForm />
    </Suspense>
  );
}

function ForgotForm() {
  const params = useSearchParams();
  const [identifier, setIdentifier] = useState(params.get("u") ?? "");
  const [sent, setSent] = useState<{ emailEnabled: boolean } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const res = await api<{ email_enabled: boolean }>("/auth/forgot", { method: "POST", json: { identifier } });
      setSent({ emailEnabled: res.email_enabled });
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthShell
      title={sent ? "Check for your link" : "Forgot password?"}
      subtitle={sent ? "The link works once and expires in 30 minutes." : "Enter your username or the email linked to your account."}
      icon={sent ? <MailCheck strokeWidth={2.1} /> : <KeyRound strokeWidth={2.1} />}
      footer={
        <Link href="/login" className="inline-flex min-h-11 items-center font-semibold text-tint">
          Back to Sign In
        </Link>
      }
    >
      <AnimatePresence mode="wait" initial={false}>
        {sent ? (
          <motion.div key="sent" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={spring.smooth} className="space-y-4 text-callout">
            {sent.emailEnabled ? (
              <p>
                If an account matches <span className="font-semibold">{identifier}</span> and has a linked email, a reset link is on its way. Check your inbox and spam folder.
              </p>
            ) : (
              <div className="flex gap-3">
                <Terminal className="mt-0.5 size-5 shrink-0 text-tint" aria-hidden />
                <p>
                  Email isn’t set up on this server, so the reset link was printed in the <span className="font-semibold">API server’s terminal</span>, where you ran <code className="rounded bg-fill px-1 font-mono text-footnote">./dev.sh</code>. Open it from there.
                </p>
              </div>
            )}
            <Button variant="gray" className="w-full" onClick={() => setSent(null)}>
              Try Again
            </Button>
          </motion.div>
        ) : (
          <motion.form key="form" onSubmit={submit} exit={{ opacity: 0, y: -8 }} transition={spring.snappy} className="space-y-4">
            {error && <Banner tone="error" title={error} />}
            <TextField
              label="Username or email"
              autoComplete="username"
              autoCapitalize="none"
              autoCorrect="off"
              required
              value={identifier}
              onChange={(e) => setIdentifier(e.target.value)}
            />
            <Button type="submit" size="lg" className="w-full" loading={busy}>
              Send Reset Link
            </Button>
          </motion.form>
        )}
      </AnimatePresence>
    </AuthShell>
  );
}
