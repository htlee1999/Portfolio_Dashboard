# Gemini API Token Usage Monitoring Setup

This guide explains how to set up and use the comprehensive Gemini API token monitoring system in your Portfolio Dashboard.

## 🎯 Overview

The monitoring system provides:
- **Real-time token usage tracking** for all Gemini API calls
- **Cost analysis** with detailed breakdowns by operation and symbol
- **Rate limit monitoring** to prevent API quota exceeded errors
- **Usage trends** with interactive charts and visualizations
- **Export functionality** for detailed usage reports
- **Automated recommendations** for cost optimization

## 📊 Features

### 1. Usage Dashboard
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

## 🚀 Getting Started

### 1. Prerequisites
The monitoring system is automatically available when you have:
- ✅ Google Gemini API configured (see `GEMINI_SETUP.md` in the documentations folder)
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
└── GEMINI_MONITORING_SETUP.md    # This guide
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

---

**Happy Monitoring! 📊✨**

Your Gemini API usage is now fully tracked and optimized. Use the monitoring dashboard to understand your usage patterns and control costs effectively.
