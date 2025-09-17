import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import yfinance as yf
from datetime import datetime

from app_utils import setup_page, inject_css, init_session_state, create_sidebar, get_stock_data, format_currency
from auth_utils import show_user_menu


class TechnicalAnalysis:
    """Comprehensive technical analysis class implementing the top 5 indicators."""
    
    def __init__(self, data):
        """
        Initialize with price data.
        
        Args:
            data (pd.DataFrame): OHLCV data with columns ['Open', 'High', 'Low', 'Close', 'Volume']
        """
        self.data = data.copy()
        self.prices = data['Close']
        self.volumes = data['Volume'] if 'Volume' in data.columns else None
        
    def calculate_rsi(self, period=14):
        """
        Calculate Relative Strength Index (RSI).
        
        Args:
            period (int): RSI calculation period (default: 14)
            
        Returns:
            pd.Series: RSI values
        """
        delta = self.prices.diff()
        gains = delta.where(delta > 0, 0)
        losses = -delta.where(delta < 0, 0)
        
        avg_gains = gains.ewm(span=period, min_periods=period).mean()
        avg_losses = losses.ewm(span=period, min_periods=period).mean()
        
        rs = avg_gains / avg_losses
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def calculate_macd(self, fast_period=12, slow_period=26, signal_period=9):
        """
        Calculate MACD (Moving Average Convergence Divergence).
        
        Args:
            fast_period (int): Fast EMA period (default: 12)
            slow_period (int): Slow EMA period (default: 26)
            signal_period (int): Signal line EMA period (default: 9)
            
        Returns:
            tuple: (macd_line, signal_line, histogram)
        """
        ema_fast = self.prices.ewm(span=fast_period, min_periods=fast_period).mean()
        ema_slow = self.prices.ewm(span=slow_period, min_periods=slow_period).mean()
        
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal_period, min_periods=signal_period).mean()
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    def calculate_bollinger_bands(self, period=20, std_dev=2):
        """
        Calculate Bollinger Bands.
        
        Args:
            period (int): Moving average period (default: 20)
            std_dev (float): Standard deviation multiplier (default: 2)
            
        Returns:
            tuple: (upper_band, middle_band, lower_band, %B, band_width)
        """
        middle_band = self.prices.rolling(window=period).mean()
        rolling_std = self.prices.rolling(window=period).std()
        
        upper_band = middle_band + (rolling_std * std_dev)
        lower_band = middle_band - (rolling_std * std_dev)
        
        # Calculate %B (Bollinger Band percentage)
        bb_percent = (self.prices - lower_band) / (upper_band - lower_band)
        
        # Calculate Band Width (volatility measure)
        band_width = (upper_band - lower_band) / middle_band
        
        return upper_band, middle_band, lower_band, bb_percent, band_width
    
    def calculate_moving_averages(self, periods=[5, 10, 20, 50]):
        """
        Calculate Simple and Exponential Moving Averages.
        
        Args:
            periods (list): List of periods to calculate (default: [5, 10, 20, 50])
            
        Returns:
            dict: Dictionary with SMA and EMA for each period
        """
        mas = {}
        for period in periods:
            mas[f'SMA_{period}'] = self.prices.rolling(window=period).mean()
            mas[f'EMA_{period}'] = self.prices.ewm(span=period, min_periods=period).mean()
        return mas
    
    def calculate_obv(self):
        """
        Calculate On-Balance Volume (OBV).
        
        Returns:
            pd.Series: OBV values
        """
        if self.volumes is None:
            return pd.Series(index=self.prices.index, dtype=float)
        
        obv = [0]
        for i in range(1, len(self.prices)):
            if self.prices.iloc[i] > self.prices.iloc[i-1]:
                obv.append(obv[-1] + self.volumes.iloc[i])
            elif self.prices.iloc[i] < self.prices.iloc[i-1]:
                obv.append(obv[-1] - self.volumes.iloc[i])
            else:
                obv.append(obv[-1])
        
        return pd.Series(obv, index=self.prices.index)
    
    def get_signals(self):
        """
        Generate trading signals for all indicators.
        
        Returns:
            dict: Dictionary with signals for each indicator
        """
        signals = {}
        
        # RSI Signals
        rsi = self.calculate_rsi()
        signals['rsi'] = {
            'overbought': rsi > 70,
            'oversold': rsi < 30,
            'neutral': (rsi >= 30) & (rsi <= 70),
            'current_value': rsi.iloc[-1] if not rsi.empty else None
        }
        
        # MACD Signals
        macd_line, signal_line, histogram = self.calculate_macd()
        signals['macd'] = {
            'bullish_crossover': (macd_line > signal_line) & (macd_line.shift(1) <= signal_line.shift(1)),
            'bearish_crossover': (macd_line < signal_line) & (macd_line.shift(1) >= signal_line.shift(1)),
            'above_signal': macd_line > signal_line,
            'current_macd': macd_line.iloc[-1] if not macd_line.empty else None,
            'current_signal': signal_line.iloc[-1] if not signal_line.empty else None
        }
        
        # Bollinger Bands Signals
        upper_bb, middle_bb, lower_bb, bb_percent, band_width = self.calculate_bollinger_bands()
        signals['bollinger'] = {
            'above_upper': self.prices > upper_bb,
            'below_lower': self.prices < lower_bb,
            'squeeze': band_width < band_width.rolling(20).mean() * 0.5,  # Low volatility
            'current_bb_percent': bb_percent.iloc[-1] if not bb_percent.empty else None,
            'current_band_width': band_width.iloc[-1] if not band_width.empty else None
        }
        
        # Moving Average Signals
        mas = self.calculate_moving_averages()
        signals['moving_averages'] = {}
        for name, ma in mas.items():
            signals['moving_averages'][name] = {
                'price_above': self.prices > ma,
                'current_value': ma.iloc[-1] if not ma.empty else None
            }
        
        # OBV Signals
        obv = self.calculate_obv()
        obv_ema = obv.ewm(span=10).mean()
        signals['obv'] = {
            'rising': obv > obv_ema,
            'falling': obv < obv_ema,
            'current_value': obv.iloc[-1] if not obv.empty else None
        }
        
        return signals
    
    def add_all_indicators(self):
        """
        Add all technical indicators to the data DataFrame.
        
        Returns:
            pd.DataFrame: Data with all indicators added
        """
        data_with_indicators = self.data.copy()
        
        # RSI
        data_with_indicators['RSI'] = self.calculate_rsi()
        
        # MACD
        macd_line, signal_line, histogram = self.calculate_macd()
        data_with_indicators['MACD'] = macd_line
        data_with_indicators['MACD_Signal'] = signal_line
        data_with_indicators['MACD_Histogram'] = histogram
        
        # Bollinger Bands
        upper_bb, middle_bb, lower_bb, bb_percent, band_width = self.calculate_bollinger_bands()
        data_with_indicators['BB_Upper'] = upper_bb
        data_with_indicators['BB_Middle'] = middle_bb
        data_with_indicators['BB_Lower'] = lower_bb
        data_with_indicators['BB_Percent'] = bb_percent
        data_with_indicators['BB_Width'] = band_width
        
        # Moving Averages
        mas = self.calculate_moving_averages()
        for name, ma in mas.items():
            data_with_indicators[name] = ma
        
        # OBV
        data_with_indicators['OBV'] = self.calculate_obv()
        
        return data_with_indicators


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
    
    fig.update_layout(
        title="Bollinger Bands",
        xaxis_title="Date",
        yaxis_title="Price",
        height=500
    )
    
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
    
    fig.update_layout(
        title="Moving Averages",
        xaxis_title="Date",
        yaxis_title="Price",
        height=500
    )
    
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
    
    fig.update_layout(
        title="On-Balance Volume (OBV)",
        xaxis_title="Date",
        yaxis_title="OBV",
        height=400
    )
    
    return fig


