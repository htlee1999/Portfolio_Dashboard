---
name: technical-evidence
description: Checks whether the technical signals a stock recommendation relies on have actually predicted this stock's moves, using a five-year back-test of each signal. Use when the recommendation cites a technical indicator.
metadata:
  title: Technical evidence
  applies_when: The recommendation cites a technical indicator (RSI, MACD, Bollinger Bands, moving averages, 52-week high, ADX).
  evidence: mixed
  rationale: Indicators that work on average across markets often fail on a single stock. The back-test compares how the stock moved after each signal with how it moved on all days. Overlapping windows and testing many signals mean some apparent successes are luck, so a "worked" result is a screen, not proof.
  sources:
    - cite: Brock, Lakonishok & LeBaron (1992), Simple Technical Trading Rules and the Stochastic Properties of Stock Returns, Journal of Finance
      url: https://doi.org/10.1111/j.1540-6261.1992.tb04681.x
    - cite: Sullivan, Timmermann & White (1999), Data-Snooping, Technical Trading Rule Performance, and the Bootstrap, Journal of Finance
      url: https://doi.org/10.1111/0022-1082.00163
---

# Technical evidence

The fact sheet lists each indicator the recommendation cites, with this stock's five-year record for that indicator's signals: how often it fired, the hit rate 20 trading days later against the base rate on all days, and a verdict.

## Steps

1. For each cited indicator, find the signal matching the recommendation's reading (for example "RSI overbought" matches "RSI rises above 70").
2. Judge the reliance:
   - verdict "worked": a "supports" finding, noting the hit rate against the base rate;
   - "no_edge": a minor challenge if the recommendation treats it as meaningful;
   - "failed" (the stock tended to move the other way): a major challenge if the recommendation leans on it;
   - "insufficient" (too few events): an info finding; the signal can't be judged on this stock.
3. If the recommendation only describes the state (price above its 200-day average) without predicting from it, there's nothing to test; skip it.

Keep it short: one finding per indicator at most.
