import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
from data_utils import (
    load_portfolio_data, save_portfolio_data, load_settings, save_settings,
    add_holding, remove_holding, clear_all_holdings,
    export_portfolio_to_csv, import_portfolio_from_csv, get_portfolio_stats, backup_data
)


def setup_page() -> None:
    """Configure Streamlit page settings."""
    st.set_page_config(
        page_title="Portfolio Analysis Dashboard",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            'Get Help': None,
            'Report a bug': None,
            'About': None
        }
    )
    
    # Track current page for conditional sidebar content
    import os
    current_file = os.path.basename(__file__)
    if current_file == "Portfolio.py":
        st.session_state.current_page = "Portfolio.py"
    else:
        # For pages in the pages/ directory
        st.session_state.current_page = f"pages/{current_file}"


def create_custom_navigation():
    """Create custom navigation based on authentication status."""
    is_authenticated = st.session_state.get("authenticated", False)
    
    # Custom CSS for navigation - sidebar spacing fixes
    st.markdown("""
    <style>
    /* Remove default margins and padding to eliminate gap above navigation */
    body {
        margin: 0;
        padding: 0;
    }
    
    /* Remove gap above sidebar header */
    [data-testid="stSidebarHeader"] {
        margin-top: 0 !important;
        padding-top: 0 !important;
    }
    
    .st-emotion-cache-595tnf {
        margin-top: 0 !important;
        padding-top: 0 !important;
    }
    
    /* Remove gaps from markdown containers */
    .stMarkdown {
        margin: 0 !important;
        padding: 0 !important;
    }
    
    .stMarkdownContainer {
        margin: 0 !important;
        padding: 0 !important;
    }
    
    /* Remove gaps from element containers */
    .stElementContainer {
        margin: 0 !important;
        padding: 0 !important;
    }
    
    /* Remove gaps from specific emotion cache classes */
    .st-emotion-cache-v3w3zg {
        margin: 0 !important;
        padding: 0 !important;
    }
    
    .st-emotion-cache-115zvt5 {
        margin: 0 !important;
        padding: 0 !important;
    }
    
    .eertqu00 {
        margin: 0 !important;
        padding: 0 !important;
    }
    
    .e1g8wfdw0 {
        margin: 0 !important;
        padding: 0 !important;
    }
    
    /* Remove all possible gaps from sidebar elements */
    .css-1d391kg {
        margin: 0 !important;
        padding: 0 !important;
    }
    
    .css-1cypcdb {
        margin: 0 !important;
        padding: 0 !important;
    }
    
    /* Target any element with custom-nav class specifically */
    div.custom-nav {
        margin: 0 !important;
        padding: 5px 0 !important;
    }
    
    /* Remove gaps from all div elements in sidebar */
    .sidebar .stMarkdown div {
        margin: 0 !important;
        padding: 0 !important;
    }
    
    /* Ensure main content area adjusts properly */
    .main .block-container {
        padding-top: 2rem;
        padding-left: 2rem;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Create navigation based on authentication status
    with st.sidebar:
        # Create the header first
        st.markdown('<h3 class="nav-header">📊 Portfolio Dashboard</h3>', unsafe_allow_html=True)
        
        if is_authenticated:
            # Authenticated user navigation
            pages = [
                ("🏠 Portfolio", "Portfolio.py"),
                ("📈 Portfolio Builder", "pages/1_Portfolio_Builder.py"),
                ("📊 Dashboard Overview", "pages/2_Dashboard_Overview.py"),
                ("🔍 Detailed Analysis", "pages/3_Detailed_Analysis.py"),
                ("📈 Technical Analysis", "pages/5_Technical_Analysis.py"),
                ("📋 Fundamental Analysis", "pages/6_Fundamental_Analysis.py"),
                ("🎯 Investment Assessment", "pages/7_Investment_Assessment.py"),
            ]
            
            for label, page in pages:
                if st.button(label, key=f"nav_{page}", use_container_width=True):
                    st.switch_page(page)
        else:
            # Non-authenticated user navigation
            pages = [
                ("🏠 Portfolio", "Portfolio.py"),
                ("📝 Sign Up", "pages/0_Sign_Up.py"),
            ]
            
            for label, page in pages:
                if st.button(label, key=f"nav_{page}", use_container_width=True):
                    st.switch_page(page)


def inject_css() -> None:
    """Inject custom CSS for consistent styling across pages."""
    st.markdown("""
    <style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        color: #1f77b4;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
    }
    .positive {
        color: #00c853;
    }
    .negative {
        color: #ff1744;
    }
    .nav-header {
        color: #2c3e50;
        margin: 0 0 10px 0;
        font-size: 20px;
        text-align: center;
        padding: 10px 0;
        border-bottom: 2px solid #3498db;
    }
    .nav-item {
        display: block;
        padding: 12px 20px;
        margin: 5px 0;
        color: #1f77b4;
        text-decoration: none;
        border-radius: 8px;
        transition: all 0.2s;
        font-weight: 500;
    }
    .nav-item:hover {
        background-color: #f0f2f6;
        color: #0d47a1;
    }
    .nav-item.active {
        background-color: #e3f2fd;
        color: #0d47a1;
        font-weight: bold;
    }
    .nav-divider {
        height: 1px;
        background-color: #e0e0e0;
        margin: 15px 0;
    }
    </style>
    """, unsafe_allow_html=True)


def init_session_state() -> None:
    """Initialize shared session state variables if missing."""
    if "portfolio" not in st.session_state:
        # Load portfolio from persistent storage for current user
        username = st.session_state.get("username")
        st.session_state.portfolio = load_portfolio_data(username)
    
    if "base_currency" not in st.session_state:
        # Load settings from persistent storage
        settings = load_settings()
        st.session_state.base_currency = settings.get("base_currency", "USD")
    
    if "data_loaded" not in st.session_state:
        st.session_state.data_loaded = True


def create_sidebar() -> None:
    """Create consistent sidebar navigation across all pages."""
    create_custom_navigation()


def handle_change_password_modal() -> bool:
    """Handle the change password modal if it's shown."""
    if st.session_state.get("show_change_password", False):
        st.markdown('<h1 class="main-header">🔑 Change Password</h1>', unsafe_allow_html=True)
        from auth_utils import change_password_form
        change_password_form()
        return True
    return False




