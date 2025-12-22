import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from app_utils import get_stock_data
from page_utils import init_protected_page
from config import SENTIMENT_AVAILABLE, get_serp_api_key, is_serp_api_configured

# Initialize protected page (handles auth, setup, CSS, sidebar, user menu)
init_protected_page(show_login_form=True)

# Check for sentiment analysis libraries
if not SENTIMENT_AVAILABLE:
    st.error("⚠️ Required libraries not installed. Please run: `pip install -r requirements.txt`")
    st.stop()

# Import sentiment analysis libraries (safe since SENTIMENT_AVAILABLE is True)
from serpapi import GoogleSearch
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from textblob import TextBlob

# Check for SERP_API_KEY
SERP_API_KEY = get_serp_api_key()
if not is_serp_api_configured():
    st.error("⚠️ SERP_API_KEY not configured!")
    st.info("""
    To use sentiment analysis, you need to:
    1. Get a free API key from https://serpapi.com/
    2. Create a `.env` file in the project root (copy from `config.env.example`)
    3. Add your API key: `SERP_API_KEY=your_actual_key`
    4. Restart the application
    """)
    st.stop()


class SentimentAnalyzer:
    """Comprehensive sentiment analysis using news data from SERPapi."""
    
    def __init__(self, api_key):
        """Initialize with SERPapi key."""
        self.api_key = api_key
        self.sia = SentimentIntensityAnalyzer()
    
    def get_account_info(self):
        """
        Get SERPapi account information including searches left.
        
        Returns:
            dict: Account information or None if error
        """
        try:
            # Make a minimal search to get account info
            params = {
                "api_key": self.api_key,
                "engine": "google",
                "q": "test",
                "num": 1
            }
            
            search = GoogleSearch(params)
            results = search.get_dict()
            
            # Extract account info from search metadata
            if "search_metadata" in results:
                metadata = results["search_metadata"]
                
                # Try to get account info from search parameters
                account_info = {
                    "total_searches_left": None,
                    "plan_name": "Unknown",
                    "searches_per_month": None,
                    "api_key_valid": True
                }
                
                # Check if there's an error
                if "error" in results:
                    account_info["api_key_valid"] = False
                    account_info["error"] = results["error"]
                
                return account_info
            
            return None
            
        except Exception as e:
            return {"error": str(e), "api_key_valid": False}
    
    def fetch_google_finance_news(self, symbol, num_results=10):
        """
        Fetch news from Google Finance using SERPapi.
        
        Args:
            symbol (str): Stock ticker symbol
            num_results (int): Number of news articles to fetch
            
        Returns:
            list: List of news articles with title, snippet, source, date, link
        """
        try:
            # Try to determine the exchange for the symbol
            import yfinance as yf
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            # Get exchange if available
            exchange = info.get('exchange', 'NASDAQ')
            
            # Format query for Google Finance
            query = f"{symbol}:{exchange}"
            
            params = {
                "api_key": self.api_key,
                "engine": "google_finance",
                "q": query
            }
            
            search = GoogleSearch(params)
            results = search.get_dict()
            
            news_articles = []
            
            # Extract news from results
            if "news_results" in results:
                for item in results["news_results"][:num_results]:
                    article = {
                        "title": item.get("title", ""),
                        "snippet": item.get("snippet", ""),
                        "source": item.get("source", "Unknown"),
                        "date": item.get("date", "Unknown"),
                        "link": item.get("link", "")
                    }
                    news_articles.append(article)
            
            return news_articles
            
        except Exception as e:
            st.warning(f"Google Finance API error: {str(e)}. Trying Google News...")
            return self.fetch_google_news(symbol, num_results)
    
    def fetch_google_news(self, symbol, num_results=10):
        """
        Fetch news from Google News using SERPapi.
        
        Args:
            symbol (str): Stock ticker symbol
            num_results (int): Number of news articles to fetch
            
        Returns:
            list: List of news articles
        """
        try:
            params = {
                "api_key": self.api_key,
                "engine": "google_news",
                "q": f"{symbol} stock",
                "gl": "us",
                "hl": "en"
            }
            
            search = GoogleSearch(params)
            results = search.get_dict()
            
            news_articles = []
            
            if "news_results" in results:
                for item in results["news_results"][:num_results]:
                    article = {
                        "title": item.get("title", ""),
                        "snippet": item.get("snippet", ""),
                        "source": item.get("source", {}).get("name", "Unknown"),
                        "date": item.get("date", "Unknown"),
                        "link": item.get("link", "")
                    }
                    news_articles.append(article)
            
            return news_articles
            
        except Exception as e:
            st.error(f"Error fetching news: {str(e)}")
            return []
    
    def analyze_sentiment_vader(self, text):
        """
        Analyze sentiment using VADER.
        
        Args:
            text (str): Text to analyze
            
        Returns:
            dict: Sentiment scores (neg, neu, pos, compound)
        """
        return self.sia.polarity_scores(text)
    
    def analyze_sentiment_textblob(self, text):
        """
        Analyze sentiment using TextBlob.
        
        Args:
            text (str): Text to analyze
            
        Returns:
            dict: Sentiment scores (polarity, subjectivity)
        """
        blob = TextBlob(text)
        return {
            "polarity": blob.sentiment.polarity,  # -1 to 1
            "subjectivity": blob.sentiment.subjectivity  # 0 to 1
        }
    
    def analyze_news_articles(self, articles):
        """
        Perform sentiment analysis on all articles.
        
        Args:
            articles (list): List of news articles
            
        Returns:
            pd.DataFrame: DataFrame with articles and sentiment scores
        """
        analyzed_articles = []
        
        for article in articles:
            # Combine title and snippet for analysis
            text = f"{article['title']} {article['snippet']}"
            
            # VADER analysis
            vader_scores = self.analyze_sentiment_vader(text)
            
            # TextBlob analysis
            textblob_scores = self.analyze_sentiment_textblob(text)
            
            # Determine overall sentiment
            compound = vader_scores['compound']
            if compound >= 0.05:
                sentiment = "Positive"
                sentiment_emoji = "🟢"
            elif compound <= -0.05:
                sentiment = "Negative"
                sentiment_emoji = "🔴"
            else:
                sentiment = "Neutral"
                sentiment_emoji = "🟡"
            
            analyzed_articles.append({
                "title": article["title"],
                "snippet": article["snippet"],
                "source": article["source"],
                "date": article["date"],
                "link": article["link"],
                "vader_compound": vader_scores['compound'],
                "vader_positive": vader_scores['pos'],
                "vader_negative": vader_scores['neg'],
                "vader_neutral": vader_scores['neu'],
                "textblob_polarity": textblob_scores['polarity'],
                "textblob_subjectivity": textblob_scores['subjectivity'],
                "sentiment": sentiment,
                "sentiment_emoji": sentiment_emoji
            })
        
        return pd.DataFrame(analyzed_articles)
    
    def get_overall_sentiment(self, df):
        """
        Calculate overall sentiment metrics.
        
        Args:
            df (pd.DataFrame): DataFrame with sentiment scores
            
        Returns:
            dict: Overall sentiment metrics
        """
        if df.empty:
            return None
        
        # Count sentiments
        sentiment_counts = df['sentiment'].value_counts().to_dict()
        
        # Average scores
        avg_vader_compound = df['vader_compound'].mean()
        avg_textblob_polarity = df['textblob_polarity'].mean()
        
        # Overall sentiment determination
        if avg_vader_compound >= 0.05:
            overall_sentiment = "Positive"
            overall_emoji = "🟢"
        elif avg_vader_compound <= -0.05:
            overall_sentiment = "Negative"
            overall_emoji = "🔴"
        else:
            overall_sentiment = "Neutral"
            overall_emoji = "🟡"
        
        return {
            "overall_sentiment": overall_sentiment,
            "overall_emoji": overall_emoji,
            "avg_vader_compound": avg_vader_compound,
            "avg_textblob_polarity": avg_textblob_polarity,
            "sentiment_counts": sentiment_counts,
            "total_articles": len(df),
            "positive_pct": sentiment_counts.get("Positive", 0) / len(df) * 100,
            "negative_pct": sentiment_counts.get("Negative", 0) / len(df) * 100,
            "neutral_pct": sentiment_counts.get("Neutral", 0) / len(df) * 100
        }


