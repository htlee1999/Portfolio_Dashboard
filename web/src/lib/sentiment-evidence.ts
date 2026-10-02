// Why each part of the sentiment pipeline is used, how well research supports it, and where to
// read more. Scorer ratings describe the evidence that a method reads the tone of financial text
// accurately; the "news tone as a signal" rating describes the evidence that tone predicts
// returns. Filtering and reading methods carry no rating.

import { doi, type EvidenceInfo, type Source } from "./evidence";

const MALO: Source = {
  cite: "Malo, Sinha, Korhonen, Wallenius & Takala (2014), Good Debt or Bad Debt: Detecting Semantic Orientations in Economic Texts, Journal of the Association for Information Science and Technology",
  url: doi("10.1002/asi.23062"),
};
const HUANG: Source = {
  cite: "Huang, Wang & Yang (2023), FinBERT: A Large Language Model for Extracting Information from Financial Text, Contemporary Accounting Research",
  url: doi("10.1111/1911-3846.12832"),
};
const LM_2011: Source = {
  cite: "Loughran & McDonald (2011), When Is a Liability Not a Liability? Textual Analysis, Dictionaries, and 10-Ks, Journal of Finance",
  url: doi("10.1111/j.1540-6261.2010.01625.x"),
};
const LM_2016: Source = {
  cite: "Loughran & McDonald (2016), Textual Analysis in Accounting and Finance: A Survey, Journal of Accounting Research",
  url: doi("10.1111/1475-679X.12123"),
};
const TETLOCK_2007: Source = {
  cite: "Tetlock (2007), Giving Content to Investor Sentiment: The Role of Media in the Stock Market, Journal of Finance",
  url: doi("10.1111/j.1540-6261.2007.01232.x"),
};
const TETLOCK_2008: Source = {
  cite: "Tetlock, Saar-Tsechansky & Macskassy (2008), More Than Words: Quantifying Language to Measure Firms' Fundamentals, Journal of Finance",
  url: doi("10.1111/j.1540-6261.2008.01362.x"),
};
const HESTON_SINHA: Source = {
  cite: "Heston & Sinha (2017), News vs. Sentiment: Predicting Stock Returns from News Stories, Financial Analysts Journal",
  url: doi("10.2469/faj.v73.n3.3"),
};
const CHAN: Source = {
  cite: "Chan (2003), Stock Price Reaction to News and No-News: Drift and Reversal after Headlines, Journal of Financial Economics",
  url: doi("10.1016/S0304-405X(03)00146-6"),
};
const BOUDOUKH: Source = {
  cite: "Boudoukh, Feldman, Kogan & Richardson (2019), Information, Trading, and Volatility: Evidence from Firm-Specific News, Review of Financial Studies",
  url: doi("10.1093/rfs/hhy083"),
};
const TFNS: Source = {
  cite: "Twitter Financial News Sentiment dataset (validation split, 2,388 labelled headlines), Hugging Face",
  url: "https://huggingface.co/datasets/zeroshot/twitter-financial-news-sentiment",
};

