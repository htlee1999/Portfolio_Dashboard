import streamlit as st
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import yfinance as yf


from app_utils import setup_page, inject_css, init_session_state, create_sidebar, get_stock_data, format_currency
from auth_utils import show_user_menu


class FundamentalAnalysis:
    """Comprehensive fundamental analysis class for financial statement analysis."""
    
    def __init__(self, symbol):
        """
        Initialize with stock symbol.
        
        Args:
            symbol (str): Stock ticker symbol
        """
        self.symbol = symbol
        self.ticker = yf.Ticker(symbol)
        self.info = None
        self.financials = None
        self.balance_sheet = None
        self.cashflow = None
        self.quarterly_financials = None
        self.quarterly_balance_sheet = None
        self.quarterly_cashflow = None
        
    def fetch_data(self):
        """Fetch all fundamental data from yfinance."""
        try:
            self.info = self.ticker.info
            self.financials = self.ticker.financials
            self.balance_sheet = self.ticker.balance_sheet
            self.cashflow = self.ticker.cashflow
            self.quarterly_financials = self.ticker.quarterly_financials
            self.quarterly_balance_sheet = self.ticker.quarterly_balance_sheet
            self.quarterly_cashflow = self.ticker.quarterly_cashflow
            return True
        except Exception as e:
            st.error(f"Error fetching data for {self.symbol}: {str(e)}")
            return False
    
    def get_key_metrics(self):
        """Extract key financial metrics."""
        if not self.info:
            return {}
        
        metrics = {
            'Company Name': self.info.get('longName', 'N/A'),
            'Sector': self.info.get('sector', 'N/A'),
            'Industry': self.info.get('industry', 'N/A'),
            'Market Cap': self.info.get('marketCap', 0),
            'Enterprise Value': self.info.get('enterpriseValue', 0),
            'P/E Ratio': self.info.get('trailingPE', 0),
            'Forward P/E': self.info.get('forwardPE', 0),
            'PEG Ratio': self.info.get('pegRatio', 0),
            'Price to Book': self.info.get('priceToBook', 0),
            'Price to Sales': self.info.get('priceToSalesTrailing12Months', 0),
            'EV/Revenue': self.info.get('enterpriseToRevenue', 0),
            'EV/EBITDA': self.info.get('enterpriseToEbitda', 0),
            'Debt to Equity': self.info.get('debtToEquity', 0),
            'Current Ratio': self.info.get('currentRatio', 0),
            'Quick Ratio': self.info.get('quickRatio', 0),
            'ROE': self.info.get('returnOnEquity', 0),
            'ROA': self.info.get('returnOnAssets', 0),
            'ROIC': self.info.get('returnOnInvestmentCapital', 0),
            'Gross Margin': self.info.get('grossMargins', 0),
            'Operating Margin': self.info.get('operatingMargins', 0),
            'Profit Margin': self.info.get('profitMargins', 0),
            'Revenue Growth': self.info.get('revenueGrowth', 0),
            'Earnings Growth': self.info.get('earningsGrowth', 0),
            'Dividend Yield': self.info.get('dividendYield', 0),
            'Payout Ratio': self.info.get('payoutRatio', 0),
            'Beta': self.info.get('beta', 0),
            '52 Week High': self.info.get('fiftyTwoWeekHigh', 0),
            '52 Week Low': self.info.get('fiftyTwoWeekLow', 0),
            'Current Price': self.info.get('currentPrice', 0),
            'Analyst Target': self.info.get('targetMeanPrice', 0),
            'Analyst Recommendation': self.info.get('recommendationMean', 'N/A'),
        }
        
        return metrics
    
    def calculate_ratios(self):
        """Calculate additional financial ratios from financial statements."""
        ratios = {}
        
        if self.financials is not None and not self.financials.empty:
            # Get the most recent year's data
            latest_year = self.financials.columns[0]
            latest_data = self.financials[latest_year]
            
            # Revenue and profitability ratios
            total_revenue = latest_data.get('Total Revenue', 0)
            net_income = latest_data.get('Net Income', 0)
            operating_income = latest_data.get('Operating Income', 0)
            
            if total_revenue and total_revenue != 0:
                ratios['Net Profit Margin'] = (net_income / total_revenue) * 100 if net_income else 0
                ratios['Operating Margin'] = (operating_income / total_revenue) * 100 if operating_income else 0
        
        if self.balance_sheet is not None and not self.balance_sheet.empty:
            # Get the most recent year's balance sheet data
            latest_year = self.balance_sheet.columns[0]
            latest_bs = self.balance_sheet[latest_year]
            
            total_assets = latest_bs.get('Total Assets', 0)
            total_liabilities = latest_bs.get('Total Liabilities', 0)
            total_equity = latest_bs.get('Total Stockholder Equity', 0)
            current_assets = latest_bs.get('Current Assets', 0)
            current_liabilities = latest_bs.get('Current Liabilities', 0)
            
            # Liquidity ratios
            if current_liabilities and current_liabilities != 0:
                ratios['Current Ratio'] = current_assets / current_liabilities if current_assets else 0
            
            # Leverage ratios
            if total_equity and total_equity != 0:
                ratios['Debt to Equity'] = total_liabilities / total_equity if total_liabilities else 0
            
            if total_assets and total_assets != 0:
                ratios['Debt to Assets'] = total_liabilities / total_assets if total_liabilities else 0
        
        return ratios
    
    def get_financial_statement_data(self, statement_type='income'):
        """Get financial statement data for visualization."""
        if statement_type == 'income':
            return self.financials
        elif statement_type == 'balance':
            return self.balance_sheet
        elif statement_type == 'cashflow':
            return self.cashflow
        return None
    
    def create_financial_chart(self, statement_type='income', top_items=10):
        """Create interactive chart for financial statements."""
        data = self.get_financial_statement_data(statement_type)
        
        if data is None or data.empty:
            return None
        
        # Get the most recent 5 years
        recent_years = data.columns[:5]
        recent_data = data[recent_years]
        
        # Get top items by absolute value in the most recent year
        latest_year_data = recent_data.iloc[:, 0]
        top_items_data = latest_year_data.abs().nlargest(top_items)
        
        # Filter data for top items
        chart_data = recent_data.loc[top_items_data.index]
        
        # Create the chart
        fig = go.Figure()
        
        for item in chart_data.index:
            fig.add_trace(go.Scatter(
                x=recent_years,
                y=chart_data.loc[item],
                mode='lines+markers',
                name=item,
                line=dict(width=2)
            ))
        
        fig.update_layout(
            title=f"{statement_type.title()} Statement - Top {top_items} Items",
            xaxis_title="Year",
            yaxis_title="Amount (Millions)",
            hovermode='x unified',
            height=500
        )
        
        return fig
    
    def create_ratio_analysis_chart(self):
        """Create a comprehensive ratio analysis chart."""
        metrics = self.get_key_metrics()
        
        # Define categories of ratios
        categories = {
            'Valuation': ['P/E Ratio', 'Forward P/E', 'PEG Ratio', 'Price to Book', 'Price to Sales'],
            'Profitability': ['ROE', 'ROA', 'Gross Margin', 'Operating Margin', 'Profit Margin'],
            'Liquidity': ['Current Ratio', 'Quick Ratio'],
            'Leverage': ['Debt to Equity'],
            'Growth': ['Revenue Growth', 'Earnings Growth']
        }
        
        # Create subplots
        fig = make_subplots(
            rows=2, cols=3,
            subplot_titles=list(categories.keys()),
            specs=[[{"type": "bar"}, {"type": "bar"}, {"type": "bar"}],
                   [{"type": "bar"}, {"type": "bar"}, {"type": "bar"}]]
        )
        
        positions = [(1, 1), (1, 2), (1, 3), (2, 1), (2, 2), (2, 3)]
        
        for i, (category, ratios) in enumerate(categories.items()):
            values = []
            labels = []
            
            for ratio in ratios:
                value = metrics.get(ratio, 0)
                if value and value != 0 and not np.isnan(value):
                    values.append(value)
                    labels.append(ratio)
            
            if values:
                fig.add_trace(
                    go.Bar(x=labels, y=values, name=category, showlegend=False),
                    row=positions[i][0], col=positions[i][1]
                )
        
        fig.update_layout(
            title="Financial Ratio Analysis",
            height=600,
            showlegend=False
        )
        
        return fig


