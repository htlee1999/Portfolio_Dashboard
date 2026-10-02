// What each fundamental measure means, how well research supports it as a signal of future
// returns, and where to read more. Ratings describe the measure as the dashboard uses it.

import { doi, type EvidenceInfo, type Source } from "./evidence";

const wiki = (page: string) => ({ site: "Wikipedia", url: `https://en.wikipedia.org/wiki/${page}` });

const BASU: Source = {
  cite: "Basu (1977), Investment Performance of Common Stocks in Relation to Their Price-Earnings Ratios, Journal of Finance",
  url: doi("10.1111/j.1540-6261.1977.tb01979.x"),
};
const FF_1992: Source = {
  cite: "Fama & French (1992), The Cross-Section of Expected Stock Returns, Journal of Finance",
  url: doi("10.1111/j.1540-6261.1992.tb04398.x"),
};
const LSV: Source = {
  cite: "Lakonishok, Shleifer & Vishny (1994), Contrarian Investment, Extrapolation, and Risk, Journal of Finance",
  url: doi("10.1111/j.1540-6261.1994.tb04772.x"),
};
const FF_VALUE: Source = {
  cite: "Fama & French (2020), The Value Premium, Review of Asset Pricing Studies",
  url: doi("10.1093/rapstu/raaa021"),
};
const FF_5: Source = {
  cite: "Fama & French (2015), A Five-Factor Asset Pricing Model, Journal of Financial Economics",
  url: doi("10.1016/j.jfineco.2014.10.010"),
};
const HXZ: Source = {
  cite: "Hou, Xue & Zhang (2015), Digesting Anomalies: An Investment Approach, Review of Financial Studies",
  url: doi("10.1093/rfs/hhu068"),
};
const FF_DISSECT: Source = {
  cite: "Fama & French (2008), Dissecting Anomalies, Journal of Finance",
  url: doi("10.1111/j.1540-6261.2008.01371.x"),
};
const ALTMAN: Source = {
  cite: "Altman (1968), Financial Ratios, Discriminant Analysis and the Prediction of Corporate Bankruptcy, Journal of Finance",
  url: doi("10.1111/j.1540-6261.1968.tb00843.x"),
};
const DAMODARAN: Source = {
  cite: "Damodaran, Ratings, Interest Coverage Ratios and Default Spread (NYU Stern data)",
  url: "https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/ratings.html",
};

