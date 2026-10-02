"use client";

import { Briefcase, RefreshCw } from "lucide-react";
import { motion } from "motion/react";
import Link from "next/link";
import { useMemo } from "react";

import { Donut, MUTED, SERIES, SignedBars } from "@/components/charts/charts";
import { CurrencyMenu } from "@/components/shell/currency-menu";
import { PageHeader } from "@/components/shell/page-header";
import { Button, IconButton } from "@/components/ui/button";
import { Card, CardHeader } from "@/components/ui/card";
import { Banner, EmptyState, Skeleton } from "@/components/ui/feedback";
import { AnimatedNumber, Delta } from "@/components/ui/stat";
import { useApi } from "@/lib/api";
import { money, number, pct, relative } from "@/lib/format";
import { spring, stagger, staggerItem } from "@/lib/motion";
import { toPositions } from "@/lib/portfolio";
import { useSession } from "@/lib/session";
import type { Metrics } from "@/lib/types";

export default function OverviewPage() {
  const { baseCurrency } = useSession();
  const { data, error, isLoading, isValidating, mutate } = useApi<Metrics>(`/portfolio/metrics?base=${baseCurrency}`);
  const { data: holdingsMeta } = useApi<{ last_updated: string | null }>("/holdings");

  const positions = useMemo(() => (data ? toPositions(data.rows) : []), [data]);
  const allocation = useMemo(() => {
    const top = positions.slice(0, 7).map((p, i) => ({ label: p.symbol, value: p.valueBase, color: SERIES[i] }));
    const rest = positions.slice(7).reduce((s, p) => s + p.valueBase, 0);
    return rest > 0 ? [...top, { label: `Other (${positions.length - 7})`, value: rest, color: MUTED }] : top;
  }, [positions]);

  const fmt = (v: number) => money(v, baseCurrency);

  return (
    <>
      <PageHeader
        title="Overview"
        subtitle={holdingsMeta?.last_updated ? `Holdings updated ${relative(holdingsMeta.last_updated)}` : undefined}
        actions={
          <>
            <IconButton label="Refresh prices" onClick={() => mutate()} disabled={isValidating}>
              <motion.span animate={{ rotate: isValidating ? 360 : 0 }} transition={isValidating ? { repeat: Infinity, duration: 0.9, ease: "linear" } : spring.snappy}>
                <RefreshCw className="size-5" />
              </motion.span>
            </IconButton>
            <CurrencyMenu />
          </>
        }
      />

      {error && <Banner tone="error" title="Couldn't load your portfolio">{error.message}</Banner>}

      {isLoading && !data ? (
        <OverviewSkeleton />
      ) : data && data.holdings_count === 0 ? (
        <Card>
          <EmptyState
            icon={<Briefcase className="size-7" />}
            title="No holdings yet"
            action={
              <Link href="/holdings">
                <Button>Add Your First Holding</Button>
              </Link>
            }
          >
            Add positions manually or import a CSV to see your portfolio come to life.
          </EmptyState>
        </Card>
      ) : data ? (
        <motion.div variants={stagger()} initial="initial" animate="animate" className="space-y-5">
          {data.unpriced.length > 0 && (
            <Banner tone="warning" title={`Prices unavailable for ${data.unpriced.join(", ")}`}>
              These holdings are excluded from the totals. Yahoo Finance may be rate-limiting; try refreshing shortly.
            </Banner>
          )}

          {/* Hero */}
          <motion.div variants={staggerItem}>
            <Card className="relative overflow-hidden">
              <div className="text-footnote font-medium text-label-2">Portfolio value</div>
              <div className="text-hero tabular mt-1">
                <AnimatedNumber value={data.total_value} format={fmt} />
              </div>
              <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-callout">
                <Delta value={data.total_gain}>
                  {money(data.total_gain, baseCurrency, { sign: true })} ({pct(data.total_gain_pct)})
                </Delta>
                <span className="text-label-2">all time</span>
              </div>
              <div className="mt-6 grid grid-cols-2 gap-4 border-t-[0.5px] border-separator pt-5 sm:grid-cols-4">
                <MiniStat label="Invested" value={fmt(data.total_invested)} />
                <MiniStat label="Positions" value={String(positions.length)} />
                <MiniStat label="Best" value={positions.length ? best(positions).symbol : "—"} detail={positions.length ? pct(best(positions).gainPct, 1) : undefined} />
                <MiniStat label="Largest" value={positions[0]?.symbol ?? "—"} detail={positions[0] ? `${number(positions[0].weight, 1)}% of portfolio` : undefined} />
              </div>
            </Card>
          </motion.div>

          <div className="grid gap-5 lg:grid-cols-5">
            <motion.div variants={staggerItem} className="lg:col-span-2">
              <Card className="h-full">
                <CardHeader title="Allocation" subtitle={`By current value in ${baseCurrency}`} />
                <Donut
                  data={allocation}
                  format={fmt}
                  ariaLabel="Portfolio allocation by holding"
                  size={180}
                  center={
                    <>
                      <span className="text-caption text-label-2">Holdings</span>
                      <span className="text-title-2">{positions.length}</span>
                    </>
                  }
                />
              </Card>
            </motion.div>
            <motion.div variants={staggerItem} className="lg:col-span-3">
              <Card className="h-full">
                <CardHeader title="Gain by position" subtitle={`Unrealized, in ${baseCurrency}`} />
                <SignedBars
                  data={positions.map((p) => ({ symbol: p.symbol, gain: p.gainBase }))}
                  xKey="symbol"
                  yKey="gain"
                  name="Gain"
                  height={260}
                  format={(v) => money(v, baseCurrency, { compact: true })}
                  ariaLabel="Unrealized gain or loss by position"
                />
              </Card>
            </motion.div>
          </div>

          <motion.div variants={staggerItem}>
            <Card padded={false}>
              <div className="px-5 pt-5 sm:px-6 sm:pt-6">
                <CardHeader
                  title="Positions"
                  subtitle="Lots of the same symbol are combined"
                  action={
                    <Link href="/holdings" className="flex min-h-11 items-center text-callout font-semibold text-tint">
                      Edit
                    </Link>
                  }
                />
              </div>
              <PositionsTable positions={positions} base={baseCurrency} />
            </Card>
          </motion.div>

          <p className="px-1 pt-2 text-center text-caption text-label-2">
            Market data from Finnhub and Yahoo Finance may be delayed. For information only.
          </p>
        </motion.div>
      ) : null}
    </>
  );
}