@st.cache_data
def get_stock_data(symbol: str, period: str = "1y"):
    """Fetch OHLCV price history and basic info for a ticker."""
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period=period)
        info = ticker.info
        return data, info
    except Exception as error:
        st.error(f"Error fetching data for {symbol}: {str(error)}")
        return None, None


@st.cache_data
def get_current_price(symbol: str):
    """Get the latest closing price for the given ticker."""
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period="1d")
        return data["Close"].iloc[-1] if not data.empty else None
    except Exception:
        return None


def calculate_portfolio_metrics(portfolio_df: pd.DataFrame, base_currency: str = "USD") -> dict:
    """Compute aggregate portfolio metrics and per-holding breakdown with multi-currency support."""
    if portfolio_df.empty:
        return {}

    total_invested = 0.0
    total_current_value = 0.0
    portfolio_rows = []

    for _, row in portfolio_df.iterrows():
        symbol = row["Symbol"]
        quantity = row["Quantity"]
        purchase_price = row["Purchase_Price"]
        currency = row.get("Currency", "USD")  # Default to USD if not specified

        current_price = get_current_price(symbol)
        if current_price is None:
            continue

        # Calculate values in original currency
        invested_value_original = float(quantity) * float(purchase_price)
        current_value_original = float(quantity) * float(current_price)
        
        # Convert to base currency for aggregation
        invested_value_base = convert_currency(invested_value_original, currency, base_currency)
        current_value_base = convert_currency(current_value_original, currency, base_currency)
        
        gain_loss_original = current_value_original - invested_value_original
        gain_loss_base = current_value_base - invested_value_base
        gain_loss_pct = (gain_loss_original / invested_value_original) * 100 if invested_value_original else 0.0

        portfolio_rows.append(
            {
                "Symbol": symbol,
                "Quantity": quantity,
                "Purchase_Price": purchase_price,
                "Current_Price": current_price,
                "Currency": currency,
                "Invested_Value_Original": invested_value_original,
                "Current_Value_Original": current_value_original,
                "Invested_Value_Base": invested_value_base,
                "Current_Value_Base": current_value_base,
                "Gain_Loss_Original": gain_loss_original,
                "Gain_Loss_Base": gain_loss_base,
                "Gain_Loss_Pct": gain_loss_pct,
            }
        )

        total_invested += invested_value_base
        total_current_value += current_value_base

    if total_invested <= 0:
        return {}

    total_gain_loss = total_current_value - total_invested
    total_gain_loss_pct = (total_gain_loss / total_invested) * 100

    return {
        "total_invested": total_invested,
        "total_current_value": total_current_value,
        "total_gain_loss": total_gain_loss,
        "total_gain_loss_pct": total_gain_loss_pct,
        "base_currency": base_currency,
        "portfolio_data": pd.DataFrame(portfolio_rows),
    }


