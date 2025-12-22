import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import yfinance as yf
from datetime import datetime

from app_utils import get_stock_data, format_currency, apply_chart_style
from technical_indicators import TechnicalAnalysis
from page_utils import init_protected_page
from config import PERIOD_OPTIONS


def create_rsi_chart(data, rsi):
    """Create RSI chart with overbought/oversold levels."""
    fig = go.Figure()
    
    # RSI line
    fig.add_trace(go.Scatter(
        x=data.index,
        y=rsi,
        mode='lines',
        name='RSI',
        line=dict(color='blue', width=2)
    ))
    
    # Overbought level
    fig.add_hline(y=70, line_dash="dash", line_color="red", 
                  annotation_text="Overbought (70)", annotation_position="top right")
    
    # Oversold level
    fig.add_hline(y=30, line_dash="dash", line_color="green", 
                  annotation_text="Oversold (30)", annotation_position="bottom right")
    
    # Neutral zone
    fig.add_hrect(y0=30, y1=70, fillcolor="lightgray", opacity=0.2, 
                  annotation_text="Neutral Zone", annotation_position="top left")
    
    fig.update_layout(
        title="Relative Strength Index (RSI)",
        xaxis_title="Date",
        yaxis_title="RSI",
        yaxis=dict(range=[0, 100]),
        height=400
    )
    
    return fig


def create_macd_chart(data, macd_line, signal_line, histogram):
    """Create MACD chart with signal line and histogram."""
    fig = make_subplots(rows=2, cols=1, 
                        subplot_titles=('MACD Line & Signal', 'MACD Histogram'),
                        vertical_spacing=0.1)
    
    # Check if MACD data is valid
    if macd_line.empty or macd_line.isna().all():
        fig.add_annotation(
            text="No MACD data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="red")
        )
        return fig
    
    # MACD and Signal lines
    fig.add_trace(go.Scatter(
        x=data.index,
        y=macd_line,
        mode='lines',
        name='MACD',
        line=dict(color='blue', width=2)
    ), row=1, col=1)
    
    fig.add_trace(go.Scatter(
        x=data.index,
        y=signal_line,
        mode='lines',
        name='Signal',
        line=dict(color='red', width=2)
    ), row=1, col=1)
    
    # Zero line for MACD
    fig.add_hline(y=0, line_dash="dash", line_color="gray", row=1, col=1)
    
    # Histogram
    if not histogram.empty and not histogram.isna().all():
        colors = ['green' if val >= 0 else 'red' for val in histogram]
        fig.add_trace(go.Bar(
            x=data.index,
            y=histogram,
            name='Histogram',
            marker_color=colors
        ), row=2, col=1)
        
        # Zero line for histogram
        fig.add_hline(y=0, line_dash="dash", line_color="black", row=2, col=1)
    
    # Update layout with better formatting
    fig.update_layout(
        title="MACD (Moving Average Convergence Divergence)",
        height=600,
        showlegend=True,
        xaxis_title="Date",
        yaxis_title="MACD Value",
        yaxis2_title="Histogram Value"
    )
    
    # Format y-axis to show more decimal places for small values
    fig.update_yaxes(tickformat=".4f", row=1, col=1)
    fig.update_yaxes(tickformat=".4f", row=2, col=1)
    
    return fig


def create_bollinger_bands_chart(data, prices, upper_bb, middle_bb, lower_bb):
    """Create Bollinger Bands chart with price and bands."""
    fig = go.Figure()
    
    # Price line
    fig.add_trace(go.Scatter(
        x=data.index,
        y=prices,
        mode='lines',
        name='Price',
        line=dict(color='blue', width=2)
    ))
    
    # Bollinger Bands
    fig.add_trace(go.Scatter(
        x=data.index,
        y=upper_bb,
        mode='lines',
        name='Upper Band',
        line=dict(color='red', width=1, dash='dash')
    ))
    
    fig.add_trace(go.Scatter(
        x=data.index,
        y=middle_bb,
        mode='lines',
        name='Middle Band (SMA)',
        line=dict(color='orange', width=1)
    ))
    
    fig.add_trace(go.Scatter(
        x=data.index,
        y=lower_bb,
        mode='lines',
        name='Lower Band',
        line=dict(color='red', width=1, dash='dash'),
        fill='tonexty',
        fillcolor='rgba(255,0,0,0.1)'
    ))
    
    apply_chart_style(fig, "Bollinger Bands", height=500, yaxis_title="Price")
    
    return fig


