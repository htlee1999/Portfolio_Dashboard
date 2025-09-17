import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import yfinance as yf
import os
from typing import Dict, Any, Optional

from app_utils import setup_page, inject_css, init_session_state, create_sidebar, get_stock_data, get_current_price
from auth_utils import show_user_menu
from data_utils import load_portfolio_data

# Import analysis classes from other pages
# We'll define simplified versions of the analysis classes here
# to avoid complex import issues in Streamlit pages

try:
    from google import genai
    from dotenv import load_dotenv
    GEMINI_AVAILABLE = True
    # Load environment variables from .env file
    load_dotenv()
except ImportError:
    GEMINI_AVAILABLE = False
    st.warning("⚠️ Google Gemini or python-dotenv not installed. Please install with: pip install google-genai python-dotenv")

# Import monitoring utilities
try:
    from gemini_monitor import log_gemini_call
    MONITORING_AVAILABLE = True
except ImportError:
    MONITORING_AVAILABLE = False


class TechnicalAnalysis:
    """Simplified technical analysis class for assessment."""
    
    def __init__(self, data):
        self.data = data.copy()
        self.prices = data['Close']
        self.volumes = data['Volume'] if 'Volume' in data.columns else None
    
    def calculate_rsi(self, period=14):
        """Calculate RSI."""
        delta = self.prices.diff()
        gains = delta.where(delta > 0, 0)
        losses = -delta.where(delta < 0, 0)
        
        avg_gains = gains.ewm(span=period, min_periods=period).mean()
        avg_losses = losses.ewm(span=period, min_periods=period).mean()
        
        rs = avg_gains / avg_losses
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def calculate_macd(self, fast_period=12, slow_period=26, signal_period=9):
        """Calculate MACD."""
        ema_fast = self.prices.ewm(span=fast_period, min_periods=fast_period).mean()
        ema_slow = self.prices.ewm(span=slow_period, min_periods=slow_period).mean()
        
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal_period, min_periods=signal_period).mean()
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    def calculate_bollinger_bands(self, period=20, std_dev=2):
        """Calculate Bollinger Bands."""
        middle_band = self.prices.rolling(window=period).mean()
        rolling_std = self.prices.rolling(window=period).std()
        
        upper_band = middle_band + (rolling_std * std_dev)
        lower_band = middle_band - (rolling_std * std_dev)
        bb_percent = (self.prices - lower_band) / (upper_band - lower_band)
        band_width = (upper_band - lower_band) / middle_band
        
        return upper_band, middle_band, lower_band, bb_percent, band_width
    
    def calculate_moving_averages(self, periods=[5, 10, 20, 50]):
        """Calculate Moving Averages."""
        mas = {}
        for period in periods:
            mas[f'SMA_{period}'] = self.prices.rolling(window=period).mean()
            mas[f'EMA_{period}'] = self.prices.ewm(span=period, min_periods=period).mean()
        return mas
    
    def calculate_obv(self):
        """Calculate OBV."""
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
        """Get trading signals."""
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
            'squeeze': band_width < band_width.rolling(20).mean() * 0.5,
            'current_bb_percent': bb_percent.iloc[-1] if not bb_percent.empty else None,
            'current_band_width': band_width.iloc[-1] if not band_width.empty else None
        }
        
        return signals


