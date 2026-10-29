/** `gemini_private`: Gemini is kept from the user's positions, portfolio and private pages (on by default). */
export type User = { username: string; role: "admin" | "user"; email?: string | null; gemini_private?: boolean; private_terms?: string[] };

export type Holding = {
  index: number;
  Symbol: string;
  Quantity: number;
  Purchase_Price: number;
  Purchase_Date: string;
  Currency: string;
};

export type MetricsRow = {
  index: number;
  symbol: string;
  quantity: number;
  currency: string;
  purchase_price: number;
  purchase_date: string;
  current_price: number;
  invested: number;
  value: number;
  gain: number;
  invested_base: number;
  value_base: number;
  gain_base: number;
  gain_pct: number;
  weight: number;
};

export type Metrics = {
  base_currency: string;
  holdings_count: number;
  total_invested: number;
  total_value: number;
  total_gain: number;
  total_gain_pct: number;
  rows: MetricsRow[];
  unpriced: string[];
};

export type Performance = {
  period: string;
  series: Array<Record<string, number | string | null>>;
  series_keys: string[];
  risk: { symbol: string; volatility: number; avg_daily_return: number }[];
  sectors: { sector: string; value: number }[];
  summary: {
    total_value: number;
    total_invested: number;
    total_gain: number;
    total_gain_pct: number;
    best: { symbol: string; gain_pct: number } | null;
    worst: { symbol: string; gain_pct: number } | null;
    holdings: number;
  };
  base_currency: string;
  unpriced: string[];
};

/** `date` is the bar the price comes from (intraday during a session). */
export type Quote = { price: number; date?: string; change: number; change_pct: number; volume: number | null };

export type TechnicalPoint = {
  date: string;
  close: number | null;
  volume: number | null;
  rsi: number | null;
  macd: number | null;
  signal: number | null;
  hist: number | null;
  bb_upper: number | null;
  bb_middle: number | null;
  bb_lower: number | null;
  sma20: number | null;
  sma50: number | null;
  sma200: number | null;
  ema20: number | null;
  obv: number | null;
  obv_ema: number | null;
  adx: number | null;
  plus_di: number | null;
  minus_di: number | null;
  atr_pct: number | null;
};

export type Signals = {
  rsi: { value: number | null; state: "overbought" | "oversold" | "neutral" | null };
  macd: { macd: number | null; signal: number | null; state: "bullish" | "bearish" | null };
  bollinger: { percent_b: number | null; state: "above" | "below" | "within" | null; upper: number | null; middle: number | null; lower: number | null };
  trend: {
    sma20: { value: number | null; price_above: boolean };
    sma50: { value: number | null; price_above: boolean };
    sma200: { value: number | null; price_above: boolean };
    golden_cross: boolean | null;
  };
  obv: { value: number | null; state: "rising" | "falling" };
  adx: { value: number | null; plus_di: number | null; minus_di: number | null; state: "strong" | "developing" | "weak" | null; direction: "up" | "down" | null };
  atr: { value: number | null; pct: number | null };
  momentum: { return_12_1: number | null; state: "positive" | "negative" | null };
  high_52w: { value: number | null; distance: number | null; state: "near" | "below" | "far" | null };
};

export type Technical = { symbol: string; period: string; quote: Quote; signals: Signals; series: TechnicalPoint[] };

export type BacktestHorizon = {
  days: number;
  n: number;
  hit_rate: number | null;
  avg_return: number | null;
  baseline_hit: number;
  baseline_avg: number | null;
  verdict: "worked" | "failed" | "no_edge" | "insufficient";
};

export type SignalBacktest = {
  symbol: string;
  start: string;
  end: string;
  horizons: number[];
  cooldown_days: number;
  min_events: number;
  signals: {
    id: string;
    indicator: "rsi" | "macd" | "bollinger" | "sma200" | "high52w" | "adx";
    label: string;
    expect: "up" | "down";
    count: number;
    last: string | null;
    horizons: BacktestHorizon[];
  }[];
};

