import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import yfinance as yf
from typing import Dict, Any, Optional

from app_utils import get_stock_data, get_current_price
from data_utils import load_portfolio_data
from technical_indicators import TechnicalAnalysis
from page_utils import init_protected_page
from config import (
    GEMINI_AVAILABLE, ML_AVAILABLE, SENTIMENT_AVAILABLE, SENTIMENT_ENABLED,
    get_serp_api_key, get_gemini_api_key, PERIOD_OPTIONS
)

# Import optional dependencies only if available
if GEMINI_AVAILABLE:
    from google import genai

if SENTIMENT_AVAILABLE:
    from serpapi import GoogleSearch
    from nltk.sentiment.vader import SentimentIntensityAnalyzer
    from textblob import TextBlob

# Import monitoring utilities
try:
    from gemini_monitor import log_gemini_call
    MONITORING_AVAILABLE = True
except ImportError:
    MONITORING_AVAILABLE = False

# Get API key for sentiment analysis
SERP_API_KEY = get_serp_api_key()


class SentimentAnalysis:
    """Simplified sentiment analysis class for investment assessment."""
    
    def __init__(self, symbol, api_key):
        """Initialize sentiment analysis for a symbol."""
        self.symbol = symbol
        self.api_key = api_key
        if SENTIMENT_AVAILABLE:
            self.sia = SentimentIntensityAnalyzer()
        else:
            self.sia = None
        self.sentiment_data = None
    
    def fetch_news(self, num_results=15):
        """Fetch news from Google Finance and Google News."""
        if not SENTIMENT_ENABLED:
            return []
        
        try:
            all_articles = []
            
            # Try Google Finance first
            try:
                import yfinance as yf
                ticker = yf.Ticker(self.symbol)
                info = ticker.info
                exchange = info.get('exchange', 'NASDAQ')
                query = f"{self.symbol}:{exchange}"
                
                params = {
                    "api_key": self.api_key,
                    "engine": "google_finance",
                    "q": query
                }
                
                search = GoogleSearch(params)
                results = search.get_dict()
                
                if "news_results" in results:
                    for item in results["news_results"][:num_results]:
                        all_articles.append({
                            "title": item.get("title", ""),
                            "snippet": item.get("snippet", ""),
                            "source": item.get("source", "Unknown"),
                            "date": item.get("date", "Unknown")
                        })
            except:
                pass
            
            # Also try Google News
            try:
                params = {
                    "api_key": self.api_key,
                    "engine": "google_news",
                    "q": f"{self.symbol} stock",
                    "gl": "us",
                    "hl": "en"
                }
                
                search = GoogleSearch(params)
                results = search.get_dict()
                
                if "news_results" in results:
                    for item in results["news_results"][:num_results]:
                        all_articles.append({
                            "title": item.get("title", ""),
                            "snippet": item.get("snippet", ""),
                            "source": item.get("source", {}).get("name", "Unknown") if isinstance(item.get("source"), dict) else item.get("source", "Unknown"),
                            "date": item.get("date", "Unknown")
                        })
            except:
                pass
            
            # Remove duplicates based on title
            seen_titles = set()
            unique_articles = []
            for article in all_articles:
                if article["title"] and article["title"] not in seen_titles:
                    seen_titles.add(article["title"])
                    unique_articles.append(article)
            
            return unique_articles[:20]  # Limit to 20 articles
            
        except Exception as e:
            st.warning(f"Could not fetch news for sentiment analysis: {str(e)}")
            return []
    
    def analyze_sentiment(self, text):
        """Analyze sentiment of text using VADER and TextBlob."""
        if not self.sia:
            return None
        
        # VADER analysis
        vader_scores = self.sia.polarity_scores(text)
        
        # TextBlob analysis
        blob = TextBlob(text)
        textblob_scores = {
            "polarity": blob.sentiment.polarity,
            "subjectivity": blob.sentiment.subjectivity
        }
        
        # Determine overall sentiment
        compound = vader_scores['compound']
        if compound >= 0.05:
            sentiment = "Positive"
        elif compound <= -0.05:
            sentiment = "Negative"
        else:
            sentiment = "Neutral"
        
        return {
            "vader_compound": compound,
            "vader_positive": vader_scores['pos'],
            "vader_negative": vader_scores['neg'],
            "vader_neutral": vader_scores['neu'],
            "textblob_polarity": textblob_scores['polarity'],
            "textblob_subjectivity": textblob_scores['subjectivity'],
            "sentiment": sentiment
        }
    
    def run_sentiment_analysis(self):
        """Run complete sentiment analysis."""
        if not SENTIMENT_ENABLED:
            return None
        
        # Fetch news
        articles = self.fetch_news()
        if not articles:
            return None
        
        # Analyze each article
        sentiments = []
        for article in articles:
            text = f"{article['title']} {article['snippet']}"
            sentiment = self.analyze_sentiment(text)
            if sentiment:
                sentiments.append(sentiment)
        
        if not sentiments:
            return None
        
        # Calculate aggregated metrics
        avg_vader_compound = sum(s['vader_compound'] for s in sentiments) / len(sentiments)
        avg_textblob_polarity = sum(s['textblob_polarity'] for s in sentiments) / len(sentiments)
        
        # Count sentiment categories
        positive_count = sum(1 for s in sentiments if s['sentiment'] == "Positive")
        negative_count = sum(1 for s in sentiments if s['sentiment'] == "Negative")
        neutral_count = sum(1 for s in sentiments if s['sentiment'] == "Neutral")
        
        total = len(sentiments)
        
        # Overall sentiment
        if avg_vader_compound >= 0.05:
            overall_sentiment = "Positive"
        elif avg_vader_compound <= -0.05:
            overall_sentiment = "Negative"
        else:
            overall_sentiment = "Neutral"
        
        self.sentiment_data = {
            "overall_sentiment": overall_sentiment,
            "avg_vader_compound": avg_vader_compound,
            "avg_textblob_polarity": avg_textblob_polarity,
            "positive_count": positive_count,
            "negative_count": negative_count,
            "neutral_count": neutral_count,
            "positive_pct": (positive_count / total) * 100,
            "negative_pct": (negative_count / total) * 100,
            "neutral_pct": (neutral_count / total) * 100,
            "total_articles": total,
            "articles_analyzed": articles[:5]  # Store first 5 articles for display
        }
        
        return self.sentiment_data


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