class FundamentalAnalysis:
    """Simplified fundamental analysis class for assessment."""
    
    def __init__(self, symbol):
        self.symbol = symbol
        self.ticker = yf.Ticker(symbol)
        self.info = None
        self.financials = None
        self.balance_sheet = None
        self.cashflow = None
    
    def fetch_data(self):
        """Fetch fundamental data."""
        try:
            self.info = self.ticker.info
            self.financials = self.ticker.financials
            self.balance_sheet = self.ticker.balance_sheet
            self.cashflow = self.ticker.cashflow
            return True
        except Exception as e:
            st.error(f"Error fetching data for {self.symbol}: {str(e)}")
            return False
    
    def get_key_metrics(self):
        """Get key financial metrics."""
        if not self.info:
            return {}
        
        metrics = {
            'Company Name': self.info.get('longName', 'N/A'),
            'Sector': self.info.get('sector', 'N/A'),
            'Industry': self.info.get('industry', 'N/A'),
            'Market Cap': self.info.get('marketCap', 0),
            'Enterprise Value': self.info.get('enterpriseValue', 0),
            'P/E Ratio': self.info.get('trailingPE', 0),
            'Forward P/E': self.info.get('forwardPE', 0),
            'PEG Ratio': self.info.get('pegRatio', 0),
            'Price to Book': self.info.get('priceToBook', 0),
            'Price to Sales': self.info.get('priceToSalesTrailing12Months', 0),
            'EV/Revenue': self.info.get('enterpriseToRevenue', 0),
            'EV/EBITDA': self.info.get('enterpriseToEbitda', 0),
            'Debt to Equity': self.info.get('debtToEquity', 0),
            'Current Ratio': self.info.get('currentRatio', 0),
            'Quick Ratio': self.info.get('quickRatio', 0),
            'ROE': self.info.get('returnOnEquity', 0),
            'ROA': self.info.get('returnOnAssets', 0),
            'ROIC': self.info.get('returnOnInvestmentCapital', 0),
            'Gross Margin': self.info.get('grossMargins', 0),
            'Operating Margin': self.info.get('operatingMargins', 0),
            'Profit Margin': self.info.get('profitMargins', 0),
            'Revenue Growth': self.info.get('revenueGrowth', 0),
            'Earnings Growth': self.info.get('earningsGrowth', 0),
            'Dividend Yield': self.info.get('dividendYield', 0),
            'Payout Ratio': self.info.get('payoutRatio', 0),
            'Beta': self.info.get('beta', 0),
            '52 Week High': self.info.get('fiftyTwoWeekHigh', 0),
            '52 Week Low': self.info.get('fiftyTwoWeekLow', 0),
            'Current Price': self.info.get('currentPrice', 0),
            'Analyst Target': self.info.get('targetMeanPrice', 0),
            'Analyst Recommendation': self.info.get('recommendationMean', 'N/A'),
        }
        
        return metrics
    
    def calculate_ratios(self):
        """Calculate additional financial ratios."""
        ratios = {}
        
        if self.financials is not None and not self.financials.empty:
            latest_year = self.financials.columns[0]
            latest_data = self.financials[latest_year]
            
            total_revenue = latest_data.get('Total Revenue', 0)
            net_income = latest_data.get('Net Income', 0)
            operating_income = latest_data.get('Operating Income', 0)
            
            if total_revenue and total_revenue != 0:
                ratios['Net Profit Margin'] = (net_income / total_revenue) * 100 if net_income else 0
                ratios['Operating Margin'] = (operating_income / total_revenue) * 100 if operating_income else 0
        
        if self.balance_sheet is not None and not self.balance_sheet.empty:
            latest_year = self.balance_sheet.columns[0]
            latest_bs = self.balance_sheet[latest_year]
            
            total_assets = latest_bs.get('Total Assets', 0)
            total_liabilities = latest_bs.get('Total Liabilities', 0)
            total_equity = latest_bs.get('Total Stockholder Equity', 0)
            current_assets = latest_bs.get('Current Assets', 0)
            current_liabilities = latest_bs.get('Current Liabilities', 0)
            
            if current_liabilities and current_liabilities != 0:
                ratios['Current Ratio'] = current_assets / current_liabilities if current_assets else 0
            
            if total_equity and total_equity != 0:
                ratios['Debt to Equity'] = total_liabilities / total_equity if total_liabilities else 0
            
            if total_assets and total_assets != 0:
                ratios['Debt to Assets'] = total_liabilities / total_assets if total_liabilities else 0
        
        return ratios


def get_portfolio_price_context(symbol: str, username: str = None) -> Dict[str, Any]:
    """
    Get portfolio price context for a specific symbol.
    
    Args:
        symbol (str): Stock ticker symbol
        username (str): Username for portfolio data
        
    Returns:
        Dict containing portfolio price context or None if not found
    """
    try:
        portfolio_df = load_portfolio_data(username)
        if portfolio_df.empty:
            return None
        
        # Filter portfolio for the specific symbol
        symbol_holdings = portfolio_df[portfolio_df['Symbol'] == symbol.upper()]
        if symbol_holdings.empty:
            return None
        
        # Calculate weighted average purchase price
        total_quantity = symbol_holdings['Quantity'].sum()
        total_invested_value = (symbol_holdings['Quantity'] * symbol_holdings['Purchase_Price']).sum()
        average_purchase_price = total_invested_value / total_quantity if total_quantity > 0 else 0
        
        # Get current price
        current_price = get_current_price(symbol)
        
        # Calculate position metrics
        current_value = total_quantity * current_price if current_price else 0
        unrealized_gain_loss = current_value - total_invested_value
        unrealized_gain_loss_pct = (unrealized_gain_loss / total_invested_value) * 100 if total_invested_value > 0 else 0
        
        return {
            'symbol': symbol,
            'total_quantity': total_quantity,
            'average_purchase_price': average_purchase_price,
            'total_invested_value': total_invested_value,
            'current_price': current_price,
            'current_value': current_value,
            'unrealized_gain_loss': unrealized_gain_loss,
            'unrealized_gain_loss_pct': unrealized_gain_loss_pct,
            'holdings_count': len(symbol_holdings),
            'currency': symbol_holdings['Currency'].iloc[0] if len(symbol_holdings) > 0 else 'USD'
        }
        
    except Exception as e:
        st.error(f"Error getting portfolio price context for {symbol}: {str(e)}")
        return None