/** `note` explains a missing or distorted value, e.g. a negative multiple or a ratio that doesn't apply to banks. */
export type Ratio = { key: string; label: string; value: number | null; unit: "x" | "fraction" | "percent"; note: string | null };

/** A measure computed from the statements; `tone` grades it against the rule of thumb in `hint`. */
export type Metric = {
  key: string;
  label: string;
  value: number | null;
  unit: "x" | "fraction" | "number";
  tone: "good" | "bad" | "neutral" | null;
  hint: string;
  note: string | null;
};

export type Piotroski = {
  score: number;
  tested: number;
  state: "strong" | "middle" | "weak";
  tests: { label: string; passed: boolean | null; group: "profitability" | "funding" | "efficiency" }[];
};

export type EarningsRecord = {
  surprises: { quarter: string; actual: number | null; estimate: number | null; surprise_pct: number | null }[];
  beats: number;
  estimates: { period: string; label: string; current: number | null; change_30d: number | null; change_90d: number | null; up_30d: number | null; down_30d: number | null }[];
  next_date: string | null;
};

/** A measure at each past fiscal year-end (oldest first) against today's trailing-12-month figure. */
export type HistoryRow = {
  key: string;
  label: string;
  unit: "x" | "fraction";
  better: "lower" | "higher";
  valuation: boolean;
  values: (number | null)[];
  now: number | null;
  median: number;
  low: number;
  high: number;
  vs_median: number | null;
  verdict: "cheaper" | "pricier" | "better" | "worse" | "in line" | null;
};

export type StatementRow = { label: string; values: (number | null)[]; growth: (number | null)[]; cagr: number | null };

export type Fundamentals = {
  symbol: string;
  profile: {
    name: string;
    sector: string | null;
    industry: string | null;
    country: string | null;
    website: string | null;
    employees: number | null;
    summary: string | null;
    /** Currency the shares trade in. */
    currency: string;
    /** Currency the statements are reported in (differs for ADRs, e.g. TSM reports in TWD). */
    financial_currency: string;
    kind: "general" | "financial" | "reit";
    kind_note: string | null;
  };
  as_of: { ratios: string | null; statements: string | null };
  headline: { price: number | null; market_cap: number | null; enterprise_value: number | null; pe: number | null; forward_pe: number | null; loss_making: boolean; week52_low: number | null; week52_high: number | null };
  ratios: Record<string, Ratio[]>;
  analyst: {
    target_mean: number | null;
    target_low: number | null;
    target_high: number | null;
    upside_pct: number | null;
    recommendation_mean: number | null;
    recommendation_key: string | null;
    analyst_count: number | null;
    dividend_yield_pct: number | null;
    payout_ratio: number | null;
  };
  quality: { piotroski: Piotroski | null; metrics: Metric[] };
  risk: { metrics: Metric[] };
  earnings: EarningsRecord;
  history: { years: string[]; rows: HistoryRow[] };
  statements: Record<"income" | "balance" | "cashflow", { years: string[]; rows: StatementRow[] }>;
};

export type ModelMetrics = {
  rmse_pct: number;
  mae_pct: number;
  skill: number | null;
  dm_p: number | null;
  directional_accuracy: number | null;
  direction_ci: [number, number] | null;
  direction_n: number;
  verdict: "skill" | "no edge" | "worse";
  band80_hit?: number;
};

export type ModelResult = { name: string; kind: "trained" | "pretrained"; metrics: ModelMetrics; next_return: number; next_close: number };

export type Band = { low: number; high: number };
export type Coverage = { target: number; hit_rate: number | null; n: number; p_value: number | null };

export type ForecastRange = {
  model: string;
  sigma_pct: number;
  long_run_sigma_pct: number | null;
  persistence: number;
  next: Record<"80" | "95", Band>;
  coverage: Record<"80" | "95", Coverage>;
  backtest: { date: string; actual: number; lo80: number; hi80: number; lo95: number; hi95: number }[];
};

