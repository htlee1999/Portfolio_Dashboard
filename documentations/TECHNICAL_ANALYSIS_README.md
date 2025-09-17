# Technical Analysis Module

This module provides comprehensive technical analysis capabilities for the Portfolio Dashboard, implementing the top 5 most effective technical indicators used by professional traders and analysts.

## Features

### 📊 Implemented Indicators

1. **RSI (Relative Strength Index)**
   - Identifies overbought (>70) and oversold (<30) conditions
   - Uses exponential moving averages for responsive calculations
   - Configurable period (default: 14)

2. **MACD (Moving Average Convergence Divergence)**
   - Shows momentum and trend changes
   - Includes MACD line, signal line, and histogram
   - Configurable periods (default: 12, 26, 9)

3. **Bollinger Bands**
   - Identifies price volatility and potential breakouts
   - Includes %B calculation and band width analysis
   - Configurable period and standard deviation (default: 20, 2.0)

4. **Moving Averages (SMA & EMA)**
   - Multiple timeframes: 5, 10, 20, 50 periods
   - Both Simple and Exponential Moving Averages
   - Trend identification and support/resistance levels

5. **OBV (On-Balance Volume)**
   - Tracks volume flow and buying/selling pressure
   - Identifies divergences between price and volume
   - Includes trend analysis with EMA smoothing

### 🎯 Key Features

- **Interactive Charts**: Professional-grade visualizations using Plotly
- **Real-time Signals**: Automatic buy/sell signal detection
- **Portfolio Integration**: Analyze stocks from your existing portfolio
- **Customizable Parameters**: Adjust all indicator settings via sidebar
- **Data Export**: Download complete analysis data as CSV
- **Multiple Timeframes**: 1 month to 5 years of historical data

## Usage

### Accessing Technical Analysis

1. Navigate to the "Technical Analysis" page in the sidebar
2. Select a stock symbol (from portfolio or custom input)
3. Choose your preferred time period
4. Adjust indicator parameters if needed
5. Click "Analyze" to generate the analysis

### Understanding the Interface

#### Current Signals Panel
- **RSI Signals**: Shows overbought/oversold status
- **MACD Signals**: Indicates bullish/bearish momentum
- **Bollinger Bands**: Shows position within bands

#### Interactive Charts
- **RSI Chart**: With overbought/oversold levels
- **MACD Chart**: MACD line, signal line, and histogram
- **Bollinger Bands Chart**: Price with upper, middle, and lower bands
- **Moving Averages Chart**: Multiple MA timeframes
- **OBV Chart**: Volume flow analysis

#### Analysis Tabs
- **Indicator Values**: Current values for all indicators
- **Signal History**: Historical signal analysis
- **Data Export**: Download complete analysis data

## Technical Implementation

### TechnicalAnalysis Class

The core functionality is implemented in the `TechnicalAnalysis` class with the following methods:

```python
# Initialize with OHLCV data
ta = TechnicalAnalysis(data)

# Calculate individual indicators
rsi = ta.calculate_rsi(period=14)
macd_line, signal_line, histogram = ta.calculate_macd()
upper_bb, middle_bb, lower_bb, bb_percent, band_width = ta.calculate_bollinger_bands()
mas = ta.calculate_moving_averages()
obv = ta.calculate_obv()

# Get trading signals
signals = ta.get_signals()

# Add all indicators to data
data_with_indicators = ta.add_all_indicators()
```

### Signal Generation

The module automatically generates trading signals based on:

- **RSI**: Overbought (>70), Oversold (<30), Neutral (30-70)
- **MACD**: Bullish crossover (MACD > Signal), Bearish crossover (MACD < Signal)
- **Bollinger Bands**: Above upper band, Below lower band, Squeeze patterns
- **Moving Averages**: Price above/below MA, MA crossovers
- **OBV**: Rising/falling volume trends, divergences

### Chart Customization

All charts are built with Plotly for maximum interactivity:
- Zoom and pan functionality
- Hover tooltips with detailed information
- Professional styling and color schemes
- Responsive design for all screen sizes

## Dependencies

The technical analysis module requires the following packages:

```
streamlit>=1.28.0
pandas>=2.0.0
numpy>=1.24.0,<2.0.0
plotly>=5.0.0
yfinance>=0.2.0
matplotlib>=3.7.0
```

## Performance Optimization

- **Caching**: All data fetching is cached to improve performance
- **Vectorized Operations**: Uses pandas for efficient calculations
- **Memory Management**: Processes data in chunks for large datasets
- **Lazy Loading**: Charts are only generated when needed

## Best Practices

### For Trading Decisions
1. **Never rely on a single indicator** - Use multiple indicators for confirmation
2. **Consider market context** - Technical analysis works best with fundamental analysis
3. **Use appropriate timeframes** - Match your analysis to your trading horizon
4. **Backtest strategies** - Test your approach with historical data

### For Analysis
1. **Start with longer timeframes** - Get the big picture first
2. **Look for confluence** - Multiple indicators pointing in the same direction
3. **Consider volume** - Volume confirms price movements
4. **Watch for divergences** - When price and indicators move differently

## Troubleshooting

### Common Issues

1. **No data available**: Check if the symbol is valid and markets are open
2. **Charts not loading**: Ensure all dependencies are installed correctly
3. **Slow performance**: Try reducing the time period or using fewer indicators

### Error Messages

- **"Could not fetch data"**: Symbol may be invalid or data source unavailable
- **"Calculation error"**: Insufficient data for the selected period
- **"Import error"**: Missing required dependencies

## Future Enhancements

Planned improvements include:
- Additional indicators (Stochastic, Williams %R, CCI)
- Pattern recognition (Head & Shoulders, Triangles)
- Backtesting capabilities
- Alert system for signal notifications
- Mobile-optimized interface

## Support

For technical issues or feature requests, please refer to the main Portfolio Dashboard documentation or create an issue in the project repository.

---

*This technical analysis module is for educational and informational purposes only. It should not be considered as financial advice. Always do your own research and consider consulting with a financial advisor before making investment decisions.*