class InvestmentAssessment:
    """Comprehensive investment assessment combining technical and fundamental analysis."""
    
    def __init__(self, symbol: str):
        """
        Initialize investment assessment for a given symbol.
        
        Args:
            symbol (str): Stock ticker symbol
        """
        self.symbol = symbol
        self.technical_analysis = None
        self.fundamental_analysis = None
        self.price_data = None
        self.assessment_result = None
        self.portfolio_context = None
        
    def run_analysis(self, period: str = "1y", username: str = None) -> bool:
        """
        Run both technical and fundamental analysis.
        
        Args:
            period (str): Time period for technical analysis
            username (str): Username for portfolio data
            
        Returns:
            bool: True if analysis completed successfully
        """
        try:
            # Get price data for technical analysis
            self.price_data, _ = get_stock_data(self.symbol, period)
            if self.price_data is None or self.price_data.empty:
                st.error(f"Could not fetch price data for {self.symbol}")
                return False
            
            # Initialize technical analysis
            self.technical_analysis = TechnicalAnalysis(self.price_data)
            
            # Initialize fundamental analysis
            self.fundamental_analysis = FundamentalAnalysis(self.symbol)
            if not self.fundamental_analysis.fetch_data():
                st.error(f"Could not fetch fundamental data for {self.symbol}")
                return False
            
            # Get portfolio price context
            self.portfolio_context = get_portfolio_price_context(self.symbol, username)
            
            return True
            
        except Exception as e:
            st.error(f"Error running analysis: {str(e)}")
            return False
    
    def get_technical_summary(self) -> Dict[str, Any]:
        """Get technical analysis summary."""
        if not self.technical_analysis:
            return {}
        
        signals = self.technical_analysis.get_signals()
        
        # Calculate current values
        rsi = self.technical_analysis.calculate_rsi()
        macd_line, signal_line, histogram = self.technical_analysis.calculate_macd()
        upper_bb, middle_bb, lower_bb, bb_percent, band_width = self.technical_analysis.calculate_bollinger_bands()
        mas = self.technical_analysis.calculate_moving_averages()
        obv = self.technical_analysis.calculate_obv()
        
        # Current price info
        current_price = self.price_data['Close'].iloc[-1]
        price_change = current_price - self.price_data['Close'].iloc[-2]
        price_change_pct = (price_change / self.price_data['Close'].iloc[-2]) * 100
        
        return {
            'current_price': current_price,
            'price_change': price_change,
            'price_change_pct': price_change_pct,
            'rsi': rsi.iloc[-1] if not rsi.empty else None,
            'macd': macd_line.iloc[-1] if not macd_line.empty else None,
            'macd_signal': signal_line.iloc[-1] if not signal_line.empty else None,
            'bb_upper': upper_bb.iloc[-1] if not upper_bb.empty else None,
            'bb_middle': middle_bb.iloc[-1] if not middle_bb.empty else None,
            'bb_lower': lower_bb.iloc[-1] if not lower_bb.empty else None,
            'bb_percent': bb_percent.iloc[-1] if not bb_percent.empty else None,
            'obv': obv.iloc[-1] if not obv.empty else None,
            'signals': signals
        }
    
    def get_fundamental_summary(self) -> Dict[str, Any]:
        """Get fundamental analysis summary."""
        if not self.fundamental_analysis:
            return {}
        
        metrics = self.fundamental_analysis.get_key_metrics()
        ratios = self.fundamental_analysis.calculate_ratios()
        
        return {
            'company_name': metrics.get('Company Name', 'N/A'),
            'sector': metrics.get('Sector', 'N/A'),
            'industry': metrics.get('Industry', 'N/A'),
            'market_cap': metrics.get('Market Cap', 0),
            'pe_ratio': metrics.get('P/E Ratio', 0),
            'forward_pe': metrics.get('Forward P/E', 0),
            'peg_ratio': metrics.get('PEG Ratio', 0),
            'price_to_book': metrics.get('Price to Book', 0),
            'price_to_sales': metrics.get('Price to Sales', 0),
            'debt_to_equity': metrics.get('Debt to Equity', 0),
            'current_ratio': metrics.get('Current Ratio', 0),
            'roe': metrics.get('ROE', 0),
            'roa': metrics.get('ROA', 0),
            'gross_margin': metrics.get('Gross Margin', 0),
            'operating_margin': metrics.get('Operating Margin', 0),
            'profit_margin': metrics.get('Profit Margin', 0),
            'revenue_growth': metrics.get('Revenue Growth', 0),
            'earnings_growth': metrics.get('Earnings Growth', 0),
            'dividend_yield': metrics.get('Dividend Yield', 0),
            'beta': metrics.get('Beta', 0),
            'analyst_target': metrics.get('Analyst Target', 0),
            'analyst_recommendation': metrics.get('Analyst Recommendation', 'N/A'),
            'calculated_ratios': ratios
        }
    
    def generate_ai_assessment(self, technical_summary: Dict, fundamental_summary: Dict, portfolio_context: Dict = None) -> Optional[Dict[str, Any]]:
        """
        Generate AI-powered investment assessment using Google Gemini 2.5 Flash API.
        
        Args:
            technical_summary: Technical analysis summary
            fundamental_summary: Fundamental analysis summary
            portfolio_context: Portfolio price context (if available)
            
        Returns:
            Dict containing AI assessment or None if failed
        """
        if not GEMINI_AVAILABLE:
            return None
        
        # Check if Gemini API key is available
        gemini_api_key = os.environ.get("GEMINI_API_KEY")
        if not gemini_api_key:
            st.warning("⚠️ Google Gemini API key not found. Please:")
            st.markdown("""
            1. Create a `.env` file in your project root directory
            2. Add your API key: `GEMINI_API_KEY=your_api_key_here`
            3. Get your free API key from: https://aistudio.google.com/
            """)
            return None
        
        try:
            # Initialize Gemini client
            client = genai.Client(api_key=gemini_api_key)
            
            # Prepare the analysis data for the AI
            analysis_data = {
                "technical_analysis": {
                    "current_price": technical_summary.get('current_price', 0),
                    "price_change_pct": technical_summary.get('price_change_pct', 0),
                    "rsi": technical_summary.get('rsi', 0),
                    "macd_signal": "bullish" if technical_summary.get('macd', 0) > technical_summary.get('macd_signal', 0) else "bearish",
                    "bollinger_position": technical_summary.get('bb_percent', 0),
                    "rsi_signal": "overbought" if technical_summary.get('rsi', 0) > 70 else "oversold" if technical_summary.get('rsi', 0) < 30 else "neutral"
                },
                "fundamental_analysis": {
                    "pe_ratio": fundamental_summary.get('pe_ratio', 0),
                    "forward_pe": fundamental_summary.get('forward_pe', 0),
                    "peg_ratio": fundamental_summary.get('peg_ratio', 0),
                    "price_to_book": fundamental_summary.get('price_to_book', 0),
                    "debt_to_equity": fundamental_summary.get('debt_to_equity', 0),
                    "roe": fundamental_summary.get('roe', 0),
                    "revenue_growth": fundamental_summary.get('revenue_growth', 0),
                    "profit_margin": fundamental_summary.get('profit_margin', 0),
                    "analyst_recommendation": fundamental_summary.get('analyst_recommendation', 'N/A')
                }
            }
            
            # Create the prompt for the AI
            portfolio_section = ""
            if portfolio_context:
                portfolio_section = f"""
            PORTFOLIO CONTEXT (Current Position):
            - Average Purchase Price: ${portfolio_context.get('average_purchase_price', 0):.2f}
            - Total Quantity Held: {portfolio_context.get('total_quantity', 0):.2f} shares
            - Total Invested Value: ${portfolio_context.get('total_invested_value', 0):.2f}
            - Current Position Value: ${portfolio_context.get('current_value', 0):.2f}
            - Unrealized Gain/Loss: ${portfolio_context.get('unrealized_gain_loss', 0):.2f} ({portfolio_context.get('unrealized_gain_loss_pct', 0):.2f}%)
            - Number of Holdings: {portfolio_context.get('holdings_count', 0)}
            """
            
            prompt = f"""
            As a professional financial analyst, please analyze the following stock data for {self.symbol} and provide a comprehensive investment assessment.

            TECHNICAL ANALYSIS:
            - Current Price: ${analysis_data['technical_analysis']['current_price']:.2f}
            - Price Change: {analysis_data['technical_analysis']['price_change_pct']:.2f}%
            - RSI: {analysis_data['technical_analysis']['rsi']:.2f} ({analysis_data['technical_analysis']['rsi_signal']})
            - MACD Signal: {analysis_data['technical_analysis']['macd_signal']}
            - Bollinger Bands Position: {analysis_data['technical_analysis']['bollinger_position']:.2f}

            FUNDAMENTAL ANALYSIS:
            - P/E Ratio: {analysis_data['fundamental_analysis']['pe_ratio']:.2f}
            - Forward P/E: {analysis_data['fundamental_analysis']['forward_pe']:.2f}
            - PEG Ratio: {analysis_data['fundamental_analysis']['peg_ratio']:.2f}
            - Price to Book: {analysis_data['fundamental_analysis']['price_to_book']:.2f}
            - Debt to Equity: {analysis_data['fundamental_analysis']['debt_to_equity']:.2f}
            - ROE: {analysis_data['fundamental_analysis']['roe']:.2f}
            - Revenue Growth: {analysis_data['fundamental_analysis']['revenue_growth']:.2f}%
            - Profit Margin: {analysis_data['fundamental_analysis']['profit_margin']:.2f}%
            - Analyst Recommendation: {analysis_data['fundamental_analysis']['analyst_recommendation']}{portfolio_section}

            Please provide:
            1. Overall recommendation (BUY, SELL, or HOLD) - consider the current portfolio position and average purchase price
            2. Confidence level (1-10)
            3. Key strengths
            4. Key risks
            5. Price target (if applicable)
            6. Time horizon for the recommendation
            7. Brief reasoning for the recommendation, including consideration of the current portfolio position
            8. Specific advice on whether to add to position, reduce position, or hold current position

            Format your response as a structured analysis suitable for investment decision-making.
            """
            
            # Call the Gemini API
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            
            # Extract the response
            ai_response = response.text
            
            # Log the API call for monitoring
            if MONITORING_AVAILABLE:
                log_gemini_call(
                    model="gemini-2.5-flash",
                    prompt=prompt,
                    response=ai_response,
                    operation="investment_assessment",
                    symbol=self.symbol,
                    success=True
                )
            
            # Parse the response to extract key information
            recommendation = "HOLD"  # Default
            confidence = 5  # Default
            strengths = []
            risks = []
            price_target = None
            time_horizon = "Medium-term"
            reasoning = ai_response
            
            # Try to extract structured information from the response
            lines = ai_response.split('\n')
            for line in lines:
                line = line.strip().upper()
                if 'BUY' in line and 'SELL' not in line and 'HOLD' not in line:
                    recommendation = "BUY"
                elif 'SELL' in line and 'BUY' not in line and 'HOLD' not in line:
                    recommendation = "SELL"
                elif 'HOLD' in line and 'BUY' not in line and 'SELL' not in line:
                    recommendation = "HOLD"
            
            return {
                'recommendation': recommendation,
                'confidence': confidence,
                'strengths': strengths,
                'risks': risks,
                'price_target': price_target,
                'time_horizon': time_horizon,
                'reasoning': reasoning,
                'raw_response': ai_response
            }
            
        except Exception as e:
            error_msg = str(e)
            st.error(f"Error calling Google Gemini API: {error_msg}")
            
            # Log the failed API call for monitoring
            if MONITORING_AVAILABLE:
                log_gemini_call(
                    model="gemini-2.5-flash",
                    prompt=prompt if 'prompt' in locals() else "",
                    response="",
                    operation="investment_assessment",
                    symbol=self.symbol,
                    success=False,
                    error_message=error_msg
                )
            
            return None
    
    def create_assessment_dashboard(self) -> None:
        """Create the assessment dashboard with all analysis results."""
        if not self.technical_analysis or not self.fundamental_analysis:
            st.error("Analysis not completed. Please run analysis first.")
            return
        
        # Get summaries
        technical_summary = self.get_technical_summary()
        fundamental_summary = self.get_fundamental_summary()
        
        # Display header with symbol and basic info
        st.markdown(f"<h2 style='text-align: center; color: #1f77b4;'>{self.symbol} Investment Assessment</h2>", unsafe_allow_html=True)
        
        # Key metrics row
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Current Price", f"${technical_summary.get('current_price', 0):.2f}")
        with col2:
            change_pct = technical_summary.get('price_change_pct', 0)
            st.metric("Daily Change", f"{change_pct:.2f}%", delta=f"{change_pct:.2f}%")
        with col3:
            st.metric("Market Cap", f"${fundamental_summary.get('market_cap', 0):,.0f}" if fundamental_summary.get('market_cap') else "N/A")
        with col4:
            st.metric("P/E Ratio", f"{fundamental_summary.get('pe_ratio', 0):.2f}" if fundamental_summary.get('pe_ratio') else "N/A")
        
        st.markdown("---")
        
        # Display portfolio context if available
        if self.portfolio_context:
            st.subheader("📊 Portfolio Position Context")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Average Purchase Price", f"${self.portfolio_context.get('average_purchase_price', 0):.2f}")
            with col2:
                st.metric("Total Quantity", f"{self.portfolio_context.get('total_quantity', 0):.2f} shares")
            with col3:
                unrealized_pct = self.portfolio_context.get('unrealized_gain_loss_pct', 0)
                st.metric("Unrealized P&L", f"{unrealized_pct:.2f}%", delta=f"{unrealized_pct:.2f}%")
            with col4:
                st.metric("Holdings Count", f"{self.portfolio_context.get('holdings_count', 0)}")
            
            # Additional portfolio metrics
            col5, col6 = st.columns(2)
            with col5:
                st.metric("Total Invested Value", f"${self.portfolio_context.get('total_invested_value', 0):,.2f}")
            with col6:
                st.metric("Current Position Value", f"${self.portfolio_context.get('current_value', 0):,.2f}")
            
            st.markdown("---")
        
        # Create tabs for different analysis views
        tab1, tab2, tab3, tab4 = st.tabs(["AI Assessment", "Technical Summary", "Fundamental Summary", "Combined Analysis"])
        
        with tab1:
            st.subheader("🤖 AI-Powered Investment Assessment")
            
            if st.button("Generate AI Assessment", type="primary"):
                with st.spinner("Generating AI assessment..."):
                    self.assessment_result = self.generate_ai_assessment(technical_summary, fundamental_summary, self.portfolio_context)
            
            if self.assessment_result:
                # Display recommendation with color coding
                recommendation = self.assessment_result.get('recommendation', 'HOLD')
                confidence = self.assessment_result.get('confidence', 5)
                
                col1, col2 = st.columns(2)
                with col1:
                    if recommendation == "BUY":
                        st.success(f"🎯 Recommendation: {recommendation}")
                    elif recommendation == "SELL":
                        st.error(f"🎯 Recommendation: {recommendation}")
                    else:
                        st.info(f"🎯 Recommendation: {recommendation}")
                
                with col2:
                    st.metric("Confidence Level", f"{confidence}/10")
                
                # Display reasoning
                st.subheader("Analysis Reasoning")
                st.write(self.assessment_result.get('reasoning', 'No reasoning provided'))
                
                # Display raw response in expander
                with st.expander("View Raw AI Response"):
                    st.text(self.assessment_result.get('raw_response', ''))
            else:
                st.info("Click 'Generate AI Assessment' to get AI-powered investment recommendation")
        
        with tab2:
            st.subheader("📈 Technical Analysis Summary")
            
            # Technical indicators
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Key Technical Indicators**")
                rsi = technical_summary.get('rsi')
                if rsi:
                    if rsi > 70:
                        st.error(f"RSI: {rsi:.2f} (Overbought)")
                    elif rsi < 30:
                        st.success(f"RSI: {rsi:.2f} (Oversold)")
                    else:
                        st.info(f"RSI: {rsi:.2f} (Neutral)")
                
                macd = technical_summary.get('macd')
                macd_signal = technical_summary.get('macd_signal')
                if macd and macd_signal:
                    if macd > macd_signal:
                        st.success("MACD: Bullish")
                    else:
                        st.error("MACD: Bearish")
                
                bb_percent = technical_summary.get('bb_percent')
                if bb_percent:
                    if bb_percent > 1:
                        st.error(f"Bollinger Bands: Above Upper Band ({bb_percent:.2f})")
                    elif bb_percent < 0:
                        st.success(f"Bollinger Bands: Below Lower Band ({bb_percent:.2f})")
                    else:
                        st.info(f"Bollinger Bands: Within Bands ({bb_percent:.2f})")
            
            with col2:
                st.write("**Price Levels**")
                current_price = technical_summary.get('current_price', 0)
                bb_upper = technical_summary.get('bb_upper')
                bb_middle = technical_summary.get('bb_middle')
                bb_lower = technical_summary.get('bb_lower')
                
                if bb_upper and bb_middle and bb_lower:
                    st.metric("Upper BB", f"${bb_upper:.2f}")
                    st.metric("Middle BB", f"${bb_middle:.2f}")
                    st.metric("Lower BB", f"${bb_lower:.2f}")
        
        with tab3:
            st.subheader("📊 Fundamental Analysis Summary")
            
            # Fundamental metrics
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Valuation Metrics**")
                pe_ratio = fundamental_summary.get('pe_ratio')
                if pe_ratio:
                    st.metric("P/E Ratio", f"{pe_ratio:.2f}")
                
                forward_pe = fundamental_summary.get('forward_pe')
                if forward_pe:
                    st.metric("Forward P/E", f"{forward_pe:.2f}")
                
                peg_ratio = fundamental_summary.get('peg_ratio')
                if peg_ratio:
                    st.metric("PEG Ratio", f"{peg_ratio:.2f}")
                
                price_to_book = fundamental_summary.get('price_to_book')
                if price_to_book:
                    st.metric("Price to Book", f"{price_to_book:.2f}")
            
            with col2:
                st.write("**Financial Health**")
                roe = fundamental_summary.get('roe')
                if roe:
                    st.metric("ROE", f"{roe:.2f}")
                
                debt_to_equity = fundamental_summary.get('debt_to_equity')
                if debt_to_equity:
                    st.metric("Debt to Equity", f"{debt_to_equity:.2f}")
                
                revenue_growth = fundamental_summary.get('revenue_growth')
                if revenue_growth:
                    st.metric("Revenue Growth", f"{revenue_growth:.2f}%")
                
                profit_margin = fundamental_summary.get('profit_margin')
                if profit_margin:
                    st.metric("Profit Margin", f"{profit_margin:.2f}%")
        
        with tab4:
            st.subheader("🔄 Combined Analysis")
            
            # Create a comprehensive comparison chart
            self.create_combined_analysis_chart(technical_summary, fundamental_summary)
            
            # Display analyst vs AI recommendation comparison
            st.write("**Recommendation Comparison**")
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Analyst Recommendation**")
                analyst_rec = fundamental_summary.get('analyst_recommendation', 'N/A')
                st.info(f"Analyst: {analyst_rec}")
            
            with col2:
                st.write("**AI Recommendation**")
                if self.assessment_result:
                    ai_rec = self.assessment_result.get('recommendation', 'N/A')
                    if ai_rec == "BUY":
                        st.success(f"AI: {ai_rec}")
                    elif ai_rec == "SELL":
                        st.error(f"AI: {ai_rec}")
                    else:
                        st.info(f"AI: {ai_rec}")
                else:
                    st.info("Generate AI assessment to see recommendation")
    
    def create_combined_analysis_chart(self, technical_summary: Dict, fundamental_summary: Dict) -> None:
        """Create a combined analysis chart."""
        # Create a radar chart for key metrics
        categories = ['Valuation', 'Growth', 'Profitability', 'Technical', 'Risk']
        
        # Normalize values to 0-100 scale for radar chart
        pe_ratio = fundamental_summary.get('pe_ratio', 0)
        pe_score = max(0, min(100, 100 - (pe_ratio - 15) * 2)) if pe_ratio else 50
        
        revenue_growth = fundamental_summary.get('revenue_growth', 0)
        growth_score = max(0, min(100, (revenue_growth + 20) * 2.5)) if revenue_growth else 50
        
        roe = fundamental_summary.get('roe', 0)
        profitability_score = max(0, min(100, roe * 10)) if roe else 50
        
        rsi = technical_summary.get('rsi', 50)
        technical_score = max(0, min(100, 100 - abs(rsi - 50) * 2)) if rsi else 50
        
        debt_to_equity = fundamental_summary.get('debt_to_equity', 0)
        risk_score = max(0, min(100, 100 - debt_to_equity * 20)) if debt_to_equity else 50
        
        values = [pe_score, growth_score, profitability_score, technical_score, risk_score]
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatterpolar(
            r=values,
            theta=categories,
            fill='toself',
            name=f'{self.symbol} Analysis',
            line_color='blue'
        ))
        
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 100]
                )),
            showlegend=True,
            title="Combined Analysis Radar Chart",
            height=500
        )
        
        st.plotly_chart(fig, use_container_width=True)