export type ChronosStatus = { available: boolean; model: string; note: string | null };

export type Prediction = {
  symbol: string;
  period: string;
  last_close: number;
  last_date: string;
  samples: { train: number; test: number; features: number; refit_every: number };
  baseline: { name: string; up_share: number; rmse_pct: number };
  models: ModelResult[];
  best_model: string | null;
  any_skill: boolean;
  alpha: number;
  range: ForecastRange;
  series: ({ date: string; actual: number } & Record<string, number | string>)[];
  feature_importance: { feature: string; importance: number }[];
  chronos: ChronosStatus | null;
};

export type Tone = "Positive" | "Neutral" | "Negative";

export type ArticleStatus = "scored" | "old" | "undated" | "duplicate" | "routine" | "off_topic";

export type Article = {
  title: string;
  source: string;
  date: string;
  published: string | null;
  link: string;
  origin: string;
  status: ArticleStatus;
  price_move: boolean;
  sentiment: Tone;
  score: number;
  confidence: number | null;
};

export type SentimentScorer = { name: string; model: string; finance: boolean };

export type Sentiment = {
  symbol: string;
  days: 7 | 30;
  query: { name: string; keywords: string[] | null; ticker: string; google_finance: string | null; google_news: string };
  scorer: SentimentScorer;
  scorer_note: string | null;
  overall: Tone | null;
  index: number | null;
  ci: [number, number] | null;
  n: number;
  min_articles: number;
  counts: Record<Tone, number>;
  pct: Record<Tone, number>;
  excluded: Record<Exclude<ArticleStatus, "scored">, number>;
  price: { change_pct: number; from: string; to: string } | null;
  price_move_share: number | null;
  daily: { date: string; n: number; mean: number }[];
  articles: Article[];
  errors: string[];
  searches_used: number;
};

export type Features = { ml: boolean; gemini: boolean; sentiment: { libraries: boolean; api_key: boolean; enabled: boolean; scorer: { finance: boolean; model: string; note: string | null } }; chronos: ChronosStatus };

export type AssessmentContext = {
  symbol: string;
  period: string;
  generated_at: string;
  technical: Omit<Technical, "series">;
  fundamental: Omit<Fundamentals, "statements">;
  predictive: {
    any_skill: boolean;
    test_days: number;
    up_share: number;
    models: { name: string; skill: number | null; dm_p: number | null; verdict: ModelMetrics["verdict"]; directional_accuracy: number | null; direction_ci: [number, number] | null; next_return: number }[];
    best: { name: string; skill: number | null; verdict: ModelMetrics["verdict"]; next_return: number } | null;
    last_close: number;
    range: Omit<ForecastRange, "backtest">;
  } | null;
  sentiment: (Omit<Sentiment, "articles"> & { headlines: { title: string; source: string; date: string; sentiment: string; link: string }[] }) | null;
  sentiment_status: { requested: boolean; enabled: boolean; error: string | null };
  position: {
    lots: number;
    quantity: number;
    avg_cost: number | null;
    invested: number;
    value: number | null;
    unrealized: number | null;
    unrealized_pct: number | null;
    currency: string;
  } | null;
  /** How the stock sits in your portfolio (manual assessments only). */
  portfolio?: PortfolioFit | null;
  market?: MarketContext | null;
  valuation?: Valuation | null;
  scores: { axis: string; score: number }[];
  ai_available: boolean;
};

export type PortfolioFit = {
  weight: number | null;
  risk_share: number | null;
  corr_to_rest: number | null;
  industry: string | null;
  industry_weight: number;
  largest: { symbol: string; weight: number }[];
  effective_bets: number | null;
  holdings: number;
  beta: number | null;
};

