import streamlit as st
import pandas as pd
import plotly.express as px

from app_utils import (
    calculate_portfolio_metrics,
    format_currency,
    create_currency_selector,
    handle_change_password_modal
)
from data_utils import load_portfolio_data
from page_utils import init_protected_page

# Initialize protected page (handles auth, setup, CSS, sidebar, user menu)
init_protected_page(show_login_form=True)

# Reload portfolio data for current user
if st.session_state.get("authenticated", False):
    username = st.session_state.get("username")
    st.session_state.portfolio = load_portfolio_data(username)

# Handle change password modal
if handle_change_password_modal():
    st.stop()

st.markdown('<h1 class="main-header">📊 Portfolio Overview</h1>', unsafe_allow_html=True)

# Base currency selection
base_currency = create_currency_selector(
    label="Select base currency for portfolio reporting:",
    subheader_text="Base Currency for Reporting"
)

st.markdown("---")

if st.session_state.portfolio.empty:
    st.info("No holdings yet. Use the Portfolio Builder page to add stocks to your portfolio.")
else:
    st.subheader("Portfolio Snapshot")
    
    # Calculate portfolio metrics (with a progress bar so a cold/slow fetch
    # shows visible progress instead of a blank, seemingly-frozen page).
    metrics = calculate_portfolio_metrics(
        st.session_state.portfolio, base_currency, show_progress=True
    )
    
    if not metrics or "total_invested" not in metrics:
        unpriced = metrics.get("unpriced_symbols", []) if metrics else []
        if unpriced:
            st.error(
                "Unable to fetch prices for any holdings: "
                f"{', '.join(unpriced)}. Yahoo Finance may be down or rate-limiting, "
                "and the Finnhub fallback did not return data. Please try again shortly."
            )
        else:
            st.error("Unable to calculate portfolio metrics. Please check your stock symbols.")
        st.stop()

    # Warn if some (but not all) holdings could not be priced — their value is
    # excluded from the totals below, so the numbers would otherwise be silently low.
    unpriced = metrics.get("unpriced_symbols", [])
    if unpriced:
        st.warning(
            f"⚠️ Could not fetch prices for: {', '.join(unpriced)}. "
            "These holdings are excluded from the totals below."
        )

    # Key Metrics Row
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

    # Charts Section
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Portfolio Allocation")
        if not metrics["portfolio_data"].empty:
            fig_pie = px.pie(
                metrics["portfolio_data"], 
                values="Current_Value_Base", 
                names="Symbol", 
                title=f"Portfolio Allocation by Current Value ({base_currency})"
            )
            fig_pie.update_traces(textposition="inside", textinfo="percent+label")
            st.plotly_chart(fig_pie, use_container_width=True)

    with col2:
        st.subheader("Gain/Loss by Stock")
        if not metrics["portfolio_data"].empty:
            fig_bar = px.bar(
                metrics["portfolio_data"], 
                x="Symbol", 
                y="Gain_Loss_Base", 
                color="Gain_Loss_Base", 
                color_continuous_scale=["red", "green"], 
                title=f"Gain/Loss by Stock ({base_currency})"
            )
            fig_bar.update_layout(showlegend=False)
            st.plotly_chart(fig_bar, use_container_width=True)

    # Detailed Holdings Table
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