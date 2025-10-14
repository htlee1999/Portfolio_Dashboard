# 🤖 Google Gemini API - Complete Setup & Monitoring Guide

This comprehensive guide covers everything you need to know about setting up and monitoring Google Gemini API usage in your Portfolio Dashboard.

## 🎯 Overview

The Gemini API integration provides:
- **AI-powered investment recommendations** in Investment Assessment
- **Comprehensive usage monitoring** with real-time tracking
- **Cost analysis** with detailed breakdowns by operation and symbol
- **Rate limit monitoring** to prevent API quota exceeded errors
- **Usage trends** with interactive charts and visualizations
- **Export functionality** for detailed usage reports
- **Automated recommendations** for cost optimization

## 🚀 Quick Setup (3 Steps)

### Step 1: Install Required Packages

```bash
pip install google-genai python-dotenv
```

### Step 2: Get Your Free Google Gemini API Token

1. Go to [https://aistudio.google.com/](https://aistudio.google.com/)
2. Sign in with your Google account
3. Click "Get API key"
4. Create a new API key
5. Give it a name (e.g., "Portfolio Dashboard")
6. Copy the generated token

### Step 3: Configure Your API Key

#### Option 1: Using .env File (Recommended)

1. **Create a `.env` file in your project root directory:**
   ```bash
   touch .env
   ```

2. **Add your API token to the `.env` file:**
   ```
   GEMINI_API_KEY=your_actual_api_token_here
   ```
   Replace `your_actual_api_token_here` with the token you copied from Google AI Studio.

3. **The `.env` file is already included in `.gitignore`** so your API key won't be committed to version control.

#### Option 2: Using Environment Variables

If you prefer not to use a `.env` file, you can set the environment variable directly:

**On macOS/Linux:**
```bash
export GEMINI_API_KEY="your_actual_api_token_here"
```

**On Windows:**
```cmd
set GEMINI_API_KEY=your_actual_api_token_here
```

## 📊 Usage Monitoring Features

### 1. 📊 Usage Dashboard
- **Page 8: Usage Monitoring** - Comprehensive analytics dashboard
- Real-time metrics: total calls, tokens, costs, success rates
- Interactive charts showing usage trends over time
- Breakdown by operations and stock symbols

### 2. Automatic Tracking
- All Gemini API calls are automatically logged
- Tracks input/output tokens, costs, success/failure status
- Records operation type and associated stock symbol
- Stores data locally in `data/gemini_usage.json`

### 3. Rate Limit Monitoring
- Tracks calls per minute, hour, and day
- Visual warnings when approaching limits
- Helps prevent API quota exceeded errors

### 4. Cost Analysis
- Real-time cost calculations based on current Gemini pricing
- Daily and monthly cost estimates
- Cost per token and per API call metrics
- Historical cost trends

## 🎯 Getting Started with Monitoring

### 1. Prerequisites
The monitoring system is automatically available when you have:
- ✅ Google Gemini API configured (see setup steps above)
- ✅ Portfolio Dashboard running
- ✅ At least one API call made through the Investment Assessment page

### 2. Access the Monitoring Dashboard
1. Start your Portfolio Dashboard: `streamlit run Portfolio.py`
2. Navigate to **Page 8: Usage Monitoring** in the sidebar
3. View your comprehensive usage analytics

### 3. First-Time Setup
If you haven't made any API calls yet:
1. Go to **Page 7: Investment Assessment**
2. Configure your Gemini API key if not already done
3. Run an AI assessment on any stock symbol
4. Return to **Page 8: Usage Monitoring** to see your data

## 📈 Understanding the Dashboard

### Key Metrics
- **Total API Calls**: Number of API requests made
- **Total Tokens**: Combined input and output tokens used
- **Total Cost**: Estimated cost in USD
- **Success Rate**: Percentage of successful API calls

### Rate Limit Status
- **Last Minute**: Calls made in the past minute (limit: 15)
- **Last Hour**: Calls made in the past hour (limit: 900)
- **Today**: Calls made today (limit: 1M tokens)

### Visualizations
- **Usage Trends**: Line charts showing token usage and costs over time
- **Operations Breakdown**: Pie charts showing usage by operation type
- **Symbol Analysis**: Bar charts showing usage by stock symbol

## 🔧 Configuration

### Token Pricing
The system uses current Gemini 2.5 Flash pricing:
- **Input tokens**: $0.000075 per 1K tokens
- **Output tokens**: $0.0003 per 1K tokens

To update pricing, edit `gemini_monitor.py`:
```python
self.pricing = {
    "gemini-2.5-flash": {
        "input": 0.000075,  # per 1K tokens
        "output": 0.0003    # per 1K tokens
    }
}
```

### Data Retention
- Usage data is stored in `data/gemini_usage.json`
- Use the "Clear Old Data" button to remove data older than 90 days
- Data is automatically loaded when the dashboard starts

## 📊 Usage Analytics

### Operations Tracked
- **investment_assessment**: AI-powered stock analysis calls
- Future operations can be easily added

### Data Points Collected
For each API call:
- Timestamp
- Model used
- Input/output token counts
- Cost calculation
- Operation type
- Stock symbol (if applicable)
- Success/failure status
- Error messages (if failed)

## 💡 Cost Optimization Tips

### 1. Monitor Usage Patterns
- Check the Usage Monitoring dashboard regularly
- Look for high-cost operations or symbols
- Identify peak usage times

### 2. Optimize Prompts
- Shorter prompts use fewer input tokens
- More specific prompts may reduce output tokens
- Consider prompt engineering for efficiency

### 3. Set Usage Alerts
- Monitor the rate limit status
- Set personal thresholds for daily costs
- Use the recommendations section for guidance

### 4. Batch Operations
- Group similar analyses when possible
- Avoid redundant API calls
- Cache results when appropriate

## 🔍 Troubleshooting

### "API key not found" Error
- Make sure your `.env` file is in the project root directory
- Verify the token is correctly formatted: `GEMINI_API_KEY=your_token_here`
- Restart your Streamlit application after creating the `.env` file

### "Required packages not installed" Error
- Run: `pip install google-genai python-dotenv`
- Make sure you're in the correct Python environment

### API Rate Limit Exceeded
- You've exceeded the free tier limits (15 requests per minute)
- Wait a minute before making more requests
- Consider upgrading to a paid plan for higher limits

### No Data Showing
- Ensure you've made at least one API call through the Investment Assessment page
- Check that your Gemini API key is properly configured
- Verify the `data/gemini_usage.json` file exists and has content

### High Costs
- Review the operations breakdown to identify expensive operations
- Check the symbol analysis for high-usage stocks
- Consider reducing analysis frequency

### Rate Limit Warnings
- Reduce the frequency of API calls
- Implement delays between requests
- Monitor the rate limit status closely

### Data Export Issues
- Ensure you have data for the selected time period
- Check file permissions for the data directory
- Try refreshing the page and exporting again

## 📁 File Structure

```
Portfolio_Dashboard/
├── gemini_monitor.py              # Core monitoring utilities
├── pages/
│   └── 8_Usage_Monitoring.py     # Monitoring dashboard page
├── data/
│   └── gemini_usage.json         # Usage data storage
└── GEMINI_API_COMPLETE.md        # This guide
```

## 🔄 Updates and Maintenance

### Regular Maintenance
- Clear old data periodically (90+ days)
- Monitor for unusual usage patterns
- Update pricing if Gemini changes rates

### Adding New Operations
To track new types of API calls:
1. Add the operation name to your API call logging
2. Update the monitoring dashboard if needed
3. The system will automatically track the new operation

### Backup Data
- The `data/gemini_usage.json` file contains all your usage data
- Consider backing up this file regularly
- Data can be exported as CSV for external analysis

## 🆘 Support

If you encounter issues:
1. Check the troubleshooting section above
2. Verify your Gemini API key is working
3. Ensure all required packages are installed
4. Check the Streamlit logs for error messages

## 📈 Future Enhancements

Potential improvements:
- Email alerts for high usage
- Integration with Google Cloud Console
- Advanced cost forecasting
- Custom usage thresholds
- API key rotation support

## 🎯 Usage Examples

### Using AI Assessment

1. **Start your Portfolio Dashboard:**
   ```bash
   streamlit run Portfolio.py
   ```

2. **Navigate to the Investment Assessment page** (page 7 in the sidebar)

3. **Select a stock symbol** and click "Run Assessment"

4. **Click "Generate AI Assessment"** to get AI-powered buy/sell/hold recommendations

### Understanding AI Recommendations

The AI Assessment page provides:
- **Technical Analysis:** RSI, MACD, Bollinger Bands, Moving Averages, OBV
- **Fundamental Analysis:** P/E ratios, financial metrics, growth rates
- **AI Recommendations:** BUY/SELL/HOLD with confidence levels and reasoning
- **Combined Analysis:** Radar chart showing overall assessment

## Free Tier Limits

- **Free Tier:** 15 requests per minute, 1 million tokens per day
- **Paid Tier:** Higher rate limits and additional features available

## Security Notes

- Never commit your `.env` file to version control
- Keep your API token secure and don't share it
- The `.env` file is already included in `.gitignore` for security

## API Call Costs Summary

| Action | API Calls |
|--------|-----------|
| Investment Assessment | 1 |
| Usage Monitoring Check | 0 (cached) |
| Data Export | 0 |
| Clear Old Data | 0 |

## Best Practices

### Efficient Usage

1. **Check usage at start of session** (1 call)
2. **Use cached data** for planning (0 calls)
3. **Run multiple analyses** without rechecking (0 calls)
4. **Recheck periodically** to sync with server (1 call)

### Strategic Analysis

1. **Morning check** - Plan your day's analyses
2. **Batch analyze** - Do multiple stocks in one session
3. **End-of-day check** - Verify remaining usage
4. **Monthly review** - Track usage patterns

### Cost Optimization

1. **Free plan users:**
   - ~3 analyses/day = 90/month
   - Monitor usage 1x/day
   - Use strategically

2. **Paid plan users:**
   - More freedom with frequency
   - Can check usage more frequently
   - Higher analysis counts

---

**Happy Monitoring! 📊✨**

Your Gemini API usage is now fully tracked and optimized. Use the monitoring dashboard to understand your usage patterns and control costs effectively.

**Ready to get started?**

```bash
# 1. Install packages
pip install google-genai python-dotenv

# 2. Configure your API key in .env file
echo "GEMINI_API_KEY=your_actual_api_token_here" >> .env

# 3. Start the app
streamlit run Portfolio.py
```

**Enjoy your AI-powered investment analysis!** 🚀