export type AIResult = {
  steps: { title: string; content: string }[];
  recommendation: "BUY" | "HOLD" | "SELL";
  confidence: number;
  time_horizon: string;
  price_target: number | null;
  /** Expected return minus the S&P 500's over the horizon, in percentage points (prompt version 3 on). */
  expected_excess_return?: number;
  strengths: string[];
  risks: string[];
  position_advice: string;
  summary: string;
  model: string;
  generated_at: string;
};

export type EvaluationFinding = {
  skill: string;
  stance: "supports" | "challenges" | "neutral";
  severity: "info" | "minor" | "major";
  finding: string;
};

export type EntryPlan = { approach: "all_at_once" | "staged" | "wait"; detail: string; size: string; review_when: string };

export type EvaluationSkill = {
  name: string;
  title: string;
  description: string;
  applies_when: string;
  evidence: "strong" | "mixed" | "weak";
  rationale: string;
  sources: { cite: string; url: string }[];
};

export type Evaluation = {
  verdict: "stands" | "weakened" | "contradicted";
  confidence_adjusted: number;
  original_confidence: number;
  recommendation: AIResult["recommendation"];
  summary: string;
  findings: EvaluationFinding[];
  counter_case: string;
  invalidation: string[];
  entry_plan: EntryPlan | null;
  skills: EvaluationSkill[];
  checks: { skill: string; check: string; passed: boolean; detail: string }[];
  model: string;
  generated_at: string;
  saved: boolean;
};

/** What the track record keeps of an evaluation. */
export type SavedEvaluation = Pick<Evaluation, "verdict" | "confidence_adjusted" | "summary" | "findings" | "counter_case" | "invalidation" | "entry_plan" | "generated_at"> & {
  skills: string[];
};

/** Return over `days` trading days after the entry close, vs the S&P 500; null until that day has passed. */
export type Checkpoint = { days: number; label: string; date: string | null; stock: number | null; benchmark: number | null; excess: number | null };

export type Signal = {
  id: number;
  timestamp: string;
  symbol: string;
  recommendation: "BUY" | "HOLD" | "SELL";
  confidence: number | null;
  /** The quote saved with the call; may be stale or intraday, and isn't split-adjusted. */
  price_at_signal: number | null;
  /** Date of the bar that quote came from (saved from prompt version 2 on). */
  quote_date: string | null;
  current_price: number | null;
  price_target: number | null;
  time_horizon: string | null;
  /** First split-adjusted close at or after the call: the price scoring starts from. */
  entry_date: string | null;
  entry_price: number | null;
  /** Since the entry close: the stock, the S&P 500, and the difference. */
  return_pct: number | null;
  benchmark_pct: number | null;
  excess_pct: number | null;
  /** Shares today per share held at the signal (above 1 after a split). */
  split_factor: number;
  checkpoints: Checkpoint[];
  /** Whether the 12-month target was reached; `hit` is null while the year is still running. */
  target: { price: number; hit: boolean | null; date: string | null } | null;
  /** BUYs only: [date, stock growth of 1, S&P 500 growth of 1] each day since the entry close. */
  path: [string, number, number][] | null;
  /** 12-1 month momentum at the entry close, as a fraction; null with under a year of history. */
  momentum: number | null;
  /** Trading days the call is scored at; the stock minus the S&P 500 there, and the AI's return (a SELL's is negated). */
  score_days: number;
  score_excess: number | null;
  score_return: number | null;
  /** What each simple rule would have said at the same moment; null when it lacked the data. */
  rules: Record<RuleKey, Signal["recommendation"] | null>;
  model: string | null;
  provider: "gemini" | "local";
  /** "scheduled" calls come from the twice-weekly run over your holdings and a fixed list of stocks. */
  source: "manual" | "scheduled";
  /** Scheduled run the call belongs to; both models' calls in a comparison run share it. */
  run: string | null;
  /** Whether you held the stock when the call was made; null for scheduled calls from before this was saved. */
  held: boolean | null;
  /** Whether the stock is on the scheduled run's fixed list; null for calls run by you. */
  in_list: boolean | null;
  /** 1 for calls made before the prompt defined BUY, SELL and confidence. */
  prompt_version: number;
  /** Expected return vs the S&P 500 in percentage points, stated with the call (prompt version 3 on). */
  expected_excess: number | null;
  outcome: "Correct" | "Wrong" | "Flat" | "Neutral" | "Pending";
  strengths: string[];
  risks: string[];
  reasoning: string;
  steps: { title: string; content: string }[];
  position_advice: string | null;
  portfolio_context: { avg_purchase_price: number; total_quantity: number; unrealized_pct: number } | null;
  evaluation: SavedEvaluation | null;
};

