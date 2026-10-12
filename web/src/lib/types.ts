export type User = { username: string; role: "admin" | "user"; email?: string | null };

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
  scores: { axis: string; score: number }[];
  ai_available: boolean;
};

export type AIResult = {
  steps: { title: string; content: string }[];
  recommendation: "BUY" | "HOLD" | "SELL";
  confidence: number;
  time_horizon: string;
  price_target: number | null;
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
  /** "scheduled" calls come from the twice-weekly run over a fixed list of stocks. */
  source: "manual" | "scheduled";
  /** Scheduled run the call belongs to; both models' calls in a comparison run share it. */
  run: string | null;
  /** 1 for calls made before the prompt defined BUY, SELL and confidence. */
  prompt_version: number;
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
  rules: RuleComparison;
  models: ModelComparison;
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
  rate: { minute: number; hour: number; day_tokens: number; limits: { minute: number; hour: number; day_tokens: number } };
  recent: { timestamp: string; model: string; operation: string; symbol: string | null; total_tokens: number; cost_usd: number; success: boolean; error_message: string | null }[];
};

/** Progress of the current or last scheduled run. */
export type RunStatus = {
  user: string;
  run: string;
  started: string;
  providers: ("local" | "gemini")[];
  total: number;
  done: number;
  current: string | null;
  ok: number;
  failed: number;
  finished: string | null;
  state: "running" | "finished" | "interrupted";
};

export type ScheduledRuns = {
  installed: boolean;
  next_run: string;
  /** Whether the next run is in the last week of the month, so Gemini runs too. */
  next_compare: boolean;
  model: string;
  /** Why the local model can't run right now, or null when it can. */
  local_problem: string | null;
  status: RunStatus | null;
  runs: {
    run: string;
    started: string;
    finished: string | null;
    providers: ("local" | "gemini")[];
    skipped: string[];
    ok: number;
    failed: number;
    errors: { symbol: string; provider: string | null; error: string }[];
  }[];
};