def display_company_overview(analysis):
    """Display company overview and key metrics."""
    st.subheader("📊 Company Overview")
    
    metrics = analysis.get_key_metrics()
    
    # Company basic info
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Market Cap", f"${metrics.get('Market Cap', 0):,.0f}" if metrics.get('Market Cap') else "N/A")
        st.metric("P/E Ratio", f"{metrics.get('P/E Ratio', 0):.2f}" if metrics.get('P/E Ratio') else "N/A")
        st.metric("Price to Book", f"{metrics.get('Price to Book', 0):.2f}" if metrics.get('Price to Book') else "N/A")
    
    with col2:
        st.metric("Enterprise Value", f"${metrics.get('Enterprise Value', 0):,.0f}" if metrics.get('Enterprise Value') else "N/A")
        st.metric("Forward P/E", f"{metrics.get('Forward P/E', 0):.2f}" if metrics.get('Forward P/E') else "N/A")
        st.metric("Price to Sales", f"{metrics.get('Price to Sales', 0):.2f}" if metrics.get('Price to Sales') else "N/A")
    
    with col3:
        current_price = metrics.get('Current Price', 0)
        target_price = metrics.get('Analyst Target', 0)
        if current_price and target_price:
            upside = ((target_price - current_price) / current_price) * 100
            st.metric("Analyst Target", f"${target_price:.2f}")
            st.metric("Upside Potential", f"{upside:.1f}%")
        else:
            st.metric("Current Price", f"${current_price:.2f}" if current_price else "N/A")
            st.metric("52W High", f"${metrics.get('52 Week High', 0):.2f}" if metrics.get('52 Week High') else "N/A")
    
    # Company description
    if analysis.info:
        st.subheader("About the Company")
        st.write(f"**{metrics.get('Company Name', 'N/A')}**")
        st.write(f"**Sector:** {metrics.get('Sector', 'N/A')}")
        st.write(f"**Industry:** {metrics.get('Industry', 'N/A')}")
        
        if 'longBusinessSummary' in analysis.info:
            st.write("**Business Summary:**")
            st.write(analysis.info['longBusinessSummary'])


