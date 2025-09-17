"""
Gemini API Usage Monitoring Dashboard

This page provides comprehensive monitoring and analytics for Gemini API token usage
in the Portfolio Dashboard application.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime, timedelta
import os

from app_utils import (
    setup_page,
    inject_css,
    init_session_state,
    create_sidebar,
)
from auth_utils import init_auth_session, show_user_menu
from gemini_monitor import get_monitor, get_usage_summary, get_usage_trends, get_rate_limit_status

# Initialize authentication
init_auth_session()

# Check authentication
if not st.session_state.get("authenticated", False):
    st.warning("🔐 Please log in to access the Usage Monitoring Dashboard")
    st.info("Use the Login page in the sidebar to authenticate")
    st.stop()

setup_page()
inject_css()
init_session_state()
create_sidebar()
show_user_menu()

st.markdown('<h1 class="main-header">📊 Gemini API Usage Monitoring</h1>', unsafe_allow_html=True)

# Check if Gemini is available
try:
    from google import genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

if not GEMINI_AVAILABLE:
    st.error("⚠️ Google Gemini not installed. Please install with: pip install google-genai")
    st.stop()

# Check if API key is configured
gemini_api_key = os.environ.get("GEMINI_API_KEY")
if not gemini_api_key:
    st.warning("⚠️ Gemini API key not configured. Usage monitoring will show historical data only.")
    st.info("Configure your API key in the Investment Assessment page to start tracking usage.")

# Get monitor instance
monitor = get_monitor()

# Sidebar controls
st.sidebar.markdown("---")
st.sidebar.subheader("📈 Monitoring Controls")

# Time period selection
time_period = st.sidebar.selectbox(
    "Time Period",
    ["Last 7 days", "Last 30 days", "Last 90 days", "All time"],
    index=1
)

# Map selection to days
days_map = {
    "Last 7 days": 7,
    "Last 30 days": 30,
    "Last 90 days": 90,
    "All time": 365
}
selected_days = days_map[time_period]

# Refresh data button
if st.sidebar.button("🔄 Refresh Data", type="primary"):
    monitor.load_usage_data()
    st.rerun()

# Clear old data button
if st.sidebar.button("🗑️ Clear Old Data (90+ days)"):
    monitor.clear_old_data(90)
    st.success("Old data cleared!")
    st.rerun()

# Get usage data
usage_summary = get_usage_summary(selected_days)
rate_limits = get_rate_limit_status()

# Main dashboard
if usage_summary["total_calls"] == 0:
    st.info("📊 No API usage data found for the selected time period.")
    st.markdown("""
    **To start tracking usage:**
    1. Configure your Gemini API key in the Investment Assessment page
    2. Use the AI Assessment feature to generate some API calls
    3. Return to this page to view your usage analytics
    """)
    st.stop()

# Key metrics row
st.subheader("📊 Usage Overview")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Total API Calls",
        f"{usage_summary['total_calls']:,}",
        delta=f"{usage_summary['successful_calls']} successful"
    )

with col2:
    st.metric(
        "Total Tokens",
        f"{usage_summary['total_tokens']:,}",
        delta=f"{usage_summary['avg_tokens_per_call']:.0f} avg/call"
    )

with col3:
    st.metric(
        "Total Cost",
        f"${usage_summary['total_cost']:.4f}",
        delta=f"${usage_summary['total_cost']/selected_days:.4f}/day" if selected_days > 1 else None
    )

with col4:
    success_rate = (usage_summary['successful_calls'] / usage_summary['total_calls'] * 100) if usage_summary['total_calls'] > 0 else 0
    st.metric(
        "Success Rate",
        f"{success_rate:.1f}%",
        delta=f"{usage_summary['failed_calls']} failed" if usage_summary['failed_calls'] > 0 else None
    )

# Rate limit status
st.subheader("⚡ Rate Limit Status")
rate_col1, rate_col2, rate_col3 = st.columns(3)

with rate_col1:
    minute_usage = rate_limits['last_minute']
    minute_limit = rate_limits['minute_limit']
    minute_pct = (minute_usage / minute_limit) * 100
    st.metric(
        "Last Minute",
        f"{minute_usage}/{minute_limit}",
        delta=f"{minute_pct:.1f}% used"
    )
    if minute_pct > 80:
        st.warning("⚠️ Approaching minute limit")

with rate_col2:
    hour_usage = rate_limits['last_hour']
    hour_limit = rate_limits['hour_limit']
    hour_pct = (hour_usage / hour_limit) * 100
    st.metric(
        "Last Hour",
        f"{hour_usage}/{hour_limit}",
        delta=f"{hour_pct:.1f}% used"
    )
    if hour_pct > 80:
        st.warning("⚠️ Approaching hour limit")

with rate_col3:
    daily_usage = rate_limits['today']
    daily_limit = rate_limits['daily_limit']
    daily_pct = (daily_usage / daily_limit) * 100
    st.metric(
        "Today",
        f"{daily_usage:,}/{daily_limit:,}",
        delta=f"{daily_pct:.1f}% used"
    )
    if daily_pct > 80:
        st.warning("⚠️ Approaching daily limit")

# Usage trends
st.subheader("📈 Usage Trends")
trends = get_usage_trends(min(selected_days, 30))  # Limit trends to 30 days for better visualization

if trends['dates']:
    # Create subplot with secondary y-axis
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('Token Usage Over Time', 'Cost Over Time'),
        vertical_spacing=0.1
    )
    
    # Token usage
    fig.add_trace(
        go.Scatter(
            x=trends['dates'],
            y=trends['tokens'],
            mode='lines+markers',
            name='Tokens',
            line=dict(color='#1f77b4', width=2),
            marker=dict(size=6)
        ),
        row=1, col=1
    )
    
    # Cost
    fig.add_trace(
        go.Scatter(
            x=trends['dates'],
            y=trends['costs'],
            mode='lines+markers',
            name='Cost (USD)',
            line=dict(color='#ff7f0e', width=2),
            marker=dict(size=6)
        ),
        row=2, col=1
    )
    
    fig.update_layout(
        height=600,
        showlegend=True,
        title_text="Usage Trends",
        title_x=0.5
    )
    
    fig.update_xaxes(title_text="Date", row=2, col=1)
    fig.update_yaxes(title_text="Tokens", row=1, col=1)
    fig.update_yaxes(title_text="Cost (USD)", row=2, col=1)
    
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No trend data available for the selected period.")

# Operations breakdown
if usage_summary['operations']:
    st.subheader("🔧 Operations Breakdown")
    
    operations_data = []
    for op, data in usage_summary['operations'].items():
        operations_data.append({
            'Operation': op,
            'Calls': data['calls'],
            'Tokens': data['tokens'],
            'Cost': data['cost']
        })
    
    operations_df = pd.DataFrame(operations_data)
    operations_df = operations_df.sort_values('Calls', ascending=False)
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Calls by operation
        fig_calls = px.pie(
            operations_df, 
            values='Calls', 
            names='Operation',
            title="API Calls by Operation"
        )
        st.plotly_chart(fig_calls, use_container_width=True)
    
    with col2:
        # Cost by operation
        fig_cost = px.pie(
            operations_df, 
            values='Cost', 
            names='Operation',
            title="Cost by Operation"
        )
        st.plotly_chart(fig_cost, use_container_width=True)
    
    # Operations table
    st.subheader("📋 Operations Details")
    st.dataframe(
        operations_df,
        use_container_width=True,
        hide_index=True
    )

# Symbols breakdown
if usage_summary['symbols']:
    st.subheader("📈 Usage by Symbol")
    
    symbols_data = []
    for symbol, data in usage_summary['symbols'].items():
        symbols_data.append({
            'Symbol': symbol,
            'Calls': data['calls'],
            'Tokens': data['tokens'],
            'Cost': data['cost']
        })
    
    symbols_df = pd.DataFrame(symbols_data)
    symbols_df = symbols_df.sort_values('Calls', ascending=False)
    
    # Top symbols chart
    top_symbols = symbols_df.head(10)
    fig_symbols = px.bar(
        top_symbols,
        x='Symbol',
        y='Calls',
        title="Top 10 Symbols by API Calls",
        color='Calls',
        color_continuous_scale='Blues'
    )
    fig_symbols.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig_symbols, use_container_width=True)
    
    # Symbols table
    st.subheader("📋 Symbol Details")
    st.dataframe(
        symbols_df,
        use_container_width=True,
        hide_index=True
    )

# Cost analysis
st.subheader("💰 Cost Analysis")
cost_col1, cost_col2 = st.columns(2)

with cost_col1:
    daily_avg = usage_summary['total_cost'] / selected_days if selected_days > 0 else 0
    monthly_estimate = daily_avg * 30
    
    st.metric("Daily Average Cost", f"${daily_avg:.4f}")
    st.metric("Monthly Estimate", f"${monthly_estimate:.2f}")

with cost_col2:
    cost_per_token = usage_summary['total_cost'] / usage_summary['total_tokens'] if usage_summary['total_tokens'] > 0 else 0
    cost_per_call = usage_summary['total_cost'] / usage_summary['total_calls'] if usage_summary['total_calls'] > 0 else 0
    
    st.metric("Cost per Token", f"${cost_per_token:.6f}")
    st.metric("Cost per Call", f"${cost_per_call:.4f}")

# Recommendations
st.subheader("💡 Recommendations")

recommendations = []

# Check for high usage
if usage_summary['total_tokens'] > 100000:  # 100K tokens
    recommendations.append("🔍 High token usage detected. Consider optimizing prompts or reducing analysis frequency.")

# Check for high costs
if usage_summary['total_cost'] > 1.0:  # $1
    recommendations.append("💰 Significant costs detected. Monitor usage closely and consider setting up alerts.")

# Check success rate
success_rate = (usage_summary['successful_calls'] / usage_summary['total_calls'] * 100) if usage_summary['total_calls'] > 0 else 100
if success_rate < 95:
    recommendations.append("⚠️ Low success rate detected. Check API key configuration and error logs.")

# Check rate limits
if rate_limits['last_minute'] > 10:
    recommendations.append("⚡ High recent usage. Consider implementing request throttling.")

if recommendations:
    for rec in recommendations:
        st.warning(rec)
else:
    st.success("✅ Usage patterns look healthy! No immediate concerns detected.")

# Export data
st.subheader("📤 Export Data")
if st.button("📥 Download Usage Data (CSV)"):
    # Convert usage data to DataFrame
    usage_data = []
    for usage in monitor.usage_data:
        if datetime.fromisoformat(usage.timestamp) >= datetime.now() - timedelta(days=selected_days):
            usage_data.append({
                'Timestamp': usage.timestamp,
                'Model': usage.model,
                'Operation': usage.operation,
                'Symbol': usage.symbol or '',
                'Input Tokens': usage.input_tokens,
                'Output Tokens': usage.output_tokens,
                'Total Tokens': usage.total_tokens,
                'Cost (USD)': usage.cost_usd,
                'Success': usage.success,
                'Error Message': usage.error_message or ''
            })
    
    if usage_data:
        df = pd.DataFrame(usage_data)
        csv = df.to_csv(index=False)
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name=f"gemini_usage_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    else:
        st.info("No data to export for the selected period.")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; font-size: 0.9em;'>
    💡 <strong>Tip:</strong> This monitoring data helps you understand your API usage patterns and optimize costs.
    <br>Data is stored locally in <code>data/gemini_usage.json</code>
</div>
""", unsafe_allow_html=True)