export const SENTIMENT = {
  finance_model: {
    name: "DistilRoBERTa financial-news model",
    evidence: "strong",
    read: "A compact language model (82 million parameters, a distilled version of RoBERTa) fine-tuned on the Financial PhraseBank: about 2,300 sentences from financial news on which every finance-trained annotator agreed. It reads the whole headline, so 'cuts losses' and 'cuts guidance' get opposite scores. It runs on the CPU and scores 100 headlines in under a second.",
    verdict: "Language models fine-tuned on financial text clearly beat word lists at reading financial tone. On 2,388 labelled financial-news headlines it was never trained on, it was right 76% of the time, against 50% for VADER; the two published FinBERT models scored 72–74%. It still misreads about 1 headline in 4, often valuation language such as '30% above fair value'.",
    learn: { site: "Hugging Face", url: "https://huggingface.co/mrm8488/distilroberta-finetuned-financial-news-sentiment-analysis" },
    sources: [
      MALO,
      HUANG,
      { cite: "Araci (2019), FinBERT: Financial Sentiment Analysis with Pre-trained Language Models", url: "https://arxiv.org/abs/1908.10063" },
      { cite: "Sanh, Debut, Chaumond & Wolf (2019), DistilBERT, a Distilled Version of BERT: Smaller, Faster, Cheaper and Lighter", url: "https://arxiv.org/abs/1910.01108" },
    ],
  },
  vader: {
    name: "VADER (fallback)",
    evidence: "weak",
    read: "A general-purpose list of about 7,500 words and emoticons rated by people for tone, with rules for emphasis and negation, built for social-media posts. Used only when torch and transformers aren't installed.",
    verdict: "General word lists misread finance: 'liability', 'tax', 'cost' and 'crude' sound negative in everyday English but are neutral in finance, and almost three-quarters of the negative words in one widely used general list aren't negative in financial filings. On the same test headlines VADER was right 50% of the time, below the 66% from calling every headline neutral.",
    learn: { site: "GitHub", url: "https://github.com/cjhutto/vaderSentiment" },
    sources: [
      { cite: "Hutto & Gilbert (2014), VADER: A Parsimonious Rule-Based Model for Sentiment Analysis of Social Media Text, Proceedings of ICWSM", url: doi("10.1609/icwsm.v8i1.14550") },
      LM_2011,
      LM_2016,
    ],
  },
  news_signal: {
    name: "News tone as a return signal",
    evidence: "mixed",
    read: "Whether the tone of recent coverage says anything about where the price goes next.",
    verdict: "Negative wording in firm-specific news predicts slightly lower earnings and returns, but prices absorb most of it within a day. Market-wide media pessimism predicts dips that reverse within a week. Weekly news tone has predicted returns for up to a quarter, but those studies use full professional news feeds across thousands of stocks, not a few dozen headlines for one.",
    sources: [TETLOCK_2007, TETLOCK_2008, HESTON_SINHA, CHAN],
  },
  benchmark: {
    name: "Accuracy test",
    read: "Every scorer considered was tested on 2,388 financial-news headlines labelled by people, none of which the models were trained on. Accuracy: DistilRoBERTa 76%, FinBERT-tone 74%, FinBERT 72%, Loughran–McDonald word list 60%, VADER 50%, TextBlob 49%. Calling every headline neutral scores 66%, because most headlines are.",
    verdict: "Accuracy on unseen data is the fair comparison: on the dataset they were trained on, these models score 95–99%, which overstates them. A measure that weights positive, neutral and negative equally (macro-F1) gave the same ranking, from 0.71 down to 0.38. TextBlob, which this page used to show, was dropped.",
    sources: [TFNS, MALO],
  },
  window: {
    name: "Recent headlines only",
    read: "Only headlines from the last 7 (or 30) days count. Google News ranks by relevance rather than date and returns stories up to months old, which are shown but left out.",
    verdict: "Prices absorb news within days. In Heston & Sinha's study, news tone summed over a week carried more information than single days, and its effect faded over the following months.",
    sources: [HESTON_SINHA, TETLOCK_2008],
  },
  firm_specific: {
    name: "Firm-specific headlines only",
    read: "A headline counts only if it names the company, a common alternative name or its ticker. Market-wide stories and other companies' news that the search returns are shown but left out. Funds and indices have no single company to look for, so every headline counts.",
    verdict: "News that is identifiably about the firm moves its price and volatility far more than general coverage that mentions it in passing.",
    sources: [BOUDOUKH, TETLOCK_2008],
  },
  duplicates: {
    name: "Duplicates counted once",
    read: "Syndicated copies of a story (sharing 70% or more of their words with a headline already counted) are left out, keeping the newest.",
    verdict: "Counting a story once per outlet would let widely syndicated stories dominate the average and make the interval look narrower than it is. Reprinted stale news also moves prices only temporarily.",
    sources: [{ cite: "Tetlock (2011), All the News That's Fit to Reprint: Do Investors React to Stale Information?, Review of Financial Studies", url: doi("10.1093/rfs/hhq141") }],
  },
  routine: {
    name: "Routine filings left out",
    read: "Automatically generated headlines about fund holdings ('Stock Sold by XYZ Advisors LLC', from 13F filings) and pre-planned insider sales (Form 4, 10b5-1 plans) are shown but not scored.",
    verdict: "13F holdings are reported up to 45 days after the quarter ends, so they are old news. Insider trades made on a fixed schedule carry no information about future returns, unlike opportunistic ones.",
    sources: [{ cite: "Cohen, Malloy & Pomorski (2012), Decoding Inside Information, Journal of Finance", url: doi("10.1111/j.1540-6261.2012.01740.x") }],
  },
  net_tone: {
    name: "Net tone and its confidence interval",
    read: "Each headline scores the model's probability that it is positive minus the probability that it is negative, from −1 to +1. Net tone is the average, with a 95% confidence interval. It counts as positive or negative only when the interval excludes zero; otherwise there is no clear tilt. Fewer than 5 headlines are too few to judge.",
    verdict: "Positive-minus-negative probability from a trained classifier is the measure Heston & Sinha used. Requiring the interval to exclude zero stops a handful of stories being read as a trend. Headlines about the same event aren't fully independent, so the true uncertainty is somewhat wider than shown.",
    sources: [HESTON_SINHA],
  },
  price_moves: {
    name: "Headlines that report price moves",
    read: "Headlines such as 'Stock slides 3%' describe a move that has already happened. The page shows the price change over the same window and how many scored headlines report a move.",
    verdict: "Much financial coverage follows prices rather than leading them, so tone partly restates recent returns. Price moves that come with news tend to continue, while moves without news tend to reverse.",
    sources: [CHAN, TETLOCK_2007],
  },
} satisfies Record<string, EvidenceInfo>;

export type SentimentKey = keyof typeof SENTIMENT;

export const GUIDE_SECTIONS: { title: string; keys: SentimentKey[] }[] = [
  { title: "Scoring headlines", keys: ["finance_model", "vader", "benchmark"] },
  { title: "Which headlines count", keys: ["window", "firm_specific", "duplicates", "routine"] },
  { title: "Reading the result", keys: ["net_tone", "price_moves", "news_signal"] },
];
