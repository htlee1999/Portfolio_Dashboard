// Why each forecasting model and testing method is used, how well research supports it, and
// where to read more. Model ratings describe the evidence that the approach forecasts daily
// stock returns (or, for GARCH, volatility); testing methods carry no rating.

import { doi, type EvidenceInfo, type Source } from "./evidence";

const FAMA: Source = {
  cite: "Fama (1970), Efficient Capital Markets: A Review of Theory and Empirical Work, Journal of Finance",
  url: doi("10.2307/2325486"),
};
const WELCH_GOYAL: Source = {
  cite: "Welch & Goyal (2008), A Comprehensive Look at the Empirical Performance of Equity Premium Prediction, Review of Financial Studies",
  url: doi("10.1093/rfs/hhm014"),
};
const CAMPBELL_THOMPSON: Source = {
  cite: "Campbell & Thompson (2008), Predicting Excess Stock Returns Out of Sample: Can Anything Beat the Historical Average?, Review of Financial Studies",
  url: doi("10.1093/rfs/hhm055"),
};
const GKX: Source = {
  cite: "Gu, Kelly & Xiu (2020), Empirical Asset Pricing via Machine Learning, Review of Financial Studies",
  url: doi("10.1093/rfs/hhaa009"),
};
const KRAUSS: Source = {
  cite: "Krauss, Do & Huck (2017), Deep Neural Networks, Gradient-Boosted Trees, Random Forests: Statistical Arbitrage on the S&P 500, European Journal of Operational Research",
  url: doi("10.1016/j.ejor.2016.10.031"),
};
const RAPACH: Source = {
  cite: "Rapach, Strauss & Zhou (2010), Out-of-Sample Equity Premium Prediction: Combination Forecasts and Links to the Real Economy, Review of Financial Studies",
  url: doi("10.1093/rfs/hhp063"),
};

