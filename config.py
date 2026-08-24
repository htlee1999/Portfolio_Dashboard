"""
Centralized configuration module.
Contains API keys, feature availability flags, and shared constants.
"""

import os
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


# =============================================================================
# API KEY RETRIEVAL
# =============================================================================

def get_serp_api_key() -> Optional[str]:
    """Get SERP API key from environment."""
    return os.getenv("SERP_API_KEY")


def get_gemini_api_key() -> Optional[str]:
    """Get Gemini API key from environment."""
    return os.environ.get("GEMINI_API_KEY")


def get_finnhub_api_key() -> Optional[str]:
    """Get Finnhub API key from environment (used as a price-data fallback)."""
    return os.getenv("FINN_API_KEY")


def is_finnhub_configured() -> bool:
    """Check if Finnhub API key is properly configured."""
    key = get_finnhub_api_key()
    return bool(key and key != "your_finnhub_api_key_here")


def is_serp_api_configured() -> bool:
    """Check if SERP API key is properly configured."""
    key = get_serp_api_key()
    return bool(key and key != "your_serpapi_key_here")


def is_gemini_api_configured() -> bool:
    """Check if Gemini API key is properly configured."""
    key = get_gemini_api_key()
    return bool(key and key != "your_gemini_api_key_here")


# =============================================================================
# FEATURE AVAILABILITY FLAGS
# =============================================================================

# Check for Google Gemini
try:
    from google import genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

# Check for Machine Learning libraries
try:
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler
    from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
    from sklearn.tree import DecisionTreeRegressor, DecisionTreeClassifier
    from sklearn.svm import SVR, SVC
    from sklearn.metrics import mean_squared_error, mean_absolute_error, accuracy_score
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False

# Check for Sentiment Analysis libraries
try:
    from serpapi import GoogleSearch
    import nltk
    from nltk.sentiment.vader import SentimentIntensityAnalyzer
    from textblob import TextBlob
    SENTIMENT_AVAILABLE = True

    # Download VADER lexicon if not already present
    try:
        nltk.data.find('sentiment/vader_lexicon.zip')
    except LookupError:
        try:
            nltk.download('vader_lexicon', quiet=True)
            nltk.download('punkt', quiet=True)
        except Exception:
            pass
except ImportError:
    SENTIMENT_AVAILABLE = False

# Combined check for sentiment functionality
SENTIMENT_ENABLED = SENTIMENT_AVAILABLE and is_serp_api_configured()


# =============================================================================
# SHARED CONSTANTS
# =============================================================================

# Portfolio DataFrame column schema
PORTFOLIO_COLUMNS = ["Symbol", "Quantity", "Purchase_Price", "Purchase_Date", "Currency"]

# =============================================================================
# TICKER NORMALIZATION
# =============================================================================
# Different sources (and users) refer to the same company with different codes.
# This map resolves common company names, misspellings, renamed tickers, and
# alternate listings to ONE canonical Yahoo Finance symbol. Where a company has
# a US-listed ADR we prefer it, because that symbol works on BOTH Yahoo and the
# Finnhub fallback (Finnhub's free tier only covers US-listed symbols).
#
# Keys are compared after upper-casing and stripping whitespace. Extend freely.
TICKER_ALIASES = {
    # Renamed / rebranded
    "FB": "META",
    "GOOGLE": "GOOGL",
    # Company name / misspelling -> US-listed ADR (works on Yahoo AND Finnhub)
    "TSMC": "TSM",          # Taiwan Semiconductor (NYSE ADR)
    "NOKIA": "NOK",         # Nokia (NYSE ADR)
    "ALIBABA": "BABA",      # Alibaba (NYSE ADR)
    "ASML.AS": "ASML",      # Prefer the NASDAQ listing over Amsterdam
    # Share-class format: Yahoo uses '-', people often type '.'
    "BRK.B": "BRK-B",
    "BRK.A": "BRK-A",
    # SK Hynix: SKHY is a valid US-listed (USD) symbol on both Yahoo and Finnhub,
    # so keep it as-is and point the company-name variants at it.
    "SKHYNIX": "SKHY",
    "SK HYNIX": "SKHY",
    "SK-HYNIX": "SKHY",
}


def normalize_symbol(symbol: str) -> str:
    """Resolve a user-entered code to its canonical Yahoo Finance symbol.

    Upper-cases, trims, and applies TICKER_ALIASES. Unknown symbols are returned
    upper-cased/trimmed unchanged, so this is always safe to call.
    """
    if not symbol:
        return symbol
    key = str(symbol).strip().upper()
    return TICKER_ALIASES.get(key, key)

# Supported currencies for the application
SUPPORTED_CURRENCIES = [
    "USD", "SGD", "EUR", "GBP", "JPY", "CAD", "AUD", "HKD",
    "CNY", "INR", "KRW", "THB", "MYR", "IDR", "PHP", "VND"
]

# Analysis period options (display label -> yfinance period code)
PERIOD_OPTIONS = {
    "1 Month": "1mo",
    "3 Months": "3mo",
    "6 Months": "6mo",
    "1 Year": "1y",
    "2 Years": "2y",
    "5 Years": "5y"
}

# Simple period list for basic dropdowns
PERIOD_LIST = ["1mo", "3mo", "6mo", "1y", "2y", "5y"]

# Default period index (1 Year)
DEFAULT_PERIOD_INDEX = 3


# =============================================================================
# TIMESTAMP HELPERS
# =============================================================================

def get_iso_timestamp() -> str:
    """Get current timestamp in ISO format."""
    return datetime.now().isoformat()

def get_file_timestamp() -> str:
    """Get current timestamp formatted for filenames (YYYYMMDD_HHMMSS)."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")
