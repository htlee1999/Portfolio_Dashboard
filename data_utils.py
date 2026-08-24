import json
import os
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Any
import streamlit as st
from config import PORTFOLIO_COLUMNS, get_iso_timestamp, get_file_timestamp, normalize_symbol
from file_utils import ensure_directory, load_json, save_json


def ensure_data_directory() -> str:
    """Ensure the data directory exists and return its path."""
    data_dir = os.path.join(os.getcwd(), "data")
    return ensure_directory(data_dir)


def get_portfolio_file_path(username: str = None) -> str:
    """Get the path to the portfolio JSON file for a specific user."""
    data_dir = ensure_data_directory()
    if username:
        return os.path.join(data_dir, f"portfolio_{username}.json")
    else:
        return os.path.join(data_dir, "portfolio.json")


def get_settings_file_path() -> str:
    """Get the path to the settings JSON file."""
    data_dir = ensure_data_directory()
    return os.path.join(data_dir, "settings.json")


def load_portfolio_data(username: str = None) -> pd.DataFrame:
    """Load portfolio data from JSON file for a specific user."""
    file_path = get_portfolio_file_path(username)
    
    if not os.path.exists(file_path):
        # Return empty DataFrame with correct columns if file doesn't exist
        return pd.DataFrame(columns=PORTFOLIO_COLUMNS)
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not data or 'holdings' not in data:
            return pd.DataFrame(columns=PORTFOLIO_COLUMNS)
        
        # Convert to DataFrame
        df = pd.DataFrame(data['holdings'])
        
        # Ensure all required columns exist
        for col in PORTFOLIO_COLUMNS:
            if col not in df.columns:
                df[col] = "USD" if col == "Currency" else None
        
        # Convert date strings back to datetime
        if 'Purchase_Date' in df.columns:
            df['Purchase_Date'] = pd.to_datetime(df['Purchase_Date']).dt.date
        
        return df
        
    except (json.JSONDecodeError, KeyError, Exception) as e:
        st.error(f"Error loading portfolio data: {str(e)}")
        return pd.DataFrame(columns=PORTFOLIO_COLUMNS)


def save_portfolio_data(portfolio_df: pd.DataFrame, username: str = None) -> bool:
    """Save portfolio data to JSON file for a specific user."""
    try:
        file_path = get_portfolio_file_path(username)
        
        # Convert DataFrame to dictionary format
        data = {
            "last_updated": get_iso_timestamp(),
            "username": username,
            "holdings": portfolio_df.to_dict('records')
        }
        
        # Ensure data directory exists
        ensure_data_directory()
        
        # Save to JSON file
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str)
        
        return True
        
    except Exception as e:
        st.error(f"Error saving portfolio data: {str(e)}")
        return False


def load_settings() -> Dict[str, Any]:
    """Load application settings from JSON file."""
    file_path = get_settings_file_path()
    
    if not os.path.exists(file_path):
        # Return default settings if file doesn't exist
        return {
            "base_currency": "USD",
            "last_updated": get_iso_timestamp()
        }
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, Exception) as e:
        st.warning(f"Error loading settings: {str(e)}. Using default settings.")
        return {
            "base_currency": "USD",
            "last_updated": get_iso_timestamp()
        }


def save_settings(settings: Dict[str, Any]) -> bool:
    """Save application settings to JSON file."""
    try:
        file_path = get_settings_file_path()

        # Add timestamp
        settings["last_updated"] = get_iso_timestamp()
        
        # Ensure data directory exists
        ensure_data_directory()
        
        # Save to JSON file
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2, default=str)
        
        return True
        
    except Exception as e:
        st.error(f"Error saving settings: {str(e)}")
        return False


def add_holding(symbol: str, quantity: float, purchase_price: float, 
                purchase_date: datetime.date, currency: str, username: str = None) -> bool:
    """Add a new holding to the portfolio for a specific user."""
    try:
        # Load current portfolio
        portfolio_df = load_portfolio_data(username)
        
        # Create new holding (normalize so alternate codes map to one symbol)
        new_holding = pd.DataFrame({
            "Symbol": [normalize_symbol(symbol)],
            "Quantity": [quantity],
            "Purchase_Price": [purchase_price],
            "Purchase_Date": [purchase_date],
            "Currency": [currency]
        })
        
        # Add to portfolio
        portfolio_df = pd.concat([portfolio_df, new_holding], ignore_index=True)
        
        # Save updated portfolio
        return save_portfolio_data(portfolio_df, username)
        
    except Exception as e:
        st.error(f"Error adding holding: {str(e)}")
        return False


def remove_holding(symbol: str, username: str = None) -> bool:
    """Remove a holding from the portfolio for a specific user."""
    try:
        # Load current portfolio
        portfolio_df = load_portfolio_data(username)
        
        # Remove holding (normalize so it matches the stored canonical symbol)
        portfolio_df = portfolio_df[portfolio_df["Symbol"] != normalize_symbol(symbol)].reset_index(drop=True)
        
        # Save updated portfolio
        return save_portfolio_data(portfolio_df, username)
        
    except Exception as e:
        st.error(f"Error removing holding: {str(e)}")
        return False




