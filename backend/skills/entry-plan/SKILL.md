---
name: entry-plan
description: Turns a BUY or add recommendation into an entry plan - all at once, staged or wait, how much, what would invalidate it and when to review - based on volatility and upcoming events rather than price predictions. Use when the recommendation is BUY or advises adding to a position.
metadata:
  title: Entry plan
  applies_when: The recommendation is BUY, or the position advice is to add.
  evidence: mixed
  rationale: Forecasting the market's return to time entries has not worked reliably out of sample, and investors who trade most earn the least. What can be planned is size and pacing. Scaling exposure down when volatility is high improved risk-adjusted returns in some studies, but later work found the gains unreliable out of sample, so treat it as risk control, not a return edge.
  sources:
    - cite: Welch & Goyal (2008), A Comprehensive Look at the Empirical Performance of Equity Premium Prediction, Review of Financial Studies
      url: https://doi.org/10.1093/rfs/hhm014
    - cite: Barber & Odean (2000), Trading Is Hazardous to Your Wealth, Journal of Finance
      url: https://doi.org/10.1111/0022-1082.00226
    - cite: Moreira & Muir (2017), Volatility-Managed Portfolios, Journal of Finance
      url: https://doi.org/10.1111/jofi.12513
    - cite: Cederburg, O'Doherty, Wang & Yan (2020), On the Performance of Volatility-Managed Portfolios, Journal of Financial Economics
      url: https://doi.org/10.1016/j.jfineco.2020.04.015
---

# Entry plan

Fill in `entry_plan`. Plan the size and pacing of the purchase; never predict the price.

## Approach

Choose one:

- **staged**: when an earnings report is due within 30 days, when current volatility is well above its long-run level (ratio above 1.2), or when the price is at or near its 52-week high. Say how many steps and over what period, for example "three equal purchases over six weeks, one after the report".
- **all_at_once**: when none of the above apply. Note that waiting has a cost: the market rises in most years.
- **wait**: only when a specific dated event (usually an earnings report within two weeks) makes the next few weeks unusually risky. Name the event and the date to revisit.

## Size

Use the fact sheet's volatility figures. Say what a typical bad month looks like for this stock (the 20-day 95% low) as a percentage, and size so that loss is acceptable. Where portfolio data is given, keep the position's share in mind. Higher volatility means a smaller position for the same risk.

## Review and invalidation

- `review_when`: a date or event to re-check the call (the next report, or a fixed date).
- The invalidation level for the trade should be observable: a price based on the volatility range or a key moving average from the fact sheet, not a round number.

Add a finding if the recommendation's position advice conflicts with this plan, for example urging a full position right before a report.
