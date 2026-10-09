---
name: valuation-sanity
description: Checks whether a recommendation's price target is plausible against analysts' targets and the valuation multiples the company has traded at before. Use when the recommendation gives a price target or is a BUY.
metadata:
  title: Valuation sanity
  applies_when: The recommendation gives a price target, or is a BUY.
  evidence: strong
  rationale: Analysts' 12-month price targets are on average about 15% too optimistic, and only 38% are met at the end of the 12 months. A target above every analyst's, or one that needs a multiple the company has never traded at, needs a specific reason.
  sources:
    - cite: Bradshaw, Brown & Huang (2013), Do Sell-Side Analysts Exhibit Differential Target Price Forecasting Ability?, Review of Accounting Studies
      url: https://doi.org/10.1007/s11142-012-9216-5
    - cite: Welch & Goyal (2008), A Comprehensive Look at the Empirical Performance of Equity Premium Prediction, Review of Financial Studies
      url: https://doi.org/10.1093/rfs/hhm014
---

# Valuation sanity

Test whether the price target and the valuation argument hold up.

## Steps

1. **Target against analysts.** The fact sheet gives the analysts' mean, low and high targets. A target above the analysts' high is a major challenge unless the recommendation gives a specific reason the analysts are all too low. A target near the mean adds little: say it mostly restates consensus, which is itself usually optimistic.
2. **Implied multiple.** The fact sheet gives the P/E the target implies at today's earnings, against the company's own fiscal-year range. If it is above the historical high, the target assumes the market will pay more for the company than it ever has: a major challenge unless earnings growth is argued with numbers. Between the median and the high: say it needs a richer multiple.
3. **Valuation claims.** If the recommendation calls the stock cheap or expensive, check that against the valuation radar score and the history verdicts ("cheaper" or "pricier" than its median).
4. **Loss-makers.** If the company is loss-making, P/E means nothing. Any target must rest on revenue or a path to profit, and the recommendation should say which.

Note what the data can't show: there is no sector comparison, so "cheap" here only means cheap against the company's own past and against analysts.