export const FUNDAMENTALS = {
  pe: {
    name: "P/E (price / earnings)",
    evidence: "mixed",
    read: "What investors pay for each unit of last year's profit. Lower means cheaper. It can't be used for loss-making companies, and it is distorted when profits are temporarily high or low.",
    verdict: "Low-P/E stocks beat high-P/E stocks for decades in the US and abroad, partly because investors extrapolate past growth too far. The value premium was weak from about 2007 to 2020, and one multiple says little without comparing to peers or the company's own history.",
    learn: wiki("Price–earnings_ratio"),
    sources: [BASU, LSV, FF_VALUE],
  },
  forward: {
    name: "Forward P/E & PEG",
    evidence: "weak",
    read: "Forward P/E uses analysts' profit forecast for the next year; PEG divides P/E by forecast growth. Both depend on analysts' estimates rather than reported results.",
    verdict: "Analyst growth forecasts are too optimistic, and the stocks they expect to grow fastest have underperformed. PEG has little academic testing behind it.",
    learn: wiki("PEG_ratio"),
    sources: [
      { cite: "La Porta (1996), Expectations and the Cross-Section of Stock Returns, Journal of Finance", url: doi("10.1111/j.1540-6261.1996.tb05223.x") },
    ],
  },
  pb: {
    name: "Price / book",
    evidence: "mixed",
    read: "Market value against accounting net assets. The main valuation yardstick for banks, insurers and REITs, where book value is close to what the assets are worth.",
    verdict: "Book-to-market was the original value factor, strong in US and international data before 2007 and weak since. Book value understates companies built on brands, software and research, which are expensed rather than recorded as assets.",
    sources: [FF_1992, FF_VALUE],
  },
  sales: {
    name: "Price / sales & EV / revenue",
    evidence: "mixed",
    read: "Value against revenue. Works for loss-making companies, but ignores margins: a low ratio may simply reflect a low-margin business.",
    verdict: "Sales-to-price has predicted returns about as well as book-to-market in some tests, but margins differ so much between industries that it is only useful within one.",
    sources: [
      { cite: "Barbee, Mukherji & Raines (1996), Do Sales–Price and Debt–Equity Explain Stock Returns Better than Book–Market and Firm Size?, Financial Analysts Journal", url: doi("10.2469/faj.v52.n2.1980") },
    ],
  },
  ev_ebitda: {
    name: "EV / EBITDA",
    evidence: "mixed",
    read: "Enterprise value (market cap plus net debt) against cash operating profit. Unlike P/E it isn't affected by how a company is financed, so it compares companies with different debt levels.",
    verdict: "In the US it beat book-to-market and P/E as a value signal. It shares the value premium's weak run since 2007.",
    learn: wiki("Enterprise_value"),
    sources: [
      { cite: "Loughran & Wellman (2011), New Evidence on the Relation between the Enterprise Multiple and Average Stock Returns, Journal of Financial and Quantitative Analysis", url: doi("10.1017/S0022109011000445") },
    ],
  },
  fcf_yield: {
    name: "Free-cash-flow yield",
    evidence: "mixed",
    read: "Free cash flow (operating cash flow minus capital spending) against market cap. It is the cash available to pay dividends, buy back shares or repay debt, and is harder to inflate with accounting choices than earnings.",
    verdict: "Cash-flow-to-price was one of the stronger value measures in historical tests. Like other value measures it has been weaker since 2007, and capital spending is lumpy, so one year can mislead.",
    sources: [LSV, FF_VALUE],
  },
  roe: {
    name: "Return on equity",
    evidence: "mixed",
    read: "Profit as a share of shareholders' equity. The key profitability measure for banks. For other companies, borrowing and buybacks shrink equity and inflate it, so compare with return on assets.",
    verdict: "Highly profitable companies have earned higher returns, and ROE is part of leading academic models. But high ROE produced by leverage or buybacks carries no such signal.",
    sources: [HXZ, FF_5],
  },
  margins: {
    name: "Return on assets & margins",
    evidence: "mixed",
    read: "Return on assets is profit as a share of everything the company owns; margins are profit as a share of revenue. Margins are only comparable within an industry.",
    verdict: "Operating profitability is one of the five Fama–French factors. Net margin and ROA mix in one-off items, interest and tax, which makes them noisier than gross or operating profitability.",
    sources: [FF_5],
  },
  gross_profitability: {
    name: "Gross profit / assets",
    evidence: "strong",
    read: "Gross profit (revenue minus the direct cost of goods) as a share of total assets. It measures how productive the assets are before spending on growth, such as advertising and research, which accounting treats as expenses.",
    verdict: "Predicted returns about as strongly as book-to-market, and works well alongside value: cheap and profitable beats either alone. One of the most robust quality measures.",
    sources: [{ cite: "Novy-Marx (2013), The Other Side of Value: The Gross Profitability Premium, Journal of Financial Economics", url: doi("10.1016/j.jfineco.2013.01.003") }],
  },
  liquidity: {
    name: "Current & quick ratio",
    evidence: "risk",
    read: "Short-term assets against bills due within a year. Below 1 means current liabilities exceed current assets. That is risky for a struggling company but normal for strong retailers and Apple, which are paid before they pay suppliers.",
    verdict: "Not a return signal. Working capital is one input to the Altman Z-score, which captures short-term risk more completely.",
    sources: [ALTMAN],
  },
  leverage: {
    name: "Debt / equity",
    evidence: "risk",
    read: "Debt against shareholders' equity. Higher means more financial risk: profits are more sensitive to downturns and to interest rates.",
    verdict: "A risk measure. Highly levered stocks have, if anything, earned higher returns, as compensation for that risk. Watch it together with interest coverage.",
    sources: [{ cite: "Bhandari (1988), Debt/Equity Ratio and Expected Common Stock Returns, Journal of Finance", url: doi("10.1111/j.1540-6261.1988.tb03952.x") }],
  },
  beta: {
    name: "Beta",
    evidence: "risk",
    read: "How much the stock has moved with the market: 1.5 means it has typically moved 1.5% for each 1% market move.",
    verdict: "Measures market risk, but high-beta stocks have not earned the extra return theory predicts. Low-beta stocks have done better on a risk-adjusted basis.",
    learn: wiki("Beta_(finance)"),
    sources: [{ cite: "Frazzini & Pedersen (2014), Betting Against Beta, Journal of Financial Economics", url: doi("10.1016/j.jfineco.2013.10.005") }],
  },
  growth: {
    name: "Revenue & earnings growth",
    evidence: "weak",
    read: "How fast sales and profit grew. The quarterly figures compare the latest quarter with the same quarter a year earlier; the annual figure compares the last two fiscal years.",
    verdict: "Past growth barely predicts future growth beyond chance, and stocks with strong past growth have tended to underperform because investors extrapolate it.",
    sources: [
      { cite: "Chan, Karceski & Lakonishok (2003), The Level and Persistence of Growth Rates, Journal of Finance", url: doi("10.1111/1540-6261.00540") },
      LSV,
    ],
  },
  analysts: {
    name: "Analyst targets & ratings",
    evidence: "weak",
    read: "The average 12-month price target and buy/hold/sell consensus from brokers' analysts.",
    verdict: "Price targets are poor forecasts and are not met far more often than their spread suggests. Upgrades and downgrades move prices, but the level of the consensus carries little information once trading costs are counted.",
    sources: [
      { cite: "Bradshaw, Brown & Huang (2013), Do Sell-Side Analysts Exhibit Differential Target Price Forecasting Ability?, Review of Accounting Studies", url: doi("10.1007/s11142-012-9216-5") },
      { cite: "Barber, Lehavy, McNichols & Trueman (2001), Can Investors Profit from the Prophets?, Journal of Finance", url: doi("10.1111/0022-1082.00336") },
      { cite: "Womack (1996), Do Brokerage Analysts' Recommendations Have Investment Value?, Journal of Finance", url: doi("10.1111/j.1540-6261.1996.tb05205.x") },
    ],
  },
  piotroski: {
    name: "Piotroski F-score",
    evidence: "strong",
    read: "Nine pass/fail tests on profitability, funding and efficiency, comparing the latest year with the one before. 8–9 means the business is strengthening on most fronts; 0–2 means weakening.",
    verdict: "Among cheap stocks, high scorers beat low scorers by a wide margin, mainly by avoiding companies about to deteriorate. The effect is strongest in smaller, less followed companies and weaker in large caps.",
    learn: wiki("Piotroski_F-score"),
    sources: [{ cite: "Piotroski (2000), Value Investing: The Use of Historical Financial Statement Information to Separate Winners from Losers, Journal of Accounting Research", url: doi("10.2307/2672906") }],
  },
  accruals: {
    name: "Accruals",
    evidence: "mixed",
    read: "Profit not yet received as cash (net income minus operating cash flow), scaled by assets. High accruals mean earnings depend on accounting estimates, such as unpaid receivables or inventory build-up, that often reverse.",
    verdict: "Companies with high accruals underperformed for decades after Sloan's study, but the effect largely faded after the early 2000s as investors caught on. Still a useful earnings-quality check.",
    sources: [
      { cite: "Sloan (1996), Do Stock Prices Fully Reflect Information in Accruals and Cash Flows about Future Earnings?, The Accounting Review", url: doi("10.2308/tar-9608042309") },
      { cite: "Green, Hand & Soliman (2011), Going, Going, Gone? The Apparent Demise of the Accruals Anomaly, Management Science", url: doi("10.1287/mnsc.1110.1320") },
    ],
  },
  asset_growth: {
    name: "Asset growth",
    evidence: "mixed",
    read: "How fast total assets grew last year, through spending, acquisitions or raising money. Fast-growing balance sheets often mean empire-building or expensive acquisitions.",
    verdict: "Fast asset growers have underperformed slow growers, and investment is a factor in the leading academic models. The effect is much stronger in small stocks than in large ones.",
    sources: [
      { cite: "Cooper, Gulen & Schill (2008), Asset Growth and the Cross-Section of Stock Returns, Journal of Finance", url: doi("10.1111/j.1540-6261.2008.01370.x") },
      FF_DISSECT,
      FF_5,
    ],
  },
  share_change: {
    name: "Share issuance & buybacks",
    evidence: "strong",
    read: "The change in shares outstanding over the last fiscal year. Falling means buybacks; rising means new shares issued (for funding, acquisitions or employee pay), which dilutes existing holders.",
    verdict: "Companies that issue shares underperform and those that buy back outperform, across company sizes and countries. One of the most reliable signals in the research.",
    sources: [
      { cite: "Pontiff & Woodgate (2008), Share Issuance and Cross-sectional Returns, Journal of Finance", url: doi("10.1111/j.1540-6261.2008.01335.x") },
      { cite: "Daniel & Titman (2006), Market Reactions to Tangible and Intangible Information, Journal of Finance", url: doi("10.1111/j.1540-6261.2006.00884.x") },
      { cite: "Ikenberry, Lakonishok & Vermaelen (1995), Market Underreaction to Open Market Share Repurchases, Journal of Financial Economics", url: doi("10.1016/0304-405X(95)00826-Z") },
      FF_DISSECT,
    ],
  },
  altman_z: {
    name: "Altman Z″-score",
    evidence: "risk",
    read: "Bankruptcy-risk score from working capital, retained earnings, operating profit and equity against liabilities. This version (Z″) is for non-manufacturers. Above 2.6 is safe; below 1.1 is the distress zone. Large buybacks can push it down for healthy companies.",
    verdict: "A well-tested predictor of failure. Distressed stocks have also earned unusually low returns, so distress is a warning about returns as well as about risk.",
    learn: wiki("Altman_Z-score"),
    sources: [
      ALTMAN,
      { cite: "Dichev (1998), Is the Risk of Bankruptcy a Systematic Risk?, Journal of Finance", url: doi("10.1111/0022-1082.00046") },
      { cite: "Campbell, Hilscher & Szilagyi (2008), In Search of Distress Risk, Journal of Finance", url: doi("10.1111/j.1540-6261.2008.01416.x") },
    ],
  },
  interest_coverage: {
    name: "Interest coverage",
    evidence: "risk",
    read: "Operating profit divided by interest expense: how many times over the company can pay its interest bill. Below 1.5× is strained. In Damodaran's mapping for large companies, about 2.5× matches the lowest investment-grade rating (BBB) and 8.5× or more matches AAA.",
    verdict: "Not a return signal. A core input to credit ratings and borrowing costs.",
    sources: [DAMODARAN],
  },
  net_debt_ebitda: {
    name: "Net debt / EBITDA",
    evidence: "risk",
    read: "Debt minus cash, against a year's cash operating profit: roughly how many years it would take to repay. Negative means more cash than debt. Lenders usually treat above 3× as high.",
    verdict: "Not a return signal. The standard leverage measure in loan agreements and credit analysis.",
    sources: [DAMODARAN],
  },
  surprise: {
    name: "Earnings surprises",
    evidence: "strong",
    read: "Reported earnings per share against analysts' estimate for the same quarter. Repeated beats suggest the business is doing better than expected.",
    verdict: "Prices keep drifting in the direction of a surprise for weeks afterwards (post-earnings-announcement drift), one of the oldest anomalies. Recent work finds it has largely disappeared in large, heavily traded US stocks, while it persists in smaller ones.",
    learn: wiki("Post–earnings-announcement_drift"),
    sources: [
      { cite: "Ball & Brown (1968), An Empirical Evaluation of Accounting Income Numbers, Journal of Accounting Research", url: doi("10.2307/2490232") },
      { cite: "Bernard & Thomas (1989), Post-Earnings-Announcement Drift: Delayed Price Response or Risk Premium?, Journal of Accounting Research", url: doi("10.2307/2491062") },
      { cite: "Martineau (2022), Rest in Peace Post-Earnings Announcement Drift, Critical Finance Review", url: doi("10.1561/104.00000122") },
    ],
  },
  revisions: {
    name: "Estimate revisions",
    evidence: "strong",
    read: "How analysts' profit forecasts have changed over the last 30 and 90 days, and how many raised or cut them.",
    verdict: "Rising estimates have predicted returns over the following months, separately from price momentum, because analysts adjust gradually and prices follow.",
    sources: [{ cite: "Chan, Jegadeesh & Lakonishok (1996), Momentum Strategies, Journal of Finance", url: doi("10.1111/j.1540-6261.1996.tb05222.x") }],
  },
} satisfies Record<string, EvidenceInfo>;

