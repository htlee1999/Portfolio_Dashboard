---
name: claim-check
description: Checks every number and signal reading in a stock recommendation against the data it was given, and flags claims that rely on unreliable inputs. Use on every recommendation.
metadata:
  title: Claim check
  applies_when: Always.
  evidence: mixed
  rationale: Checking specific claims against given facts reduces invented content in language-model answers, while asking a model to simply reconsider its answer does not reliably improve it. This check is the first kind; it can only catch errors the fact sheet covers.
  sources:
    - cite: Dhuliawala, Komeili, Xu, Raileanu, Li, Celikyilmaz & Weston (2023), Chain-of-Verification Reduces Hallucination in Large Language Models
      url: https://arxiv.org/abs/2309.11495
    - cite: Huang, Chen, Mishra, Zheng, Yu, Song & Zhou (2024), Large Language Models Cannot Self-Correct Reasoning Yet, ICLR
      url: https://arxiv.org/abs/2310.01798
---

# Claim check

Verify the recommendation against the fact sheet, claim by claim. You are checking, not re-analysing.

## Steps

1. List the factual claims in the recommendation: numbers (price, RSI, P/E, growth, targets, returns), signal readings ("overbought", "MACD bullish", "above the 200-day"), and statements about data ("analysts are bullish", "news is positive").
2. Compare each with the fact sheet. A number counts as matching if it is within rounding.
3. Review the failed automatic screens. They match wording with simple patterns and quote the sentence they matched: read that sentence and decide. Confirm the screen as a finding only if the sentence really makes the claim; otherwise dismiss it in a "neutral" info finding. For example, "analyst sentiment" is not news sentiment.
4. Flag reliance on inputs marked unreliable in the fact sheet:
   - a forecast model whose verdict is not "skill" (it did not beat a no-change forecast), used as evidence of direction. Saying the models have no edge, or calling their output neutral, is the correct reading, not reliance. The GARCH price range is a volatility estimate and fine to use;
   - news tone used as a signal when its tilt is "no clear tilt" or there were too few headlines;
   - any section the fact sheet marks as missing, discussed as if it were known.

## Severity

- **major**: a wrong number or reading that the recommendation leans on, or a conclusion drawn from missing data.
- **minor**: a wrong number that doesn't change the argument, or an overstated reading ("strongly bullish" for a mild signal).
- **info**: a claim you could not check because the fact sheet doesn't cover it. Say so; don't guess.

Report claims that check out only as one short "supports" finding listing them. Spend the detail on problems.