export type RuleKey = "always_buy" | "momentum" | "analyst" | "app_score";

/** The AI against simple rules on the AI's calls that have reached the scoring checkpoint. */
export type RuleComparison = {
  checked: number;
  rows: { key: "ai" | RuleKey; label: string; calls: number; win_rate: number | null; avg_return: number | null }[];
};

type ModelRow = { model: string; calls: number; win_rate: number | null; avg_return: number | null };

/** Each model's scored calls, and the paired calls from comparison runs (same stock, same context). */
export type ModelComparison = {
  models: string[];
  all: ModelRow[];
  pairs: number;
  agreement: number | null;
  paired: ModelRow[];
  pairs_checked: number;
};

export type TrackRecord = {
  signals: Signal[];
  symbols: string[];
  horizon: number | "stated";
  flat_band: number;
  benchmark_available: boolean;
  calibration: Calibration;
  confidence: ConfidenceCalibration;
  ranking: Ranking;
  rules: RuleComparison;
  models: ModelComparison;
};

/** Scored BUY/SELL calls by stated confidence: the probability claimed against how often they were right. */
export type ConfidenceCalibration = {
  rows: { label: string; n: number; stated: number; actual: number | null; ci: [number, number] | null }[];
  n: number;
  brier: number | null;
};

/** How well each scheduled run ranked its stocks, HOLDs included. */
export type Ranking = {
  runs: { run: string; model: string; n: number; ic: number; spread: number | null; top: string[]; bottom: string[] }[];
  count: number;
  mean_ic: number | null;
  ic_t: number | null;
  mean_spread: number | null;
  positive_share: number | null;
  min_ranked: number;
};

/** Scored BUY/SELL calls grouped by evaluation verdict, and Brier scores of original vs adjusted confidence. */
export type Calibration = {
  groups: { verdict: SavedEvaluation["verdict"] | "not_evaluated"; n: number; win_rate: number | null; avg_return: number | null }[];
  evaluated: number;
  lowered: number;
  brier_original: number | null;
  brier_adjusted: number | null;
};

export type Usage = {
  days: number;
  total_calls: number;
  successful_calls: number;
  failed_calls: number;
  total_tokens: number;
  total_cost: number;
  avg_tokens_per_call: number;
  daily: { date: string; calls: number; tokens: number; cost: number }[];
  operations: { name: string; calls: number; tokens: number; cost: number }[];
  symbols: { name: string; calls: number; tokens: number; cost: number }[];
  /** Gemini against its three limits: requests and tokens in the last minute, requests since midnight Pacific. */
  rate: { rpm: number; tpm: number; rpd: number; limits: { rpm: number; tpm: number; rpd: number }; resets_at: string };
  recent: { timestamp: string; model: string; operation: string; symbol: string | null; total_tokens: number; cost_usd: number; success: boolean; error_message: string | null }[];
};

/** Progress of the current or last scheduled run. A day's run is assessed a chunk an hour: "running"
 * while a chunk is going, "waiting" between chunks, "incomplete" if the day's slots ran out. */