export const FORECAST = {
  no_change: {
    name: "No-change forecast (the benchmark)",
    evidence: "strong",
    read: "Predicts that tomorrow's close equals today's, so a return of zero. Every model on this page is scored by how much it improves on it.",
    verdict: "Daily stock returns are close to unpredictable from past prices, so this simple forecast is hard to beat. Most return predictors published in the literature fail to beat a naive benchmark once tested on later data.",
    learn: { site: "Wikipedia", url: "https://en.wikipedia.org/wiki/Random_walk_hypothesis" },
    sources: [FAMA, WELCH_GOYAL, CAMPBELL_THOMPSON],
  },
  ridge: {
    name: "Ridge regression",
    evidence: "mixed",
    read: "A straight-line model of tomorrow's return on the inputs, with its weights shrunk toward zero so it can't chase noise. The amount of shrinkage is chosen by cross-validation.",
    verdict: "Shrinkage is a well-established defence against overfitting, and penalised linear models deliver small but real out-of-sample gains for monthly returns across many stocks. For one stock's daily returns, gains are rarely distinguishable from zero.",
    learn: { site: "Wikipedia", url: "https://en.wikipedia.org/wiki/Ridge_regression" },
    sources: [
      { cite: "Hoerl & Kennard (1970), Ridge Regression: Biased Estimation for Nonorthogonal Problems, Technometrics", url: doi("10.1080/00401706.1970.10488634") },
      GKX,
      RAPACH,
    ],
  },
  gradient_boosting: {
    name: "Gradient boosting",
    evidence: "mixed",
    read: "Builds many small decision trees, each correcting the errors of the ones before, so it can pick up non-linear effects. Trees are kept shallow and learning slow to limit overfitting.",
    verdict: "Tree ensembles rank among the best return forecasters in large studies, but those gains come from thousands of stocks and decades of data. Trained on one stock's last year or two, they tend to fit noise, and here they often did worse than no change.",
    learn: { site: "Wikipedia", url: "https://en.wikipedia.org/wiki/Gradient_boosting" },
    sources: [
      { cite: "Friedman (2001), Greedy Function Approximation: A Gradient Boosting Machine, Annals of Statistics", url: doi("10.1214/aos/1013203451") },
      KRAUSS,
      GKX,
    ],
  },
  random_forest: {
    name: "Random forest",
    evidence: "mixed",
    read: "Averages many decision trees, each grown on a random sample of days and inputs. Each leaf must hold at least 20 days, so the forest averages rather than memorises.",
    verdict: "Random forests were profitable on daily S&P 500 data before trading costs, but the edge shrank sharply after 2001 as markets became more efficient. Trees can't predict outside the range they were trained on, which is why this page models returns rather than prices.",
    learn: { site: "Wikipedia", url: "https://en.wikipedia.org/wiki/Random_forest" },
    sources: [
      { cite: "Breiman (2001), Random Forests, Machine Learning", url: doi("10.1023/A:1010933404324") },
      KRAUSS,
    ],
  },
  chronos: {
    name: "Chronos-Bolt (pretrained)",
    evidence: "weak",
    read: "A transformer that Amazon pretrained on a large collection of time series, used here without any training on this stock (zero-shot). The tiny version has 9 million parameters and runs on the CPU in about a second.",
    verdict: "It forecasts well across general benchmarks, which are mostly series with trends and seasonal patterns, unlike daily stock returns. In this dashboard's tests its point forecasts were worse than no change on every stock checked, although its ranges were reasonably calibrated.",
    learn: { site: "GitHub", url: "https://github.com/amazon-science/chronos-forecasting" },
    sources: [{ cite: "Ansari et al. (2024), Chronos: Learning the Language of Time Series, Transactions on Machine Learning Research", url: "https://arxiv.org/abs/2403.07815" }],
  },
  garch: {
    name: "GARCH(1,1) range",
    evidence: "strong",
    read: "Volatility clusters: calm days follow calm days and turbulent days follow turbulent ones. GARCH estimates tomorrow's volatility from yesterday's move, yesterday's volatility and the long-run level. The range uses a fat-tailed (Student-t) distribution, because big moves happen more often than a bell curve allows.",
    verdict: "How much a stock will move is far more predictable than which way. In a comparison of 330 volatility models, none clearly beat GARCH(1,1) on exchange rates; on stock returns, models that let falls raise volatility more than rises did somewhat better.",
    learn: { site: "Wikipedia", url: "https://en.wikipedia.org/wiki/Autoregressive_conditional_heteroskedasticity" },
    sources: [
      { cite: "Engle (1982), Autoregressive Conditional Heteroscedasticity with Estimates of the Variance of United Kingdom Inflation, Econometrica", url: doi("10.2307/1912773") },
      { cite: "Bollerslev (1986), Generalized Autoregressive Conditional Heteroskedasticity, Journal of Econometrics", url: doi("10.1016/0304-4076(86)90063-1") },
      { cite: "Hansen & Lunde (2005), A Forecast Comparison of Volatility Models: Does Anything Beat a GARCH(1,1)?, Journal of Applied Econometrics", url: doi("10.1002/jae.800") },
    ],
  },
  returns: {
    name: "Forecasting returns, not prices",
    read: "The models predict tomorrow's percentage change. Predicting the price itself looks accurate because tomorrow's price is close to today's, but a model trained on a trending price fails once the price leaves its training range.",
    verdict: "Regressions on trending series produce good-looking but spurious fits. Forecasting the direction or size of the change, rather than the price level, also proves more useful for trading decisions.",
    sources: [
      { cite: "Granger & Newbold (1974), Spurious Regressions in Econometrics, Journal of Econometrics", url: doi("10.1016/0304-4076(74)90034-7") },
      { cite: "Leung, Daouk & Chen (2000), Forecasting Stock Indices: A Comparison of Classification and Level Estimation Models, International Journal of Forecasting", url: doi("10.1016/S0169-2070(99)00048-5") },
    ],
  },
  walk_forward: {
    name: "Walk-forward testing",
    read: "Each model is trained on the earlier part of the history, then forecasts the following month using only data available at the time. It is then refitted with that month added, and so on through the test window.",
    verdict: "Scoring a model on data it was trained on overstates its accuracy. Testing on later, unseen data is the standard, and even then trying many variants on the same history risks finding one that worked by luck.",
    sources: [
      { cite: "Tashman (2000), Out-of-Sample Tests of Forecasting Accuracy: An Analysis and Review, International Journal of Forecasting", url: doi("10.1016/S0169-2070(00)00065-0") },
      { cite: "Bailey, Borwein, López de Prado & Zhu (2014), Pseudo-Mathematics and Financial Charlatanism: The Effects of Backtest Overfitting on Out-of-Sample Performance, Notices of the AMS", url: doi("10.1090/noti1105") },
    ],
  },
  skill: {
    name: "Skill vs no change (out-of-sample R²)",
    read: "The share of the no-change forecast's squared error that a model removes on the test days. Positive means it helped, zero means no help, and negative means it was worse than doing nothing.",
    verdict: "The standard measure for return forecasts. For daily returns even +1% would matter if it held up, but most published predictors score at or below zero out of sample.",
    sources: [CAMPBELL_THOMPSON, WELCH_GOYAL],
  },
  significance: {
    name: "Significance (Diebold–Mariano test)",
    read: "Checks whether a model's lower error could be luck. Because several models are tested at once, the bar is divided by the number of models (a Bonferroni correction), so one doesn't pass by chance.",
    verdict: "The standard test for comparing two forecasts' accuracy, used here with Harvey, Leybourne & Newbold's small-sample correction.",
    sources: [{ cite: "Diebold & Mariano (1995), Comparing Predictive Accuracy, Journal of Business & Economic Statistics", url: doi("10.1080/07350015.1995.10524599") }],
  },
  direction: {
    name: "Direction accuracy",
    read: "How often a model called up or down correctly, with a 95% confidence interval. If the interval includes 50%, it can't be told apart from a coin flip. Compare it with the share of up days too, which a forecast of 'always up' would score.",
    verdict: "A simple, intuitive check. On roughly 100–150 test days, the interval is about ±8 points wide, so direction accuracies between about 42% and 58% are all consistent with chance.",
    sources: [{ cite: "Wilson (1927), Probable Inference, the Law of Succession, and Statistical Inference, Journal of the American Statistical Association", url: doi("10.1080/01621459.1927.10502953") }],
  },
  coverage: {
    name: "Range coverage",
    read: "How often past 80% and 95% ranges held the actual next close. A well-calibrated range holds about 80% and 95% of the time; the test asks whether any gap could be chance.",
    verdict: "Standard backtests for value-at-risk models and interval forecasts.",
    sources: [
      { cite: "Kupiec (1995), Techniques for Verifying the Accuracy of Risk Measurement Models, Journal of Derivatives", url: doi("10.3905/jod.1995.407942") },
      { cite: "Christoffersen (1998), Evaluating Interval Forecasts, International Economic Review", url: doi("10.2307/2527341") },
    ],
  },
} satisfies Record<string, EvidenceInfo>;

export type ForecastKey = keyof typeof FORECAST;

export const MODEL_EVIDENCE: Record<string, ForecastKey> = {
  "Ridge regression": "ridge",
  "Gradient boosting": "gradient_boosting",
  "Random forest": "random_forest",
  "Chronos-Bolt": "chronos",
};

export const GUIDE_SECTIONS: { title: string; keys: ForecastKey[] }[] = [
  { title: "The models", keys: ["no_change", "ridge", "gradient_boosting", "random_forest", "chronos"] },
  { title: "The range", keys: ["garch", "coverage"] },
  { title: "How they are tested", keys: ["returns", "walk_forward", "skill", "significance", "direction"] },
];