def create_moving_averages_chart(data, prices, mas):
    """Create Moving Averages chart."""
    fig = go.Figure()
    
    # Price line
    fig.add_trace(go.Scatter(
        x=data.index,
        y=prices,
        mode='lines',
        name='Price',
        line=dict(color='black', width=2)
    ))
    
    # Moving Averages
    colors = ['red', 'blue', 'green', 'orange', 'purple', 'brown', 'pink', 'gray']
    for i, (name, ma) in enumerate(mas.items()):
        fig.add_trace(go.Scatter(
            x=data.index,
            y=ma,
            mode='lines',
            name=name,
            line=dict(color=colors[i % len(colors)], width=1)
        ))
    
    apply_chart_style(fig, "Moving Averages", height=500, yaxis_title="Price")
    
    return fig


def create_obv_chart(data, obv):
    """Create OBV chart."""
    fig = go.Figure()
    
    # OBV line
    fig.add_trace(go.Scatter(
        x=data.index,
        y=obv,
        mode='lines',
        name='OBV',
        line=dict(color='purple', width=2)
    ))
    
    # OBV EMA for trend
    obv_ema = obv.ewm(span=10).mean()
    fig.add_trace(go.Scatter(
        x=data.index,
        y=obv_ema,
        mode='lines',
        name='OBV EMA(10)',
        line=dict(color='orange', width=1, dash='dash')
    ))
    
    apply_chart_style(fig, "On-Balance Volume (OBV)", height=400, yaxis_title="OBV")
    
    return fig


