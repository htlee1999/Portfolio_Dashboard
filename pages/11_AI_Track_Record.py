"""
AI Track Record Dashboard

Reviews historical AI recommendation signals and computes hindsight outcomes
("what if I had followed the AI's advice?").
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import yfinance as yf
from datetime import datetime

from page_utils import init_protected_page
from data_utils import load_recommendation_history

# Initialize protected page (handles auth, setup, CSS, sidebar, user menu)
init_protected_page()

st.markdown('<h1 class="main-header">AI Track Record</h1>', unsafe_allow_html=True)


# ── Helpers ──────────────────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def fetch_current_prices(symbols: list) -> dict:
    """Fetch current prices for a list of symbols (cached 5 min)."""
    prices = {}
    for sym in symbols:
        try:
            ticker = yf.Ticker(sym)
            hist = ticker.history(period="1d")
            if not hist.empty:
                prices[sym] = hist["Close"].iloc[-1]
        except Exception:
            pass
    return prices


def compute_outcome(row: pd.Series) -> dict:
    """Compute return and correctness for a single signal."""
    signal_price = row.get("price_at_signal")
    current_price = row.get("current_price")
    rec = row.get("recommendation", "HOLD")

    if signal_price is None or current_price is None or signal_price == 0:
        return {"return_pct": None, "outcome": "N/A"}

    pct = (current_price - signal_price) / signal_price * 100

    if rec == "BUY":
        correct = pct > 0
        return {"return_pct": round(pct, 2), "outcome": "Correct" if correct else "Wrong"}
    elif rec == "SELL":
        # A correct SELL means the price dropped after the signal
        correct = pct < 0
        avoided = -pct  # positive means loss avoided
        return {"return_pct": round(avoided, 2), "outcome": "Correct" if correct else "Wrong"}
    else:  # HOLD
        return {"return_pct": round(pct, 2), "outcome": "Neutral"}


# ── Load Data ────────────────────────────────────────────────────────────────

username = st.session_state.get("username")
history = load_recommendation_history(username)

if not history:
    st.info("No AI recommendations recorded yet. Generate an assessment on the Investment Assessment page to start building your track record.")
    st.stop()

df = pd.DataFrame(history)
df["timestamp"] = pd.to_datetime(df["timestamp"])
df = df.sort_values("timestamp", ascending=False).reset_index(drop=True)

# Fetch current prices for all symbols in history
symbols = df["symbol"].unique().tolist()
current_prices = fetch_current_prices(symbols)
df["current_price"] = df["symbol"].map(current_prices)

# Compute outcomes
outcomes = df.apply(compute_outcome, axis=1, result_type="expand")
df["return_pct"] = outcomes["return_pct"]
df["outcome"] = outcomes["outcome"]

# ── Sidebar Filters ──────────────────────────────────────────────────────────

st.sidebar.markdown("---")
st.sidebar.subheader("Filters")

symbol_filter = st.sidebar.multiselect("Symbols", options=sorted(symbols), default=sorted(symbols))
signal_filter = st.sidebar.multiselect("Signal Type", options=["BUY", "SELL", "HOLD"], default=["BUY", "SELL", "HOLD"])

filtered = df[df["symbol"].isin(symbol_filter) & df["recommendation"].isin(signal_filter)].copy()

# ── Header Metrics ───────────────────────────────────────────────────────────

st.markdown("---")

evaluable = filtered[filtered["outcome"].isin(["Correct", "Wrong"])]
total_signals = len(filtered)
win_count = len(evaluable[evaluable["outcome"] == "Correct"])
win_rate = (win_count / len(evaluable) * 100) if len(evaluable) > 0 else 0
avg_return = filtered["return_pct"].dropna().mean() if not filtered["return_pct"].dropna().empty else 0

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Signals", total_signals)
with col2:
    st.metric("Win Rate", f"{win_rate:.1f}%")
with col3:
    st.metric("Avg Return / Signal", f"{avg_return:+.2f}%")
with col4:
    best = filtered["return_pct"].dropna().max() if not filtered["return_pct"].dropna().empty else 0
    worst = filtered["return_pct"].dropna().min() if not filtered["return_pct"].dropna().empty else 0
    st.metric("Best / Worst", f"{best:+.1f}% / {worst:+.1f}%")

# ── Signal History Table ─────────────────────────────────────────────────────

st.markdown("---")
st.subheader("Signal History")

display_df = filtered[["timestamp", "symbol", "recommendation", "confidence",
                        "price_at_signal", "current_price", "return_pct", "outcome", "time_horizon"]].copy()
display_df.columns = ["Date", "Symbol", "Signal", "Confidence", "Price at Signal",
                       "Current Price", "Return %", "Outcome", "Time Horizon"]
display_df["Date"] = display_df["Date"].dt.strftime("%Y-%m-%d %H:%M")

# Style the dataframe
def color_signal(val):
    if val == "BUY":
        return "color: #00c853"
    elif val == "SELL":
        return "color: #ff1744"
    return ""

def color_outcome(val):
    if val == "Correct":
        return "color: #00c853"
    elif val == "Wrong":
        return "color: #ff1744"
    return ""

def color_return(val):
    try:
        v = float(val)
        return "color: #00c853" if v > 0 else "color: #ff1744" if v < 0 else ""
    except (ValueError, TypeError):
        return ""

styled = display_df.style.map(color_signal, subset=["Signal"]) \
                          .map(color_outcome, subset=["Outcome"]) \
                          .map(color_return, subset=["Return %"]) \
                          .format({"Price at Signal": "${:.2f}",
                                   "Current Price": "${:.2f}",
                                   "Return %": "{:+.2f}%"}, na_rep="N/A")

st.dataframe(styled, use_container_width=True, hide_index=True)

# ── Simulated Portfolio ("What If") ──────────────────────────────────────────

st.markdown("---")
st.subheader("What If: Simulated Portfolio")
st.markdown("*If you invested $1,000 on every BUY signal, here's how it would have played out:*")

buy_signals = filtered[filtered["recommendation"] == "BUY"].dropna(subset=["return_pct"]).copy()

if not buy_signals.empty:
    hypothetical_investment = 1000
    buy_signals = buy_signals.sort_values("timestamp")
    buy_signals["profit"] = hypothetical_investment * buy_signals["return_pct"] / 100
    total_invested = hypothetical_investment * len(buy_signals)
    total_value = total_invested + buy_signals["profit"].sum()
    total_return_pct = (total_value - total_invested) / total_invested * 100

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Invested", f"${total_invested:,.0f}")
    with col2:
        st.metric("Current Value", f"${total_value:,.2f}")
    with col3:
        st.metric("Total Return", f"{total_return_pct:+.2f}%",
                  delta=f"${buy_signals['profit'].sum():+,.2f}")

    # Cumulative return chart
    buy_signals["cumulative_profit"] = buy_signals["profit"].cumsum()
    buy_signals["cumulative_invested"] = hypothetical_investment * (buy_signals.reset_index().index + 1)
    buy_signals["cumulative_value"] = buy_signals["cumulative_invested"].values + buy_signals["cumulative_profit"].values
    buy_signals["cumulative_return_pct"] = (buy_signals["cumulative_value"] - buy_signals["cumulative_invested"].values) / buy_signals["cumulative_invested"].values * 100

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=buy_signals["timestamp"],
        y=buy_signals["cumulative_return_pct"],
        mode="lines+markers",
        name="Cumulative Return %",
        line=dict(color="#1f77b4", width=2),
        hovertemplate="Date: %{x}<br>Return: %{y:+.2f}%<extra></extra>",
    ))
    fig.add_hline(y=0, line_dash="dash", line_color="gray")
    fig.update_layout(
        title="Cumulative Return if Following AI BUY Signals",
        xaxis_title="Date",
        yaxis_title="Cumulative Return %",
        template="plotly_dark",
        height=400,
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No BUY signals with available price data to simulate.")

# ── Per-Symbol Breakdown ─────────────────────────────────────────────────────

st.markdown("---")
st.subheader("Per-Symbol Breakdown")

if not filtered.empty:
    symbol_stats = []
    for sym in sorted(filtered["symbol"].unique()):
        sym_df = filtered[filtered["symbol"] == sym]
        sym_eval = sym_df[sym_df["outcome"].isin(["Correct", "Wrong"])]
        sym_wins = len(sym_eval[sym_eval["outcome"] == "Correct"]) if len(sym_eval) > 0 else 0
        sym_wr = (sym_wins / len(sym_eval) * 100) if len(sym_eval) > 0 else 0
        avg_ret = sym_df["return_pct"].dropna().mean()
        symbol_stats.append({
            "Symbol": sym,
            "Signals": len(sym_df),
            "BUY": len(sym_df[sym_df["recommendation"] == "BUY"]),
            "SELL": len(sym_df[sym_df["recommendation"] == "SELL"]),
            "HOLD": len(sym_df[sym_df["recommendation"] == "HOLD"]),
            "Win Rate": f"{sym_wr:.0f}%",
            "Avg Return": f"{avg_ret:+.2f}%" if not np.isnan(avg_ret) else "N/A",
        })

    stats_df = pd.DataFrame(symbol_stats)
    st.dataframe(stats_df, use_container_width=True, hide_index=True)

# ── Signal Distribution Chart ────────────────────────────────────────────────

st.markdown("---")
st.subheader("Signal Distribution")

col1, col2 = st.columns(2)

with col1:
    sig_counts = filtered["recommendation"].value_counts()
    colors = {"BUY": "#00c853", "SELL": "#ff1744", "HOLD": "#2196f3"}
    fig_pie = px.pie(
        names=sig_counts.index,
        values=sig_counts.values,
        color=sig_counts.index,
        color_discrete_map=colors,
        title="Signals by Type",
    )
    fig_pie.update_layout(template="plotly_dark", height=350)
    st.plotly_chart(fig_pie, use_container_width=True)

with col2:
    outcome_counts = filtered[filtered["outcome"] != "Neutral"]["outcome"].value_counts()
    outcome_colors = {"Correct": "#00c853", "Wrong": "#ff1744", "N/A": "#9e9e9e"}
    fig_out = px.pie(
        names=outcome_counts.index,
        values=outcome_counts.values,
        color=outcome_counts.index,
        color_discrete_map=outcome_colors,
        title="Outcome Distribution",
    )
    fig_out.update_layout(template="plotly_dark", height=350)
    st.plotly_chart(fig_out, use_container_width=True)

# ── Signal Detail Expander ───────────────────────────────────────────────────

st.markdown("---")
st.subheader("Signal Details")
st.markdown("*Click on a signal to see the full AI reasoning and context:*")

for idx, row in filtered.head(20).iterrows():
    date_str = row["timestamp"].strftime("%Y-%m-%d")
    rec = row["recommendation"]
    sym = row["symbol"]
    ret = row.get("return_pct")
    ret_str = f"{ret:+.2f}%" if ret is not None and not np.isnan(ret) else "N/A"
    icon = {"BUY": "🟢", "SELL": "🔴", "HOLD": "🔵"}.get(rec, "⚪")

    with st.expander(f"{icon} {date_str} | {sym} | {rec} | Confidence: {row['confidence']}/10 | Return: {ret_str}"):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Price at Signal:** ${row['price_at_signal']:.2f}" if row.get('price_at_signal') else "**Price at Signal:** N/A")
            st.markdown(f"**Current Price:** ${row['current_price']:.2f}" if row.get('current_price') else "**Current Price:** N/A")
            st.markdown(f"**Price Target:** ${row['price_target']:.2f}" if row.get('price_target') else "**Price Target:** N/A")
            st.markdown(f"**Time Horizon:** {row.get('time_horizon', 'N/A')}")

        with col2:
            ctx = row.get("portfolio_context")
            if ctx and isinstance(ctx, dict):
                st.markdown(f"**Avg Purchase Price:** ${ctx.get('avg_purchase_price', 0):.2f}")
                st.markdown(f"**Quantity Held:** {ctx.get('total_quantity', 0):.2f}")
                st.markdown(f"**Unrealized P&L:** {ctx.get('unrealized_pct', 0):.2f}%")
            else:
                st.markdown("*No portfolio position at time of signal*")

        strengths = row.get("strengths", [])
        risks = row.get("risks", [])
        if strengths:
            st.markdown("**Strengths:**")
            for s in strengths:
                st.markdown(f"- {s}")
        if risks:
            st.markdown("**Risks:**")
            for r in risks:
                st.markdown(f"- {r}")

        reasoning = row.get("reasoning", "")
        if reasoning:
            st.markdown("**AI Reasoning:**")
            st.markdown(reasoning)