def display_financial_ratios(analysis):
    """Display comprehensive financial ratios."""
    st.subheader("📈 Financial Ratios")
    
    metrics = analysis.get_key_metrics()
    calculated_ratios = analysis.calculate_ratios()
    
    # Combine all ratios
    all_ratios = {**metrics, **calculated_ratios}
    
    # Create tabs for different ratio categories
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Valuation", "Profitability", "Liquidity", "Leverage", "Growth"])
    
    with tab1:
        valuation_ratios = {
            'P/E Ratio': all_ratios.get('P/E Ratio', 0),
            'Forward P/E': all_ratios.get('Forward P/E', 0),
            'PEG Ratio': all_ratios.get('PEG Ratio', 0),
            'Price to Book': all_ratios.get('Price to Book', 0),
            'Price to Sales': all_ratios.get('Price to Sales', 0),
            'EV/Revenue': all_ratios.get('EV/Revenue', 0),
            'EV/EBITDA': all_ratios.get('EV/EBITDA', 0)
        }
        
        for ratio, value in valuation_ratios.items():
            if value and value != 0 and not np.isnan(value):
                st.metric(ratio, f"{value:.2f}")
    
    with tab2:
        profitability_ratios = {
            'ROE': all_ratios.get('ROE', 0),
            'ROA': all_ratios.get('ROA', 0),
            'ROIC': all_ratios.get('ROIC', 0),
            'Gross Margin': all_ratios.get('Gross Margin', 0),
            'Operating Margin': all_ratios.get('Operating Margin', 0),
            'Profit Margin': all_ratios.get('Profit Margin', 0),
            'Net Profit Margin': all_ratios.get('Net Profit Margin', 0)
        }
        
        for ratio, value in profitability_ratios.items():
            if value and value != 0 and not np.isnan(value):
                if 'Margin' in ratio:
                    st.metric(ratio, f"{value:.2f}%")
                else:
                    st.metric(ratio, f"{value:.2f}")
    
    with tab3:
        liquidity_ratios = {
            'Current Ratio': all_ratios.get('Current Ratio', 0),
            'Quick Ratio': all_ratios.get('Quick Ratio', 0)
        }
        
        for ratio, value in liquidity_ratios.items():
            if value and value != 0 and not np.isnan(value):
                st.metric(ratio, f"{value:.2f}")
    
    with tab4:
        leverage_ratios = {
            'Debt to Equity': all_ratios.get('Debt to Equity', 0),
            'Debt to Assets': all_ratios.get('Debt to Assets', 0)
        }
        
        for ratio, value in leverage_ratios.items():
            if value and value != 0 and not np.isnan(value):
                st.metric(ratio, f"{value:.2f}")
    
    with tab5:
        growth_ratios = {
            'Revenue Growth': all_ratios.get('Revenue Growth', 0),
            'Earnings Growth': all_ratios.get('Earnings Growth', 0)
        }
        
        for ratio, value in growth_ratios.items():
            if value and value != 0 and not np.isnan(value):
                st.metric(ratio, f"{value:.2f}%")