# Main UI
st.markdown('<h1 class="main-header">💭 Sentiment Analysis</h1>', unsafe_allow_html=True)

st.markdown("""
Analyze market sentiment for stocks using real-time news data from Google Finance and Google News.
Sentiment is analyzed using both **VADER** (specialized for social media and short text) and 
**TextBlob** (general-purpose sentiment analysis).
""")

# Quick API status display
if "serp_account_info" in st.session_state:
    account_data = st.session_state.serp_account_info
    searches_left = account_data.get("total_searches_left", "Unknown")
    
    if isinstance(searches_left, (int, float)):
        if searches_left < 10:
            st.error(f"⚠️ API Status: {searches_left} searches remaining - Running very low!")
        elif searches_left < 25:
            st.warning(f"⚠️ API Status: {searches_left} searches remaining")
        else:
            st.success(f"✅ API Status: {searches_left} searches remaining")
    else:
        st.info("ℹ️ Check your API usage in the 'SERPapi Account Information' section below")

st.markdown("---")

# Display SERPapi account information
with st.expander("📊 SERPapi Account Information", expanded=False):
    if st.button("🔄 Check API Usage", key="check_api_usage"):
        with st.spinner("Checking SERPapi account..."):
            analyzer = SentimentAnalyzer(SERP_API_KEY)
            
            # Get account info using SERPapi account endpoint
            try:
                import requests
                response = requests.get(
                    f"https://serpapi.com/account?api_key={SERP_API_KEY}",
                    timeout=10
                )
                
                if response.status_code == 200:
                    account_data = response.json()
                    
                    # Store in session state
                    st.session_state.serp_account_info = account_data
                    st.session_state.serp_last_check = datetime.now()
                    
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        searches_left = account_data.get("total_searches_left", "Unknown")
                        st.metric("Searches Left", searches_left)
                    
                    with col2:
                        searches_this_month = account_data.get("this_month_usage", 0)
                        st.metric("Used This Month", searches_this_month)
                    
                    with col3:
                        plan_name = account_data.get("plan", "Free")
                        st.metric("Plan", plan_name)
                    
                    with col4:
                        monthly_limit = account_data.get("plan_searches_left", "N/A")
                        st.metric("Monthly Limit", monthly_limit)
                    
                    # Additional details
                    st.markdown("---")
                    st.markdown(f"**Account ID:** {account_data.get('account_id', 'N/A')}")
                    st.markdown(f"**Email:** {account_data.get('account_email', 'Not available')}")
                    
                    # Usage bar
                    if searches_this_month and isinstance(searches_this_month, (int, float)):
                        monthly_searches = account_data.get("plan_searches_left", 100)
                        if isinstance(monthly_searches, (int, float)):
                            total_monthly = searches_this_month + monthly_searches
                            usage_pct = (searches_this_month / total_monthly * 100) if total_monthly > 0 else 0
                            
                            st.markdown("**Monthly Usage:**")
                            st.progress(usage_pct / 100)
                            st.caption(f"{usage_pct:.1f}% used ({searches_this_month}/{total_monthly} searches)")
                    
                    # Warnings
                    if isinstance(searches_left, (int, float)):
                        if searches_left < 10:
                            st.error("⚠️ Low on searches! Consider upgrading your plan.")
                        elif searches_left < 25:
                            st.warning("⚠️ You're running low on searches.")
                        else:
                            st.success("✅ You have plenty of searches remaining.")
                    
                    st.info(f"Last checked: {st.session_state.serp_last_check.strftime('%Y-%m-%d %H:%M:%S')}")
                    
                else:
                    st.error(f"Failed to fetch account info: {response.status_code}")
                    st.info("You can check your usage at: https://serpapi.com/account")
                    
            except Exception as e:
                st.error(f"Error checking account: {str(e)}")
                st.info("You can manually check your usage at: https://serpapi.com/account")
    
    # Show cached info if available
    elif "serp_account_info" in st.session_state:
        account_data = st.session_state.serp_account_info
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            searches_left = account_data.get("total_searches_left", "Unknown")
            st.metric("Searches Left", searches_left)
        
        with col2:
            searches_this_month = account_data.get("this_month_usage", 0)
            st.metric("Used This Month", searches_this_month)
        
        with col3:
            plan_name = account_data.get("plan", "Free")
            st.metric("Plan", plan_name)
        
        with col4:
            monthly_limit = account_data.get("plan_searches_left", "N/A")
            st.metric("Monthly Limit", monthly_limit)
        
        if "serp_last_check" in st.session_state:
            st.caption(f"Last checked: {st.session_state.serp_last_check.strftime('%Y-%m-%d %H:%M:%S')}")
    
    else:
        st.info("👆 Click 'Check API Usage' to see your SERPapi account status and remaining searches")
        st.markdown("""
        **What you'll see:**
        - Remaining searches this month
        - Total searches used
        - Your current plan
        - Monthly limit
        
        **Note:** Checking your account usage counts as 1 API call.
        """)