def main():
    """Main function to run the investment assessment page."""
    setup_page()
    inject_css()
    init_session_state()
    create_sidebar()
    
    # Check authentication
    if not st.session_state.get("authenticated", False):
        st.warning("🔐 Please log in to access the Investment Assessment page")
        st.info("Use the Login page in the sidebar to authenticate")
        return
    
    # Main page interface for symbol selection
    st.markdown('<h1 class="main-header">🎯 Investment Assessment</h1>', unsafe_allow_html=True)
    
    # Get symbols from portfolio or allow manual input
    portfolio = st.session_state.get("portfolio", pd.DataFrame())
    if not portfolio.empty:
        portfolio_symbols = portfolio['Symbol'].unique().tolist()
        symbol_options = portfolio_symbols + ["Custom Symbol"]
    else:
        symbol_options = ["Custom Symbol"]
    
    # Handle quick analyze from portfolio buttons
    if 'quick_assess' in st.session_state:
        symbol = st.session_state.quick_assess
        del st.session_state.quick_assess  # Clear the quick assess flag
        # Automatically trigger analysis
        st.session_state.auto_assess = True
    else:
        # Create columns for symbol selection
        col1, col2 = st.columns([2, 1])
        
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
    
    # Google Gemini API setup check
    if not GEMINI_AVAILABLE:
        st.error("⚠️ Required packages not installed")
        st.code("pip install google-genai python-dotenv")
    else:
        gemini_api_key = os.environ.get("GEMINI_API_KEY")
        if not gemini_api_key:
            st.warning("⚠️ Gemini API key not found")
            st.markdown("""
            **Setup Instructions:**
            1. Create `.env` file in project root
            2. Add: `GEMINI_API_KEY=your_key_here`
            3. Get free key: [aistudio.google.com](https://aistudio.google.com/)
            """)
    
    # Run assessment button
    assess_clicked = st.button("🚀 Run Assessment", type="primary", use_container_width=True)
    auto_assess = st.session_state.get('auto_assess', False)
    
    # Add user menu after assessment settings
    show_user_menu()
    
    if assess_clicked or auto_assess:
        if auto_assess:
            del st.session_state.auto_assess  # Clear the auto assess flag
            
        with st.spinner(f"Running comprehensive assessment for {symbol}..."):
            assessment = InvestmentAssessment(symbol)
            username = st.session_state.get("username")
            if assessment.run_analysis(period, username):
                st.session_state.assessment_data = assessment
                st.success(f"Successfully completed assessment for {symbol}")
            else:
                st.error(f"Failed to complete assessment for {symbol}")
    
    # Display assessment if available
    if 'assessment_data' in st.session_state and st.session_state.assessment_data:
        assessment = st.session_state.assessment_data
        
        # Display the assessment dashboard
        assessment.create_assessment_dashboard()
    
    else:
        st.info("👆 Select a symbol and click 'Run Assessment' to begin comprehensive analysis")
        
        # Show portfolio symbols if available
        if not portfolio.empty:
            st.subheader("Your Portfolio Symbols")
            st.write("Quick access to assess stocks in your portfolio:")
            
            cols = st.columns(min(len(portfolio_symbols), 4))
            for i, sym in enumerate(portfolio_symbols):
                with cols[i % 4]:
                    if st.button(f"Assess {sym}", key=f"assess_{sym}"):
                        st.session_state.quick_assess = sym
                        st.rerun()
    
    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: gray;'>
            Investment Assessment powered by Technical Analysis, Fundamental Analysis, and AI | 
            Data is delayed and for informational purposes only
        </div>
        """, 
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
