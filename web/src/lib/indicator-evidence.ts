// What each technical indicator means, how well its signal is supported by research,
// and where to read more. Ratings describe the signal as the dashboard uses it.

export type Evidence = "strong" | "mixed" | "weak" | "risk";

export type Source = { cite: string; url?: string };

export type IndicatorInfo = {
  name: string;
  evidence: Evidence;
  read: string;
  verdict: string;
  learn?: string;
  sources: Source[];
};

export const EVIDENCE_LABEL: Record<Evidence, string> = {
  strong: "Strong evidence",
  mixed: "Mixed evidence",
  weak: "Weak evidence",
  risk: "Risk measure",
};

export const EVIDENCE_TONE = {
  strong: "positive",
  mixed: "warning",
  weak: "neutral",
  risk: "tint",
} as const satisfies Record<Evidence, string>;

const CHARTSCHOOL = "https://chartschool.stockcharts.com/table-of-contents";
const doi = (id: string) => `https://doi.org/${id}`;

const PARK_IRWIN: Source = {
  cite: "Park & Irwin (2007), What Do We Know About the Profitability of Technical Analysis?, Journal of Economic Surveys",
  url: doi("10.1111/j.1467-6419.2007.00519.x"),
};
const BROCK: Source = {
  cite: "Brock, Lakonishok & LeBaron (1992), Simple Technical Trading Rules and the Stochastic Properties of Stock Returns, Journal of Finance",
  url: doi("10.1111/j.1540-6261.1992.tb04681.x"),
};
const SULLIVAN: Source = {
  cite: "Sullivan, Timmermann & White (1999), Data-Snooping, Technical Trading Rule Performance, and the Bootstrap, Journal of Finance",
  url: doi("10.1111/0022-1082.00163"),
};
const WILDER: Source = { cite: "Wilder (1978), New Concepts in Technical Trading Systems (book)" };