st.markdown("---")

# Check for quick analysis from sidebar
quick_sentiment = st.session_state.get("quick_sentiment", None)
if quick_sentiment:
    symbol = quick_sentiment
    num_articles = 20
    news_source = "Both"
    # Clear the quick analysis flag
    st.session_state.quick_sentiment = None
    # Set auto-run flag
    auto_run = True
else:
    auto_run = False

# Stock selection
col1, col2 = st.columns([3, 1])

with col1:
    # Get symbol from sidebar selection or allow manual input
    default_symbol = st.session_state.get("selected_stock", symbol if quick_sentiment else "AAPL")
    symbol = st.text_input(
        "Enter Stock Symbol",
        value=default_symbol,
        help="Enter a stock ticker symbol (e.g., AAPL, GOOGL, TSLA)"
    ).upper()

with col2:
    num_articles = st.number_input(
        "Number of Articles",
        min_value=5,
        max_value=50,
        value=num_articles if quick_sentiment else 20,
        step=5,
        help="Number of news articles to analyze"
    )

# News source selection
news_source = st.radio(
    "News Source",
    ["Google Finance", "Google News", "Both"],
    horizontal=True,
    index=2 if quick_sentiment else 2,  # Default to "Both"
    help="Google Finance provides stock-specific news, Google News provides broader coverage"
)

