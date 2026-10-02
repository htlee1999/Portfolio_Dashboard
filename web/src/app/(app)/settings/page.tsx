"use client";

import { Activity, FileJson, Gauge, History, KeyRound, LogOut, Mail, Moon, Sun, SunMoon, UserPlus } from "lucide-react";
import { useState } from "react";
import { mutate as globalMutate } from "swr";

import { PageHeader } from "@/components/shell/page-header";
import { Button } from "@/components/ui/button";
import { Badge, Card, List, ListRow, Section } from "@/components/ui/card";
import { Segmented, Select, TextField } from "@/components/ui/controls";
import { Banner } from "@/components/ui/feedback";
import { Disclosure, Sheet } from "@/components/ui/overlay";
import { useToast } from "@/components/ui/toast";
import { api, useApi } from "@/lib/api";
import { bytes, dateTime, relative } from "@/lib/format";
import { CURRENCIES } from "@/lib/portfolio";
import { useSession } from "@/lib/session";
import { useTheme, type ThemePref } from "@/lib/theme";

type DataStats = {
  username: string;
  holdings: number;
  symbols: string[];
  currencies: string[];
  last_updated: string | null;
  portfolio_file: string;
  files: { path: string; size: number; modified: string; mine: boolean }[];
};

export default function SettingsPage() {
  const { user, baseCurrency, setBaseCurrency, logout } = useSession();
  const { pref, setPref } = useTheme();
  const [pwOpen, setPwOpen] = useState(false);
  const [emailOpen, setEmailOpen] = useState(false);

  return (
    <>
      <PageHeader title="Settings" />
      <div className="max-w-3xl space-y-8">
        {/* Destinations that live in the sidebar on larger screens */}
        <Section className="lg:hidden">
          <List>
            <ListRow href="/performance" title="Performance" leading={<IconTile icon={<Activity />} color="#007aff" />} />
            <ListRow href="/track-record" title="Track Record" leading={<IconTile icon={<History />} color="#5856d6" />} />
            <ListRow href="/usage" title="API Usage" leading={<IconTile icon={<Gauge />} color="#ff9500" />} />
          </List>
        </Section>

        <Section title="Account">
          <List>
            <ListRow
              title={user?.username}
              subtitle={`Signed in · ${user?.role}`}
              leading={
                <span className="flex size-10 items-center justify-center rounded-full bg-gradient-to-b from-[#a1a1a6] to-[#8e8e93] text-headline text-white uppercase">
                  {user?.username.slice(0, 1)}
                </span>
              }
            />
            <ListRow
              title="Email"
              leading={<IconTile icon={<Mail />} color="#007aff" />}
              trailing={<span className={`text-callout ${user?.email ? "text-label-2" : "text-label-3"}`}>{user?.email ?? "Not set"}</span>}
              onClick={() => setEmailOpen(true)}
              chevron
            />
            <ListRow title="Change Password" leading={<IconTile icon={<KeyRound />} color="#8e8e93" />} onClick={() => setPwOpen(true)} chevron />
            <ListRow title={<span className="text-negative">Sign Out</span>} leading={<IconTile icon={<LogOut />} color="#ff3b30" />} onClick={logout} />
          </List>
        </Section>

        <Section title="Appearance">
          <Card>
            <Segmented<ThemePref>
              label="Appearance"
              className="w-full"
              value={pref}
              onChange={setPref}
              options={[
                { value: "system", label: <span className="flex items-center gap-1.5"><SunMoon className="size-4" />Automatic</span> },
                { value: "light", label: <span className="flex items-center gap-1.5"><Sun className="size-4" />Light</span> },
                { value: "dark", label: <span className="flex items-center gap-1.5"><Moon className="size-4" />Dark</span> },
              ]}
            />
          </Card>
        </Section>

        <Section title="Portfolio" description="Totals and charts are reported in this currency. Shared by all users.">
          <Card>
            <Select label="Base currency" options={CURRENCIES} value={baseCurrency} onChange={(e) => setBaseCurrency(e.target.value)} />
          </Card>
        </Section>

        <DataSection />

        {user?.role === "admin" && <UsersSection />}
      </div>

      <PasswordSheet open={pwOpen} onClose={() => setPwOpen(false)} />
      <EmailSheet key={user?.email ?? ""} open={emailOpen} current={user?.email ?? null} onClose={() => setEmailOpen(false)} />
    </>
  );
}

