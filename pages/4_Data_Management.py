import streamlit as st
import json
import os
from datetime import datetime
import pandas as pd

from app_utils import (
    setup_page,
    inject_css,
    init_session_state,
    create_sidebar,
    load_portfolio_data,
    save_portfolio_data,
    load_settings,
    save_settings,
    get_portfolio_stats,
    backup_data,
    export_portfolio_to_csv,
)
from auth_utils import init_auth_session, show_user_menu, change_password_form, admin_only, create_user_management_page

# Initialize authentication
init_auth_session()

# Check authentication
if not st.session_state.get("authenticated", False):
    st.warning("🔐 Please log in to access Data Management")
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

# Load current user's data
username = st.session_state.get("username")

st.markdown('<h1 class="main-header">🗄️ Data Management</h1>', unsafe_allow_html=True)
st.markdown(f"**Managing data for user:** `{username}`")

# Load current user's data
portfolio_df = load_portfolio_data(username)
settings = load_settings()
stats = get_portfolio_stats(username)

# Tabs for different data management functions
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Portfolio Data", "⚙️ Settings", "📁 File Management", "🔧 JSON Editor", "📈 Statistics"])

with tab1:
    st.subheader("Portfolio Holdings")
    
    if not portfolio_df.empty:
        st.dataframe(portfolio_df, use_container_width=True)
        
        # Quick actions
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔄 Refresh Data"):
                st.rerun()
        
        with col2:
            if st.button("💾 Save Changes"):
                if save_portfolio_data(portfolio_df):
                    st.success("Portfolio data saved!")
                else:
                    st.error("Failed to save portfolio data")
        
        with col3:
            if st.button("📤 Export CSV"):
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
        st.info("No portfolio data found. Add some holdings in the Portfolio Builder page.")

with tab2:
    st.subheader("Application Settings")
    
    # Display current settings
    st.json(settings)
    
    # Edit settings
    st.subheader("Edit Settings")
    
    new_base_currency = st.selectbox(
        "Base Currency:",
        ["USD", "SGD", "EUR", "GBP", "JPY", "CAD", "AUD", "HKD", "CNY", "INR", "KRW", "THB", "MYR", "IDR", "PHP", "VND"],
        index=0 if settings.get("base_currency", "USD") == "USD" else 1 if settings.get("base_currency", "USD") == "SGD" else 0
    )
    
    if st.button("💾 Save Settings"):
        new_settings = settings.copy()
        new_settings["base_currency"] = new_base_currency
        new_settings["last_updated"] = datetime.now().isoformat()
        
        if save_settings(new_settings):
            st.success("Settings saved!")
            st.rerun()
        else:
            st.error("Failed to save settings")

with tab3:
    st.subheader("File Management")
    
    # Show user-specific file information
    st.write(f"**Files for user:** `{username}`")
    
    # User's portfolio file
    portfolio_file = f"data/portfolio_{username}.json"
    if os.path.exists(portfolio_file):
        file_size = os.path.getsize(portfolio_file)
        st.write(f"📄 **Portfolio File:** `portfolio_{username}.json` ({file_size} bytes)")
        
        # Show last modified time
        mod_time = os.path.getmtime(portfolio_file)
        mod_date = datetime.fromtimestamp(mod_time).strftime("%Y-%m-%d %H:%M:%S")
        st.write(f"🕒 **Last Modified:** {mod_date}")
    else:
        st.write(f"📄 **Portfolio File:** `portfolio_{username}.json` (not created yet)")
    
    # Show all data files
    data_dir = "data"
    if os.path.exists(data_dir):
        st.write("\n**All Data Files:**")
        for root, dirs, files in os.walk(data_dir):
            level = root.replace(data_dir, '').count(os.sep)
            indent = ' ' * 2 * level
            st.write(f"{indent}{os.path.basename(root)}/")
            subindent = ' ' * 2 * (level + 1)
            for file in files:
                file_path = os.path.join(root, file)
                file_size = os.path.getsize(file_path)
                # Highlight user's files
                if file == f"portfolio_{username}.json":
                    st.write(f"{subindent}🔹 **{file}** ({file_size} bytes) ← Your portfolio")
                else:
                    st.write(f"{subindent}{file} ({file_size} bytes)")
    else:
        st.warning("Data directory does not exist yet.")
    
    # File operations
    st.subheader("File Operations")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("💾 Create Backup"):
            backup_path = backup_data()
            if backup_path:
                st.success(f"Backup created: {os.path.basename(backup_path)}")
            else:
                st.error("Failed to create backup")
    
    with col2:
        if st.button("🔄 Refresh Files"):
            st.rerun()
    
    with col3:
        if st.button("📊 Show Stats"):
            st.rerun()

