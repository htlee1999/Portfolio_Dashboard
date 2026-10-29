/**
 * "How to read this page" walkthroughs, one per page. Each step names a part of the page as it
 * appears on screen, says what it shows, and how to interpret it. Keep these in step with the
 * page and with documentations/FEATURES.md when either changes.
 */

export type GuideStep = {
  title: string;
  /** What you're looking at. */
  body: string;
  /** How to interpret it. */
  meaning?: string;
  /** A common misreading or limit. */
  caution?: string;
};

export type Guide = { intro: string; steps: GuideStep[] };

export const GUIDES = {
  overview: {
    intro: "A snapshot of what your portfolio is worth today and how each position is doing, all in your base currency.",
    steps: [
      {
        title: "Portfolio value",
        body: "The big number is what all your holdings are worth at the latest prices. Under it is your all-time gain or loss versus what you paid, in money and as a percentage.",
        meaning: "The gain is unrealized, on paper: you'd only lock it in by selling. Green means today's value is above your cost.",
        caution: "Totals are converted to your base currency (Settings) at today's exchange rate, so currency moves change the total even when prices don't.",
      },
      {
        title: "Invested, Positions, Best and Largest",
        body: "Invested is the total you paid. Positions counts the different stocks you hold. Best is the position with the highest percentage return. Largest is your biggest position and its share of the portfolio.",
        meaning: "If Largest is well above 20%, a lot of your result rides on one stock: that's concentration risk.",
      },
      {
        title: "Allocation",
        body: "The donut shows how your money is split by current value. The 7 largest positions get their own slice and the rest are grouped as Other.",
        meaning: "Look for one slice that dominates, or many slices in the same industry: both mean less diversification than the count suggests.",
      },
      {
        title: "Gain by position",
        body: "Bars show each position's unrealized gain or loss in your base currency, green up and red down.",
        meaning: "This shows where your money was made or lost. A small percentage gain on a large position can outweigh a big percentage on a small one.",
      },
      {
        title: "Positions table",
        body: "One row per stock. Several purchases of the same stock are combined, with an average cost per share, current price, value, weight and return.",
        meaning: "Return % is in the stock's own currency, so it shows how the stock did. The gain in your base currency also includes exchange-rate moves.",
        caution: "If a price can't be fetched, that stock is left out of the totals and named in a warning at the top. Use the refresh button to try again.",
      },
    ],
  },

  holdings: {
    intro: "Where you record what you own. Every other page reads from this list.",
    steps: [
      {
        title: "One row per purchase",
        body: "Each row is a lot: one purchase with its symbol, number of shares, price paid, date and currency. Buying the same stock twice gives two rows.",
        meaning: "Keeping lots separate lets the app work out your average cost and when you bought. Overview combines them per stock.",
      },
      {
        title: "Adding a holding",
        body: "Enter the symbol, shares, price per share, purchase date and currency, then Add Holding. Common names are converted to the ticker for you (TSMC becomes TSM, BRK.B becomes BRK-B).",
        caution: "Use the price in the stock's own trading currency, for example SGD for a Singapore listing, and pick that currency.",
      },
      {
        title: "Importing and exporting",
        body: "Import a CSV to add many lots at once (download the CSV Template for the columns). Export CSV downloads your lots. Create Backup saves a snapshot on the server.",
        caution: "Importing adds rows; it doesn't replace what's there. Delete All asks before removing everything, and a backup first is wise.",
      },
    ],
  },

  performance: {
    intro: "What your money actually did, from every purchase, sale and dividend; then how your current mix of holdings would have performed against the S&P 500.",
    steps: [
      {
        title: "Actual returns",
        body: "Rebuilt day by day from your lots, the sales you record on Holdings and the dividends your shares were paid. Money-weighted (IRR) is the yearly rate your own deposits and withdrawals earned. Time-weighted chains each day's return, so the timing and size of deposits don't count.",
        meaning: "Time-weighted judges the holdings; money-weighted judges you, timing included. If money-weighted is well below time-weighted, you tended to add money before weak stretches.",
        caution: "Dividends are before withholding tax. Lots are taken as entered, so enter them in today's share terms after a split.",
      },
      {
        title: "Vs the same trades in SPY",
        body: "Every purchase also buys SPY with the same money on the same day, and every sale sells the same amount of it. The figure is your holdings plus dividends received, minus that SPY account.",
        meaning: "Positive means your picks and timing beat simply buying the index whenever you invested. This is the fairest single test of whether stock-picking is paying.",
        caution: "One period, a handful of stocks: a large gap can come from one big winner. Look at Risk to see how concentrated that is.",
      },
      {
        title: "Dividends and realized gains",
        body: "Dividends by holding and year, and each sale's gain against the lots it came from (oldest first), in the lot's currency and in your base currency at the exchange rates of the purchase and sale days.",
      },
      {
        title: "Pick a period",
        body: "Choose a range from 1 month to 5 years for the Current allocation section below Actual returns.",
      },
      {
        title: "Growth of 100",
        body: "Each line starts at 100. Portfolio is your holdings weighted by today's values; S&P 500 is the benchmark. You can pin individual holdings to compare.",
        meaning: "A line at 120 has gained 20% since the start. If Portfolio ends above the S&P 500, your current mix beat the market over that period.",
        caution: "This is a back-test of today's allocation, not your actual history: it ignores when you bought and any trades.",
      },
      {
        title: "Portfolio, S&P 500 and Relative",
        body: "The figures above the chart are each line's return over the period. Relative is your portfolio's return minus the S&P 500's.",
        meaning: "Positive Relative means your mix beat the index; negative means you'd have done better in an index fund over that period.",
      },
      {
        title: "Sectors",
        body: "Your money split by industry, using each company's sector. Funds show as ETF / Fund.",
        meaning: "Heavy weight in one sector means one industry shock can move the whole portfolio.",
      },
      {
        title: "Risk",
        body: "Volatility per holding: how much its daily returns swing, annualized, over the last 12 months whatever period you picked. Also its average daily return.",
        meaning: "Around 15–20% is typical for a large, steady stock; 40% or more is a bumpy ride. Higher volatility means larger swings both ways, not necessarily higher returns.",
      },
    ],
  },

  technical: {
    intro: "Price-based indicators for one stock: what the trend and momentum look like now, and whether those signals have actually worked on this stock.",
    steps: [
      {
        title: "Choose a stock and period",
        body: "Pick a symbol and a period. Indicators are calculated on longer history behind the scenes, so long averages like the 200-day are always defined.",
      },
      {
        title: "Price chart",
        body: "The price with an overlay: Bollinger Bands (a channel two standard deviations around the 20-day average), or the 20, 50 and 200-day moving averages.",
        meaning: "Price above its rising averages is an uptrend; below falling averages a downtrend. A close outside the Bollinger Bands is an unusually large move for this stock.",
      },
      {
        title: "Short-term momentum and trend",
        body: "Cards for RSI, MACD, Bollinger position, the 20/50-day trend and On-Balance Volume, each with its current reading and label.",
        meaning: "RSI above 70 is called overbought and below 30 oversold. MACD above its signal line is bullish momentum. Rising OBV means volume is flowing in on up days.",
        caution: "Overbought doesn't mean about to fall: strong stocks can stay above 70 for weeks. Treat these as descriptions of recent moves, not forecasts.",
      },
      {
        title: "Long-term trend, strength and volatility",
        body: "12-1 month momentum, distance from the 52-week high, the 200-day average and golden/death cross, ADX trend strength, and ATR (the average daily range).",
        meaning: "12-1 momentum is the best-researched of these: stocks that rose over the past year (skipping the latest month) have tended to keep outperforming. ADX of 25 or more means a strong trend; below 20 the stock is drifting sideways.",
      },
      {
        title: "Signal track record",
        body: "Tests 13 signals on this stock over 5 years: after each time one fired, how often the price moved the expected way within 5, 20 or 60 days, against the stock's normal rate.",
        meaning: "Worked means the signal beat the stock's normal hit rate by a statistically meaningful margin; Failed means it did worse. Too few means it hasn't fired enough times to judge.",
        caution: "Most signals usually read Too few or show no edge. That's the honest finding for most stocks, not a bug.",
      },
      {
        title: "Indicator settings and evidence",
        body: "Sliders change the RSI, MACD and Bollinger periods; the charts update as you drag. Indicator guide & evidence rates the research behind each indicator, with sources.",
        caution: "Tuning settings until a signal looks good on past data is curve-fitting. It usually stops working on new data.",
      },
    ],
  },

  fundamentals: {
    intro: "The business behind the share price: valuation, profitability, balance-sheet health and what analysts expect, each read against the company's own history.",
    steps: [
      {
        title: "Headline",
        body: "Price and 52-week range, market cap, P/E and dividend yield.",
        meaning: "P/E is the price paid per dollar of yearly profit: 15 means 15 years of current earnings. Loss-making companies have no meaningful P/E.",
      },
      {
        title: "Ratios",
        body: "Grouped as valuation, profitability, liquidity, leverage and growth, from the last 12 months.",
        meaning: "Lower valuation multiples are cheaper; higher margins and ROE mean a more profitable business; current ratio above 1 means short-term assets cover short-term debts. Compare within an industry: a bank's ratios look nothing like a software company's.",
        caution: "n/m means not meaningful, usually because profit or equity is negative. Banks, insurers and REITs skip ratios that don't apply to them.",
      },
      {
        title: "Against its own history",
        body: "Each measure today against the company's last 4 fiscal year-ends, labelled cheaper or pricier (valuation) and better or worse (everything else) when it's 10% or more from its usual level.",
        meaning: "This answers \"is it cheap for this company?\" rather than against a fixed rule. Pricier than usual plus worse margins is a warning; cheaper with stable quality may be an opportunity.",
      },
      {
        title: "Quality",
        body: "The Piotroski F-score (9 pass/fail tests of profitability, funding and efficiency), gross profit to assets, accruals, asset growth and changes in share count.",
        meaning: "An F-score of 8–9 is strong and 0–2 weak. Negative accruals mean profits are backed by cash. A falling share count means buybacks; a rising one, dilution.",
      },
      {
        title: "Financial risk",
        body: "Altman Z″ (bankruptcy risk), interest coverage and net debt to EBITDA.",
        meaning: "Z″ above 2.6 is safe and below 1.1 distressed. Interest cover under 1.5× is strained. Net debt over 3× EBITDA is high; negative means more cash than debt.",
      },
      {
        title: "Earnings and Analyst view",
        body: "Reported earnings against estimates for the last 4 quarters, recent estimate revisions, the next report date, and the analyst consensus with low, mean and high price targets.",
        meaning: "Rising estimates and repeated beats are a positive trend. Earnings dates often bring big moves.",
        caution: "Analyst targets are usually optimistic and change after the price moves; treat them as sentiment, not a valuation.",
      },
      {
        title: "Statements",
        body: "Up to 5 years of key income statement, balance sheet and cash flow lines, with yearly growth and compound annual growth.",
        meaning: "Check that revenue and operating cash flow grow together. Profits rising while cash flow falls deserves a closer look.",
      },
    ],
  },

  forecast: {
    intro: "Machine-learning models try to predict tomorrow's return, and are tested honestly against simply predicting no change. Also a well-calibrated range for the next close.",
    steps: [
      {
        title: "Train Models",
        body: "Choose the training period and test window, then Train Models. Each model is refitted month by month on past data only, and forecasts the following days it hasn't seen.",
        meaning: "This walk-forward testing mimics real use: no model gets to peek at the future.",
      },
      {
        title: "Models against no change",
        body: "Each model's skill: how much of the no-change forecast's error it removed (positive is better), a p-value, and how often it got the direction right next to the share of up days.",
        meaning: "A model only counts as useful if it's labelled Beats no change, which needs a p-value below the corrected threshold. Direction right is only good if it beats the up-day share, which an always-up guess would score.",
        caution: "Expect No model beat the no-change forecast. Daily stock returns are close to unpredictable, and in testing no model beat it on any stock checked.",
      },
      {
        title: "Predicted vs actual daily return",
        body: "Each model's forecasts against what actually happened over the test window.",
        meaning: "Points scattered with no slope mean the forecasts carry little information, even if the model looks clever.",
      },
      {
        title: "Next-session range",
        body: "A GARCH model estimates how far the next close is likely to move: an 80% and a 95% range around today's price.",
        meaning: "This forecasts risk, not direction, and it's the part that works: in testing about 80% of closes landed in the 80% range. Use it to size positions or set stops.",
      },
      {
        title: "Range backtest",
        body: "How often the past ranges actually contained the next close, with a coverage test.",
        meaning: "Close to 80% and 95% means the ranges are trustworthy for this stock. Well below means it moves more than the model expects.",
      },
      {
        title: "Method & evidence",
        body: "What the random forest leans on, and the research and sources behind every modelling choice.",
      },
    ],
  },

  sentiment: {
    intro: "Recent news headlines about the company, scored for tone by a model trained on financial news, with an honest margin of error.",
    steps: [
      {
        title: "Run an analysis",
        body: "Pick the window (7 or 30 days) and news source, then Analyze Sentiment. Each source uses one SERPapi search from your monthly allowance; Check Quota shows what's left.",
      },
      {
        title: "Net tone",
        body: "The average headline score from −1 (negative) to +1 (positive), with a 95% confidence interval.",
        meaning: "It's labelled Positive or Negative only when the whole interval is on one side of zero; otherwise it's no clear tilt. Fewer than 5 headlines is too few to judge.",
        caution: "Tone describes coverage. Research finds it predicts returns only weakly and briefly, so treat it as context, not a signal.",
      },
      {
        title: "Price change and price-move headlines",
        body: "The stock's move over the same window, and the share of headlines that just report a price move (\"shares slide 3%\").",
        meaning: "If many headlines are price reports, the tone mostly restates a move that already happened.",
      },
      {
        title: "Which headlines count",
        body: "Every headline is listed, but only recent, non-duplicate, firm-specific ones that aren't routine filings are scored. The list shows why any were left out.",
      },
      {
        title: "Tone by day and the headlines",
        body: "The average score per day, and each headline with its score and label. Sort them by Recent, Positive or Negative.",
        caution: "The model misreads about 1 headline in 4, often valuation language. Read the strongest ones yourself before relying on them.",
      },
    ],
  },

  assessment: {
    intro: "Gathers the technical, fundamental, forecast and news evidence for one stock and asks the AI for a BUY, HOLD or SELL call with its reasoning, then optionally checks that call.",
    steps: [
      {
        title: "Run Analysis",
        body: "Pick a stock and lookback, optionally include news, then Run Analysis. It collects every input and shows your position in the stock if you hold it.",
      },
      {
        title: "Signal profile",
        body: "A radar of 0–100 scores for valuation, growth, profitability, momentum, balance sheet, quality, earnings, sentiment and forecast. 50 is neutral or unknown.",
        meaning: "Big points far out are strengths; dips toward the centre are weaknesses. It's a rough visual summary without industry comparison.",
      },
      {
        title: "Generate Assessment",
        body: "The AI returns a recommendation, confidence out of 10, time horizon, price target, step-by-step reasoning, strengths, risks and advice on your position.",
        meaning: "BUY means it expects the stock to beat the S&P 500 by more than 1 point over the horizon, SELL to lag it, HOLD neither. Confidence 7 means a 70% chance the call is right.",
        caution: "AI output can be wrong and isn't financial advice. Check its reasoning against the numbers on the other research pages.",
      },
      {
        title: "Get a second look (Evaluate)",
        body: "An optional review that checks the call's claims against the computed facts, builds the case against it, and lists what would show it's wrong.",
        meaning: "The verdict is stands, weakened or contradicted. Confidence can only go down, never up, and the call itself never changes.",
      },
      {
        title: "Save and compare",
        body: "Every assessment is saved to your Track Record, where it's later scored against the S&P 500. Download PDF exports the report.",
        meaning: "One call tells you little. The Track Record shows whether these calls have actually beaten the market over time.",
      },
    ],
  },

  trackRecord: {
    intro: "Checks every past AI recommendation against what actually happened, measured against the S&P 500 so a rising market doesn't count as skill.",
    steps: [
      {
        title: "Score at",
        body: "Choose when calls are judged: 1 week, 1 month, 3 months, 6 months, 1 year, or each call's own stated horizon. Filters narrow it by symbol, source, model or prompt version.",
        meaning: "Judging every call over the same length of time keeps the comparison fair. Calls younger than the checkpoint are Pending.",
      },
      {
        title: "Win rate and Avg vs S&P 500",
        body: "Win rate is correct calls ÷ (correct + wrong), with a 95% range. Avg vs S&P 500 is how far the calls beat or trailed the index on average.",
        meaning: "A BUY is correct if the stock beat the S&P 500 by more than 1 point; a SELL if it lagged by more. A win rate whose range sits above 50% is evidence of skill.",
        caution: "Below 30 scored calls a banner warns the numbers are anecdotes. The 95% range will be very wide.",
      },
      {
        title: "Against simple rules",
        body: "The AI's calls compared with simple rules on the same stocks and dates: always BUY, 12-1 momentum, the analyst consensus and the app's radar scores.",
        meaning: "This is the key test. If the AI doesn't beat these rules, it isn't adding accuracy.",
      },
      {
        title: "What if you followed every BUY?",
        body: "$1,000 put into each BUY at the first close after the call and held to today, against the same money in the S&P 500 on the same days.",
        meaning: "This turns the calls into money. Ending above the S&P 500 line means following the BUYs would have beaten the index.",
      },
      {
        title: "Sold or held?",
        body: "For stocks you owned when a call was made: selling at that point versus holding to today.",
        meaning: "Shows whether acting on the calls would have helped your actual holdings.",
      },
      {
        title: "Model comparison and second look",
        body: "Gemini vs local model compares the two on identical inputs. Is the second look right? checks whether weakened or contradicted calls really did worse.",
        meaning: "In the head-to-head, both models saw the same data, so differences are the model's. If the second look works, contradicted calls should have lower win rates.",
      },
      {
        title: "Signals and scheduled runs",
        body: "Every call is listed; expand one for its reasoning, checkpoints and target. The Scheduled runs card shows the twice-weekly automatic assessments.",
        caution: "Repeated calls on one stock move together, so check By symbol: one stock can carry the whole record.",
      },
    ],
  },

  risk: {
    intro: "How your holdings move together, which ones drive the swings, how much the portfolio could lose, and what a trade would change.",
    steps: [
      {
        title: "What stands out",
        body: "Warnings from rules of thumb: one stock above 20% of the portfolio, one industry above 30%, a sector at more than twice its S&P 500 weight, or fewer than 4 independent bets.",
        meaning: "These are the concentrations that decide most of your result. Each is a prompt to check the position size is deliberate.",
      },
      {
        title: "Volatility, beta, independent bets and a bad day",
        body: "Volatility is how much the portfolio swings in a year. Beta is how much it has moved for each 1% the S&P 500 moved. Independent bets is the diversification ratio squared: roughly how many unrelated positions your holdings behave like. A bad day is the loss exceeded on 1 trading day in 20 (95% value at risk), with the average of those worst days.",
        meaning: "Ten stocks that all move together are closer to one bet than ten. Beta above 1 means bigger falls than the market in a selloff.",
        caution: "All of this comes from the last year of daily returns in your base currency. A calm year understates risk.",
      },
      {
        title: "Weight vs share of risk",
        body: "Each holding's share of the portfolio's value beside its share of the portfolio's variance, with its beta and its correlation with everything else you hold.",
        meaning: "A holding whose risk share is much bigger than its weight is volatile, highly correlated with the rest, or both. That's where trimming reduces risk most.",
      },
      {
        title: "Worst stretch",
        body: "Today's weights held for the last three years: the largest fall from a peak, when it happened, and how far below its peak the portfolio is now, against the S&P 500.",
        caution: "Holdings listed more recently count as flat before they listed, which understates the drawdown.",
      },
      {
        title: "Exposure",
        body: "Your money by sector (funds looked through to their holdings' sectors, against the S&P 500), by industry, by trading currency and by country.",
        meaning: "Sector shows the tilt against the market; industry is where concentration usually hides (several chip makers are one bet on chips).",
      },
      {
        title: "Correlation",
        body: "How each pair of holdings' daily returns move together. Warm cells move together, cool cells offset, neutral cells are unrelated. Hover a cell for its value.",
        meaning: "Diversification comes from holdings with low or negative correlation, not from the number of holdings.",
      },
      {
        title: "Stress tests",
        body: "Today's holdings through five past selloffs, peak to trough of the S&P 500, with the loss in money. A holding that wasn't trading then is estimated from its beta. The sliders apply a market move through each holding's beta, or move one industry while the rest stay flat.",
        caution: "Past selloffs are examples, not limits; the next one will hit different industries.",
      },
      {
        title: "What if?",
        body: "Enter trades (buy or sell amounts in your base currency, up to four) to see the portfolio's risk before and after, and the warnings that would remain.",
        meaning: "Use it before every trade, especially to see whether a new stock adds a real bet or more of what you already own.",
      },
    ],
  },
  plan: {
    intro: "Your decisions written down before you need them: why you own each stock, what would make you sell, target weights, a watchlist and alerts.",
    steps: [
      {
        title: "Needs attention",
        body: "Your alert rules that have triggered, earnings reports within a week, reviews that are due, and holdings more than the band away from their target weight.",
        meaning: "Start here each visit. Each item links to an AI assessment of that stock.",
        caution: "It's checked when the page opens. With email set up, the same list is emailed when a scheduled run starts.",
      },
      {
        title: "Why you own it",
        body: "For each holding: your thesis, the conditions that would make you sell, a review date and price or estimate alerts. The badge is the latest AI call on it.",
        meaning: "Sell conditions written in advance stop the purchase price and recent moves from deciding for you. An evaluation's “what would show the call is wrong” can be added here from AI Assessment.",
      },
      {
        title: "Target weights",
        body: "The weight you want each holding to be. The table shows today's weight and the trade (in money and shares) that would restore the target. Add a stock you plan to buy by symbol.",
        meaning: "Rebalancing to targets sells what has run up and buys what has lagged, which keeps one winner from becoming most of the risk.",
        caution: "Trades ignore tax and fees, which can make small rebalances not worth it; that's what the band is for.",
      },
      {
        title: "Earnings calendar and watchlist",
        body: "Next report dates for holdings and watched stocks, and for each watched stock its price, distance from its 52-week high, forward P/E, analyst view and the latest AI call.",
      },
    ],
  },
  usage: {
    intro: "How much the AI features are being used, what they cost, and how close you are to Gemini's rate limits.",
    steps: [
      {
        title: "Totals",
        body: "Calls, tokens and estimated cost for the selected range, and the success rate.",
        meaning: "Tokens are roughly word pieces; cost is estimated from the price list. Local-model calls cost nothing.",
      },
      {
        title: "Rate limits",
        body: "Gemini's three free-tier limits: requests and tokens in the last minute, and requests today. The daily count resets at midnight Pacific time, shown in your local time.",
        meaning: "Bars turn amber past half and red past 80%. When a minute is full, Gemini calls wait for it to clear; when the day's requests are used up, they're refused until the reset. Local-model calls don't count.",
      },
      {
        title: "Charts and recent calls",
        body: "Tokens and cost per day, calls by symbol and the latest calls with their status.",
        meaning: "Failed calls are listed with their status; a run of failures usually means a rate limit or an API key problem.",
      },
    ],
  },

  settings: {
    intro: "Your account, how the app looks, the currency totals are shown in, what Gemini may see, and your raw data.",
    steps: [
      {
        title: "Account",
        body: "Link an email for password resets and change your password.",
        caution: "Without an email, a forgotten password can only be reset by an admin.",
      },
      {
        title: "Appearance and base currency",
        body: "Choose light, dark or automatic. The base currency is what totals and charts are shown in.",
        caution: "The base currency is shared by all users of this app.",
      },
      {
        title: "AI Privacy",
        body: "Keep my portfolio from Gemini leaves your position, portfolio weights, holdings, plan and past calls out of everything sent to Gemini, and stops Gemini chat reading pages other than stock analysis.",
        meaning: "Google may train on free-tier Gemini prompts. Prices and news still go to Gemini; they're public. The local model always sees everything, since nothing leaves this machine.",
      },
      {
        title: "Hidden from Gemini",
        body: "Emails, phone numbers, ID, card and account numbers, keys, passwords and addresses are swapped for placeholders before anything goes to Gemini, and swapped back in its reply. Add words to always hide, such as your name or employer.",
        caution: "This is a safety net, not a guarantee: details written in an unusual form can get through. Use the local model for anything sensitive.",
      },
      {
        title: "Data",
        body: "Counts of your lots, symbols and currencies, the data files, and Edit portfolio JSON for direct edits.",
        caution: "Direct JSON edits are checked before saving, but a backup from Holdings first is still wise.",
      },
    ],
  },

  retrograde: {
    intro: "When each planet appears to move backwards, where those periods overlap, and what astrologers say they mean. The dates are cross-checked across three ephemerides.",
    steps: [
      {
        title: "Pick planets and a year",
        body: "Switch planets on or off with the chips; Mercury, Venus and Mars are on by default. Use the arrows to change year.",
        meaning: "Jupiter to Pluto are retrograde for months every year, so turning them on fills the calendar with overlaps.",
      },
      {
        title: "The status row",
        body: "Retrograde now, which selected planets are in shadow, the next station and the number of overlap days this year.",
        meaning: "A station is the day a planet appears to stop and turn: Rx turning retrograde, D turning direct.",
      },
      {
        title: "At a glance",
        body: "The year as a timeline: one row per planet, solid for retrograde and faded for shadow. The Overlap row marks when two or more are retrograde together. The red line is today.",
        meaning: "The shadow is the stretch of sky the retrograde covers twice; astrologers say its themes build up before and wind down after.",
      },
      {
        title: "Calendar",
        body: "Each day carries a stripe per planet: solid retrograde, faded shadow. Ringed days have overlapping retrogrades. Select a day to see each planet's state and any station.",
      },
      {
        title: "Overlaps",
        body: "Every stretch when two or more selected planets are retrograde at once, with exact start, end and length.",
      },
      {
        title: "What it means in astrology",
        body: "For each planet: what it governs, how often it goes retrograde, the traditional reading, what it's said to be good for and what's avoided, with sources.",
        caution: "These are astrological traditions, not predictions. The dates are measured astronomy; the meanings are belief.",
      },
      {
        title: "Periods and sources",
        body: "Each period's start and end in your timezone, the zodiac degree, the shadow, and a verification badge. Select a row to compare NASA JPL Horizons, Swiss Ephemeris and Astronomy Engine.",
        meaning: "Verified 3/3 means all three sources agree on both stations, usually within minutes.",
      },
      {
        title: "Testing it against markets",
        body: "vs Markets (top right) tests whether ETFs actually behave differently during these periods.",
      },
    ],
  },

  retroMarkets: {
    intro: "Tests whether ETFs actually behave differently while planets are retrograde, with the statistics to tell a real pattern from coincidence.",
    steps: [
      {
        title: "Choose what to test",
        body: "Pick planets, whether to count only the retrograde or include the shadow, the start year, and which ETFs. SPY (the S&P 500) is always included as the benchmark.",
        meaning: "Starting in a later year is a robustness check: a real effect should hold whether you start in 2000 or 2015.",
      },
      {
        title: "Read the summary banner first",
        body: "It counts how many comparisons pass the multiple-testing check (q < 0.05).",
        meaning: "\"No reliable link\" means nothing here is distinguishable from chance, however striking some cells look.",
      },
      {
        title: "The heatmap",
        body: "Each cell is the ETF's annualized return during the windows minus its return at other times, in percentage points. Green means better during retrograde, red worse.",
        meaning: "* means p < 0.05 for that cell alone; ** means it's still significant after correcting for every test on the page. Only ** is worth attention.",
        caution: "ETFs move together, so a whole red column is mostly one market effect counted many times. Switch Measure to vs S&P 500 to strip that out.",
      },
      {
        title: "p and q, in plain terms",
        body: "p is how often sliding the retrograde calendar to random dates (same lengths and spacing) produced a gap at least this big. q adjusts p for running many tests.",
        meaning: "p = 0.15 means 15% of random placements did as well, which is easily luck. With 100 tests about 5 will hit p < 0.05 by chance, which is why q matters.",
      },
      {
        title: "Detail: inside vs outside",
        body: "Select a cell for its numbers: annualized return inside and outside the windows, volatility and the share of up days.",
        meaning: "The verdict badge sums it up: No evidence, Nominal only (p passes, q doesn't) or Significant after correction.",
      },
      {
        title: "Growth chart",
        body: "Growth of $1 in the ETF and SPY with the windows shaded in each planet's colour.",
        meaning: "Look for whether the drops sit inside shaded bands consistently, or only a few memorable times.",
      },
      {
        title: "Each window: is it a pattern or a few crashes?",
        body: "Fell in compares how often the ETF fell during windows with how often it falls over any stretch of the same length. Median window is the middle result; Without worst drops the worst few.",
        meaning: "If Fell in matches the normal rate and the median is positive, most windows were ordinary. If the average turns positive without the worst windows, a few crashes drive the result. That's coincidence, not a pattern.",
        caution: "Big shocks (2008, March 2020) landing in a window can dominate everything. Check the table for which dates they are.",
      },
      {
        title: "How this is tested",
        body: "The methods card at the bottom explains the test and its caveats.",
        caution: "Correlation isn't cause, and none of this is investment advice.",
      },
    ],
  },
} satisfies Record<string, Guide>;

export type GuideKey = keyof typeof GUIDES;