function IconTile({ icon, color }: { icon: React.ReactNode; color: string }) {
  return (
    <span className="squircle flex size-[30px] shrink-0 items-center justify-center rounded-[7px] text-white [&_svg]:size-[18px]" style={{ background: color }}>
      {icon}
    </span>
  );
}

function EmailSheet({ open, current, onClose }: { open: boolean; current: string | null; onClose: () => void }) {
  const toast = useToast();
  const [email, setEmail] = useState(current ?? "");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<"save" | "remove" | null>(null);

  async function save(next: string | null) {
    setError(null);
    setBusy(next ? "save" : "remove");
    try {
      await api("/auth/email", { method: "PUT", json: { email: next, current_password: password } });
      await globalMutate("/auth/me");
      toast(next ? "Email linked" : "Email removed");
      setPassword("");
      onClose();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(null);
    }
  }

  return (
    <Sheet open={open} onClose={onClose} title={current ? "Change Email" : "Link Email"}>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          save(email.trim());
        }}
        className="space-y-4"
      >
        <p className="text-callout text-label-2">Used to send you a reset link if you forget your password.</p>
        {error && <Banner tone="error" title={error} />}
        <TextField label="Email" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        <TextField label="Current password" type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} hint="Confirms it’s you." />
        <Button type="submit" size="lg" className="w-full" loading={busy === "save"}>
          Save Email
        </Button>
        {current && (
          <Button type="button" variant="plain" className="w-full !text-negative" disabled={!password} loading={busy === "remove"} onClick={() => save(null)}>
            Remove Email
          </Button>
        )}
      </form>
    </Sheet>
  );
}

function PasswordSheet({ open, onClose }: { open: boolean; onClose: () => void }) {
  const toast = useToast();
  const [form, setForm] = useState({ current: "", next: "", confirm: "" });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (form.next !== form.confirm) return setError("New passwords do not match.");
    setBusy(true);
    try {
      await api("/auth/password", { method: "POST", json: { current_password: form.current, new_password: form.next } });
      toast("Password changed");
      setForm({ current: "", next: "", confirm: "" });
      onClose();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Sheet open={open} onClose={onClose} title="Change Password">
      <form onSubmit={submit} className="space-y-4">
        {error && <Banner tone="error" title={error} />}
        <TextField label="Current password" type="password" autoComplete="current-password" required value={form.current} onChange={(e) => setForm({ ...form, current: e.target.value })} />
        <TextField label="New password" type="password" autoComplete="new-password" required minLength={10} hint="At least 10 characters." value={form.next} onChange={(e) => setForm({ ...form, next: e.target.value })} />
        <TextField label="Confirm new password" type="password" autoComplete="new-password" required value={form.confirm} onChange={(e) => setForm({ ...form, confirm: e.target.value })} />
        <Button type="submit" size="lg" className="w-full" loading={busy}>
          Change Password
        </Button>
      </form>
    </Sheet>
  );
}

function DataSection() {
  const { data } = useApi<DataStats>("/data/stats");
  const { data: raw } = useApi<unknown>("/data/raw");

  return (
    <Section title="Data" description={data ? `Stored locally in data/${data.portfolio_file} · updated ${relative(data.last_updated)}` : undefined}>
      <Card>
        {data && (
          <div className="mb-2 flex flex-wrap gap-2">
            <Badge tone="tint">{data.holdings} lots</Badge>
            <Badge>{data.symbols.length} symbols</Badge>
            <Badge>{data.currencies.join(" · ") || "No currencies"}</Badge>
          </div>
        )}
        <Disclosure title="Files" subtitle={data ? `${data.files.length} files in data/` : undefined}>
          <ul className="space-y-1 text-footnote">
            {data?.files.map((f) => (
              <li key={f.path} className="flex items-center justify-between gap-3">
                <span className={`truncate font-mono ${f.mine ? "font-semibold" : "text-label-2"}`}>{f.path}</span>
                <span className="shrink-0 text-label-2 tabular">
                  {bytes(f.size)} · {dateTime(f.modified)}
                </span>
              </li>
            ))}
          </ul>
        </Disclosure>
        <Disclosure title="Edit portfolio JSON" subtitle="Advanced: edit holdings directly" leading={<FileJson className="size-5 text-tint" />}>
          {raw ? <JsonEditor key={JSON.stringify(raw)} initial={raw} /> : null}
        </Disclosure>
      </Card>
    </Section>
  );
}

