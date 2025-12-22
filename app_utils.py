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


def apply_chart_style(fig, title: str, height: int = 500,
                      xaxis_title: str = "Date", yaxis_title: str = None,
                      show_legend: bool = True) -> None:
    """
    Apply consistent styling to Plotly figures.

    Args:
        fig: Plotly figure object
        title: Chart title
        height: Chart height in pixels (default: 500)
        xaxis_title: X-axis label (default: "Date")
        yaxis_title: Y-axis label (optional)
        show_legend: Whether to show legend (default: True)
    """
    layout_kwargs = {
        "title": title,
        "height": height,
        "showlegend": show_legend,
        "hovermode": "x unified"
    }

    if xaxis_title:
        layout_kwargs["xaxis_title"] = xaxis_title
    if yaxis_title:
        layout_kwargs["yaxis_title"] = yaxis_title

    fig.update_layout(**layout_kwargs)


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
    import inspect
    import os
    
    # Get the calling frame to determine which page is calling this function
    frame = inspect.currentframe().f_back
    calling_file = frame.f_globals.get('__file__', '')
    
    if calling_file:
        current_file = os.path.basename(calling_file)
        if current_file == "Portfolio.py":
            st.session_state.current_page = "Portfolio.py"
        else:
            # For pages in the pages/ directory
            st.session_state.current_page = f"pages/{current_file}"
    else:
        # Fallback if we can't determine the calling file
        st.session_state.current_page = "unknown"


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
    
    /* Hide Streamlit's default navigation elements */
    [data-testid="collapsedControl"] {
        display: none !important;
    }
    
    /* Hide any default Streamlit navigation that might appear */
    .stApp > div:first-child > div:first-child > div:first-child {
        display: none !important;
    }
    
    /* Hide default sidebar navigation elements */
    [data-testid="stSidebarNav"] {
        display: none !important;
    }
    
    /* Hide any default page navigation */
    .stApp > div:first-child > div:first-child {
        display: none !important;
    }
    
    /* Ensure our custom sidebar is visible */
    [data-testid="stSidebar"] {
        display: block !important;
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
                ("🏠 Portfolio Overview", "pages/1_Portfolio_Overview.py"),
                ("📈 Portfolio Builder", "pages/1_Portfolio_Builder.py"),
                ("🔍 Detailed Analysis", "pages/3_Detailed_Analysis.py"),
                ("📈 Technical Analysis", "pages/5_Technical_Analysis.py"),
                ("📋 Fundamental Analysis", "pages/6_Fundamental_Analysis.py"),
                ("🤖 Predictive Analysis", "pages/9_Predictive_Analysis.py"),
                ("💭 Sentiment Analysis", "pages/10_Sentiment_Analysis.py"),
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


def create_stock_selection_sidebar() -> None:
    """Create stock selection sidebar for analysis pages."""
    # Check if we're on an analysis page using multiple methods
    current_page = st.session_state.get("current_page", "")
    
    # Method 1: Check current_page session state
    analysis_pages = [
        "pages/5_Technical_Analysis.py",
        "pages/6_Fundamental_Analysis.py", 
        "pages/7_Investment_Assessment.py",
        "pages/9_Predictive_Analysis.py",
        "pages/10_Sentiment_Analysis.py"
    ]
    
    # Method 2: Check if we're in an analysis context by looking at session state keys
    is_analysis_page = (
        current_page in analysis_pages or
        'ta_data' in st.session_state or
        'fundamental_analysis' in st.session_state or
        'assessment_data' in st.session_state or
        'pa_results' in st.session_state or
        'sentiment_data' in st.session_state or
        'quick_analyze' in st.session_state or
        'quick_fundamental' in st.session_state or
        'quick_assess' in st.session_state or
        'quick_predictive' in st.session_state or
        'quick_sentiment' in st.session_state
    )
    
    # Debug information (uncomment for debugging)
    # with st.sidebar:
    #     st.write(f"Debug - Current page: {current_page}")
    #     st.write(f"Debug - Is analysis page: {is_analysis_page}")
    #     st.write(f"Debug - Session keys: {list(st.session_state.keys())}")
    
    if is_analysis_page:
        with st.sidebar:
            st.markdown("---")
            st.markdown("### 📈 Stock Selection")
            
            # Get symbols from portfolio or allow manual input
            portfolio = st.session_state.get("portfolio", pd.DataFrame())
            if not portfolio.empty:
                portfolio_symbols = portfolio['Symbol'].unique().tolist()
                symbol_options = portfolio_symbols + ["Custom Symbol"]
            else:
                symbol_options = ["Custom Symbol"]
            
            # Stock selection
            selected_option = st.selectbox("Select Stock", symbol_options, key="sidebar_stock_select")
            
            if selected_option == "Custom Symbol":
                custom_symbol = st.text_input("Enter Stock Symbol", value="AAPL", key="sidebar_custom_symbol").upper()
                selected_symbol = custom_symbol
            else:
                selected_symbol = selected_option
            
            # Store selected symbol in session state
            st.session_state.selected_stock = selected_symbol
            
            # Show current selection
            if selected_symbol:
                st.success(f"✅ Selected: **{selected_symbol}**")
            
            # Quick action buttons for analysis pages
            if current_page == "pages/5_Technical_Analysis.py" or 'ta_data' in st.session_state:
                if st.button("📈 Run Technical Analysis", key="sidebar_tech_analysis", use_container_width=True):
                    st.session_state.quick_analyze = selected_symbol
                    st.rerun()
            
            elif current_page == "pages/6_Fundamental_Analysis.py" or 'fundamental_analysis' in st.session_state:
                if st.button("📊 Run Fundamental Analysis", key="sidebar_fund_analysis", use_container_width=True):
                    st.session_state.quick_fundamental = selected_symbol
                    st.rerun()
            
            elif current_page == "pages/7_Investment_Assessment.py" or 'assessment_data' in st.session_state:
                if st.button("🎯 Run Investment Assessment", key="sidebar_investment_assess", use_container_width=True):
                    st.session_state.quick_assess = selected_symbol
                    st.rerun()
            
            elif current_page == "pages/9_Predictive_Analysis.py" or 'pa_results' in st.session_state:
                if st.button("🤖 Run Predictive Analysis", key="sidebar_predictive_analysis", use_container_width=True):
                    st.session_state.quick_predictive = selected_symbol
                    st.rerun()
            
            elif current_page == "pages/10_Sentiment_Analysis.py" or 'sentiment_data' in st.session_state:
                if st.button("💭 Run Sentiment Analysis", key="sidebar_sentiment_analysis", use_container_width=True):
                    st.session_state.quick_sentiment = selected_symbol
                    st.rerun()
            
            # Generic fallback button
            else:
                if st.button("🚀 Run Analysis", key="sidebar_generic_analysis", use_container_width=True):
                    st.session_state.quick_analyze = selected_symbol
                    st.rerun()


def create_sidebar() -> None:
    """Create consistent sidebar navigation across all pages."""
    create_custom_navigation()
    create_stock_selection_sidebar()


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


# Supported currencies for the application
SUPPORTED_CURRENCIES = ["USD", "SGD", "EUR", "GBP", "JPY", "CAD", "AUD", "HKD", "CNY", "INR", "KRW", "THB", "MYR", "IDR", "PHP", "VND"]


def create_currency_selector(label: str = "Select base currency:",
                             show_subheader: bool = True,
                             subheader_text: str = "Base Currency",
                             auto_save: bool = True) -> str:
    """
    Create a reusable currency selection dropdown.

    Args:
        label: Label for the selectbox
        show_subheader: Whether to show a subheader above the dropdown
        subheader_text: Text for the subheader
        auto_save: Whether to auto-save when currency changes

    Returns:
        str: The selected currency code
    """
    if show_subheader:
        st.subheader(subheader_text)

    current_currency = st.session_state.get("base_currency", "USD")

    # Find the index of the current currency
    try:
        current_index = SUPPORTED_CURRENCIES.index(current_currency)
    except ValueError:
        current_index = 0

    selected_currency = st.selectbox(
        label,
        SUPPORTED_CURRENCIES,
        index=current_index
    )

    # Save if changed and auto_save is enabled
    if auto_save and selected_currency != current_currency:
        st.session_state.base_currency = selected_currency
        save_settings_to_storage()

    return selected_currency


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


def generate_ai_report_pdf(assessment_result: dict, symbol: str, technical_summary: str = "", 
                          fundamental_summary: str = "", sentiment_summary: str = "", 
                          predictive_summary: str = "") -> str:
    """
    Generate a comprehensive PDF report for AI investment assessment.
    
    Args:
        assessment_result: Dictionary containing AI assessment data
        symbol: Stock symbol being analyzed
        technical_summary: Technical analysis summary
        fundamental_summary: Fundamental analysis summary
        sentiment_summary: Sentiment analysis summary
        predictive_summary: Predictive analysis summary
    
    Returns:
        str: Path to the generated PDF file, or None if generation failed
    """
    try:
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
        from datetime import datetime
        import os
        
        # Create exports directory
        data_dir = os.path.join(os.path.dirname(__file__), "data")
        exports_dir = os.path.join(data_dir, "exports")
        if not os.path.exists(exports_dir):
            os.makedirs(exports_dir)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ai_report_{symbol}_{timestamp}.pdf"
        file_path = os.path.join(exports_dir, filename)
        
        # Create PDF document
        doc = SimpleDocTemplate(file_path, pagesize=A4, 
                              rightMargin=72, leftMargin=72, 
                              topMargin=72, bottomMargin=18)
        
        # Get styles
        styles = getSampleStyleSheet()
        
        # Create custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.darkblue
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            spaceAfter=12,
            spaceBefore=12,
            textColor=colors.darkblue
        )
        
        subheading_style = ParagraphStyle(
            'CustomSubHeading',
            parent=styles['Heading3'],
            fontSize=12,
            spaceAfter=8,
            spaceBefore=8,
            textColor=colors.darkgreen
        )
        
        body_style = ParagraphStyle(
            'CustomBody',
            parent=styles['Normal'],
            fontSize=10,
            spaceAfter=6,
            alignment=TA_JUSTIFY
        )
        
        # Build content
        story = []
        
        # Title
        story.append(Paragraph(f"AI Investment Assessment Report", title_style))
        story.append(Paragraph(f"Stock Symbol: {symbol.upper()}", heading_style))
        story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", body_style))
        story.append(Spacer(1, 20))
        
        # Executive Summary
        story.append(Paragraph("Executive Summary", heading_style))
        
        recommendation = assessment_result.get('recommendation', 'HOLD')
        confidence = assessment_result.get('confidence', 5)
        time_horizon = assessment_result.get('time_horizon', 'Medium-term')
        price_target = assessment_result.get('price_target')
        
        # Recommendation table
        rec_data = [
            ['Recommendation', recommendation],
            ['Confidence Level', f"{confidence}/10"],
            ['Time Horizon', time_horizon],
            ['Price Target', f"${price_target:.2f}" if price_target else "N/A"]
        ]
        
        rec_table = Table(rec_data, colWidths=[2*inch, 3*inch])
        rec_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('BACKGROUND', (0, 0), (0, -1), colors.lightblue),
        ]))
        
        story.append(rec_table)
        story.append(Spacer(1, 20))
        
        # AI Reasoning Process
        reasoning_steps = assessment_result.get('reasoning_steps', [])
        if reasoning_steps:
            story.append(Paragraph("AI Reasoning Process", heading_style))
            for i, step_data in enumerate(reasoning_steps, 1):
                step_title = step_data.get('step', f'Step {i}')
                step_content = step_data.get('content', '')
                
                story.append(Paragraph(f"{i}. {step_title}", subheading_style))
                if step_content:
                    story.append(Paragraph(step_content, body_style))
                else:
                    story.append(Paragraph("No detailed reasoning for this step.", body_style))
                story.append(Spacer(1, 10))
        
        # Strengths and Risks
        strengths = assessment_result.get('strengths', [])
        risks = assessment_result.get('risks', [])
        
        if strengths or risks:
            story.append(Paragraph("Key Analysis Points", heading_style))
            
            col_data = []
            if strengths:
                col_data.append(['Key Strengths', 'Key Risks'])
                max_len = max(len(strengths), len(risks))
                for i in range(max_len):
                    strength = strengths[i] if i < len(strengths) else ""
                    risk = risks[i] if i < len(risks) else ""
                    col_data.append([f"✓ {strength}", f"⚠ {risk}"])
            else:
                col_data = [['Key Risks']]
                for risk in risks:
                    col_data.append([f"⚠ {risk}"])
            
            analysis_table = Table(col_data, colWidths=[3*inch, 3*inch] if strengths else [6*inch])
            analysis_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(analysis_table)
            story.append(Spacer(1, 20))
        
        # Complete Analysis
        complete_analysis = assessment_result.get('reasoning', 'No reasoning provided')
        if complete_analysis:
            story.append(Paragraph("Complete Analysis", heading_style))
            story.append(Paragraph(complete_analysis, body_style))
            story.append(Spacer(1, 20))
        
        # Analysis Summaries
        if technical_summary:
            story.append(Paragraph("Technical Analysis Summary", heading_style))
            story.append(Paragraph(technical_summary, body_style))
            story.append(Spacer(1, 15))
        
        if fundamental_summary:
            story.append(Paragraph("Fundamental Analysis Summary", heading_style))
            story.append(Paragraph(fundamental_summary, body_style))
            story.append(Spacer(1, 15))
        
        if sentiment_summary:
            story.append(Paragraph("Sentiment Analysis Summary", heading_style))
            story.append(Paragraph(sentiment_summary, body_style))
            story.append(Spacer(1, 15))
        
        if predictive_summary:
            story.append(Paragraph("Predictive Analysis Summary", heading_style))
            story.append(Paragraph(predictive_summary, body_style))
            story.append(Spacer(1, 15))
        
        # Footer
        story.append(Spacer(1, 30))
        story.append(Paragraph("Generated by Portfolio Analysis Dashboard", 
                              ParagraphStyle('Footer', parent=styles['Normal'], 
                                           fontSize=8, alignment=TA_CENTER, 
                                           textColor=colors.grey)))
        
        # Build PDF
        doc.build(story)
        
        return file_path
        
    except Exception as e:
        # Handle both Streamlit and non-Streamlit contexts
        try:
            st.error(f"Error generating PDF report: {str(e)}")
        except:
            print(f"Error generating PDF report: {str(e)}")
        return None


