import io
import os
from datetime import datetime

import pandas as pd
import streamlit as st

from app_utils import (
    setup_page,
    inject_css,
    init_session_state,
    create_sidebar,
    format_currency,
    add_holding_to_storage,
    remove_holding_from_storage,
    clear_all_holdings_from_storage,
    save_settings_to_storage,
    import_portfolio_from_csv,
    export_portfolio_to_csv,
    get_portfolio_stats,
    backup_data,
)
from auth_utils import init_auth_session, show_user_menu, change_password_form

# Initialize authentication
init_auth_session()

# Check authentication
if not st.session_state.get("authenticated", False):
    st.warning("🔐 Please log in to access the Portfolio Builder")
    st.info("Use the Login page in the sidebar to authenticate")
    st.stop()

setup_page()
inject_css()
init_session_state()
create_sidebar()
show_user_menu()

# Handle change password modal
if st.session_state.get("show_change_password", False):
    st.markdown('<h1 class="main-header">🔑 Change Password</h1>', unsafe_allow_html=True)
    change_password_form()
    st.stop()

st.markdown('<h1 class="main-header">📈 Portfolio Builder</h1>', unsafe_allow_html=True)

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

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("Manual Stock Entry")

    with st.form("add_stock_form"):
        symbol = st.text_input("Stock Symbol (e.g., AAPL, GOOGL)")
        quantity = st.number_input("Quantity", min_value=0.01, value=1.0, step=0.01)
        
        col_price, col_currency = st.columns([2, 1])
        with col_price:
            purchase_price = st.number_input("Purchase Price", min_value=0.01, value=100.0, step=0.01)
        with col_currency:
            currency = st.selectbox(
                "Currency",
                ["USD", "SGD", "EUR", "GBP", "JPY", "CAD", "AUD", "HKD", "CNY", "INR", "KRW", "THB", "MYR", "IDR", "PHP", "VND"],
                index=0
            )
        
        purchase_date = st.date_input("Purchase Date", value=datetime.now().date())

        if st.form_submit_button("Add Stock"):
            if symbol:
                success = add_holding_to_storage(symbol, quantity, purchase_price, purchase_date, currency)
                if success:
                    st.success(f"Added {symbol.upper()} ({format_currency(purchase_price, currency)}) to portfolio!")
                    st.rerun()
                else:
                    st.error("Failed to add stock to portfolio")
            else:
                st.error("Please enter a stock symbol")

with col2:
    st.subheader("CSV Upload")
    st.info("Upload a CSV file with columns: Symbol, Quantity, Purchase_Price, Purchase_Date, Currency")

    uploaded_file = st.file_uploader("Choose CSV file", type="csv")
    if uploaded_file is not None:
        try:
            csv_df = pd.read_csv(uploaded_file)
            success = import_portfolio_from_csv(csv_df)
            if success:
                st.success(f"Successfully uploaded {len(csv_df)} stocks!")
                st.rerun()
            else:
                st.error("Failed to import CSV data")
        except Exception as e:
            st.error(f"Error reading CSV file: {str(e)}")

    if st.button("Download CSV Template"):
        template_df = pd.DataFrame(
            {
                "Symbol": ["AAPL", "GOOGL", "MSFT"],
                "Quantity": [10, 5, 15],
                "Purchase_Price": [150.0, 2500.0, 300.0],
                "Purchase_Date": ["2024-01-01", "2024-01-15", "2024-02-01"],
                "Currency": ["USD", "SGD", "USD"],
            }
        )
        csv_buffer = io.StringIO()
        template_df.to_csv(csv_buffer, index=False)
        st.download_button(label="📥 Download Template", data=csv_buffer.getvalue(), file_name="portfolio_template.csv", mime="text/csv")


st.subheader("Current Portfolio Holdings")
if not st.session_state.portfolio.empty:
    col1, col2 = st.columns([3, 1])

    with col1:
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
        
        st.dataframe(display_df, use_container_width=True)

    with col2:
        st.write("**Actions:**")
        
        # Data management buttons
        col_clear, col_export, col_backup = st.columns(3)
        
        with col_clear:
            if st.button("🗑️ Clear All", help="Clear all holdings"):
                if clear_all_holdings_from_storage():
                    st.success("All holdings cleared!")
                    st.rerun()
                else:
                    st.error("Failed to clear holdings")
        
        with col_export:
            if st.button("📤 Export CSV", help="Export portfolio to CSV"):
                file_path = export_portfolio_to_csv()
                if file_path:
                    with open(file_path, 'rb') as f:
                        st.download_button(
                            label="Download CSV",
                            data=f.read(),
                            file_name=f"portfolio_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv"
                        )
                else:
                    st.error("Failed to export portfolio")
        
        with col_backup:
            if st.button("💾 Backup", help="Create data backup"):
                backup_path = backup_data()
                if backup_path:
                    st.success(f"Backup created: {os.path.basename(backup_path)}")
                else:
                    st.error("Failed to create backup")

        # Remove individual holdings
        if len(st.session_state.portfolio) > 0:
            st.write("**Remove Holdings:**")
            symbol_to_remove = st.selectbox("Remove Stock:", options=["Select..."] + list(st.session_state.portfolio["Symbol"].unique()))
            if symbol_to_remove != "Select..." and st.button("Remove Selected"):
                if remove_holding_from_storage(symbol_to_remove):
                    st.success(f"Removed {symbol_to_remove} from portfolio!")
                    st.rerun()
                else:
                    st.error("Failed to remove stock")
else:
    st.info("No stocks in portfolio. Add some stocks to get started!")

# Data Management Section
st.markdown("---")
st.subheader("📊 Data Management")

# Show portfolio statistics
stats = get_portfolio_stats()
if stats:
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Holdings", stats.get("total_holdings", 0))
    
    with col2:
        currencies = stats.get("currencies", [])
        st.metric("Currencies", len(currencies))
        if currencies:
            st.caption(f"({', '.join(currencies)})")
    
    with col3:
        symbols = stats.get("symbols", [])
        st.metric("Unique Symbols", len(symbols))
    
    with col4:
        last_updated = stats.get("last_updated", "Never")
        if last_updated:
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
                last_updated = dt.strftime("%Y-%m-%d %H:%M")
            except:
                pass
        st.metric("Last Updated", last_updated)

# Data folder information
st.markdown("**Data Storage:**")
st.info(f"📁 Portfolio data is stored in: `data/portfolio.json`\n"
        f"⚙️ Settings are stored in: `data/settings.json`\n"
        f"💾 Backups are stored in: `data/backups/`\n"
        f"📤 Exports are stored in: `data/exports/`")