class PredictiveAnalysis:
    """Simplified predictive analysis class for investment assessment."""
    
    def __init__(self, data):
        """
        Initialize with price data.
        
        Args:
            data (pd.DataFrame): OHLCV data with columns ['Open', 'High', 'Low', 'Close', 'Volume']
        """
        self.data = data.copy()
        self.prices = data['Close']
        self.volumes = data['Volume'] if 'Volume' in data.columns else None
        
    def calculate_rsi(self, prices, period=14):
        """Calculate Relative Strength Index."""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def prepare_features(self):
        """Create technical indicators and features for ML models."""
        df = self.data.copy()
        
        # Price-based indicators
        df['SMA_5'] = df['Close'].rolling(window=5).mean()
        df['SMA_20'] = df['Close'].rolling(window=20).mean()
        df['EMA_12'] = df['Close'].ewm(span=12).mean()
        df['EMA_26'] = df['Close'].ewm(span=26).mean()
        
        # Bollinger Bands
        df['BB_Middle'] = df['Close'].rolling(window=20).mean()
        bb_std = df['Close'].rolling(window=20).std()
        df['BB_Upper'] = df['BB_Middle'] + (bb_std * 2)
        df['BB_Lower'] = df['BB_Middle'] - (bb_std * 2)
        df['BB_Percent'] = (df['Close'] - df['BB_Lower']) / (df['BB_Upper'] - df['BB_Lower'])
        
        # Price ratios
        df['High_Low_Ratio'] = df['High'] / df['Low']
        df['Open_Close_Ratio'] = df['Open'] / df['Close']
        
        # Momentum indicators
        df['RSI'] = self.calculate_rsi(df['Close'])
        
        # MACD
        df['MACD'] = df['EMA_12'] - df['EMA_26']
        df['MACD_Signal'] = df['MACD'].ewm(span=9).mean()
        df['MACD_Histogram'] = df['MACD'] - df['MACD_Signal']
        
        # Volume indicators
        if self.volumes is not None:
            df['Volume_SMA'] = df['Volume'].rolling(window=20).mean()
            df['Volume_Ratio'] = df['Volume'] / df['Volume_SMA']
        else:
            df['Volume_SMA'] = 1
            df['Volume_Ratio'] = 1
        
        # Price change indicators
        df['Price_Change_1d'] = df['Close'].pct_change(1)
        df['Price_Change_5d'] = df['Close'].pct_change(5)
        df['Price_Change_20d'] = df['Close'].pct_change(20)
        
        # Volatility
        df['Volatility'] = df['Close'].rolling(window=20).std()
        
        # Drop rows with NaN values
        df = df.dropna()
        
        return df
    
    def run_prediction_analysis(self, prediction_days=5):
        """Run simplified prediction analysis."""
        if not ML_AVAILABLE:
            return None
            
        try:
            df_with_features = self.prepare_features()
            
            if df_with_features.empty or len(df_with_features) < 50:
                return None
            
            # Prepare features for ML
            feature_cols = [col for col in df_with_features.columns if col not in ['Open', 'High', 'Low', 'Close', 'Volume']]
            X = df_with_features[feature_cols].values
            
            # Regression target: next day's close price
            y_regression = df_with_features['Close'].shift(-1).dropna().values
            X_regression = X[:-1]  # Remove last row since we don't have target for it
            
            # Classification target: price direction (1 if next day higher, 0 if lower)
            y_classification = (df_with_features['Close'].shift(-1) > df_with_features['Close']).astype(int).dropna().values
            X_classification = X[:-1]
            
            # Use 80% for training, 20% for testing
            split_idx = int(0.8 * len(X_regression))
            
            X_train, X_test = X_regression[:split_idx], X_regression[split_idx:]
            y_reg_train, y_reg_test = y_regression[:split_idx], y_regression[split_idx:]
            y_class_train, y_class_test = y_classification[:split_idx], y_classification[split_idx:]
            
            # Train Random Forest model
            rf_reg = RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42, n_jobs=1)
            rf_class = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42, n_jobs=1)
            
            rf_reg.fit(X_train, y_reg_train)
            rf_class.fit(X_train, y_class_train)
            
            # Make predictions
            rf_reg_pred = rf_reg.predict(X_test)
            rf_class_pred = rf_class.predict(X_test)
            
            # Evaluate performance
            rmse = np.sqrt(mean_squared_error(y_reg_test, rf_reg_pred))
            mae = mean_absolute_error(y_reg_test, rf_reg_pred)
            
            # Directional accuracy
            actual_direction = np.diff(y_reg_test) > 0
            pred_direction = np.diff(rf_reg_pred) > 0
            directional_accuracy = accuracy_score(actual_direction, pred_direction) if len(actual_direction) > 0 else 0
            
            # Feature importance
            feature_importance = rf_reg.feature_importances_
            top_features = sorted(zip(feature_cols, feature_importance), key=lambda x: x[1], reverse=True)[:5]
            
            # Generate future predictions
            latest_features = X[-1:].reshape(1, -1)
            future_predictions = []
            current_price = self.prices.iloc[-1]
            
            for _ in range(min(prediction_days, 5)):  # Limit to 5 days for stability
                pred_price = rf_reg.predict(latest_features)[0]
                future_predictions.append(pred_price)
                # Update features for next prediction (simplified)
                latest_features = latest_features.copy()
            
            return {
                'rmse': rmse,
                'mae': mae,
                'directional_accuracy': directional_accuracy,
                'top_features': top_features,
                'future_predictions': future_predictions,
                'current_price': current_price,
                'model_performance': {
                    'rmse': rmse,
                    'mae': mae,
                    'directional_accuracy': directional_accuracy
                }
            }
            
        except Exception as e:
            st.error(f"Error in predictive analysis: {str(e)}")
            return None


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
    """Comprehensive investment assessment combining technical, fundamental, sentiment, and predictive analysis."""
    
    def __init__(self, symbol: str):
        """
        Initialize investment assessment for a given symbol.
        
        Args:
            symbol (str): Stock ticker symbol
        """
        self.symbol = symbol
        self.technical_analysis = None
        self.fundamental_analysis = None
        self.predictive_analysis = None
        self.sentiment_analysis = None
        self.price_data = None
        self.assessment_result = None
        self.portfolio_context = None
        
    def run_analysis(self, period: str = "1y", username: str = None, include_sentiment: bool = True) -> bool:
        """
        Run technical, fundamental, predictive, and sentiment analysis.
        
        Args:
            period (str): Time period for technical analysis
            username (str): Username for portfolio data
            include_sentiment (bool): Whether to include sentiment analysis
            
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
            
            # Initialize predictive analysis
            if ML_AVAILABLE:
                self.predictive_analysis = PredictiveAnalysis(self.price_data)
            
            # Initialize sentiment analysis if enabled
            if include_sentiment and SENTIMENT_ENABLED:
                with st.spinner("Running sentiment analysis..."):
                    self.sentiment_analysis = SentimentAnalysis(self.symbol, SERP_API_KEY)
                    self.sentiment_analysis.run_sentiment_analysis()
            
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
    
    def get_predictive_summary(self) -> Dict[str, Any]:
        """Get predictive analysis summary."""
        if not self.predictive_analysis or not ML_AVAILABLE:
            return {}
        
        try:
            prediction_results = self.predictive_analysis.run_prediction_analysis(prediction_days=5)
            if prediction_results:
                return {
                    'model_performance': prediction_results.get('model_performance', {}),
                    'top_features': prediction_results.get('top_features', []),
                    'future_predictions': prediction_results.get('future_predictions', []),
                    'current_price': prediction_results.get('current_price', 0),
                    'rmse': prediction_results.get('rmse', 0),
                    'mae': prediction_results.get('mae', 0),
                    'directional_accuracy': prediction_results.get('directional_accuracy', 0)
                }
        except Exception as e:
            st.error(f"Error in predictive analysis: {str(e)}")
        
        return {}
    
    def get_sentiment_summary(self) -> Dict[str, Any]:
        """Get sentiment analysis summary."""
        if not self.sentiment_analysis or not SENTIMENT_ENABLED:
            return {}
        
        sentiment_data = self.sentiment_analysis.sentiment_data
        if not sentiment_data:
            return {}
        
        return {
            'overall_sentiment': sentiment_data.get('overall_sentiment', 'Neutral'),
            'avg_vader_compound': sentiment_data.get('avg_vader_compound', 0),
            'avg_textblob_polarity': sentiment_data.get('avg_textblob_polarity', 0),
            'positive_pct': sentiment_data.get('positive_pct', 0),
            'negative_pct': sentiment_data.get('negative_pct', 0),
            'neutral_pct': sentiment_data.get('neutral_pct', 0),
            'total_articles': sentiment_data.get('total_articles', 0),
            'articles_analyzed': sentiment_data.get('articles_analyzed', [])
        }
    
    def generate_ai_assessment(self, technical_summary: Dict, fundamental_summary: Dict, portfolio_context: Dict = None, predictive_summary: Dict = None, sentiment_summary: Dict = None) -> Optional[Dict[str, Any]]:
        """
        Generate AI-powered investment assessment using Google Gemini 2.5 Flash API.
        
        Args:
            technical_summary: Technical analysis summary
            fundamental_summary: Fundamental analysis summary
            portfolio_context: Portfolio price context (if available)
            predictive_summary: Predictive analysis summary (if available)
            sentiment_summary: Sentiment analysis summary (if available)
            
        Returns:
            Dict containing AI assessment or None if failed
        """
        if not GEMINI_AVAILABLE:
            return None
        
        # Check if Gemini API key is available
        gemini_api_key = get_gemini_api_key()
        if not gemini_api_key:
            st.warning("⚠️ Google Gemini API key not found. Please:")
            st.markdown("""
            1. Create a `.env` file in your project root directory
            2. Add your API key: `GEMINI_API_KEY=your_api_key_here`
            3. Get your free API key from: https://aistudio.google.com/
            """)
            return None
        
        try:
            # Initialize Gemini client with reasoning capabilities
            # Define a dummy function to encourage the model to show its reasoning steps
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
            
            # Add predictive analysis section
            predictive_section = ""
            if predictive_summary and predictive_summary.get('model_performance'):
                future_predictions = predictive_summary.get('future_predictions', [])
                directional_accuracy = predictive_summary.get('directional_accuracy', 0)
                rmse = predictive_summary.get('rmse', 0)
                top_features = predictive_summary.get('top_features', [])
                
                predictions_text = ""
                if future_predictions:
                    predictions_text = f"Next 5 days: {', '.join([f'${p:.2f}' for p in future_predictions[:5]])}"
                
                top_features_text = ""
                if top_features:
                    top_features_text = f"Key predictive factors: {', '.join([f[0] for f in top_features[:3]])}"
                
                predictive_section = f"""
            PREDICTIVE ANALYSIS (Machine Learning):
            - Model Accuracy (RMSE): {rmse:.4f}
            - Directional Accuracy: {directional_accuracy:.2%}
            - Price Predictions: {predictions_text}
            - {top_features_text}
            """
            
            # Add sentiment analysis section
            sentiment_section = ""
            if sentiment_summary and sentiment_summary.get('total_articles', 0) > 0:
                overall_sentiment = sentiment_summary.get('overall_sentiment', 'Neutral')
                vader_compound = sentiment_summary.get('avg_vader_compound', 0)
                positive_pct = sentiment_summary.get('positive_pct', 0)
                negative_pct = sentiment_summary.get('negative_pct', 0)
                neutral_pct = sentiment_summary.get('neutral_pct', 0)
                total_articles = sentiment_summary.get('total_articles', 0)
                
                sentiment_section = f"""
            SENTIMENT ANALYSIS (News & Market Sentiment):
            - Overall Market Sentiment: {overall_sentiment}
            - VADER Sentiment Score: {vader_compound:.3f} (range: -1 to +1)
            - Sentiment Distribution: {positive_pct:.1f}% Positive, {negative_pct:.1f}% Negative, {neutral_pct:.1f}% Neutral
            - Based on {total_articles} recent news articles
            - Sentiment Interpretation: {'Bullish market mood' if vader_compound > 0.2 else 'Bearish market mood' if vader_compound < -0.2 else 'Neutral to mixed market mood'}
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
            - Analyst Recommendation: {analysis_data['fundamental_analysis']['analyst_recommendation']}{portfolio_section}{predictive_section}{sentiment_section}

            Please provide a STEP-BY-STEP analysis with your reasoning process:
            
            STEP 1 - TECHNICAL ANALYSIS INTERPRETATION:
            Analyze the technical indicators and explain what they reveal about momentum and trend.
            
            STEP 2 - FUNDAMENTAL ANALYSIS INTERPRETATION:
            Evaluate the valuation metrics and financial health. Are they attractive or concerning?
            
            STEP 3 - SENTIMENT ANALYSIS INTERPRETATION (if available):
            How does market sentiment align with or diverge from technical/fundamental signals?
            
            STEP 4 - PREDICTIVE ANALYSIS INTERPRETATION (if available):
            What do the predictive models suggest about future price movement?
            
            STEP 5 - PORTFOLIO CONTEXT INTERPRETATION (if available):
            Given the current position, what action makes sense?
            
            STEP 6 - SYNTHESIS & RECOMMENDATION:
            Integrate all analyses to form a recommendation.

            Then provide your final structured assessment:
            1. Overall recommendation (BUY, SELL, or HOLD) - consider the current portfolio position, average purchase price, predictive analysis, AND market sentiment
            2. Confidence level (1-10) - factor in sentiment alignment with technical/fundamental signals
            3. Key strengths (bullet points)
            4. Key risks (bullet points)
            5. Price target (if applicable) - consider fundamental valuation, predictive forecasts, and sentiment momentum
            6. Time horizon for the recommendation
            7. Specific advice on whether to add to position, reduce position, or hold current position
            8. Final summary reasoning

            Format your response clearly with visible step numbers and structured sections.
            """
            
            # Call the Gemini API
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            
            # Extract the response
            ai_response = response.text
            
            # Extract reasoning steps from the response
            reasoning_steps = []
            try:
                # Try to extract step-by-step reasoning
                lines = ai_response.split('\n')
                current_step = None
                current_content = []
                
                for line in lines:
                    # Check if this is a new step
                    if 'STEP' in line.upper() and any(char.isdigit() for char in line):
                        # Save previous step if exists
                        if current_step:
                            reasoning_steps.append({
                                'step': current_step,
                                'content': '\n'.join(current_content).strip()
                            })
                        # Start new step
                        current_step = line.strip()
                        current_content = []
                    elif current_step:
                        # Add line to current step content
                        current_content.append(line)
                
                # Save last step
                if current_step:
                    reasoning_steps.append({
                        'step': current_step,
                        'content': '\n'.join(current_content).strip()
                    })
            except Exception as e:
                st.warning(f"Could not extract reasoning steps: {str(e)}")
            
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
            for i, line in enumerate(lines):
                line_upper = line.strip().upper()
                
                # Extract recommendation
                if 'RECOMMENDATION' in line_upper:
                    if 'BUY' in line_upper and 'SELL' not in line_upper:
                        recommendation = "BUY"
                    elif 'SELL' in line_upper and 'BUY' not in line_upper:
                        recommendation = "SELL"
                    elif 'HOLD' in line_upper:
                        recommendation = "HOLD"
                
                # Extract confidence level
                if 'CONFIDENCE' in line_upper:
                    # Try to find a number between 1-10
                    import re
                    match = re.search(r'\b([1-9]|10)\b', line)
                    if match:
                        confidence = int(match.group(1))
                
                # Extract time horizon
                if 'TIME HORIZON' in line_upper or 'TIMEFRAME' in line_upper:
                    if 'SHORT' in line_upper:
                        time_horizon = "Short-term"
                    elif 'LONG' in line_upper:
                        time_horizon = "Long-term"
                    else:
                        time_horizon = "Medium-term"
                
                # Extract strengths
                if 'STRENGTH' in line_upper and ':' in line:
                    # Look for bullet points in following lines
                    for j in range(i+1, min(i+10, len(lines))):
                        next_line = lines[j].strip()
                        if next_line.startswith(('-', '•', '*', '+')):
                            strengths.append(next_line.lstrip('-•*+ '))
                        elif next_line and not next_line.startswith(' ') and ':' in next_line:
                            break
                
                # Extract risks
                if 'RISK' in line_upper and ':' in line:
                    # Look for bullet points in following lines
                    for j in range(i+1, min(i+10, len(lines))):
                        next_line = lines[j].strip()
                        if next_line.startswith(('-', '•', '*', '+')):
                            risks.append(next_line.lstrip('-•*+ '))
                        elif next_line and not next_line.startswith(' ') and ':' in next_line:
                            break
                
                # Extract price target
                if 'PRICE TARGET' in line_upper or 'TARGET PRICE' in line_upper:
                    import re
                    match = re.search(r'\$(\d+\.?\d*)', line)
                    if match:
                        price_target = float(match.group(1))
            
            return {
                'recommendation': recommendation,
                'confidence': confidence,
                'strengths': strengths,
                'risks': risks,
                'price_target': price_target,
                'time_horizon': time_horizon,
                'reasoning': reasoning,
                'reasoning_steps': reasoning_steps,
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
        predictive_summary = self.get_predictive_summary()
        sentiment_summary = self.get_sentiment_summary()
        
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
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["AI Assessment", "Technical Summary", "Fundamental Summary", "Sentiment Analysis", "Predictive Analysis", "Combined Analysis"])
        
        with tab1:
            st.subheader("🤖 AI-Powered Investment Assessment")
            
            if st.button("Generate AI Assessment", type="primary"):
                with st.spinner("Generating AI assessment with sentiment analysis..."):
                    self.assessment_result = self.generate_ai_assessment(technical_summary, fundamental_summary, self.portfolio_context, predictive_summary, sentiment_summary)
            
            if self.assessment_result:
                # Display recommendation with color coding
                recommendation = self.assessment_result.get('recommendation', 'HOLD')
                confidence = self.assessment_result.get('confidence', 5)
                time_horizon = self.assessment_result.get('time_horizon', 'Medium-term')
                price_target = self.assessment_result.get('price_target')
                
                # Top-level metrics
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    if recommendation == "BUY":
                        st.success(f"🎯 **Recommendation**\n\n# {recommendation}")
                    elif recommendation == "SELL":
                        st.error(f"🎯 **Recommendation**\n\n# {recommendation}")
                    else:
                        st.info(f"🎯 **Recommendation**\n\n# {recommendation}")
                
                with col2:
                    st.metric("Confidence Level", f"{confidence}/10", help="AI confidence in recommendation (1-10)")
                
                with col3:
                    st.metric("Time Horizon", time_horizon)
                
                with col4:
                    if price_target:
                        st.metric("Price Target", f"${price_target:.2f}")
                    else:
                        st.metric("Price Target", "N/A")
                
                st.markdown("---")
                
                # Display reasoning steps
                reasoning_steps = self.assessment_result.get('reasoning_steps', [])
                if reasoning_steps:
                    st.subheader("🧠 AI Reasoning Process")
                    st.markdown("*Here's how the AI analyzed the data step-by-step:*")
                    
                    for i, step_data in enumerate(reasoning_steps, 1):
                        step_title = step_data.get('step', f'Step {i}')
                        step_content = step_data.get('content', '')
                        
                        # Use expanders for each reasoning step
                        with st.expander(f"**{step_title}**", expanded=(i <= 2)):  # First 2 steps expanded
                            if step_content:
                                st.markdown(step_content)
                            else:
                                st.info("No detailed reasoning for this step")
                    
                    st.markdown("---")
                
                # Display strengths and risks
                strengths = self.assessment_result.get('strengths', [])
                risks = self.assessment_result.get('risks', [])
                
                if strengths or risks:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if strengths:
                            st.subheader("💪 Key Strengths")
                            for strength in strengths:
                                st.success(f"✓ {strength}")
                    
                    with col2:
                        if risks:
                            st.subheader("⚠️ Key Risks")
                            for risk in risks:
                                st.warning(f"⚠ {risk}")
                    
                    st.markdown("---")
                
                # Display full reasoning
                st.subheader("📋 Complete Analysis")
                st.write(self.assessment_result.get('reasoning', 'No reasoning provided'))
                
                # Display raw response in expander
                with st.expander("🔍 View Raw AI Response"):
                    st.text(self.assessment_result.get('raw_response', ''))
                
                # PDF Export Button
                st.markdown("---")
                st.subheader("📄 Export Report")
                
                col1, col2, col3 = st.columns([1, 1, 2])
                with col1:
                    if st.button("📥 Download PDF Report", type="primary", help="Generate and download comprehensive AI assessment report"):
                        with st.spinner("Generating PDF report..."):
                            from app_utils import generate_ai_report_pdf
                            
                            # Get analysis summaries for PDF
                            technical_summary_text = self.get_technical_summary_text(technical_summary)
                            fundamental_summary_text = self.get_fundamental_summary_text(fundamental_summary)
                            sentiment_summary_text = self.get_sentiment_summary_text(sentiment_summary)
                            predictive_summary_text = self.get_predictive_summary_text(predictive_summary)
                            
                            # Generate PDF
                            pdf_path = generate_ai_report_pdf(
                                self.assessment_result,
                                self.symbol,
                                technical_summary_text,
                                fundamental_summary_text,
                                sentiment_summary_text,
                                predictive_summary_text
                            )
                            
                            if pdf_path:
                                with open(pdf_path, 'rb') as f:
                                    st.download_button(
                                        label="📄 Download PDF Report",
                                        data=f.read(),
                                        file_name=f"ai_report_{self.symbol}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                                        mime="application/pdf"
                                    )
                                st.success("PDF report generated successfully!")
                            else:
                                st.error("Failed to generate PDF report")
                
                with col2:
                    st.info("💡 **PDF includes:**\n- Executive summary\n- AI reasoning process\n- Strengths & risks\n- Complete analysis\n- All summaries")
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
            st.subheader("💭 Sentiment Analysis")
            
            if sentiment_summary and sentiment_summary.get('total_articles', 0) > 0:
                # Overall sentiment
                overall_sentiment = sentiment_summary.get('overall_sentiment', 'Neutral')
                vader_compound = sentiment_summary.get('avg_vader_compound', 0)
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if overall_sentiment == "Positive":
                        st.success(f"**Overall Sentiment:** 🟢 {overall_sentiment}")
                    elif overall_sentiment == "Negative":
                        st.error(f"**Overall Sentiment:** 🔴 {overall_sentiment}")
                    else:
                        st.info(f"**Overall Sentiment:** 🟡 {overall_sentiment}")
                
                with col2:
                    st.metric("VADER Score", f"{vader_compound:.3f}", help="Range: -1 (very negative) to +1 (very positive)")
                
                with col3:
                    st.metric("Articles Analyzed", sentiment_summary.get('total_articles', 0))
                
                # Sentiment distribution
                st.markdown("---")
                st.write("**Sentiment Distribution:**")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    positive_pct = sentiment_summary.get('positive_pct', 0)
                    st.metric("🟢 Positive", f"{positive_pct:.1f}%")
                
                with col2:
                    negative_pct = sentiment_summary.get('negative_pct', 0)
                    st.metric("🔴 Negative", f"{negative_pct:.1f}%")
                
                with col3:
                    neutral_pct = sentiment_summary.get('neutral_pct', 0)
                    st.metric("🟡 Neutral", f"{neutral_pct:.1f}%")
                
                # Progress bars for visual representation
                st.progress(positive_pct / 100, text=f"Positive: {positive_pct:.1f}%")
                st.progress(negative_pct / 100, text=f"Negative: {negative_pct:.1f}%")
                st.progress(neutral_pct / 100, text=f"Neutral: {neutral_pct:.1f}%")
                
                # Sample articles
                articles = sentiment_summary.get('articles_analyzed', [])
                if articles:
                    st.markdown("---")
                    st.write("**Sample News Headlines:**")
                    for i, article in enumerate(articles[:5], 1):
                        with st.expander(f"{i}. {article.get('title', 'N/A')[:80]}..."):
                            st.write(f"**Source:** {article.get('source', 'Unknown')}")
                            st.write(f"**Date:** {article.get('date', 'Unknown')}")
                            st.write(f"**Snippet:** {article.get('snippet', 'N/A')}")
                
                # Interpretation
                st.markdown("---")
                st.subheader("📊 Sentiment Interpretation")
                
                if vader_compound > 0.3:
                    st.success("🚀 **Very Bullish**: Strong positive sentiment suggests high market confidence and potential upward momentum")
                elif vader_compound > 0.1:
                    st.success("📈 **Bullish**: Positive sentiment indicates favorable market mood")
                elif vader_compound > -0.1:
                    st.info("➡️ **Neutral**: Mixed or balanced sentiment, no clear directional bias")
                elif vader_compound > -0.3:
                    st.warning("📉 **Bearish**: Negative sentiment suggests caution and potential downward pressure")
                else:
                    st.error("💣 **Very Bearish**: Strong negative sentiment indicates high pessimism and potential selling pressure")
                
                st.info("""
                **Using Sentiment for Investment Decisions:**
                - **Confirmation**: Positive sentiment + positive technicals/fundamentals = stronger buy signal
                - **Divergence**: Negative sentiment + strong fundamentals = potential contrarian opportunity
                - **Timing**: Sentiment can help time entries/exits within your investment thesis
                - **Risk Management**: Very negative sentiment may warrant smaller position sizes
                """)
                
            elif not SENTIMENT_ENABLED:
                st.warning("⚠️ Sentiment analysis not available")
                if not SENTIMENT_AVAILABLE:
                    st.error("Required packages not installed. Please run:")
                    st.code("pip install google-search-results nltk textblob vaderSentiment")
                elif not SERP_API_KEY or SERP_API_KEY == "your_serpapi_key_here":
                    st.error("SERPapi key not configured. Please:")
                    st.markdown("""
                    1. Get API key from https://serpapi.com/
                    2. Add to `.env` file: `SERP_API_KEY=your_key`
                    3. Restart the application
                    """)
            else:
                st.info("No sentiment data available for this stock. This may be due to limited news coverage.")
        
        with tab5:
            st.subheader("🤖 Predictive Analysis")
            
            if predictive_summary and predictive_summary.get('model_performance'):
                # Model performance metrics
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("RMSE", f"{predictive_summary.get('rmse', 0):.4f}")
                with col2:
                    st.metric("MAE", f"{predictive_summary.get('mae', 0):.4f}")
                with col3:
                    directional_acc = predictive_summary.get('directional_accuracy', 0)
                    st.metric("Directional Accuracy", f"{directional_acc:.2%}")
                
                # Future predictions
                future_predictions = predictive_summary.get('future_predictions', [])
                if future_predictions:
                    st.subheader("📈 Price Predictions")
                    current_price = predictive_summary.get('current_price', 0)
                    
                    col1, col2, col3, col4, col5 = st.columns(5)
                    for i, pred_price in enumerate(future_predictions[:5]):
                        with [col1, col2, col3, col4, col5][i]:
                            change_pct = ((pred_price - current_price) / current_price) * 100 if current_price > 0 else 0
                            st.metric(f"Day {i+1}", f"${pred_price:.2f}", delta=f"{change_pct:.2f}%")
                
                # Top features
                top_features = predictive_summary.get('top_features', [])
                if top_features:
                    st.subheader("🔍 Key Predictive Factors")
                    feature_df = pd.DataFrame(top_features, columns=['Feature', 'Importance'])
                    st.dataframe(feature_df, use_container_width=True)
                
                # Model reliability assessment
                st.subheader("📊 Model Assessment")
                rmse = predictive_summary.get('rmse', 0)
                directional_acc = predictive_summary.get('directional_accuracy', 0)
                
                if rmse < 0.05 and directional_acc > 0.6:
                    st.success("✅ Model shows good predictive performance")
                elif rmse < 0.1 and directional_acc > 0.55:
                    st.warning("⚠️ Model shows moderate predictive performance")
                else:
                    st.error("❌ Model shows limited predictive performance")
                
                st.info("""
                **Model Performance Guidelines:**
                - RMSE < 0.05: Excellent accuracy
                - RMSE 0.05-0.1: Good accuracy  
                - RMSE > 0.1: Limited accuracy
                - Directional Accuracy > 60%: Good trend prediction
                - Directional Accuracy < 55%: Limited trend prediction
                """)
            else:
                if not ML_AVAILABLE:
                    st.error("⚠️ Machine learning libraries not available. Please install scikit-learn.")
                else:
                    st.info("🤖 Predictive analysis will be available after running the assessment")
        
        with tab6:
            st.subheader("🔄 Combined Analysis")
            
            # Create a comprehensive comparison chart
            self.create_combined_analysis_chart(technical_summary, fundamental_summary, predictive_summary, sentiment_summary)
            
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
    
    def create_combined_analysis_chart(self, technical_summary: Dict, fundamental_summary: Dict, predictive_summary: Dict = None, sentiment_summary: Dict = None) -> None:
        """Create a combined analysis chart."""
        # Create a radar chart for key metrics
        categories = ['Valuation', 'Growth', 'Profitability', 'Technical', 'Risk', 'Sentiment', 'Predictive']
        
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
        
        # Add sentiment score if available
        if sentiment_summary and sentiment_summary.get('total_articles', 0) > 0:
            vader_compound = sentiment_summary.get('avg_vader_compound', 0)
            # Convert VADER score (-1 to +1) to 0-100 scale
            # -1 = 0 (worst), 0 = 50 (neutral), +1 = 100 (best)
            sentiment_score = max(0, min(100, (vader_compound + 1) * 50))
        else:
            sentiment_score = 50  # Default neutral score
        
        # Add predictive score if available
        if predictive_summary and predictive_summary.get('directional_accuracy'):
            directional_acc = predictive_summary.get('directional_accuracy', 0)
            predictive_score = max(0, min(100, directional_acc * 100))
        else:
            predictive_score = 50  # Default neutral score
        
        values = [pe_score, growth_score, profitability_score, technical_score, risk_score, sentiment_score, predictive_score]
        
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
            title="Combined Analysis Radar Chart (Including Sentiment & Predictive Analysis)",
            height=500
        )
        
        st.plotly_chart(fig, use_container_width=True)

    def get_technical_summary_text(self, technical_summary: Dict) -> str:
        """Convert technical summary dict to formatted text."""
        if not technical_summary:
            return "No technical analysis data available."
        
        text_parts = []
        
        # RSI
        rsi = technical_summary.get('rsi')
        if rsi:
            if rsi > 70:
                text_parts.append(f"RSI: {rsi:.2f} (Overbought - potential sell signal)")
            elif rsi < 30:
                text_parts.append(f"RSI: {rsi:.2f} (Oversold - potential buy signal)")
            else:
                text_parts.append(f"RSI: {rsi:.2f} (Neutral)")
        
        # MACD
        macd = technical_summary.get('macd')
        macd_signal = technical_summary.get('macd_signal')
        if macd and macd_signal:
            if macd > macd_signal:
                text_parts.append("MACD: Bullish crossover detected")
            else:
                text_parts.append("MACD: Bearish crossover detected")
        
        # Bollinger Bands
        bb_percent = technical_summary.get('bb_percent')
        if bb_percent:
            if bb_percent > 1:
                text_parts.append(f"Bollinger Bands: Above upper band ({bb_percent:.2f}) - potential overbought")
            elif bb_percent < 0:
                text_parts.append(f"Bollinger Bands: Below lower band ({bb_percent:.2f}) - potential oversold")
            else:
                text_parts.append(f"Bollinger Bands: Within normal range ({bb_percent:.2f})")
        
        # Price levels
        current_price = technical_summary.get('current_price', 0)
        support = technical_summary.get('support', 0)
        resistance = technical_summary.get('resistance', 0)
        if current_price and support and resistance:
            text_parts.append(f"Current Price: ${current_price:.2f}")
            text_parts.append(f"Support Level: ${support:.2f}")
            text_parts.append(f"Resistance Level: ${resistance:.2f}")
        
        return "\n".join(text_parts) if text_parts else "No technical indicators available."

    def get_fundamental_summary_text(self, fundamental_summary: Dict) -> str:
        """Convert fundamental summary dict to formatted text."""
        if not fundamental_summary:
            return "No fundamental analysis data available."
        
        text_parts = []
        
        # Key ratios
        pe_ratio = fundamental_summary.get('pe_ratio')
        if pe_ratio:
            text_parts.append(f"P/E Ratio: {pe_ratio:.2f}")
        
        pb_ratio = fundamental_summary.get('pb_ratio')
        if pb_ratio:
            text_parts.append(f"P/B Ratio: {pb_ratio:.2f}")
        
        debt_to_equity = fundamental_summary.get('debt_to_equity')
        if debt_to_equity:
            text_parts.append(f"Debt-to-Equity: {debt_to_equity:.2f}")
        
        roe = fundamental_summary.get('roe')
        if roe:
            text_parts.append(f"Return on Equity: {roe:.2%}")
        
        # Market cap
        market_cap = fundamental_summary.get('market_cap')
        if market_cap:
            if market_cap >= 1e12:
                text_parts.append(f"Market Cap: ${market_cap/1e12:.2f}T")
            elif market_cap >= 1e9:
                text_parts.append(f"Market Cap: ${market_cap/1e9:.2f}B")
            elif market_cap >= 1e6:
                text_parts.append(f"Market Cap: ${market_cap/1e6:.2f}M")
            else:
                text_parts.append(f"Market Cap: ${market_cap:,.0f}")
        
        return "\n".join(text_parts) if text_parts else "No fundamental metrics available."

    def get_sentiment_summary_text(self, sentiment_summary: Dict) -> str:
        """Convert sentiment summary dict to formatted text."""
        if not sentiment_summary:
            return "No sentiment analysis data available."
        
        text_parts = []
        
        # Overall sentiment
        overall_sentiment = sentiment_summary.get('overall_sentiment', 'Neutral')
        text_parts.append(f"Overall Sentiment: {overall_sentiment}")
        
        # VADER score
        vader_compound = sentiment_summary.get('vader_compound')
        if vader_compound:
            text_parts.append(f"VADER Score: {vader_compound:.3f}")
        
        # TextBlob score
        textblob_polarity = sentiment_summary.get('textblob_polarity')
        if textblob_polarity:
            text_parts.append(f"TextBlob Score: {textblob_polarity:.3f}")
        
        # Article count
        article_count = sentiment_summary.get('article_count', 0)
        text_parts.append(f"Articles Analyzed: {article_count}")
        
        return "\n".join(text_parts) if text_parts else "No sentiment data available."

    def get_predictive_summary_text(self, predictive_summary: Dict) -> str:
        """Convert predictive summary dict to formatted text."""
        if not predictive_summary:
            return "No predictive analysis data available."
        
        text_parts = []
        
        # Prediction
        prediction = predictive_summary.get('prediction')
        if prediction:
            text_parts.append(f"ML Prediction: {prediction}")
        
        # Confidence
        confidence = predictive_summary.get('confidence')
        if confidence:
            text_parts.append(f"Model Confidence: {confidence:.2%}")
        
        # Price forecast
        price_forecast = predictive_summary.get('price_forecast')
        if price_forecast:
            text_parts.append(f"Price Forecast: ${price_forecast:.2f}")
        
        # Model used
        model_used = predictive_summary.get('model_used')
        if model_used:
            text_parts.append(f"Model Used: {model_used}")
        
        return "\n".join(text_parts) if text_parts else "No predictive data available."


def main():
    """Main function to run the investment assessment page."""
    # Initialize protected page (handles auth, setup, CSS, sidebar, user menu)
    init_protected_page()

    # Main page interface
    st.markdown('<h1 class="main-header">🎯 Investment Assessment</h1>', unsafe_allow_html=True)
    
    # Get selected symbol from sidebar
    symbol = st.session_state.get("selected_stock", "AAPL")
    
    # Handle quick assess from sidebar button
    if 'quick_assess' in st.session_state:
        symbol = st.session_state.quick_assess
        del st.session_state.quick_assess  # Clear the quick assess flag
        # Automatically trigger analysis
        st.session_state.auto_assess = True
    
    # Analysis settings
    st.subheader("Analysis Settings")
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        st.info(f"**Selected Stock:** {symbol}")
    with col2:
        # Time period selection
        selected_period = st.selectbox("Time Period", list(PERIOD_OPTIONS.keys()))
        period = PERIOD_OPTIONS[selected_period]
    with col3:
        # Sentiment analysis option
        if SENTIMENT_ENABLED:
            include_sentiment = st.checkbox("Include Sentiment Analysis", value=True, help="Analyze news sentiment using SERPapi (uses API calls)")
        else:
            include_sentiment = False
            if not SENTIMENT_AVAILABLE:
                st.warning("⚠️ Sentiment packages not installed")
            elif not SERP_API_KEY:
                st.warning("⚠️ SERPapi key not configured")
    
    # API and ML setup checks
    if not GEMINI_AVAILABLE:
        st.error("⚠️ Required packages not installed")
        st.code("pip install google-genai python-dotenv")
    else:
        gemini_api_key = get_gemini_api_key()
        if not gemini_api_key:
            st.warning("⚠️ Gemini API key not found")
            st.markdown("""
            **Setup Instructions:**
            1. Create `.env` file in project root
            2. Add: `GEMINI_API_KEY=your_key_here`
            3. Get free key: [aistudio.google.com](https://aistudio.google.com/)
            """)
    
    if not ML_AVAILABLE:
        st.warning("⚠️ Machine learning libraries not available")
        st.code("pip install scikit-learn")
        st.info("Predictive analysis features will be limited without scikit-learn")
    
    # Run assessment button
    assess_clicked = st.button("🚀 Run Assessment", type="primary", use_container_width=True)
    auto_assess = st.session_state.get('auto_assess', False)
    
    if assess_clicked or auto_assess:
        if auto_assess:
            del st.session_state.auto_assess  # Clear the auto assess flag
            
        with st.spinner(f"Running comprehensive assessment for {symbol}..."):
            assessment = InvestmentAssessment(symbol)
            username = st.session_state.get("username")
            if assessment.run_analysis(period, username, include_sentiment):
                st.session_state.assessment_data = assessment
                if include_sentiment and SENTIMENT_ENABLED:
                    st.success(f"Successfully completed assessment for {symbol} (including sentiment analysis)")
                else:
                    st.success(f"Successfully completed assessment for {symbol}")
            else:
                st.error(f"Failed to complete assessment for {symbol}")
    
    # Display assessment if available
    if 'assessment_data' in st.session_state and st.session_state.assessment_data:
        assessment = st.session_state.assessment_data
        
        # Display the assessment dashboard
        assessment.create_assessment_dashboard()
    
    else:
        st.info("👆 Select a stock from the sidebar and click 'Run Assessment' to begin comprehensive analysis")
    
    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: gray;'>
            Investment Assessment powered by Technical Analysis, Fundamental Analysis, and AI | 
            Select stocks from the sidebar to assess | 
            Data is delayed and for informational purposes only
        </div>
        """, 
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
