import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

from app_utils import (
    setup_page,
    inject_css,
    init_session_state,
    create_sidebar,
    get_benchmark_data,
    get_stock_data,
    calculate_portfolio_metrics,
    format_currency,
    save_settings_to_storage,
)


setup_page()
inject_css()
init_session_state()
create_sidebar()


st.markdown('<h1 class="main-header">🔍 Detailed Analysis</h1>', unsafe_allow_html=True)

if st.session_state.portfolio.empty:
    st.warning("Please add some stocks to your portfolio first!")
    st.stop()

# Base currency selection
st.subheader("Base Currency for Analysis")
base_currency = st.selectbox(
    "Select base currency for analysis:",
    ["USD", "SGD", "EUR", "GBP", "JPY", "CAD", "AUD", "HKD", "CNY", "INR", "KRW", "THB", "MYR", "IDR", "PHP", "VND"],
    index=0 if st.session_state.base_currency == "USD" else 1 if st.session_state.base_currency == "SGD" else 0
)

# Save base currency if changed
if base_currency != st.session_state.base_currency:
    st.session_state.base_currency = base_currency
    save_settings_to_storage()

st.markdown("---")

period = st.selectbox("Select Analysis Period:", ["1mo", "3mo", "6mo", "1y", "2y", "5y"], index=3)

metrics = calculate_portfolio_metrics(st.session_state.portfolio, base_currency)
if not metrics:
    st.error("Unable to calculate portfolio metrics.")
    st.stop()


st.subheader("Portfolio Performance vs S&P 500")
benchmark_data = get_benchmark_data("^GSPC", period)

if benchmark_data is not None and not benchmark_data.empty:
    portfolio_symbols = st.session_state.portfolio["Symbol"].unique()

    fig = make_subplots(
        rows=2,
        cols=1,
        subplot_titles=("Portfolio vs S&P 500", "Volume"),
        vertical_spacing=0.1,
        row_width=[0.7, 0.3],
    )

    benchmark_normalized = (benchmark_data["Close"] / benchmark_data["Close"].iloc[0]) * 100
    fig.add_trace(
        go.Scatter(x=benchmark_data.index, y=benchmark_normalized, name="S&P 500", line=dict(color="blue", width=2)),
        row=1,
        col=1,
    )

    colors = px.colors.qualitative.Set1
    for i, symbol in enumerate(portfolio_symbols):
        stock_data, _ = get_stock_data(symbol, period)
        if stock_data is not None and not stock_data.empty:
            stock_normalized = (stock_data["Close"] / stock_data["Close"].iloc[0]) * 100
            fig.add_trace(
                go.Scatter(
                    x=stock_data.index,
                    y=stock_normalized,
                    name=symbol,
                    line=dict(color=colors[i % len(colors)]),
                ),
                row=1,
                col=1,
            )

    fig.update_layout(height=600, title_text="Portfolio Performance Analysis", showlegend=True)
    fig.update_xaxes(title_text="Date")
    fig.update_yaxes(title_text="Normalized Performance (%)", row=1, col=1)

    st.plotly_chart(fig, use_container_width=True)


col1, col2 = st.columns(2)

with col1:
    st.subheader("Risk Metrics")
    if not metrics["portfolio_data"].empty:
        portfolio_symbols = st.session_state.portfolio["Symbol"].unique()
        returns_data = []
        for symbol in portfolio_symbols:
            stock_data, _ = get_stock_data(symbol, "1y")
            if stock_data is not None and not stock_data.empty:
                returns = stock_data["Close"].pct_change().dropna()
                returns_data.append(
                    {
                        "Symbol": symbol,
                        "Volatility": returns.std() * np.sqrt(252) * 100,
                        "Avg_Daily_Return": returns.mean() * 100,
                    }
                )

        if returns_data:
            risk_df = pd.DataFrame(returns_data)
            st.dataframe(risk_df.round(2), use_container_width=True)

with col2:
    st.subheader("Sector Breakdown")
    portfolio_symbols = st.session_state.portfolio["Symbol"].unique()
    sector_data = []
    for symbol in portfolio_symbols:
        _, info = get_stock_data(symbol, "1d")
        if info:
            sector = info.get("sector", "Unknown")
            weight = metrics["portfolio_data"][metrics["portfolio_data"]["Symbol"] == symbol]["Current_Value_Base"].iloc[0]
            sector_data.append({"Sector": sector, "Value": weight})

    if sector_data:
        sector_df = pd.DataFrame(sector_data)
        sector_summary = sector_df.groupby("Sector")["Value"].sum().reset_index()
        fig_sector = px.pie(sector_summary, values="Value", names="Sector", title="Portfolio by Sector")
        st.plotly_chart(fig_sector, use_container_width=True)


st.subheader("Performance Summary")
if not metrics["portfolio_data"].empty:
    summary_stats = {
        "Metric": [
            f"Total Portfolio Value ({base_currency})",
            f"Total Invested ({base_currency})",
            f"Total Gain/Loss ({base_currency})",
            "Total Return %",
            "Best Performer",
            "Worst Performer",
            "Number of Holdings",
        ],
        "Value": [
            format_currency(metrics['total_current_value'], base_currency),
            format_currency(metrics['total_invested'], base_currency),
            format_currency(metrics['total_gain_loss'], base_currency),
            f"{metrics['total_gain_loss_pct']:.2f}%",
            metrics["portfolio_data"].loc[metrics["portfolio_data"]["Gain_Loss_Pct"].idxmax(), "Symbol"],
            metrics["portfolio_data"].loc[metrics["portfolio_data"]["Gain_Loss_Pct"].idxmin(), "Symbol"],
            str(len(metrics["portfolio_data"])),
        ],
    }

    summary_df = pd.DataFrame(summary_stats)
    st.table(summary_df)


