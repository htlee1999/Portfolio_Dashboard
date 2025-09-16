import streamlit as st
import pandas as pd

from app_utils import setup_page, inject_css, init_session_state, create_sidebar, calculate_portfolio_metrics, format_currency, save_settings_to_storage
from data_utils import load_portfolio_data
from auth_utils import init_auth_session, require_auth, show_user_menu, logout, change_password_form

# Initialize authentication
init_auth_session()

# Check authentication
if not st.session_state.get("authenticated", False):
    st.warning("🔐 Please log in to access the Portfolio Dashboard")
    st.info("Use the Login page in the sidebar to authenticate")
    
    # Show login form
    from auth_utils import login_form
    login_form()
    
    st.stop()

setup_page()
inject_css()
init_session_state()
create_sidebar()
show_user_menu()

# Reload portfolio data for current user
if st.session_state.get("authenticated", False):
    username = st.session_state.get("username")
    st.session_state.portfolio = load_portfolio_data(username)

# Handle change password modal
if st.session_state.get("show_change_password", False):
    st.markdown('<h1 class="main-header">🔑 Change Password</h1>', unsafe_allow_html=True)
    change_password_form()
    st.stop()

st.markdown('<h1 class="main-header">Portfolio Analysis Dashboard</h1>', unsafe_allow_html=True)
st.write(
    "Use the links in the sidebar to build your portfolio, view a dashboard overview, or dive into detailed analysis."
)

if st.session_state.portfolio.empty:
    st.info("No holdings yet. Start with the Portfolio Builder page to add stocks.")
else:
    st.subheader("Current Portfolio Snapshot")
    
    # Display portfolio with formatted currency
    display_df = st.session_state.portfolio.copy()
    if "Currency" in display_df.columns:
        # Format the purchase price with currency symbols
        display_df["Purchase_Price_Formatted"] = display_df.apply(
            lambda row: format_currency(row["Purchase_Price"], row["Currency"]), axis=1
        )
        # Reorder columns for better display
        display_df = display_df[["Symbol", "Quantity", "Purchase_Price_Formatted", "Currency", "Purchase_Date"]]
        display_df = display_df.rename(columns={"Purchase_Price_Formatted": "Purchase_Price"})
    
    st.dataframe(display_df.tail(10), use_container_width=True)

    metrics = calculate_portfolio_metrics(st.session_state.portfolio, st.session_state.base_currency)
    if metrics:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Invested", format_currency(metrics['total_invested'], st.session_state.base_currency))
        with col2:
            st.metric("Current Value", format_currency(metrics['total_current_value'], st.session_state.base_currency))
        with col3:
            st.metric("Return %", f"{metrics['total_gain_loss_pct']:.2f}%")


st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray;'>
        Built with Streamlit and Yahoo Finance API | 
        Data is delayed and for informational purposes only
    </div>
    """, 
    unsafe_allow_html=True,
)