export const INDICATORS = {
  rsi: {
    name: "RSI",
    evidence: "weak",
    read: "Momentum on a 0–100 scale using Wilder's smoothing. Above 70 is overbought and below 30 oversold, meaning the move is stretched, not that it will reverse. In strong trends RSI can stay above 70 (or below 30) for weeks, so read it alongside the trend.",
    verdict: "The 70/30 rule has not held up as a profitable signal on its own in tests since the 1990s. Short-term reversal effects exist, but at horizons of days to a month, not as a standalone RSI rule.",
    learn: `${CHARTSCHOOL}/technical-indicators-and-overlays/technical-indicators/relative-strength-index-rsi`,
    sources: [
      WILDER,
      { cite: "Jegadeesh (1990), Evidence of Predictable Behavior of Security Returns, Journal of Finance", url: doi("10.1111/j.1540-6261.1990.tb05110.x") },
      PARK_IRWIN,
    ],
  },
  macd: {
    name: "MACD",
    evidence: "weak",
    read: "12-day EMA minus 26-day EMA, with a 9-day signal line. Crossing above the signal is bullish; crossing below is bearish. The histogram shows the gap.",
    verdict: "A lagging, short-horizon trend rule. Crossovers whipsaw in sideways markets, and simple crossover rules like it largely stopped beating buy-and-hold after costs from the 1990s onwards.",
    learn: `${CHARTSCHOOL}/technical-indicators-and-overlays/technical-indicators/macd-moving-average-convergence-divergence-oscillator`,
    sources: [{ cite: "Appel (1979), The Moving Average Convergence-Divergence Trading Method (book)" }, PARK_IRWIN],
  },
  bollinger: {
    name: "Bollinger Bands",
    evidence: "weak",
    read: "A 20-day average ± 2 standard deviations. A close outside the bands means the move is unusually large, not that it will reverse: in strong trends price often \"walks\" along a band. A narrow squeeze often precedes a breakout.",
    verdict: "Tested band-touch strategies were not profitable after trading costs. Most useful as a volatility gauge (band width) rather than a buy or sell trigger.",
    learn: `${CHARTSCHOOL}/technical-indicators-and-overlays/technical-overlays/bollinger-bands`,
    sources: [
      { cite: "Bollinger (2001), Bollinger on Bollinger Bands (book)" },
      { cite: "Lento, Gradojevic & Wright (2007), Investment Information Content in Bollinger Bands?, Applied Financial Economics Letters", url: doi("10.1080/17446540701206576") },
    ],
  },
  trend: {
    name: "20 / 50-day averages",
    evidence: "mixed",
    read: "Price above its 20 and 50-day averages indicates a short to medium-term uptrend; below both, a downtrend.",
    verdict: "Moving-average rules showed real predictive power historically, but much of the edge weakened after the 1980s and is sensitive to data-snooping. They work better on volatile, smaller stocks.",
    learn: `${CHARTSCHOOL}/technical-indicators-and-overlays/technical-overlays/moving-averages-simple-and-exponential`,
    sources: [
      BROCK,
      SULLIVAN,
      { cite: "Han, Yang & Zhou (2013), A New Anomaly: The Cross-Sectional Profitability of Technical Analysis, Journal of Financial and Quantitative Analysis", url: doi("10.1017/S0022109013000586") },
    ],
  },
  obv: {
    name: "On-Balance Volume",
    evidence: "weak",
    read: "Adds volume on up days and subtracts it on down days. OBV rising with price confirms the trend; diverging from price can warn of a reversal.",
    verdict: "OBV itself has little academic testing. Research does show trading volume matters for momentum, so treat OBV as confirmation, not a signal on its own.",
    learn: `${CHARTSCHOOL}/technical-indicators-and-overlays/technical-indicators/on-balance-volume-obv`,
    sources: [
      { cite: "Granville (1963), Granville's New Key to Stock Market Profits (book)" },
      { cite: "Lee & Swaminathan (2000), Price Momentum and Trading Volume, Journal of Finance", url: doi("10.1111/0022-1082.00280") },
    ],
  },
  momentum: {
    name: "12-1 momentum",
    evidence: "strong",
    read: "The return over the past 12 months, skipping the most recent month (which tends to reverse). Positive means the stock has been a medium-term winner.",
    verdict: "One of the most robust findings in finance: past 3–12 month winners have kept outperforming over the next months across decades, countries and asset classes. It can crash sharply in market rebounds.",
    learn: `${CHARTSCHOOL}/technical-indicators-and-overlays/technical-indicators/rate-of-change-roc-and-momentum`,
    sources: [
      { cite: "Jegadeesh & Titman (1993), Returns to Buying Winners and Selling Losers, Journal of Finance", url: doi("10.1111/j.1540-6261.1993.tb04702.x") },
      { cite: "Moskowitz, Ooi & Pedersen (2012), Time Series Momentum, Journal of Financial Economics", url: doi("10.1016/j.jfineco.2011.11.003") },
      { cite: "Asness, Moskowitz & Pedersen (2013), Value and Momentum Everywhere, Journal of Finance", url: doi("10.1111/jofi.12021") },
    ],
  },
  high52w: {
    name: "52-week high",
    evidence: "strong",
    read: "How far the price is below its highest level of the past year. Near the high (within 5%) is historically a positive sign; far below (25%+) a negative one.",
    verdict: "Stocks near their 52-week high have outperformed those far from it, and this measure explained much of the momentum effect. Investors appear to anchor on the old high and under-react to good news.",
    sources: [
      { cite: "George & Hwang (2004), The 52-Week High and Momentum Investing, Journal of Finance", url: doi("10.1111/j.1540-6261.2004.00695.x") },
    ],
  },
  sma200: {
    name: "200-day average",
    evidence: "mixed",
    read: "The standard long-term trend line. Price above it marks a long-term uptrend; the 50-day crossing above the 200-day is the \"golden cross\", crossing below the \"death cross\".",
    verdict: "As a trend filter it has historically reduced drawdowns more than it raised returns. Evidence is stronger for whole markets and asset classes than for picking individual stocks.",
    learn: `${CHARTSCHOOL}/trading-strategies-and-models/trading-strategies/moving-average-trading-strategies/trading-using-the-golden-cross`,
    sources: [
      { cite: "Faber (2007), A Quantitative Approach to Tactical Asset Allocation, SSRN", url: "https://ssrn.com/abstract=962461" },
      BROCK,
      SULLIVAN,
    ],
  },
  adx: {
    name: "ADX",
    evidence: "weak",
    read: "Measures how strong a trend is, not its direction (+DI above −DI means up). Above 25 a trend is in place, so trend signals (moving averages, MACD) are more reliable and RSI extremes mean strength. Below 20 the stock is ranging, where RSI and Bollinger extremes are more useful.",
    verdict: "Little evidence as a buy or sell signal by itself. Its value is as a filter that tells you which of the other indicators to trust right now.",
    learn: `${CHARTSCHOOL}/technical-indicators-and-overlays/technical-indicators/average-directional-index-adx`,
    sources: [WILDER, PARK_IRWIN],
  },
  atr: {
    name: "ATR",
    evidence: "risk",
    read: "The average daily price range, including gaps. Use it to size positions and set stops: a stop two ATRs away sits outside normal daily noise.",
    verdict: "Not a return signal. Volatility is persistent (calm and turbulent periods cluster), so recent ATR is a sound estimate of near-term risk.",
    learn: `${CHARTSCHOOL}/technical-indicators-and-overlays/technical-indicators/average-true-range-atr-and-average-true-range-percent-atrp`,
    sources: [
      WILDER,
      { cite: "Engle (1982), Autoregressive Conditional Heteroscedasticity, Econometrica", url: doi("10.2307/1912773") },
    ],
  },
} satisfies Record<string, IndicatorInfo>;

export type IndicatorKey = keyof typeof INDICATORS;
