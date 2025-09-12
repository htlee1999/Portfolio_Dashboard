import streamlit as st
import pandas as pd

from app_utils import setup_page, inject_css, init_session_state, create_sidebar, calculate_portfolio_metrics, format_currency, save_settings_to_storage


setup_page()
inject_css()
init_session_state()
create_sidebar()


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