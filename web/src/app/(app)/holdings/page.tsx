"use client";

import { Archive, Download, FileDown, FileUp, Plus, Trash2, Briefcase } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useRef, useState } from "react";
import { mutate as globalMutate } from "swr";

import { PageHeader } from "@/components/shell/page-header";
import { Button, IconButton } from "@/components/ui/button";
import { Badge, Card } from "@/components/ui/card";
import { Select, TextField } from "@/components/ui/controls";
import { Banner, EmptyState, LoadingBlock } from "@/components/ui/feedback";
import { Sheet } from "@/components/ui/overlay";
import { useToast } from "@/components/ui/toast";
import { api, download, useApi } from "@/lib/api";
import { money, number, relative, shortDate } from "@/lib/format";
import { spring } from "@/lib/motion";
import { CURRENCIES } from "@/lib/portfolio";
import type { Holding } from "@/lib/types";

const refreshPortfolio = () => globalMutate((k) => typeof k === "string" && (k.startsWith("/holdings") || k.startsWith("/portfolio/") || k.startsWith("/data/")));

export default function HoldingsPage() {
  const toast = useToast();
  const { data, error, isLoading, mutate } = useApi<{ holdings: Holding[]; last_updated: string | null }>("/holdings");
  const [adding, setAdding] = useState(false);
  const [confirmClear, setConfirmClear] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const holdings = data?.holdings ?? [];
  const symbols = new Set(holdings.map((h) => h.Symbol));
  const currencies = new Set(holdings.map((h) => h.Currency));

  async function remove(h: Holding) {
    const optimistic = { holdings: holdings.filter((x) => x.index !== h.index), last_updated: data?.last_updated ?? null };
    try {
      await mutate(
        api(`/holdings/${h.index}`, { method: "DELETE" }).then(() => api<typeof optimistic>("/holdings")),
        { optimisticData: optimistic, rollbackOnError: true },
      );
      refreshPortfolio();
      toast(`Removed ${h.Symbol} lot`);
    } catch (e) {
      toast((e as Error).message, "error");
    }
  }

  async function importCsv(file: File) {
    setBusy("import");
    const body = new FormData();
    body.append("file", file);
    try {
      const res = await api<{ imported: number }>("/holdings/import", { method: "POST", body });
      refreshPortfolio();
      toast(`Imported ${res.imported} holding${res.imported === 1 ? "" : "s"}`);
    } catch (e) {
      toast((e as Error).message, "error");
    } finally {
      setBusy(null);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  async function run(key: string, fn: () => Promise<unknown>, done?: string) {
    setBusy(key);
    try {
      await fn();
      if (done) toast(done);
    } catch (e) {
      toast((e as Error).message, "error");
    } finally {
      setBusy(null);
    }
  }

  return (
    <>
      <PageHeader
        title="Holdings"
        subtitle={data?.last_updated ? `${holdings.length} lots · updated ${relative(data.last_updated)}` : "Your purchase lots"}
        actions={
          <>
            <input ref={fileRef} type="file" accept=".csv,text/csv" className="hidden" onChange={(e) => e.target.files?.[0] && importCsv(e.target.files[0])} />
            <Button variant="gray" icon={<FileUp className="size-[18px]" />} loading={busy === "import"} onClick={() => fileRef.current?.click()}>
              Import CSV
            </Button>
            <Button icon={<Plus className="size-[18px]" strokeWidth={2.5} />} onClick={() => setAdding(true)}>
              Add Holding
            </Button>
          </>
        }
      />

      {error && <Banner tone="error" title="Couldn't load holdings">{error.message}</Banner>}

      {isLoading && !data ? (
        <LoadingBlock />
      ) : holdings.length === 0 ? (
        <Card>
          <EmptyState
            icon={<Briefcase className="size-7" />}
            title="Start your portfolio"
            action={
              <div className="flex flex-col gap-2 sm:flex-row">
                <Button onClick={() => setAdding(true)}>Add Holding</Button>
                <Button variant="gray" onClick={() => download("/holdings/template")}>
                  Download CSV Template
                </Button>
              </div>
            }
          >
            Add each purchase as a lot. CSV columns: Symbol, Quantity, Purchase_Price, Purchase_Date, Currency.
          </EmptyState>
        </Card>
      ) : (
        <div className="space-y-5">
          <div className="flex flex-wrap gap-2">
            <Badge tone="tint">{symbols.size} symbols</Badge>
            <Badge>{holdings.length} lots</Badge>
            <Badge>{[...currencies].join(" · ")}</Badge>
          </div>

          <Card padded={false} className="overflow-hidden">
            {/* Phones: one stacked row per lot instead of a six-column table. */}
            <ul className="tabular sm:hidden">
              <AnimatePresence initial={false}>
                {holdings.map((h) => (
                  <motion.li
                    key={`${h.index}-${h.Symbol}-${h.Purchase_Date}`}
                    layout
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0, x: -24 }}
                    transition={spring.smooth}
                    className="flex items-center gap-3 border-t-[0.5px] border-separator py-2 pr-2 pl-5 first:border-t-0"
                  >
                    <div className="min-w-0 flex-1">
                      <div className="text-body font-semibold">{h.Symbol}</div>
                      <div className="truncate text-footnote text-label-2">{shortDate(h.Purchase_Date, true)}</div>
                    </div>
                    <div className="shrink-0 text-right">
                      <div className="text-callout">
                        {number(h.Quantity, h.Quantity % 1 ? 2 : 0)} × {money(h.Purchase_Price, h.Currency)}
                      </div>
                      <div className="text-footnote text-label-2">{money(h.Quantity * h.Purchase_Price, h.Currency)}</div>
                    </div>
                    <IconButton label={`Delete ${h.Symbol} lot from ${h.Purchase_Date}`} className="!text-label-2 hover:!text-negative hover:bg-negative-fill" onClick={() => remove(h)}>
                      <Trash2 className="size-[18px]" />
                    </IconButton>
                  </motion.li>
                ))}
              </AnimatePresence>
            </ul>
            <div className="hidden overflow-x-auto sm:block">
              <table className="w-full min-w-[600px] text-callout">
                <thead>
                  <tr className="text-left text-caption text-label-2 [&>th]:px-3 [&>th]:pt-4 [&>th]:pb-2 [&>th]:font-medium [&>th:first-child]:pl-6">
                    <th>Symbol</th>
                    <th className="text-right">Shares</th>
                    <th className="text-right">Cost / share</th>
                    <th className="text-right">Cost basis</th>
                    <th>Purchased</th>
                    <th className="w-14" aria-label="Actions" />
                  </tr>
                </thead>
                <tbody className="tabular">
                  <AnimatePresence initial={false}>
                    {holdings.map((h) => (
                      <motion.tr
                        key={`${h.index}-${h.Symbol}-${h.Purchase_Date}`}
                        layout
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0, x: -24 }}
                        transition={spring.smooth}
                        className="border-t-[0.5px] border-separator [&>td]:px-3 [&>td]:py-2 [&>td:first-child]:pl-6"
                      >
                        <td className="font-semibold">{h.Symbol}</td>
                        <td className="text-right">{number(h.Quantity, h.Quantity % 1 ? 2 : 0)}</td>
                        <td className="text-right">{money(h.Purchase_Price, h.Currency)}</td>
                        <td className="text-right text-label-2">{money(h.Quantity * h.Purchase_Price, h.Currency)}</td>
                        <td className="text-label-2">{shortDate(h.Purchase_Date, true)}</td>
                        <td>
                          <IconButton label={`Delete ${h.Symbol} lot from ${h.Purchase_Date}`} className="!text-label-2 hover:!text-negative hover:bg-negative-fill" onClick={() => remove(h)}>
                            <Trash2 className="size-[18px]" />
                          </IconButton>
                        </td>
                      </motion.tr>
                    ))}
                  </AnimatePresence>
                </tbody>
              </table>
            </div>
          </Card>

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <ActionTile icon={<Download />} label="Export CSV" loading={busy === "export"} onClick={() => run("export", () => download("/holdings/export"))} />
            <ActionTile icon={<FileDown />} label="CSV Template" onClick={() => download("/holdings/template")} />
            <ActionTile
              icon={<Archive />}
              label="Create Backup"
              loading={busy === "backup"}
              onClick={() => run("backup", () => api<{ file: string }>("/holdings/backup", { method: "POST" }), "Backup saved to data/backups")}
            />
            <ActionTile icon={<Trash2 />} label="Delete All" destructive onClick={() => setConfirmClear(true)} />
          </div>
        </div>
      )}

      <AddHoldingSheet open={adding} onClose={() => setAdding(false)} />

      <Sheet
        open={confirmClear}
        onClose={() => setConfirmClear(false)}
        title="Delete all holdings?"
        footer={
          <>
            <Button variant="gray" onClick={() => setConfirmClear(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              loading={busy === "clear"}
              onClick={() =>
                run("clear", async () => {
                  await api("/holdings", { method: "DELETE" });
                  refreshPortfolio();
                  setConfirmClear(false);
                }, "All holdings deleted")
              }
            >
              Delete All
            </Button>
          </>
        }
      >
        <p className="text-body text-label-2">
          This removes all {holdings.length} lots from your portfolio. Consider exporting a CSV or creating a backup first.
        </p>
      </Sheet>
    </>
  );
}