export type RunStatus = {
  user: string;
  run: string;
  started: string;
  providers: ("local" | "gemini")[];
  total: number;
  /** How many of the run's stocks are your holdings (missing on runs from before holdings were added). */
  held?: number;
  done: number;
  current: string | null;
  ok: number;
  failed: number;
  finished: string | null;
  /** When the next chunk starts, while waiting. */
  next_chunk?: string;
  state: "running" | "waiting" | "finished" | "incomplete";
};

export type ScheduledRuns = {
  installed: boolean;
  next_run: string;
  /** Whether the next run is in the last week of the month, so Gemini runs too. */
  next_compare: boolean;
  model: string;
  /** Stocks per hourly chunk, and the first and last hour chunks start. */
  chunk: number;
  /** What the next run covers: your holdings (assessed first), the fixed list's size, and the stocks in all. */
  held: string[];
  list_size: number;
  total: number;
  hours: [number, number];
  /** Why the local model can't run right now, or null when it can. */
  local_problem: string | null;
  status: RunStatus | null;
  runs: {
    run: string;
    started: string;
    finished: string | null;
    providers: ("local" | "gemini")[];
    skipped: string[];
    /** Stocks in the run; null for runs from before chunking. */
    total: number | null;
    /** How many of them were your holdings. */
    held: number;
    ok: number;
    failed: number;
    errors: { symbol: string; provider: string | null; error: string }[];
  }[];
};

export type RetroSourceId = "horizons" | "swisseph" | "local";

export type RetroStation = {
  sign: string;
  degree: number;
  longitude: number;
  /** Consensus (median) time across sources, UTC. */
  time: string;
  by_source: Partial<Record<RetroSourceId, string | null>>;
  spread_hours: number;
  agree: number;
};

export type RetroPeriod = {
  planet: string;
  name: string;
  start: string;
  end: string;
  shadow_start: string | null;
  shadow_end: string | null;
  station_retrograde: RetroStation;
  station_direct: RetroStation;
  verification: {
    status: "verified" | "partial" | "conflict" | "single";
    sources_agreeing: number;
    sources_available: number;
    max_spread_hours: number;
  };
};

export type RetrogradeCalendar = {
  range: { start: string; end: string };
  generated_at: string;
  reference: RetroSourceId;
  agree_hours: number;
  planets: { id: string; name: string }[];
  sources: { id: RetroSourceId; name: string; method: string; url: string; status: "ok" | "error"; error?: string; stations?: number }[];
  periods: RetroPeriod[];
};

export type RetroCompare = {
  days_in: number;
  days_out: number;
  /** Annualized return inside / outside the windows, %. */
  ann_in: number;
  ann_out: number;
  /** ann_in − ann_out, percentage points. */
  diff: number;
  daily_diff_bp: number;
  vol_in: number;
  vol_out: number;
  up_in: number;
  up_out: number;
  /** Circular-shift p-value and its Benjamini–Hochberg q-value. */
  p: number;
  q: number;
  shifts: number;
};

export type RetroMarkets = {
  generated_at: string;
  since: number;
  window: "retrograde" | "shadow";
  benchmark: string;
  planets: string[];
  missing: string[];
  tests: { id: string; label: string; planets: string[]; share_of_days: number | null }[];
  results: {
    symbol: string;
    name: string;
    group: string;
    first_date: string;
    days: number;
    tests: Record<string, { absolute: RetroCompare | null; excess?: RetroCompare | null }>;
  }[];
  periods: {
    planet: string;
    start: string;
    end: string;
    trading_days: number;
    complete: boolean;
    returns: Record<string, { ret: number; typical: number | null; typical_down: number | null }>;
  }[];
  growth: ({ date: string } & Record<string, number | string | null>)[];
  method: { min_days: number; exclude_shift_days: number; tests_run: number };
};

/* ── Sales and actual returns ── */

export type SaleLot = { Purchase_Date: string; Purchase_Price: number; Quantity: number; Currency: string };