@st.cache_data
def get_benchmark_data(symbol: str = "^GSPC", period: str = "1y"):
    """Get benchmark historical data (default S&P 500)."""
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period=period)
        return data
    except Exception:
        return None


@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_exchange_rate(from_currency: str, to_currency: str) -> float:
    """Get exchange rate between two currencies using Yahoo Finance."""
    if from_currency == to_currency:
        return 1.0
    
    try:
        # Try to get exchange rate from Yahoo Finance
        symbol = f"{from_currency}{to_currency}=X"
        ticker = yf.Ticker(symbol)
        data = ticker.history(period="1d")
        
        if not data.empty:
            return float(data["Close"].iloc[-1])
        else:
            # Fallback to free API
            return get_exchange_rate_fallback(from_currency, to_currency)
    except Exception:
        return get_exchange_rate_fallback(from_currency, to_currency)


def get_exchange_rate_fallback(from_currency: str, to_currency: str) -> float:
    """Fallback method to get exchange rate using free API."""
    try:
        url = f"https://api.exchangerate-api.com/v4/latest/{from_currency}"
        response = requests.get(url, timeout=5)
        data = response.json()
        return data["rates"].get(to_currency, 1.0)
    except Exception:
        # If all else fails, return 1.0 (assume same currency)
        return 1.0


def convert_currency(amount: float, from_currency: str, to_currency: str) -> float:
    """Convert amount from one currency to another."""
    if from_currency == to_currency:
        return amount
    
    exchange_rate = get_exchange_rate(from_currency, to_currency)
    return amount * exchange_rate


def format_currency(amount: float, currency: str) -> str:
    """Format amount with appropriate currency symbol and formatting."""
    currency_symbols = {
        "USD": "$",
        "SGD": "S$",
        "EUR": "€",
        "GBP": "£",
        "JPY": "¥",
        "CAD": "C$",
        "AUD": "A$",
        "HKD": "HK$",
        "CNY": "¥",
        "INR": "₹",
        "KRW": "₩",
        "THB": "฿",
        "MYR": "RM",
        "IDR": "Rp",
        "PHP": "₱",
        "VND": "₫"
    }
    
    symbol = currency_symbols.get(currency, currency)
    
    if currency in ["JPY", "KRW", "IDR", "VND"]:
        # No decimal places for these currencies
        return f"{symbol}{amount:,.0f}"
    else:
        return f"{symbol}{amount:,.2f}"


def save_portfolio_to_storage() -> bool:
    """Save current portfolio to persistent storage."""
    try:
        username = st.session_state.get("username")
        return save_portfolio_data(st.session_state.portfolio, username)
    except Exception as e:
        st.error(f"Error saving portfolio: {str(e)}")
        return False


def save_settings_to_storage() -> bool:
    """Save current settings to persistent storage."""
    try:
        settings = {
            "base_currency": st.session_state.base_currency
        }
        return save_settings(settings)
    except Exception as e:
        st.error(f"Error saving settings: {str(e)}")
        return False


def add_holding_to_storage(symbol: str, quantity: float, purchase_price: float, 
                          purchase_date, currency: str) -> bool:
    """Add a new holding to persistent storage."""
    try:
        username = st.session_state.get("username")
        success = add_holding(symbol, quantity, purchase_price, purchase_date, currency, username)
        if success:
            # Reload portfolio from storage
            st.session_state.portfolio = load_portfolio_data(username)
        return success
    except Exception as e:
        st.error(f"Error adding holding: {str(e)}")
        return False


def remove_holding_from_storage(symbol: str) -> bool:
    """Remove a holding from persistent storage."""
    try:
        username = st.session_state.get("username")
        success = remove_holding(symbol, username)
        if success:
            # Reload portfolio from storage
            st.session_state.portfolio = load_portfolio_data(username)
        return success
    except Exception as e:
        st.error(f"Error removing holding: {str(e)}")
        return False


def clear_all_holdings_from_storage() -> bool:
    """Clear all holdings from persistent storage."""
    try:
        username = st.session_state.get("username")
        success = clear_all_holdings(username)
        if success:
            # Reload portfolio from storage
            st.session_state.portfolio = load_portfolio_data(username)
        return success
    except Exception as e:
        st.error(f"Error clearing holdings: {str(e)}")
        return False


