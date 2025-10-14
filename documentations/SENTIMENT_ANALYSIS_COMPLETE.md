# 💭 Sentiment Analysis - Complete Guide

## Overview

The Sentiment Analysis feature provides comprehensive market sentiment analysis for stocks by extracting and analyzing news articles from Google Finance and Google News using SERPapi and advanced Natural Language Processing (NLP) tools. This feature is available both as a standalone page and integrated into the Investment Assessment workflow.

## 🚀 Quick Start (3 Steps)

### Step 1: Install Required Packages

```bash
pip install -r requirements.txt
```

This will install:
- `google-search-results` (SERPapi client)
- `nltk` (Natural Language Toolkit)
- `textblob` (Text processing and sentiment)
- `vaderSentiment` (VADER sentiment analyzer)

### Step 2: Get Your SERPapi API Key

1. Go to **[https://serpapi.com/](https://serpapi.com/)**
2. Sign up for a free account
3. Navigate to your dashboard
4. Copy your API key

**Free Plan**: 100 searches/month (good for testing!)

### Step 3: Configure Your API Key

#### Option A: Using .env file (Recommended)

1. Create a `.env` file in the project root (if it doesn't exist):
   ```bash
   cp config.env.example .env
   ```

2. Edit `.env` and add your SERPapi key:
   ```bash
   # Open in your favorite editor
   nano .env
   # or
   code .env
   ```

3. Add this line (replace with your actual key):
   ```
   SERP_API_KEY=your_actual_serpapi_key_here
   ```

4. Save and close the file

#### Option B: Verify Setup (Automated)

Run the setup verification script:
```bash
python setup_sentiment.py
```

This will:
- ✅ Check all required packages are installed
- ✅ Download NLTK data automatically
- ✅ Test your SERPapi connection
- ✅ Verify configuration

## 📊 Features

### 🔍 News Data Extraction
- **Google Finance News**: Stock-specific news, analyst reports, and company announcements
- **Google News**: Broader market coverage and industry trends
- **Flexible Sourcing**: Choose between Google Finance, Google News, or both

### 📊 Dual Sentiment Analysis
1. **VADER (Valence Aware Dictionary and sEntiment Reasoner)**
   - Specialized for social media and short text
   - Excellent for news headlines and snippets
   - Provides compound score and detailed breakdowns

2. **TextBlob**
   - General-purpose sentiment analysis
   - Provides polarity and subjectivity scores
   - Useful for understanding objectivity vs. subjectivity

### 📈 Comprehensive Visualizations
- Overall sentiment metrics
- Sentiment distribution (pie chart and bar chart)
- Sentiment score timelines
- Individual article analysis with detailed scores

### 💾 Export Capabilities
- Download sentiment analysis results as CSV
- Includes all sentiment scores and article metadata

### 📊 SERPapi Usage Tracking

#### Real-Time Usage Monitoring
Located right after the main header, this expandable section provides detailed account information:

**Quick Status (Visible on Page Load)**
- **At-a-glance display** showing remaining searches
- **Color-coded alerts:**
  - 🟢 Green (>25 searches): "You have plenty of searches remaining"
  - 🟡 Orange (10-25 searches): "You're running low on searches"
  - 🔴 Red (<10 searches): "Low on searches! Consider upgrading"

**Detailed Account Information**
Click **"🔄 Check API Usage"** to see:

**Main Metrics (4-column display):**
- **Searches Left** - Total remaining searches in your account
- **Used This Month** - Number of searches used this month
- **Plan** - Your current SERPapi plan (Free, Basic, Pro, etc.)
- **Monthly Limit** - Your plan's search allocation

**Additional Details:**
- Account ID
- Registered email (if available)
- Monthly usage progress bar
- Visual percentage of usage
- Last check timestamp

**Smart Warnings:**
- ⚠️ Red alert when < 10 searches remaining
- ⚠️ Yellow warning when < 25 searches remaining
- ✅ Green success when plenty of searches available

#### Real-Time Usage Tracking
After each sentiment analysis:
- **Automatic counter update** - Decrements your remaining searches
- **Usage notification** - Shows how many searches were used
- **Approximate remaining** - Updates the count without making extra API calls

**Search Cost:**
- Google Finance only: **1 search**
- Google News only: **1 search**
- Both sources: **2 searches**

## 🎯 Integration with Investment Assessment

The sentiment analysis feature is fully integrated into the Investment Assessment page, providing AI-powered recommendations that consider:

1. **Technical Analysis** - Price patterns and indicators
2. **Fundamental Analysis** - Financial metrics and ratios
3. **💭 Sentiment Analysis** - News sentiment and market mood (NEW!)
4. **Predictive Analysis** - Machine learning forecasts
5. **Portfolio Context** - Your current positions

### Enhanced AI Assessment
- Google Gemini now receives sentiment data
- AI considers market mood in recommendations
- Recommendations now factor in sentiment alignment with technical/fundamental signals
- AI provides sentiment-specific insights (contrarian vs momentum opportunities)

### New Sentiment Tab
- Dedicated sentiment analysis tab in the dashboard
- Shows overall sentiment (🟢 Positive, 🟡 Neutral, 🔴 Negative)
- VADER sentiment score display
- Sentiment distribution (Positive/Negative/Neutral percentages)
- Sample news headlines with sources
- Sentiment interpretation guide

### Enhanced Radar Chart
- Added "Sentiment" dimension to the Combined Analysis chart
- 7-point radar chart now includes:
  - Valuation
  - Growth
  - Profitability
  - Technical
  - Risk
  - **Sentiment** (NEW!)
  - Predictive

## How to Use

### Method 1: Standalone Sentiment Analysis Page

1. **Navigate to Sentiment Analysis**
   - Click "💭 Sentiment Analysis" in the sidebar

2. **Select a Stock**
   - Enter a stock symbol (e.g., AAPL, GOOGL, TSLA)
   - Or use the stock selection in the sidebar

3. **Configure Settings**
   - **Number of Articles**: 5-50 articles (default: 20)
   - **News Source**: 
     - Google Finance (stock-specific)
     - Google News (broader coverage)
     - Both (recommended)

4. **Run Analysis**
   - Click "🔍 Analyze Sentiment" button
   - Or use the sidebar "💭 Run Sentiment Analysis" button

5. **Review Results**
   - Overall sentiment metrics
   - Sentiment distribution charts
   - Individual article analysis
   - Export results as needed

### Method 2: Quick Analysis from Sidebar

For any stock in your portfolio:
1. Select the stock in the sidebar
2. Click "💭 Run Sentiment Analysis"
3. Results will be displayed automatically

### Method 3: Integrated Investment Assessment

1. **Navigate to Investment Assessment**
   - Click "🎯 Investment Assessment" in sidebar

2. **Select Your Stock**
   - Use sidebar stock selection
   - Or click "Run Investment Assessment" from sidebar

3. **Configure Analysis**
   - Select time period (1 month to 5 years)
   - **Check "Include Sentiment Analysis"** ✅ (enabled by default)

4. **Run Assessment**
   - Click "🚀 Run Assessment"
   - Wait for analysis to complete (includes sentiment fetch)
   - Success message will confirm sentiment was included

5. **Review Results**
   - Navigate through tabs:
     - **AI Assessment**: Get AI recommendation (now includes sentiment!)
     - **Technical Summary**: View technical indicators
     - **Fundamental Summary**: Review financials
     - **💭 Sentiment Analysis**: See market sentiment (NEW!)
     - **Predictive Analysis**: ML forecasts
     - **Combined Analysis**: Radar chart with all factors

## Understanding the Results

### Overall Sentiment Metrics

#### Overall Sentiment
- **🟢 Positive**: Average VADER compound score ≥ 0.05
- **🟡 Neutral**: Average VADER compound score between -0.05 and 0.05
- **🔴 Negative**: Average VADER compound score ≤ -0.05

#### VADER Score
- Range: -1 (extremely negative) to +1 (extremely positive)
- **> 0.5**: Very positive
- **0.05 to 0.5**: Positive
- **-0.05 to 0.05**: Neutral
- **-0.5 to -0.05**: Negative
- **< -0.5**: Very negative

#### TextBlob Polarity
- Range: -1 (negative) to +1 (positive)
- Provides a complementary view to VADER

### VADER Breakdown

Each article includes detailed VADER scores:
- **Positive**: Proportion of positive sentiment (0-1)
- **Negative**: Proportion of negative sentiment (0-1)
- **Neutral**: Proportion of neutral sentiment (0-1)
- **Compound**: Overall sentiment score (-1 to +1)

### TextBlob Metrics

#### Polarity
- How positive or negative the text is
- -1 (very negative) to +1 (very positive)

#### Subjectivity
- How subjective vs. objective the text is
- 0 (very objective) to 1 (very subjective)
- **Low subjectivity** (< 0.3): Factual, objective reporting
- **High subjectivity** (> 0.7): Opinion-based, subjective content

## Sentiment Distribution Visualizations

### Pie Chart
Shows the proportion of positive, negative, and neutral articles in your analysis.

### Bar Chart
Displays sentiment percentages for easy comparison.

### Timeline Chart
Shows how sentiment varies across articles:
- **VADER Compound Score**: Overall sentiment trend
- **TextBlob Polarity Score**: Alternative sentiment view

Reference lines:
- Solid gray line: Zero (neutral)
- Green dotted line: +0.05 (positive threshold)
- Red dotted line: -0.05 (negative threshold)

## Individual Article Analysis

### Sorting Options
- **Most Recent**: Default chronological order
- **Most Positive**: Highest VADER compound scores first
- **Most Negative**: Lowest VADER compound scores first
- **Highest Subjectivity**: Most subjective/opinion-based articles first

### Article Information
Each expandable article includes:
- Full title and snippet
- Source and publication date
- Link to full article
- Overall sentiment classification
- VADER compound score
- TextBlob polarity and subjectivity
- Detailed VADER breakdown

## AI Assessment Enhancement

### How AI Uses Sentiment

The Google Gemini AI now receives sentiment data and considers:

1. **Sentiment Alignment**
   - Does sentiment support technical signals?
   - Is market mood aligned with fundamentals?

2. **Confirmation vs Divergence**
   - Confirming: All factors aligned (stronger signal)
   - Diverging: Sentiment conflicts with fundamentals (caution or opportunity)

3. **Timing Insights**
   - Sentiment can indicate good entry/exit timing
   - Extreme sentiment may signal reversals

4. **Risk Assessment**
   - Very negative sentiment increases risk
   - May recommend smaller position sizes

5. **Contrarian vs Momentum**
   - Positive sentiment = momentum play
   - Negative sentiment + strong fundamentals = contrarian opportunity

### AI Prompt Now Includes:

```
SENTIMENT ANALYSIS (News & Market Sentiment):
- Overall Market Sentiment: Positive/Negative/Neutral
- VADER Sentiment Score: X.XXX
- Sentiment Distribution: X% Positive, Y% Negative, Z% Neutral
- Based on N recent news articles
- Sentiment Interpretation: Bullish/Bearish/Neutral market mood
```

### AI Provides:

1. Recommendation (BUY/SELL/HOLD) considering sentiment
2. Confidence level factoring sentiment alignment
3. Sentiment-specific insights
4. Contrarian vs momentum opportunity assessment
5. Entry/exit timing suggestions based on sentiment

## Combined Analysis Radar Chart

The 7-point radar chart now visualizes all factors including sentiment:

**Sentiment Score Calculation:**
- VADER score converted to 0-100 scale
- -1.0 (very negative) = 0 points
- 0.0 (neutral) = 50 points
- +1.0 (very positive) = 100 points

**Interpretation:**
- **High sentiment score** (>70): Strong positive market mood
- **Moderate score** (40-60): Neutral to mixed sentiment
- **Low score** (<30): Negative market mood

**Look for:**
- **Balanced profile**: All factors aligned = high confidence
- **Sentiment outlier**: Sentiment differs from other factors = investigate
- **Cluster patterns**: Related factors move together

## Best Practices

### For Investment Analysis

1. **Use Both News Sources**
   - Combine Google Finance and Google News for comprehensive coverage
   - Google Finance for company-specific news
   - Google News for broader market context

2. **Analyze 15-30 Articles**
   - Too few articles may not be representative
   - Too many articles may include less relevant news
   - 20 articles is a good balance

3. **Check Subjectivity Scores**
   - Low subjectivity (< 0.3): More reliable factual reporting
   - High subjectivity (> 0.7): Opinion-based, take with caution

4. **Read the Actual Articles**
   - Automated sentiment isn't perfect
   - Verify important findings by reading full articles
   - Look for context that may be missed by algorithms

5. **Look for Patterns**
   - Single articles may not be representative
   - Look for overall trends in sentiment
   - Compare sentiment over time

6. **Combine with Other Analysis**
   - Use sentiment analysis alongside:
     - Technical Analysis (price patterns, indicators)
     - Fundamental Analysis (financials, ratios)
     - Predictive Analysis (future price trends)

### Interpreting Sentiment

#### Strong Positive Sentiment (VADER > 0.3)
- May indicate good news, positive earnings, or bullish outlook
- Could signal buying opportunity
- Verify with price action and fundamentals

#### Strong Negative Sentiment (VADER < -0.3)
- May indicate bad news, poor earnings, or bearish outlook
- Could signal selling pressure
- May also represent buying opportunity if oversold

#### Neutral or Mixed Sentiment (VADER -0.1 to 0.1)
- Market uncertainty or lack of clear direction
- May indicate consolidation period
- Wait for clearer signals

#### Divergence from Price
- **Positive sentiment + falling price**: Possible oversold condition
- **Negative sentiment + rising price**: Possible overbought condition
- Investigate the cause of divergence

### Cost Management

Each analysis uses 1-2 API calls:
- Google Finance only: 1 call
- Google News only: 1 call  
- Both: 2 calls

**Free plan**: 100 calls/month = 50-100 analyses
**Recommended**: Analyze strategically, focus on portfolio stocks

### When to Include Sentiment:
✅ **Include:**
- Major investment decisions
- Stocks you're considering buying
- Earnings season assessments
- When timing matters

❌ **Skip:**
- Quick portfolio checks
- Stocks you're very familiar with
- When API quota is low
- Routine monitoring

## Example Use Cases

### Case 1: Confirmation Play

**Stock:** AAPL
**Analysis Results:**
- Technical: Bullish (RSI 55, MACD positive)
- Fundamental: Strong (P/E 25, ROE 45%)
- Sentiment: 🟢 Positive (VADER 0.35, 65% positive news)
- Predictive: Upward trend

**AI Recommendation:** BUY
**Confidence:** 8/10
**Reasoning:** All factors aligned, sentiment confirms momentum

**Action:** Strong buy signal, consider normal to slightly larger position

---

### Case 2: Contrarian Opportunity

**Stock:** NVDA
**Analysis Results:**
- Technical: Neutral (RSI 45, consolidating)
- Fundamental: Excellent (P/E 30, Revenue Growth 40%)
- Sentiment: 🔴 Negative (VADER -0.25, 55% negative news)
- Predictive: Slight downward short-term

**AI Recommendation:** BUY (contrarian)
**Confidence:** 6/10
**Reasoning:** Strong fundamentals, negative sentiment creates opportunity

**Action:** Contrarian buy, smaller position, expect short-term volatility

---

### Case 3: Divergence Warning

**Stock:** XYZ
**Analysis Results:**
- Technical: Bullish (overbought RSI 75)
- Fundamental: Weak (High P/E 60, Debt increasing)
- Sentiment: 🟢 Positive (VADER 0.40, 70% positive)
- Predictive: Continuation but slowing

**AI Recommendation:** HOLD or SELL
**Confidence:** 7/10
**Reasoning:** Positive sentiment not backed by fundamentals, technical overbought

**Action:** Take profits or reduce position, sentiment-driven rally unsustainable

## API Cost Estimation

### SERPapi Usage

Each sentiment analysis uses:
- 1 API call for Google Finance (if selected)
- 1 API call for Google News (if selected)
- 2 API calls if "Both" is selected

**Monthly Budget Planning:**

| Analyses per Day | Monthly API Calls | Plan Needed |
|-----------------|------------------|-------------|
| 1-2 per day     | 60-120          | Free        |
| 3-5 per day     | 180-300         | Paid ($50)  |
| 10+ per day     | 600+            | Paid ($100+)|

### Optimization Tips

1. **Cache Results**: Results are stored in session state
2. **Analyze Strategically**: Focus on key stocks in your portfolio
3. **Batch Analysis**: Analyze multiple aspects of one stock at once
4. **Use Wisely**: Don't re-analyze the same stock repeatedly

## Troubleshooting

### "SERP_API_KEY not configured" Error

**Solution:**
1. Ensure you have created a `.env` file
2. Check that `SERP_API_KEY` is set correctly
3. Restart the Streamlit application

### "Required libraries not installed" Error

**Solution:**
```bash
pip install -r requirements.txt
```

### NLTK Download Issues

**Solution:**
```python
import nltk
nltk.download('vader_lexicon')
nltk.download('punkt')
```

### No News Articles Found

**Possible Causes:**
1. Stock symbol is incorrect
2. Stock has limited news coverage
3. API rate limit reached
4. Temporary API issue

**Solutions:**
- Verify the stock symbol
- Try a different news source (Google News vs. Google Finance)
- Check your SERPapi account for rate limit status
- Wait a few minutes and try again

### API Rate Limit Exceeded

**Solution:**
1. Check your SERPapi dashboard for usage
2. Wait until your monthly limit resets
3. Consider upgrading to a paid plan for higher limits

### Sentiment Seems Incorrect

**Remember:**
- Automated sentiment analysis isn't perfect
- Context may be lost in headlines
- Sarcasm and nuanced language may be misinterpreted
- Always verify by reading the full article

### Sentiment Not Available

**Issue:** Sentiment tab shows "not available"

**Possible Causes:**
1. Packages not installed
2. SERPapi key not configured
3. Stock has limited news coverage
4. API rate limit reached

**Solutions:**
1. Run: `pip install google-search-results nltk textblob vaderSentiment`
2. Add `SERP_API_KEY` to `.env` file
3. Try a different, more popular stock
4. Check SERPapi dashboard for usage

### Sentiment Checkbox Disabled

**Issue:** Can't enable sentiment analysis

**Cause:** Prerequisites not met

**Fix:**
- Check error message below checkbox
- Install missing packages or configure API key
- Restart application after fixing

### AI Not Considering Sentiment

**Issue:** AI recommendation doesn't mention sentiment

**Cause:** Sentiment data not included in assessment

**Fix:**
- Ensure "Include Sentiment Analysis" was checked
- Verify sentiment tab shows data
- Re-generate AI assessment

## Limitations and Disclaimers

### Technical Limitations

1. **Sentiment Analysis Accuracy**
   - Not 100% accurate
   - May misinterpret sarcasm, context, or complex language
   - Works best on straightforward news headlines

2. **News Coverage**
   - Depends on availability of news articles
   - Some stocks have more coverage than others
   - Timing may vary by source

3. **API Limitations**
   - SERPapi has usage limits based on your plan
   - Free plan: 100 searches/month
   - Each analysis counts as 1-2 API calls

4. **Language Support**
   - Optimized for English language news
   - May not work well with other languages

### Investment Disclaimers

⚠️ **Important**: This tool is for informational purposes only

- **Not Financial Advice**: Do not use as the sole basis for investment decisions
- **No Guarantees**: Past sentiment does not predict future performance
- **Verify Information**: Always verify news with credible sources
- **Consider Multiple Factors**: Use alongside other analysis methods
- **Risk Warning**: All investments carry risk of loss

### Data and Privacy

- News data is fetched in real-time via SERPapi
- No news data is stored permanently
- Your API key is stored locally in `.env`
- Session data is cleared when you close the app

## Advanced Usage

### Combining with Other Features

1. **Technical + Sentiment Analysis**
   - Run technical analysis first
   - Check sentiment to confirm signals
   - Strong technicals + positive sentiment = stronger signal

2. **Fundamental + Sentiment Analysis**
   - Review fundamental metrics
   - Check if sentiment aligns with fundamentals
   - Divergence may indicate market inefficiency

3. **Predictive + Sentiment Analysis**
   - Run predictive models
   - Verify predictions with current sentiment
   - Strong predictions + positive sentiment = higher confidence

### Custom Workflows

#### Pre-Earnings Analysis
1. Analyze sentiment 1-2 weeks before earnings
2. Look for insider sentiment or analyst upgrades
3. Compare with historical patterns

#### Crisis Management
1. When stock drops significantly, check sentiment
2. Determine if it's company-specific or market-wide
3. Look for recovery signals in sentiment

#### Portfolio Health Check
1. Run sentiment analysis on all holdings weekly
2. Track sentiment changes over time
3. Adjust positions based on sentiment trends

## Future Enhancements (Roadmap)

Potential future features:
- Historical sentiment tracking
- Sentiment correlation with price movements
- Multi-stock sentiment comparison
- Sentiment alerts and notifications
- Advanced sentiment models (BERT, FinBERT)
- Social media sentiment integration
- Sentiment-based trading signals

## Support and Resources

### Documentation
- [SERPapi Documentation](https://serpapi.com/google-finance-api)
- [VADER Sentiment Analysis](https://github.com/cjhutto/vaderSentiment)
- [TextBlob Documentation](https://textblob.readthedocs.io/)

### Academic Resources
- VADER Paper: [VADER: A Parsimonious Rule-based Model for Sentiment Analysis](http://comp.social.gatech.edu/papers/icwsm14.vader.hutto.pdf)
- TextBlob: Built on NLTK and Pattern libraries

### Getting Help
- Check the main README.md for general setup
- Review this documentation for sentiment-specific issues
- Verify API key and library installation
- Check SERPapi dashboard for account status

## License and Attribution

This feature uses:
- **SERPapi**: For news data extraction (requires API key)
- **VADER**: MIT License
- **TextBlob**: MIT License
- **NLTK**: Apache 2.0 License

---

**Last Updated**: October 2025  
**Version**: 2.0.0 (Consolidated)  
**Maintainer**: Portfolio Dashboard Team

**Ready to get started?**

```bash
# 1. Install packages
pip install -r requirements.txt

# 2. Run setup verification
python setup_sentiment.py

# 3. Start the app
streamlit run Portfolio.py
```

**Happy analyzing!** 💭📊