def main():
    """Main technical analysis page."""
    setup_page()
    inject_css()
    init_session_state()
    create_sidebar()
    show_user_menu()
    
    # Check authentication
    if not st.session_state.get("authenticated", False):
        st.warning("🔐 Please log in to access the Technical Analysis page")
        st.info("Use the Login page in the sidebar to authenticate")
        return
    
    st.markdown('<h1 class="main-header">📈 Technical Analysis</h1>', unsafe_allow_html=True)
    
    # Main content area for symbol selection and analysis parameters
    st.subheader("Analysis Settings")
    
    # Get symbols from portfolio or allow manual input
    portfolio = st.session_state.get("portfolio", pd.DataFrame())
    if not portfolio.empty:
        portfolio_symbols = portfolio['Symbol'].unique().tolist()
        symbol_options = portfolio_symbols + ["Custom Symbol"]
    else:
        symbol_options = ["Custom Symbol"]
    
    # Handle quick analyze from portfolio buttons
    if 'quick_analyze' in st.session_state:
        symbol = st.session_state.quick_analyze
        del st.session_state.quick_analyze  # Clear the quick analyze flag
        # Automatically trigger analysis
        st.session_state.auto_analyze = True
    else:
        col1, col2 = st.columns([1, 1])
        with col1:
            selected_option = st.selectbox("Select Symbol", symbol_options)
            
            if selected_option == "Custom Symbol":
                symbol = st.text_input("Enter Stock Symbol", value="AAPL").upper()
            else:
                symbol = selected_option
        
        with col2:
            # Time period selection
            period_options = {
                "1 Month": "1mo",
                "3 Months": "3mo", 
                "6 Months": "6mo",
                "1 Year": "1y",
                "2 Years": "2y",
                "5 Years": "5y"
            }
            selected_period = st.selectbox("Time Period", list(period_options.keys()))
            period = period_options[selected_period]
    
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
    
    # Quick symbol switcher (only show when analysis is active)
    if 'ta_data' in st.session_state and not st.session_state.ta_data.empty:
        st.markdown("---")
        st.subheader("Quick Switch")
        st.write("Switch to another symbol:")
        
        # Show portfolio symbols for quick switching
        if not portfolio.empty:
            cols = st.columns(min(6, len(portfolio_symbols)))
            for i, sym in enumerate(portfolio_symbols[:6]):  # Show first 6 symbols
                with cols[i]:
                    if st.button(f"📈 {sym}", key=f"quick_switch_{sym}"):
                        st.session_state.quick_analyze = sym
                        st.rerun()
        
        if st.button("➕ Custom Symbol", key="quick_custom"):
            # Clear analysis to go back to selection
            if 'ta_data' in st.session_state:
                del st.session_state.ta_data
            st.rerun()
    
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
        st.info("👆 Select a symbol and click 'Analyze' to begin technical analysis")
        
        # Show portfolio symbols if available
        if not portfolio.empty:
            st.subheader("Your Portfolio Symbols")
            st.write("Quick access to analyze stocks in your portfolio:")
            
            cols = st.columns(min(len(portfolio_symbols), 4))
            for i, sym in enumerate(portfolio_symbols):
                with cols[i % 4]:
                    if st.button(f"Analyze {sym}", key=f"analyze_{sym}"):
                        st.session_state.quick_analyze = sym
                        st.rerun()


if __name__ == "__main__":
    main()