export type Sale = {
  id: string;
  type: "SELL";
  Symbol: string;
  Quantity: number;
  Price: number;
  Fees: number;
  Date: string;
  Currency: string;
  lots: SaleLot[];
  cost: number;
  proceeds: number;
  realized: number;
  created: string;
};

export type Returns =
  | { base_currency: string; empty: true }
  | {
      base_currency: string;
      empty: false;
      start: string;
      years: number;
      summary: {
        bought: number;
        sold: number;
        value: number;
        dividends: number;
        dividends_ttm: number;
        realized: number;
        unrealized: number;
        total_gain: number;
        twr_pct: number;
        twr_annual_pct: number | null;
        irr_pct: number | null;
        benchmark_twr_pct: number;
        benchmark_irr_pct: number | null;
        benchmark_value: number;
        value_added: number;
      };
      series: { date: string; value: number; with_income: number; net_invested: number; benchmark_value: number; twr: number; benchmark_twr: number }[];
      dividends: {
        by_symbol: { symbol: string; amount: number }[];
        by_year: { year: string; amount: number }[];
        recent: { symbol: string; date: string; per_share: number; shares: number; amount: number; currency: string }[];
      };
      realized: {
        id: string;
        symbol: string;
        date: string;
        quantity: number;
        price: number;
        fees: number;
        currency: string;
        proceeds: number;
        cost: number;
        gain: number;
        gain_pct: number | null;
        gain_base: number;
        held_days: number | null;
      }[];
      missing: string[];
      benchmark: string;
    };

/* ── Portfolio risk ── */

export type RiskFlag = { severity: "warning" | "info"; kind: string; message: string };

export type RiskHolding = {
  symbol: string;
  name: string;
  value: number;
  weight: number;
  sector: string;
  industry: string;
  country: string;
  fund: boolean;
  currency: string;
  vol: number | null;
  beta: number | null;
  risk_share: number | null;
  corr_to_rest: number | null;
  history_days: number;
};

export type RiskPortfolio = {
  vol: number;
  beta: number | null;
  var95: number;
  var99: number;
  cvar95: number;
  var95_amount: number;
  cvar95_amount: number;
  diversification_ratio: number | null;
  effective_bets: number | null;
  hhi_bets: number;
  avg_corr: number | null;
  bench_vol: number;
  max_drawdown: number;
  drawdown_from: string;
  drawdown_to: string;
  current_drawdown: number;
  bench_max_drawdown: number;
  holdings_used: number;
};

export type Exposure = { name: string; weight: number; benchmark?: number | null };

export type Scenario = {
  name: string;
  start: string;
  end: string;
  benchmark: number;
  portfolio: number;
  loss: number;
  estimated: number;
  rows: { symbol: string; return: number; estimated: boolean }[];
};

export type Risk = {
  total_value: number;
  base_currency: string;
  window_days: number;
  excluded: string[];
  as_of: string;
  empty?: boolean;
  portfolio: RiskPortfolio | null;
  holdings: RiskHolding[];
  correlation: { symbols: string[]; matrix: number[][] } | null;
  exposure: { sector: Exposure[]; industry: Exposure[]; currency: Exposure[]; country: Exposure[] } | null;
  scenarios: Scenario[];
  drawdown: { date: string; portfolio: number; benchmark: number }[] | null;
  flags: RiskFlag[];
};

export type WhatIfSide = RiskPortfolio & {
  total_value: number;
  flags: RiskFlag[];
  top_industry: Exposure | null;
  holdings: Record<string, RiskHolding>;
  worst_scenario: Scenario | null;
};

export type WhatIf = {
  base_currency: string;
  trades: { symbol: string; amount: number }[];
  symbols: string[];
  before: WhatIfSide | null;
  after: WhatIfSide | null;
};

/* ── Market backdrop ── */