function JsonEditor({ initial }: { initial: unknown }) {
  const toast = useToast();
  const original = JSON.stringify(initial, null, 2);
  const [text, setText] = useState(original);
  const [jsonError, setJsonError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function save() {
    setJsonError(null);
    let parsed: unknown;
    try {
      parsed = JSON.parse(text);
    } catch (e) {
      return setJsonError(`Invalid JSON: ${(e as Error).message}`);
    }
    setSaving(true);
    try {
      await api("/data/raw", { method: "PUT", json: parsed });
      globalMutate((k) => typeof k === "string" && (k.startsWith("/holdings") || k.startsWith("/portfolio/") || k.startsWith("/data/")));
      toast("Portfolio JSON saved");
    } catch (e) {
      setJsonError((e as Error).message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      {jsonError && <div className="mb-3"><Banner tone="error" title={jsonError} /></div>}
      <label className="sr-only" htmlFor="json-editor">Portfolio JSON</label>
      <textarea
        id="json-editor"
        value={text}
        onChange={(e) => setText(e.target.value)}
        spellCheck={false}
        className="squircle h-80 w-full resize-y rounded-[12px] bg-fill-2 p-3 font-mono text-caption outline-none focus:shadow-[0_0_0_3.5px_color-mix(in_srgb,var(--tint)_35%,transparent)]"
      />
      <div className="mt-3 flex justify-end gap-2">
        <Button variant="gray" onClick={() => setText(original)}>
          Revert
        </Button>
        <Button loading={saving} onClick={save}>
          Save JSON
        </Button>
      </div>
    </>
  );
}

function UsersSection() {
  const toast = useToast();
  const { data, mutate } = useApi<{ username: string; role: string; email: string | null; created_at: string | null; last_login: string | null }[]>("/users");
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ username: "", password: "", role: "user", email: "" });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api("/users", { method: "POST", json: { ...form, email: form.email.trim() || null } });
      toast(`Created ${form.username}`);
      setForm({ username: "", password: "", role: "user", email: "" });
      setOpen(false);
      mutate();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Section
      title="Users"
      description="Admin only"
      action={
        <Button variant="plain" size="sm" icon={<UserPlus className="size-4" />} onClick={() => setOpen(true)}>
          Add User
        </Button>
      }
    >
      <List>
        {data?.map((u) => (
          <ListRow
            key={u.username}
            title={u.username}
            subtitle={`${u.email ?? "No email"} · last sign-in ${u.last_login ? relative(u.last_login) : "never"}`}
            trailing={<Badge tone={u.role === "admin" ? "tint" : "neutral"} className="capitalize">{u.role}</Badge>}
          />
        ))}
      </List>
      <Sheet open={open} onClose={() => setOpen(false)} title="Add User">
        <form onSubmit={create} className="space-y-4">
          {error && <Banner tone="error" title={error} />}
          <TextField label="Username" required autoCapitalize="none" value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} />
          <TextField label="Password" type="password" required minLength={10} autoComplete="new-password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
          <TextField label="Email (optional)" type="email" autoComplete="off" hint="Lets them reset a forgotten password." value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
          <Select label="Role" options={[{ value: "user", label: "User" }, { value: "admin", label: "Admin" }]} value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })} />
          <Button type="submit" size="lg" className="w-full" loading={busy}>
            Create User
          </Button>
        </form>
      </Sheet>
    </Section>
  );
}