# Analyze button or auto-run
if st.button("🔍 Analyze Sentiment", type="primary", use_container_width=True) or auto_run:
    if not symbol:
        st.warning("Please enter a stock symbol")
    else:
        with st.spinner(f"Fetching news and analyzing sentiment for {symbol}..."):
            analyzer = SentimentAnalyzer(SERP_API_KEY)
            
            # Fetch news based on source selection
            all_articles = []
            
            if news_source in ["Google Finance", "Both"]:
                finance_articles = analyzer.fetch_google_finance_news(symbol, num_articles)
                all_articles.extend(finance_articles)
                if finance_articles:
                    st.success(f"✅ Fetched {len(finance_articles)} articles from Google Finance")
            
            if news_source in ["Google News", "Both"]:
                news_articles = analyzer.fetch_google_news(symbol, num_articles)
                all_articles.extend(news_articles)
                if news_articles:
                    st.success(f"✅ Fetched {len(news_articles)} articles from Google News")
            
            # Remove duplicates based on title
            seen_titles = set()
            unique_articles = []
            for article in all_articles:
                if article["title"] not in seen_titles:
                    seen_titles.add(article["title"])
                    unique_articles.append(article)
            
            if not unique_articles:
                st.error(f"No news articles found for {symbol}. Please try a different symbol or news source.")
            else:
                st.info(f"📰 Analyzing {len(unique_articles)} unique articles...")
                
                # Analyze sentiment
                df_sentiment = analyzer.analyze_news_articles(unique_articles)
                
                # Store in session state
                st.session_state.sentiment_data = df_sentiment
                st.session_state.sentiment_symbol = symbol
                
                # Get overall sentiment
                overall_metrics = analyzer.get_overall_sentiment(df_sentiment)
                
                st.success(f"✅ Sentiment analysis complete for {symbol}!")
                
                # Update API usage info if available
                if "serp_account_info" in st.session_state:
                    # Decrement searches left (approximate)
                    if news_source == "Both":
                        searches_used = 2
                    else:
                        searches_used = 1
                    
                    current_left = st.session_state.serp_account_info.get("total_searches_left", 0)
                    if isinstance(current_left, (int, float)):
                        st.session_state.serp_account_info["total_searches_left"] = max(0, current_left - searches_used)
                        
                        # Update used this month
                        current_used = st.session_state.serp_account_info.get("this_month_usage", 0)
                        st.session_state.serp_account_info["this_month_usage"] = current_used + searches_used
                        
                        st.info(f"📊 API Usage: {searches_used} search(es) used. Approximately {st.session_state.serp_account_info['total_searches_left']} searches remaining.")
                
                # Display overall metrics
                st.markdown("---")
                st.subheader(f"📊 Overall Sentiment for {symbol}")
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric(
                        "Overall Sentiment",
                        f"{overall_metrics['overall_emoji']} {overall_metrics['overall_sentiment']}"
                    )
                
                with col2:
                    st.metric(
                        "VADER Score",
                        f"{overall_metrics['avg_vader_compound']:.3f}",
                        help="Range: -1 (very negative) to +1 (very positive)"
                    )
                
                with col3:
                    st.metric(
                        "TextBlob Polarity",
                        f"{overall_metrics['avg_textblob_polarity']:.3f}",
                        help="Range: -1 (very negative) to +1 (very positive)"
                    )
                
                with col4:
                    st.metric(
                        "Total Articles",
                        overall_metrics['total_articles']
                    )
                
                # Sentiment distribution
                st.markdown("---")
                st.subheader("📈 Sentiment Distribution")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    # Pie chart
                    fig_pie = go.Figure(data=[go.Pie(
                        labels=["Positive", "Negative", "Neutral"],
                        values=[
                            overall_metrics['sentiment_counts'].get("Positive", 0),
                            overall_metrics['sentiment_counts'].get("Negative", 0),
                            overall_metrics['sentiment_counts'].get("Neutral", 0)
                        ],
                        marker=dict(colors=['#00c853', '#ff1744', '#ffc107']),
                        hole=0.4
                    )])
                    fig_pie.update_layout(
                        title="Sentiment Distribution",
                        showlegend=True
                    )
                    st.plotly_chart(fig_pie, use_container_width=True)
                
                with col2:
                    # Bar chart with percentages
                    fig_bar = go.Figure(data=[go.Bar(
                        x=["Positive", "Negative", "Neutral"],
                        y=[
                            overall_metrics['positive_pct'],
                            overall_metrics['negative_pct'],
                            overall_metrics['neutral_pct']
                        ],
                        marker=dict(color=['#00c853', '#ff1744', '#ffc107']),
                        text=[
                            f"{overall_metrics['positive_pct']:.1f}%",
                            f"{overall_metrics['negative_pct']:.1f}%",
                            f"{overall_metrics['neutral_pct']:.1f}%"
                        ],
                        textposition='auto'
                    )])
                    fig_bar.update_layout(
                        title="Sentiment Percentage",
                        yaxis_title="Percentage (%)",
                        showlegend=False
                    )
                    st.plotly_chart(fig_bar, use_container_width=True)
                
                # Sentiment scores over articles
                st.markdown("---")
                st.subheader("📉 Sentiment Scores Timeline")
                
                fig_timeline = make_subplots(
                    rows=2, cols=1,
                    subplot_titles=("VADER Compound Score", "TextBlob Polarity Score"),
                    vertical_spacing=0.15
                )
                
                # VADER scores
                fig_timeline.add_trace(
                    go.Scatter(
                        x=list(range(len(df_sentiment))),
                        y=df_sentiment['vader_compound'],
                        mode='lines+markers',
                        name='VADER',
                        line=dict(color='#1f77b4', width=2),
                        marker=dict(size=6),
                        fill='tozeroy',
                        fillcolor='rgba(31, 119, 180, 0.2)'
                    ),
                    row=1, col=1
                )
                
                # Add zero line
                fig_timeline.add_hline(y=0, line_dash="dash", line_color="gray", row=1, col=1)
                fig_timeline.add_hline(y=0.05, line_dash="dot", line_color="green", row=1, col=1)
                fig_timeline.add_hline(y=-0.05, line_dash="dot", line_color="red", row=1, col=1)
                
                # TextBlob scores
                fig_timeline.add_trace(
                    go.Scatter(
                        x=list(range(len(df_sentiment))),
                        y=df_sentiment['textblob_polarity'],
                        mode='lines+markers',
                        name='TextBlob',
                        line=dict(color='#ff7f0e', width=2),
                        marker=dict(size=6),
                        fill='tozeroy',
                        fillcolor='rgba(255, 127, 14, 0.2)'
                    ),
                    row=2, col=1
                )
                
                fig_timeline.add_hline(y=0, line_dash="dash", line_color="gray", row=2, col=1)
                
                fig_timeline.update_xaxes(title_text="Article Index", row=2, col=1)
                fig_timeline.update_yaxes(title_text="Score", range=[-1, 1], row=1, col=1)
                fig_timeline.update_yaxes(title_text="Score", range=[-1, 1], row=2, col=1)
                
                fig_timeline.update_layout(height=600, showlegend=True)
                
                st.plotly_chart(fig_timeline, use_container_width=True)
                
                # Individual articles
                st.markdown("---")
                st.subheader("📰 Individual Article Analysis")
                
                # Sort options
                sort_by = st.selectbox(
                    "Sort articles by",
                    ["Most Recent", "Most Positive", "Most Negative", "Highest Subjectivity"],
                    key="sort_articles"
                )
                
                # Apply sorting
                if sort_by == "Most Positive":
                    df_display = df_sentiment.sort_values("vader_compound", ascending=False)
                elif sort_by == "Most Negative":
                    df_display = df_sentiment.sort_values("vader_compound", ascending=True)
                elif sort_by == "Highest Subjectivity":
                    df_display = df_sentiment.sort_values("textblob_subjectivity", ascending=False)
                else:  # Most Recent
                    df_display = df_sentiment
                
                # Display articles in expandable sections
                for idx, row in df_display.iterrows():
                    with st.expander(f"{row['sentiment_emoji']} {row['title'][:100]}...", expanded=False):
                        col1, col2 = st.columns([3, 1])
                        
                        with col1:
                            st.markdown(f"**{row['title']}**")
                            st.markdown(f"_{row['snippet']}_")
                            st.markdown(f"**Source:** {row['source']} | **Date:** {row['date']}")
                            st.markdown(f"[Read Full Article]({row['link']})")
                        
                        with col2:
                            st.markdown("**Sentiment Scores**")
                            st.markdown(f"**Overall:** {row['sentiment_emoji']} {row['sentiment']}")
                            st.markdown(f"**VADER:** {row['vader_compound']:.3f}")
                            st.markdown(f"**TextBlob:** {row['textblob_polarity']:.3f}")
                            st.markdown(f"**Subjectivity:** {row['textblob_subjectivity']:.3f}")
                            
                            # Show detailed VADER scores
                            st.markdown("---")
                            st.markdown("**VADER Breakdown**")
                            st.markdown(f"Positive: {row['vader_positive']:.3f}")
                            st.markdown(f"Negative: {row['vader_negative']:.3f}")
                            st.markdown(f"Neutral: {row['vader_neutral']:.3f}")
                
                # Export option
                st.markdown("---")
                st.subheader("💾 Export Results")
                
                csv = df_sentiment.to_csv(index=False)
                st.download_button(
                    label="📥 Download Sentiment Analysis (CSV)",
                    data=csv,
                    file_name=f"{symbol}_sentiment_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )

# Display cached results if available
elif "sentiment_data" in st.session_state and "sentiment_symbol" in st.session_state:
    st.info(f"📊 Showing previous results for **{st.session_state.sentiment_symbol}**. Click 'Analyze Sentiment' to refresh.")

# Information section
st.markdown("---")
st.markdown("### ℹ️ About Sentiment Analysis")

with st.expander("📚 Understanding Sentiment Scores"):
    st.markdown("""
    #### VADER (Valence Aware Dictionary and sEntiment Reasoner)
    
    VADER is specifically designed for social media text and performs well on short headlines and snippets.
    
    - **Compound Score**: Overall sentiment ranging from -1 (extremely negative) to +1 (extremely positive)
        - Positive: ≥ 0.05
        - Neutral: between -0.05 and 0.05
        - Negative: ≤ -0.05
    - **Individual Scores**: Proportion of text that falls in positive, negative, and neutral categories
    
    #### TextBlob
    
    TextBlob provides general-purpose sentiment analysis with two metrics:
    
    - **Polarity**: Sentiment orientation from -1 (negative) to +1 (positive)
    - **Subjectivity**: How subjective the text is, from 0 (objective) to 1 (subjective)
    
    #### Best Practices
    
    - **VADER** is generally more accurate for financial news headlines and social media
    - **TextBlob** provides additional context through subjectivity scores
    - Use both scores together for a comprehensive view
    - Consider the **subjectivity score** - highly subjective articles may be less reliable
    - Always verify sentiment with actual news content, as automated analysis isn't perfect
    """)

with st.expander("🔍 News Sources"):
    st.markdown("""
    #### Google Finance
    - Provides stock-specific news directly from Google Finance
    - More focused on the specific company and stock
    - Usually includes analyst reports and company announcements
    
    #### Google News
    - Broader news coverage from various sources
    - May include general market news and industry trends
    - Good for understanding broader market context
    
    #### Recommendation
    Use **Both** sources for the most comprehensive sentiment analysis.
    """)

with st.expander("⚠️ Limitations & Disclaimers"):
    st.markdown("""
    #### Important Notes
    
    - **Not Financial Advice**: This tool is for informational purposes only and should not be used as the sole basis for investment decisions
    - **Accuracy**: Automated sentiment analysis is not 100% accurate and may misinterpret sarcasm, context, or complex language
    - **Timeliness**: News data may have a slight delay; for critical decisions, verify with real-time sources
    - **Bias**: News sources may have inherent biases; consider multiple sources
    - **API Limits**: SERPapi has usage limits based on your subscription plan
    
    #### Best Practices for Investment Decisions
    
    1. **Combine with Other Analysis**: Use sentiment alongside technical and fundamental analysis
    2. **Verify News**: Read the actual articles to understand the full context
    3. **Consider the Source**: Evaluate the credibility of news sources
    4. **Look for Patterns**: Single articles may not be representative; look for overall trends
    5. **Stay Updated**: Sentiment can change rapidly with breaking news
    """)

st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray;'>
    Built with Streamlit, SERPapi, VADER, and TextBlob | 
    News data is for informational purposes only
</div>
""", unsafe_allow_html=True)