def display_financial_statements(analysis):
    """Display financial statements with interactive charts."""
    st.subheader("📋 Financial Statements")
    
    # Create tabs for different statements
    tab1, tab2, tab3 = st.tabs(["Income Statement", "Balance Sheet", "Cash Flow Statement"])
    
    with tab1:
        st.write("**Income Statement**")
        if analysis.financials is not None and not analysis.financials.empty:
            # Display the most recent 5 years
            recent_financials = analysis.financials.iloc[:, :5]
            st.dataframe(recent_financials, use_container_width=True)
            
            # Create chart
            chart = analysis.create_financial_chart('income', 8)
            if chart:
                st.plotly_chart(chart, use_container_width=True)
        else:
            st.warning("Income statement data not available")
    
    with tab2:
        st.write("**Balance Sheet**")
        if analysis.balance_sheet is not None and not analysis.balance_sheet.empty:
            # Display the most recent 5 years
            recent_balance = analysis.balance_sheet.iloc[:, :5]
            st.dataframe(recent_balance, use_container_width=True)
            
            # Create chart
            chart = analysis.create_financial_chart('balance', 8)
            if chart:
                st.plotly_chart(chart, use_container_width=True)
        else:
            st.warning("Balance sheet data not available")
    
    with tab3:
        st.write("**Cash Flow Statement**")
        if analysis.cashflow is not None and not analysis.cashflow.empty:
            # Display the most recent 5 years
            recent_cashflow = analysis.cashflow.iloc[:, :5]
            st.dataframe(recent_cashflow, use_container_width=True)
            
            # Create chart
            chart = analysis.create_financial_chart('cashflow', 8)
            if chart:
                st.plotly_chart(chart, use_container_width=True)
        else:
            st.warning("Cash flow statement data not available")


def display_analyst_estimates(analysis):
    """Display analyst estimates and recommendations."""
    st.subheader("🎯 Analyst Estimates & Recommendations")
    
    metrics = analysis.get_key_metrics()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Analyst Recommendation", metrics.get('Analyst Recommendation', 'N/A'))
        st.metric("Target Price", f"${metrics.get('Analyst Target', 0):.2f}" if metrics.get('Analyst Target') else "N/A")
    
    with col2:
        st.metric("Dividend Yield", f"{metrics.get('Dividend Yield', 0):.2f}%" if metrics.get('Dividend Yield') else "N/A")
        st.metric("Payout Ratio", f"{metrics.get('Payout Ratio', 0):.2f}%" if metrics.get('Payout Ratio') else "N/A")
    
    with col3:
        st.metric("Beta", f"{metrics.get('Beta', 0):.2f}" if metrics.get('Beta') else "N/A")
        st.metric("52W Range", f"${metrics.get('52 Week Low', 0):.2f} - ${metrics.get('52 Week High', 0):.2f}" 
                 if metrics.get('52 Week Low') and metrics.get('52 Week High') else "N/A")


def main():
    """Main function to run the fundamental analysis page."""
    setup_page()
    inject_css()
    init_session_state()
    create_sidebar()
    show_user_menu()
    
    st.markdown('<h1 class="main-header">📊 Fundamental Analysis</h1>', unsafe_allow_html=True)
    
    st.write("Analyze company fundamentals including financial statements, ratios, and key metrics.")
    
    # Stock symbol input
    col1, col2 = st.columns([1, 3])
    
    with col1:
        symbol = st.text_input("Enter Stock Symbol", value="AAPL", help="Enter a valid stock ticker symbol (e.g., AAPL, MSFT, GOOGL)")
    
    with col2:
        if st.button("Analyze", type="primary"):
            if symbol:
                with st.spinner(f"Fetching fundamental data for {symbol}..."):
                    analysis = FundamentalAnalysis(symbol)
                    if analysis.fetch_data():
                        st.session_state.fundamental_analysis = analysis
                        st.success(f"Successfully loaded data for {symbol}")
                    else:
                        st.error(f"Failed to load data for {symbol}")
            else:
                st.warning("Please enter a stock symbol")
    
    # Display analysis if available
    if hasattr(st.session_state, 'fundamental_analysis') and st.session_state.fundamental_analysis:
        analysis = st.session_state.fundamental_analysis
        
        # Create tabs for different analysis sections
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "Company Overview", 
            "Financial Ratios", 
            "Financial Statements", 
            "Analyst Estimates",
            "Ratio Analysis Chart"
        ])
        
        with tab1:
            display_company_overview(analysis)
        
        with tab2:
            display_financial_ratios(analysis)
        
        with tab3:
            display_financial_statements(analysis)
        
        with tab4:
            display_analyst_estimates(analysis)
        
        with tab5:
            st.subheader("📊 Ratio Analysis Visualization")
            chart = analysis.create_ratio_analysis_chart()
            if chart:
                st.plotly_chart(chart, use_container_width=True)
            else:
                st.warning("Unable to create ratio analysis chart")
    
    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: gray;'>
            Fundamental Analysis powered by Yahoo Finance API | 
            Data is delayed and for informational purposes only
        </div>
        """, 
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
