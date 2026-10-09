---
name: counter-case
description: Builds the strongest case against a stock recommendation from the signals that disagree with it, and states what would show the call is wrong. Use on every recommendation.
metadata:
  title: Counter-case
  applies_when: Always.
  evidence: mixed
  rationale: Asking people to consider how the opposite could be true reduces their tendency to weigh evidence in favour of what they already believe, more than simply asking them to be unbiased. Evidence comes from laboratory studies of judgement, not from investment returns.
  sources:
    - cite: Lord, Lepper & Preston (1984), Considering the Opposite - A Corrective Strategy for Social Judgment, Journal of Personality and Social Psychology
      url: https://doi.org/10.1037/0022-3514.47.6.1231
    - cite: Okawa (2026), Emergence of Biased Consensus in Multi-Agent LLM Debates, ICML
      url: https://arxiv.org/abs/2608.02827
---

# Counter-case

Argue against the recommendation as a careful sceptic would, using only the fact sheet.

## Steps

1. Start from the opposing signals in the fact sheet: radar axes that point the other way, and analyst consensus if it disagrees. For a HOLD, use the strongest signals on either side.
2. Write the counter-case in `counter_case`: 2–4 sentences, the strongest specific argument, citing numbers. Not a list of generic risks ("markets are volatile").
3. Judge whether the recommendation addressed it:
   - addressed and answered with evidence → a "supports" finding;
   - mentioned but dismissed without evidence → "challenges", minor;
   - ignored, and the opposing signals are strong (score below 30 or above 70 against the call) → "challenges", major.
4. Write 2–4 `invalidation` conditions: observable events that would show the call is wrong, each with a number or date where possible. For example "Price closes below the 200-day average (312.40)" or "The 2 November report misses EPS estimates". Avoid conditions that can't be checked, such as "sentiment worsens".

A counter-case that is weak is a finding too: if the opposing signals are few and mild, say so.