export type FundamentalKey = keyof typeof FUNDAMENTALS;

/** Evidence entry for each ratio or metric key sent by the backend. */
export const EVIDENCE_FOR: Record<string, FundamentalKey> = {
  trailingPE: "pe",
  forwardPE: "forward",
  pegRatio: "forward",
  priceToBook: "pb",
  priceToSalesTrailing12Months: "sales",
  enterpriseToRevenue: "sales",
  enterpriseToEbitda: "ev_ebitda",
  fcfYield: "fcf_yield",
  returnOnEquity: "roe",
  returnOnAssets: "margins",
  grossMargins: "margins",
  operatingMargins: "margins",
  profitMargins: "margins",
  currentRatio: "liquidity",
  quickRatio: "liquidity",
  debtToEquity: "leverage",
  beta: "beta",
  annualRevenueGrowth: "growth",
  revenueGrowth: "growth",
  earningsGrowth: "growth",
  gross_profitability: "gross_profitability",
  accruals: "accruals",
  asset_growth: "asset_growth",
  share_change: "share_change",
  altman_z: "altman_z",
  interest_coverage: "interest_coverage",
  net_debt_ebitda: "net_debt_ebitda",
};

export const GUIDE_SECTIONS: { title: string; keys: FundamentalKey[] }[] = [
  { title: "Valuation", keys: ["pe", "forward", "pb", "sales", "ev_ebitda", "fcf_yield"] },
  { title: "Profitability & quality", keys: ["gross_profitability", "piotroski", "roe", "margins", "accruals", "asset_growth", "share_change"] },
  { title: "Earnings & analysts", keys: ["revisions", "surprise", "growth", "analysts"] },
  { title: "Risk", keys: ["altman_z", "interest_coverage", "net_debt_ebitda", "leverage", "liquidity", "beta"] },
];
