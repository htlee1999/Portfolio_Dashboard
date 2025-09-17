import streamlit as st
import plotly.express as px
import pandas as pd

from app_utils import (
    setup_page,
    inject_css,
    init_session_state,
    create_sidebar,
    calculate_portfolio_metrics,
    format_currency,
    save_settings_to_storage,
    handle_change_password_modal,
)
from auth_utils import init_auth_session, show_user_menu

# Initialize authentication
init_auth_session()

# Check authentication
if not st.session_state.get("authenticated", False):
    st.warning("🔐 Please log in to access the Dashboard Overview")
    st.info("Use the Login page in the sidebar to authenticate")
    st.stop()

setup_page()
inject_css()
init_session_state()
create_sidebar()
show_user_menu()

# Handle change password modal
if handle_change_password_modal():
    st.stop()

st.markdown('<h1 class="main-header">📊 Portfolio Dashboard</h1>', unsafe_allow_html=True)

if st.session_state.portfolio.empty:
    st.warning("Please add some stocks to your portfolio first!")
    st.stop()

# Base currency selection
st.subheader("Base Currency for Reporting")
base_currency = st.selectbox(
    "Select base currency for portfolio reporting:",
    ["USD", "SGD", "EUR", "GBP", "JPY", "CAD", "AUD", "HKD", "CNY", "INR", "KRW", "THB", "MYR", "IDR", "PHP", "VND"],
    index=0 if st.session_state.base_currency == "USD" else 1 if st.session_state.base_currency == "SGD" else 0
)

# Save base currency if changed
if base_currency != st.session_state.base_currency:
    st.session_state.base_currency = base_currency
    save_settings_to_storage()

st.markdown("---")

metrics = calculate_portfolio_metrics(st.session_state.portfolio, base_currency)

if not metrics:
    st.error("Unable to calculate portfolio metrics. Please check your stock symbols.")
    st.stop()

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Invested", format_currency(metrics['total_invested'], base_currency))

with col2:
    st.metric("Current Value", format_currency(metrics['total_current_value'], base_currency))

with col3:
    st.metric(
        "Total Gain/Loss",
        format_currency(metrics['total_gain_loss'], base_currency),
        delta=f"{metrics['total_gain_loss_pct']:.2f}%",
    )

with col4:
    st.metric("Return %", f"{metrics['total_gain_loss_pct']:.2f}%")


col1, col2 = st.columns(2)

with col1:
    st.subheader("Portfolio Allocation")
    if not metrics["portfolio_data"].empty:
        fig_pie = px.pie(
            metrics["portfolio_data"], values="Current_Value_Base", names="Symbol", title=f"Portfolio Allocation by Current Value ({base_currency})"
        )
        fig_pie.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig_pie, use_container_width=True)

with col2:
    st.subheader("Gain/Loss by Stock")
    if not metrics["portfolio_data"].empty:
        fig_bar = px.bar(
            metrics["portfolio_data"], x="Symbol", y="Gain_Loss_Base", color="Gain_Loss_Base", color_continuous_scale=["red", "green"], title=f"Gain/Loss by Stock ({base_currency})"
        )
        fig_bar.update_layout(showlegend=False)
        st.plotly_chart(fig_bar, use_container_width=True)


st.subheader("Detailed Holdings")
if not metrics["portfolio_data"].empty:
    display_df = metrics["portfolio_data"].copy()

    # Format prices with original currency symbols
    display_df["Purchase_Price_Formatted"] = display_df.apply(
        lambda row: format_currency(row["Purchase_Price"], row["Currency"]), axis=1
    )
    display_df["Current_Price_Formatted"] = display_df.apply(
        lambda row: format_currency(row["Current_Price"], row["Currency"]), axis=1
    )
    display_df["Invested_Value_Original_Formatted"] = display_df.apply(
        lambda row: format_currency(row["Invested_Value_Original"], row["Currency"]), axis=1
    )
    display_df["Current_Value_Original_Formatted"] = display_df.apply(
        lambda row: format_currency(row["Current_Value_Original"], row["Currency"]), axis=1
    )
    display_df["Gain_Loss_Original_Formatted"] = display_df.apply(
        lambda row: format_currency(row["Gain_Loss_Original"], row["Currency"]), axis=1
    )
    
    # Format base currency values
    display_df["Invested_Value_Base_Formatted"] = display_df["Invested_Value_Base"].apply(
        lambda x: format_currency(x, base_currency)
    )
    display_df["Current_Value_Base_Formatted"] = display_df["Current_Value_Base"].apply(
        lambda x: format_currency(x, base_currency)
    )
    display_df["Gain_Loss_Base_Formatted"] = display_df["Gain_Loss_Base"].apply(
        lambda x: format_currency(x, base_currency)
    )
    
    display_df["Gain_Loss_Pct"] = display_df["Gain_Loss_Pct"].map("{:.2f}%".format)

    # Select and reorder columns for display
    display_columns = [
        "Symbol", "Quantity", "Currency", 
        "Purchase_Price_Formatted", "Current_Price_Formatted",
        "Invested_Value_Original_Formatted", "Current_Value_Original_Formatted", "Gain_Loss_Original_Formatted",
        "Invested_Value_Base_Formatted", "Current_Value_Base_Formatted", "Gain_Loss_Base_Formatted",
        "Gain_Loss_Pct"
    ]
    
    display_df = display_df[display_columns]
    
    # Rename columns for better display
    display_df = display_df.rename(columns={
        "Purchase_Price_Formatted": "Purchase Price",
        "Current_Price_Formatted": "Current Price",
        "Invested_Value_Original_Formatted": f"Invested Value (Original)",
        "Current_Value_Original_Formatted": f"Current Value (Original)",
        "Gain_Loss_Original_Formatted": f"Gain/Loss (Original)",
        "Invested_Value_Base_Formatted": f"Invested Value ({base_currency})",
        "Current_Value_Base_Formatted": f"Current Value ({base_currency})",
        "Gain_Loss_Base_Formatted": f"Gain/Loss ({base_currency})",
        "Gain_Loss_Pct": "Gain/Loss %"
    })

    st.dataframe(display_df, use_container_width=True)