def clear_all_holdings(username: str = None) -> bool:
    """Clear all holdings from the portfolio for a specific user."""
    try:
        # Create empty portfolio
        empty_portfolio = pd.DataFrame(columns=PORTFOLIO_COLUMNS)
        
        # Save empty portfolio
        return save_portfolio_data(empty_portfolio, username)
        
    except Exception as e:
        st.error(f"Error clearing holdings: {str(e)}")
        return False


def export_portfolio_to_csv() -> str:
    """Export portfolio data to CSV and return the file path."""
    try:
        portfolio_df = load_portfolio_data()
        
        if portfolio_df.empty:
            return None
        
        # Create export directory
        data_dir = ensure_data_directory()
        export_dir = os.path.join(data_dir, "exports")
        if not os.path.exists(export_dir):
            os.makedirs(export_dir)
        
        # Generate filename with timestamp
        filename = f"portfolio_export_{get_file_timestamp()}.csv"
        file_path = os.path.join(export_dir, filename)
        
        # Export to CSV
        portfolio_df.to_csv(file_path, index=False)
        
        return file_path
        
    except Exception as e:
        st.error(f"Error exporting portfolio: {str(e)}")
        return None


def import_portfolio_from_csv(csv_data: pd.DataFrame) -> bool:
    """Import portfolio data from CSV DataFrame."""
    try:
        # Validate required columns
        required_columns = ["Symbol", "Quantity", "Purchase_Price", "Purchase_Date"]
        if not all(col in csv_data.columns for col in required_columns):
            st.error(f"CSV must contain columns: {', '.join(required_columns)}")
            return False
        
        # Add Currency column if not present
        if "Currency" not in csv_data.columns:
            csv_data["Currency"] = "USD"
            st.warning("Currency column not found in CSV. Defaulting to USD for all entries.")
        
        # Clean and validate data (normalize alternate codes to one symbol)
        csv_data["Symbol"] = csv_data["Symbol"].apply(normalize_symbol)
        csv_data["Purchase_Date"] = pd.to_datetime(csv_data["Purchase_Date"]).dt.date
        
        # Load current portfolio
        portfolio_df = load_portfolio_data()
        
        # Append new data
        portfolio_df = pd.concat([portfolio_df, csv_data], ignore_index=True)
        
        # Save updated portfolio
        return save_portfolio_data(portfolio_df)
        
    except Exception as e:
        st.error(f"Error importing portfolio: {str(e)}")
        return False


def get_portfolio_stats(username: str = None) -> Dict[str, Any]:
    """Get portfolio statistics and metadata for a specific user."""
    try:
        portfolio_df = load_portfolio_data(username)
        settings = load_settings()
        
        stats = {
            "total_holdings": len(portfolio_df),
            "currencies": portfolio_df["Currency"].unique().tolist() if not portfolio_df.empty else [],
            "symbols": portfolio_df["Symbol"].unique().tolist() if not portfolio_df.empty else [],
            "last_updated": None,
            "base_currency": settings.get("base_currency", "USD"),
            "username": username
        }
        
        # Get last updated time from portfolio file
        file_path = get_portfolio_file_path(username)
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    stats["last_updated"] = data.get("last_updated")
            except:
                pass
        
        return stats
        
    except Exception as e:
        st.error(f"Error getting portfolio stats: {str(e)}")
        return {}


def backup_data() -> str:
    """Create a backup of all data files."""
    try:
        data_dir = ensure_data_directory()
        backup_dir = os.path.join(data_dir, "backups")
        
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        
        # Generate backup filename with timestamp
        backup_filename = f"portfolio_backup_{get_file_timestamp()}.json"
        backup_path = os.path.join(backup_dir, backup_filename)
        
        # Create backup data
        portfolio_df = load_portfolio_data()
        settings = load_settings()
        
        backup_data = {
            "portfolio": portfolio_df.to_dict('records'),
            "settings": settings,
            "backup_created": get_iso_timestamp()
        }
        
        # Save backup
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2, default=str)
        
        return backup_path
        
    except Exception as e:
        st.error(f"Error creating backup: {str(e)}")
        return None


# =============================================================================
# RECOMMENDATION HISTORY
# =============================================================================

def get_recommendation_history_file_path(username: str = None) -> str:
    """Get the path to the recommendation history JSON file for a specific user."""
    data_dir = ensure_data_directory()
    if username:
        return os.path.join(data_dir, f"recommendation_history_{username}.json")
    else:
        return os.path.join(data_dir, "recommendation_history.json")


def load_recommendation_history(username: str = None) -> List[Dict]:
    """Load recommendation history from JSON file."""
    file_path = get_recommendation_history_file_path(username)
    return load_json(file_path, default=[])


def save_recommendation_record(record: Dict[str, Any], username: str = None) -> bool:
    """Append a recommendation record to the history file."""
    try:
        history = load_recommendation_history(username)
        history.append(record)
        file_path = get_recommendation_history_file_path(username)
        return save_json(file_path, history)
    except Exception as e:
        st.error(f"Error saving recommendation record: {str(e)}")
        return False