function best<T extends { gainPct: number }>(ps: T[]) {
  return ps.reduce((a, b) => (b.gainPct > a.gainPct ? b : a));
}

function MiniStat({ label, value, detail }: { label: string; value: string; detail?: string }) {
  return (
    <div className="min-w-0">
      <div className="text-caption text-label-2">{label}</div>
      <div className="truncate text-headline tabular">{value}</div>
      {detail && <div className="truncate text-caption text-label-2">{detail}</div>}
    </div>
  );
}

function PositionsTable({ positions, base }: { positions: ReturnType<typeof toPositions>; base: string }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[640px] text-callout">
        <thead>
          <tr className="text-left text-caption text-label-2 [&>th]:px-3 [&>th]:pb-2 [&>th]:font-medium [&>th:first-child]:pl-5 sm:[&>th:first-child]:pl-6 [&>th:last-child]:pr-5 sm:[&>th:last-child]:pr-6">
            <th>Symbol</th>
            <th className="text-right">Shares</th>
            <th className="text-right">Price</th>
            <th className="text-right">Value ({base})</th>
            <th className="text-right">Gain ({base})</th>
            <th className="text-right">Return</th>
            <th className="w-36">Weight</th>
          </tr>
        </thead>
        <tbody className="tabular">
          {positions.map((p) => (
            <tr key={p.symbol} className="border-t-[0.5px] border-separator transition-colors hover:bg-fill-2 [&>td]:px-3 [&>td]:py-3 [&>td:first-child]:pl-5 sm:[&>td:first-child]:pl-6 [&>td:last-child]:pr-5 sm:[&>td:last-child]:pr-6">
              <td>
                <Link href={`/technical?symbol=${p.symbol}`} className="font-semibold hover:text-tint">
                  {p.symbol}
                </Link>
                {p.lots > 1 && <span className="ml-1.5 text-caption text-label-2">{p.lots} lots</span>}
              </td>
              <td className="text-right">{number(p.quantity, p.quantity % 1 ? 2 : 0)}</td>
              <td className="text-right">{money(p.price, p.currency)}</td>
              <td className="text-right font-medium">{money(p.valueBase, base)}</td>
              <td className="text-right">
                <Delta value={p.gainBase}>{money(p.gainBase, base, { sign: true })}</Delta>
              </td>
              <td className="text-right">
                <Delta value={p.gainPct}>{pct(p.gainPct, 1)}</Delta>
              </td>
              <td>
                <div className="flex items-center gap-2">
                  <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-fill-2">
                    <motion.div
                      className="h-full rounded-full bg-[var(--series-1)]"
                      initial={{ width: 0 }}
                      animate={{ width: `${p.weight}%` }}
                      transition={spring.smooth}
                    />
                  </div>
                  <span className="w-11 text-right text-caption text-label-2">{number(p.weight, 1)}%</span>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function OverviewSkeleton() {
  return (
    <div className="space-y-5">
      <Card>
        <Skeleton className="h-4 w-28" />
        <Skeleton className="mt-3 h-14 w-64" />
        <Skeleton className="mt-3 h-4 w-40" />
      </Card>
      <div className="grid gap-5 lg:grid-cols-5">
        <Card className="lg:col-span-2">
          <Skeleton className="h-56" />
        </Card>
        <Card className="lg:col-span-3">
          <Skeleton className="h-56" />
        </Card>
      </div>
      <p className="text-center text-footnote text-label-2">Fetching live prices…</p>
    </div>
  );
}