def main():
    """Main technical analysis page."""
    # Initialize protected page (handles auth, setup, CSS, sidebar, user menu)
    init_protected_page()

    st.markdown('<h1 class="main-header">📈 Technical Analysis</h1>', unsafe_allow_html=True)
    
    # Add explanation section
    with st.expander("📚 Technical Analysis Guide - How to Read Each Indicator", expanded=False):
        st.markdown("""
        ### Understanding Technical Analysis Indicators
        
        Technical analysis uses mathematical calculations based on price and volume data to predict future price movements. 
        Here's how to interpret each indicator in your analysis:
        """)
        
        # RSI Explanation
        st.markdown("""
        #### 1. RSI (Relative Strength Index) 📊
        **What it measures:** Speed and magnitude of price changes to identify overbought/oversold conditions.
        
        **How to read:**
        - **Above 70:** Overbought (price may be too high) 🔴
        - **Below 30:** Oversold (price may be too low) 🟢
        - **30-70:** Neutral zone (normal trading range) ⚪
        
        **Trading signals:**
        - **Buy opportunity:** RSI below 30 (potential bounce)
        - **Sell opportunity:** RSI above 70 (potential pullback)
        - **Warning:** RSI staying in extreme zones for extended periods
        """)
        
        # MACD Explanation
        st.markdown("""
        #### 2. MACD (Moving Average Convergence Divergence) 📈
        **What it measures:** Relationship between two moving averages to identify momentum changes.
        
        **Components:**
        - **MACD Line:** 12-day EMA minus 26-day EMA
        - **Signal Line:** 9-day EMA of MACD line
        - **Histogram:** Difference between MACD and Signal lines
        
        **How to read:**
        - **MACD > Signal:** Bullish momentum 🟢
        - **MACD < Signal:** Bearish momentum 🔴
        - **MACD crosses above Signal:** Buy signal 📈
        - **MACD crosses below Signal:** Sell signal 📉
        - **Histogram above zero:** Increasing bullish momentum
        - **Histogram below zero:** Increasing bearish momentum
        """)
        
        # Bollinger Bands Explanation
        st.markdown("""
        #### 3. Bollinger Bands 📏
        **What it measures:** Price volatility and potential support/resistance levels.
        
        **Components:**
        - **Upper Band:** 20-day SMA + 2 standard deviations
        - **Middle Band:** 20-day Simple Moving Average
        - **Lower Band:** 20-day SMA - 2 standard deviations
        
        **How to read:**
        - **Price touches upper band:** Potentially overbought 🔴
        - **Price touches lower band:** Potentially oversold 🟢
        - **Bands squeeze together:** Low volatility (breakout coming) ⚡
        - **Bands expand:** High volatility 📊
        - **Price between bands:** Normal trading range ⚪
        
        **Trading signals:**
        - **Buy:** Price bouncing off lower band
        - **Sell:** Price touching upper band
        - **Watch:** Band squeeze (potential breakout)
        """)
        
        # Moving Averages Explanation
        st.markdown("""
        #### 4. Moving Averages 📊
        **What it measures:** Trend direction and strength by smoothing price data.
        
        **Types:**
        - **SMA (Simple Moving Average):** Equal weight to all periods
        - **EMA (Exponential Moving Average):** More weight to recent prices
        
        **How to read:**
        - **Price above MA:** Uptrend 🟢
        - **Price below MA:** Downtrend 🔴
        - **Shorter MA above longer MA:** Bullish trend (Golden Cross) 📈
        - **Shorter MA below longer MA:** Bearish trend (Death Cross) 📉
        - **MA slope upward:** Strengthening trend
        - **MA slope downward:** Weakening trend
        
        **Trading signals:**
        - **Strong buy:** Price above multiple MAs + Golden Cross
        - **Strong sell:** Price below multiple MAs + Death Cross
        """)
        
        # OBV Explanation
        st.markdown("""
        #### 5. OBV (On-Balance Volume) 📊
        **What it measures:** Buying and selling pressure by tracking volume flow.
        
        **How it works:**
        - Adds volume on up days
        - Subtracts volume on down days
        - Shows cumulative volume flow
        
        **How to read:**
        - **OBV rising:** Buying pressure increasing 🟢
        - **OBV falling:** Selling pressure increasing 🔴
        - **OBV above its EMA:** Bullish momentum 📈
        - **OBV below its EMA:** Bearish momentum 📉
        - **OBV diverging from price:** Potential trend reversal ⚠️
        
        **Trading signals:**
        - **Confirms uptrend:** OBV rising with price
        - **Warning sign:** OBV falling while price rises (bearish divergence)
        """)
        
        # Trading Signals Guide
        st.markdown("""
        ### 🎯 Key Trading Signals to Watch For
        
        **Strong Buy Signal:** 
        - RSI < 30 + MACD bullish crossover + Price near lower Bollinger Band
        
        **Strong Sell Signal:** 
        - RSI > 70 + MACD bearish crossover + Price near upper Bollinger Band
        
        **Trend Confirmation:** 
        - Price above multiple MAs + OBV rising + MACD above signal line
        
        **Reversal Warning:** 
        - Divergence between price and OBV + RSI in extreme zones
        
        ### ⚠️ Important Notes
        - **Never rely on a single indicator** - Always look for confirmation across multiple indicators
        - **Consider market context** - Indicators work better in trending vs. sideways markets
        - **Use proper risk management** - Set stop losses and position sizes appropriately
        - **Practice with paper trading** before using real money
        """)
    
    # Get selected symbol from sidebar
    symbol = st.session_state.get("selected_stock", "AAPL")
    
    # Handle quick analyze from sidebar button
    if 'quick_analyze' in st.session_state:
        symbol = st.session_state.quick_analyze
        del st.session_state.quick_analyze  # Clear the quick analyze flag
        # Automatically trigger analysis
        st.session_state.auto_analyze = True
    
    # Analysis parameters
    st.subheader("Analysis Settings")
    
    col1, col2 = st.columns([1, 1])
    with col1:
        st.info(f"**Selected Stock:** {symbol}")
    with col2:
        # Time period selection
        selected_period = st.selectbox("Time Period", list(PERIOD_OPTIONS.keys()))
        period = PERIOD_OPTIONS[selected_period]
    
    # Analysis parameters
    st.subheader("Indicator Parameters")
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        rsi_period = st.slider("RSI Period", 5, 30, 14)
    with col2:
        macd_fast = st.slider("MACD Fast Period", 5, 20, 12)
    with col3:
        macd_slow = st.slider("MACD Slow Period", 15, 50, 26)
    with col4:
        bb_period = st.slider("Bollinger Bands Period", 10, 30, 20)
    with col5:
        bb_std = st.slider("Bollinger Bands Std Dev", 1.0, 3.0, 2.0)
    
    
    # Fetch data
    analyze_clicked = st.button("Analyze", type="primary")
    auto_analyze = st.session_state.get('auto_analyze', False)
    
    if analyze_clicked or auto_analyze:
        if auto_analyze:
            del st.session_state.auto_analyze  # Clear the auto analyze flag
            
        with st.spinner(f"Fetching data for {symbol}..."):
            data, info = get_stock_data(symbol, period)
            
            if data is None or data.empty:
                st.error(f"Could not fetch data for {symbol}. Please check the symbol and try again.")
                return
            
            # Store data in session state
            st.session_state.ta_data = data
            st.session_state.ta_symbol = symbol
            st.session_state.ta_info = info
    
    # Display analysis if data is available
    if 'ta_data' in st.session_state and not st.session_state.ta_data.empty:
        data = st.session_state.ta_data
        symbol = st.session_state.ta_symbol
        info = st.session_state.ta_info
        
        # Add back button and symbol info
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            if st.button("← Back to Selection", type="secondary"):
                # Clear the analysis data to go back to selection
                if 'ta_data' in st.session_state:
                    del st.session_state.ta_data
                if 'ta_symbol' in st.session_state:
                    del st.session_state.ta_symbol
                if 'ta_info' in st.session_state:
                    del st.session_state.ta_info
                st.rerun()
        with col2:
            st.markdown(f"<h2 style='text-align: center; color: #1f77b4;'>{symbol} Technical Analysis</h2>", unsafe_allow_html=True)
        with col3:
            if st.button("🔄 Refresh Data", type="secondary"):
                # Clear cached data to force refresh
                if 'ta_data' in st.session_state:
                    del st.session_state.ta_data
                st.rerun()
        
        st.markdown("---")
        
        # Initialize technical analysis
        ta = TechnicalAnalysis(data)
        
        # Display stock info
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Current Price", f"${data['Close'].iloc[-1]:.2f}")
        with col2:
            price_change = data['Close'].iloc[-1] - data['Close'].iloc[-2]
            st.metric("Daily Change", f"${price_change:.2f}")
        with col3:
            price_change_pct = (price_change / data['Close'].iloc[-2]) * 100
            st.metric("Daily Change %", f"{price_change_pct:.2f}%")
        with col4:
            st.metric("Volume", f"{data['Volume'].iloc[-1]:,}")
        
        # Calculate indicators
        rsi = ta.calculate_rsi(rsi_period)
        macd_line, signal_line, histogram = ta.calculate_macd(macd_fast, macd_slow)
        upper_bb, middle_bb, lower_bb, bb_percent, band_width = ta.calculate_bollinger_bands(bb_period, bb_std)
        mas = ta.calculate_moving_averages()
        obv = ta.calculate_obv()
        
        # Get signals
        signals = ta.get_signals()
        
        # Quick Reference Guide
        with st.expander("🔍 Quick Reference - What Do These Signals Mean?", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("""
                **RSI Signals:**
                - 🔴 Overbought (>70): Consider selling
                - 🟢 Oversold (<30): Consider buying
                - ⚪ Neutral (30-70): Normal range
                
                **MACD Signals:**
                - 🟢 MACD > Signal: Bullish momentum
                - 🔴 MACD < Signal: Bearish momentum
                - 📈 Crossover up: Buy signal
                - 📉 Crossover down: Sell signal
                """)
            
            with col2:
                st.markdown("""
                **Bollinger Bands:**
                - 🔴 Above upper band: Overbought
                - 🟢 Below lower band: Oversold
                - ⚡ Squeeze: Low volatility (breakout coming)
                
                **Moving Averages:**
                - 🟢 Price above MAs: Uptrend
                - 🔴 Price below MAs: Downtrend
                - 📈 Golden Cross: Strong buy signal
                """)
        
        # Display current signals
        st.subheader("Current Signals")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.write("**RSI Signals**")
            current_rsi = signals['rsi']['current_value']
            if current_rsi:
                if current_rsi > 70:
                    st.error(f"Overbought: {current_rsi:.2f}")
                elif current_rsi < 30:
                    st.success(f"Oversold: {current_rsi:.2f}")
                else:
                    st.info(f"Neutral: {current_rsi:.2f}")
        
        with col2:
            st.write("**MACD Signals**")
            current_macd = signals['macd']['current_macd']
            current_signal = signals['macd']['current_signal']
            if current_macd and current_signal:
                if current_macd > current_signal:
                    st.success("Bullish (MACD > Signal)")
                else:
                    st.error("Bearish (MACD < Signal)")
        
        with col3:
            st.write("**Bollinger Bands**")
            current_bb_percent = signals['bollinger']['current_bb_percent']
            if current_bb_percent:
                if current_bb_percent > 1:
                    st.error("Above Upper Band")
                elif current_bb_percent < 0:
                    st.success("Below Lower Band")
                else:
                    st.info(f"Within Bands: {current_bb_percent:.2f}")
        
        # Charts
        st.subheader("Technical Analysis Charts")
        
        # RSI Chart
        st.plotly_chart(create_rsi_chart(data, rsi), use_container_width=True)
        
        # MACD Chart
        # Debug MACD values
        if not macd_line.empty and not macd_line.isna().all():
            st.write(f"**MACD Debug Info:**")
            st.write(f"MACD Range: {macd_line.min():.6f} to {macd_line.max():.6f}")
            st.write(f"Signal Range: {signal_line.min():.6f} to {signal_line.max():.6f}")
            st.write(f"Histogram Range: {histogram.min():.6f} to {histogram.max():.6f}")
        
        st.plotly_chart(create_macd_chart(data, macd_line, signal_line, histogram), use_container_width=True)
        
        # Bollinger Bands Chart
        st.plotly_chart(create_bollinger_bands_chart(data, data['Close'], upper_bb, middle_bb, lower_bb), use_container_width=True)
        
        # Moving Averages Chart
        st.plotly_chart(create_moving_averages_chart(data, data['Close'], mas), use_container_width=True)
        
        # OBV Chart
        if not obv.empty:
            st.plotly_chart(create_obv_chart(data, obv), use_container_width=True)
        
        # Detailed Analysis
        st.subheader("Detailed Analysis")
        
        # Create tabs for different analysis views
        tab1, tab2, tab3 = st.tabs(["Indicator Values", "Signal History", "Data Export"])
        
        with tab1:
            st.write("**Current Indicator Values**")
            
            # Create a summary DataFrame
            summary_data = {
                'Indicator': ['RSI', 'MACD', 'MACD Signal', 'BB Upper', 'BB Middle', 'BB Lower', 'BB %', 'OBV'],
                'Current Value': [
                    f"{rsi.iloc[-1]:.2f}" if not rsi.empty else "N/A",
                    f"{macd_line.iloc[-1]:.4f}" if not macd_line.empty else "N/A",
                    f"{signal_line.iloc[-1]:.4f}" if not signal_line.empty else "N/A",
                    f"${upper_bb.iloc[-1]:.2f}" if not upper_bb.empty else "N/A",
                    f"${middle_bb.iloc[-1]:.2f}" if not middle_bb.empty else "N/A",
                    f"${lower_bb.iloc[-1]:.2f}" if not lower_bb.empty else "N/A",
                    f"{bb_percent.iloc[-1]:.2f}" if not bb_percent.empty else "N/A",
                    f"{obv.iloc[-1]:,.0f}" if not obv.empty else "N/A"
                ]
            }
            
            summary_df = pd.DataFrame(summary_data)
            st.dataframe(summary_df, use_container_width=True)
        
        with tab2:
            st.write("**Signal Analysis Over Time**")
            
            # Create signals DataFrame
            signals_df = pd.DataFrame({
                'Date': data.index,
                'Price': data['Close'],
                'RSI': rsi,
                'MACD': macd_line,
                'MACD_Signal': signal_line,
                'BB_Upper': upper_bb,
                'BB_Lower': lower_bb,
                'BB_Percent': bb_percent,
                'OBV': obv
            })
            
            # Add signal columns
            signals_df['RSI_Overbought'] = signals_df['RSI'] > 70
            signals_df['RSI_Oversold'] = signals_df['RSI'] < 30
            signals_df['MACD_Bullish'] = signals_df['MACD'] > signals_df['MACD_Signal']
            signals_df['Price_Above_BB'] = signals_df['Price'] > signals_df['BB_Upper']
            signals_df['Price_Below_BB'] = signals_df['Price'] < signals_df['BB_Lower']
            
            st.dataframe(signals_df.tail(20), use_container_width=True)
        
        with tab3:
            st.write("**Export Analysis Data**")
            
            # Add all indicators to data
            data_with_indicators = ta.add_all_indicators()
            
            # Download button
            csv = data_with_indicators.to_csv()
            st.download_button(
                label="Download Complete Analysis Data (CSV)",
                data=csv,
                file_name=f"{symbol}_technical_analysis_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
    
    else:
        st.info("👆 Select a stock from the sidebar and click 'Analyze' to begin technical analysis")


if __name__ == "__main__":
    main()