export type MarketReading = {
  key: string;
  label: string;
  value: number;
  unit: string;
  detail: string | null;
  lean: "supportive" | "neutral" | "headwind";
  rule: string;
};

export type MarketContext = {
  as_of: string;
  regime: "risk-on" | "mixed" | "risk-off";
  supportive: number;
  headwinds: number;
  readings: MarketReading[];
  sectors: { symbol: string; name: string; return_3m: number; return_12m: number | null; vs_spy_3m: number | null }[];
  spy_3m: number | null;
  spy_12m: number | null;
};

/* ── Valuation anchors ── */

export type PeerRow = {
  key: string;
  label: string;
  unit: "x" | "fraction";
  better: "lower" | "higher";
  value: number | null;
  median: number | null;
  n: number;
  /** Share of peers the company beats on this measure. */
  rank: number | null;
  vs_median: number | null;
};

export type Valuation = {
  symbol: string;
  peers: {
    source: "finnhub" | "portfolio";
    industry: string | null;
    peers: ({ symbol: string; name: string; market_cap: number | null } & Record<string, number | string | null>)[];
    rows: PeerRow[];
  };
  anchor: {
    currency: string;
    discount_rate: number;
    discount_inputs: { risk_free: number; beta: number | null; premium: number; clamped: boolean };
    terminal_growth: number;
    fcf: number | null;
    enterprise_value: number | null;
    implied_growth: number | null;
    sensitivity: { rate: number; growth: number | null }[];
    history: { revenue_cagr: number | null; fcf_cagr: number | null; eps_growth_next_year: number | null; years: number };
    yields: { earnings: number | null; forward_earnings: number | null; fcf: number | null; dividend: number | null; shareholder: number | null; treasury_10y: number };
    yield_gap: number | null;
    note: string | null;
  };
};

/* ── Plan ── */

export type Thesis = { thesis: string; sell_if: string[]; review_date: string | null; created: string; updated: string };

export type AlertKind = "price_above" | "price_below" | "below_cost" | "weight_above" | "drawdown" | "estimate_cut";

export type AlertRule = { id: string; symbol: string; kind: AlertKind; value: number; note: string | null; created: string };

export type Plan = {
  targets: Record<string, number>;
  band: number;
  watchlist: string[];
  journal: Record<string, Thesis>;
  alerts: AlertRule[];
};

export type PlanQuote = {
  symbol: string;
  name: string;
  currency: string;
  price: number | null;
  change_pct: number | null;
  high_52w: number | null;
  from_high: number | null;
  next_earnings: string | null;
  estimate_90d: number | null;
  forward_pe: number | null;
  target_mean: number | null;
  recommendation: string | null;
};

export type LastCall = { timestamp: string; recommendation: "BUY" | "HOLD" | "SELL"; confidence: number | null; source: string };

export type Triggered = { kind: "rule" | "earnings" | "review" | "drift"; symbol: string | null; message: string; severity: "warning" | "info"; rule: string | null };

export type PlanStatus = {
  base_currency: string;
  total_value: number;
  band: number;
  targeted: number;
  triggered: Triggered[];
  rebalance: { symbol: string; weight: number; target: number | null; value: number; drift: number | null; trade: number | null; shares: number | null; price: number | null; currency: string }[];
  calendar: { symbol: string; date: string; days: number; held: boolean; watching: boolean }[];
  watchlist: (PlanQuote & { last_call: LastCall | null; held: boolean; thesis: boolean })[];
  holdings: {
    symbol: string;
    quantity: number;
    avg_cost: number | null;
    value_base: number;
    weight: number;
    currency: string;
    price: number;
    quote: PlanQuote | null;
    thesis: Thesis | null;
    last_call: LastCall | null;
    alerts: AlertRule[];
  }[];
  alerts: (AlertRule & { label: string; unit: "price" | "pct" })[];
  kinds: Record<AlertKind, { label: string; unit: "price" | "pct" }>;
  as_of: string;
  review_soon: string[];
};