function ActionTile({ icon, label, onClick, loading, destructive }: { icon: React.ReactNode; label: string; onClick: () => void; loading?: boolean; destructive?: boolean }) {
  return (
    <motion.button
      whileTap={{ scale: 0.97 }}
      transition={spring.snappy}
      onClick={onClick}
      disabled={loading}
      className={`squircle flex min-h-14 cursor-pointer items-center gap-3 rounded-[16px] bg-elevated px-4 text-left text-callout font-medium shadow-[var(--shadow-card)] transition-colors hover:bg-fill-2 disabled:opacity-50 [&_svg]:size-5 ${destructive ? "text-negative" : ""}`}
    >
      <span className={destructive ? "text-negative" : "text-tint"}>{icon}</span>
      {loading ? "Working…" : label}
    </motion.button>
  );
}

function AddHoldingSheet({ open, onClose }: { open: boolean; onClose: () => void }) {
  const toast = useToast();
  const today = new Date().toISOString().slice(0, 10);
  const [form, setForm] = useState({ symbol: "", quantity: "", price: "", date: today, currency: "USD" });
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => setForm({ ...form, [k]: e.target.value });

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSaving(true);
    try {
      await api("/holdings", {
        method: "POST",
        json: {
          symbol: form.symbol.trim(),
          quantity: Number(form.quantity),
          purchase_price: Number(form.price),
          purchase_date: form.date,
          currency: form.currency,
        },
      });
      refreshPortfolio();
      toast(`Added ${form.symbol.trim().toUpperCase()}`);
      setForm({ symbol: "", quantity: "", price: "", date: today, currency: form.currency });
      onClose();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <Sheet open={open} onClose={onClose} title="Add Holding">
      <form id="add-holding" onSubmit={submit} className="space-y-4">
        {error && <Banner tone="error" title={error} />}
        <TextField label="Symbol" placeholder="AAPL" required autoCapitalize="characters" autoCorrect="off" spellCheck={false} value={form.symbol} onChange={set("symbol")} hint="Company names like TSMC or Alibaba are mapped to their US tickers." />
        <div className="grid grid-cols-2 gap-3">
          <TextField label="Shares" type="number" inputMode="decimal" min="0.0001" step="any" required value={form.quantity} onChange={set("quantity")} />
          <TextField label="Price per share" type="number" inputMode="decimal" min="0.0001" step="any" required value={form.price} onChange={set("price")} />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <TextField label="Purchase date" type="date" required max={today} value={form.date} onChange={set("date")} />
          <Select label="Currency" options={CURRENCIES} value={form.currency} onChange={set("currency")} />
        </div>
        <Button type="submit" size="lg" className="w-full" loading={saving}>
          Add to Portfolio
        </Button>
      </form>
    </Sheet>
  );
}
