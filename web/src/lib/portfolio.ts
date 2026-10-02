import type { MetricsRow } from "./types";

export const CURRENCIES = ["USD", "SGD", "EUR", "GBP", "JPY", "CAD", "AUD", "HKD", "CNY", "INR", "KRW", "THB", "MYR", "IDR", "PHP", "VND"] as const;

export type Position = {
  symbol: string;
  currency: string;
  lots: number;
  quantity: number;
  avgCost: number;
  price: number;
  value: number;
  invested: number;
  valueBase: number;
  investedBase: number;
  gainBase: number;
  gainPct: number;
  weight: number;
};

/** Merge purchase lots into one position per symbol. */
export function toPositions(rows: MetricsRow[]): Position[] {
  const map = new Map<string, Position>();
  for (const r of rows) {
    const p = map.get(r.symbol) ?? {
      symbol: r.symbol, currency: r.currency, lots: 0, quantity: 0, avgCost: 0, price: r.current_price,
      value: 0, invested: 0, valueBase: 0, investedBase: 0, gainBase: 0, gainPct: 0, weight: 0,
    };
    p.lots += 1;
    p.quantity += r.quantity;
    p.value += r.value;
    p.invested += r.invested;
    p.valueBase += r.value_base;
    p.investedBase += r.invested_base;
    p.weight += r.weight;
    map.set(r.symbol, p);
  }
  return [...map.values()]
    .map((p) => ({
      ...p,
      avgCost: p.quantity ? p.invested / p.quantity : 0,
      gainBase: p.valueBase - p.investedBase,
      gainPct: p.invested ? ((p.value - p.invested) / p.invested) * 100 : 0,
    }))
    .sort((a, b) => b.valueBase - a.valueBase);
}