with tab4:
    st.subheader("JSON Data Editor")
    
    # Portfolio JSON editor
    st.write(f"**Portfolio Data (JSON) for user:** `{username}`")
    portfolio_file = f"data/portfolio_{username}.json"
    
    if os.path.exists(portfolio_file):
        try:
            with open(portfolio_file, 'r', encoding='utf-8') as f:
                portfolio_json = json.load(f)
            
            # Display JSON in text area for editing
            json_text = st.text_area(
                "Edit Portfolio JSON:",
                value=json.dumps(portfolio_json, indent=2, default=str),
                height=400
            )
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("💾 Save JSON Changes"):
                    try:
                        # Parse and validate JSON
                        updated_json = json.loads(json_text)
                        
                        # Save to file
                        with open(portfolio_file, 'w', encoding='utf-8') as f:
                            json.dump(updated_json, f, indent=2, default=str)
                        
                        st.success("JSON data saved!")
                        st.rerun()
                    except json.JSONDecodeError as e:
                        st.error(f"Invalid JSON: {str(e)}")
                    except Exception as e:
                        st.error(f"Error saving JSON: {str(e)}")
            
            with col2:
                if st.button("🔄 Reset to Original"):
                    st.rerun()
        
        except Exception as e:
            st.error(f"Error reading portfolio JSON: {str(e)}")
    else:
        st.warning("Portfolio JSON file not found.")
    
    # Settings JSON editor
    st.write("**Settings Data (JSON):**")
    settings_file = "data/settings.json"
    
    if os.path.exists(settings_file):
        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                settings_json = json.load(f)
            
            # Display JSON in text area for editing
            settings_text = st.text_area(
                "Edit Settings JSON:",
                value=json.dumps(settings_json, indent=2, default=str),
                height=200
            )
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("💾 Save Settings JSON"):
                    try:
                        # Parse and validate JSON
                        updated_json = json.loads(settings_text)
                        
                        # Save to file
                        with open(settings_file, 'w', encoding='utf-8') as f:
                            json.dump(updated_json, f, indent=2, default=str)
                        
                        st.success("Settings JSON saved!")
                        st.rerun()
                    except json.JSONDecodeError as e:
                        st.error(f"Invalid JSON: {str(e)}")
                    except Exception as e:
                        st.error(f"Error saving settings JSON: {str(e)}")
            
            with col2:
                if st.button("🔄 Reset Settings"):
                    st.rerun()
        
        except Exception as e:
            st.error(f"Error reading settings JSON: {str(e)}")
    else:
        st.warning("Settings JSON file not found.")

with tab5:
    st.subheader(f"Portfolio Statistics for {username}")
    
    if stats:
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Total Holdings", stats.get("total_holdings", 0))
            st.metric("Unique Symbols", len(stats.get("symbols", [])))
            st.metric("Currencies Used", len(stats.get("currencies", [])))
        
        with col2:
            st.metric("Base Currency", stats.get("base_currency", "USD"))
            last_updated = stats.get("last_updated", "Never")
            if last_updated:
                try:
                    dt = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
                    last_updated = dt.strftime("%Y-%m-%d %H:%M")
                except:
                    pass
            st.metric("Last Updated", last_updated)
        
        # Detailed breakdown
        if stats.get("currencies"):
            st.write("**Currencies in Portfolio:**")
            for currency in stats["currencies"]:
                st.write(f"• {currency}")
        
        if stats.get("symbols"):
            st.write("**Symbols in Portfolio:**")
            symbols_text = ", ".join(stats["symbols"])
            st.write(symbols_text)
    
    else:
        st.info("No statistics available. Add some holdings to see statistics.")

# User Management Section (Admin only)
if st.session_state.get("user_role") == "admin":
    st.markdown("---")
    st.markdown("### 👥 User Management")
    create_user_management_page()

# Footer
st.markdown("---")
st.markdown("**Data Storage Information:**")
st.info(
    f"📁 **Your Portfolio Data**: `data/portfolio_{username}.json`\n"
    "⚙️ **Settings**: `data/settings.json` (shared)\n"
    "💾 **Backups**: `data/backups/`\n"
    "📤 **Exports**: `data/exports/`\n"
    "👥 **Users**: `data/users.json`\n\n"
    f"Each user has their own portfolio file. Your data is stored in `portfolio_{username}.json`"
)
