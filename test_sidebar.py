#!/usr/bin/env python3
"""
Test script to demonstrate the stock selection sidebar functionality.
This simulates how the sidebar would work in the actual Streamlit app.
"""

import streamlit as st
import pandas as pd
from app_utils import setup_page, create_sidebar, init_session_state

def test_sidebar():
    """Test the stock selection sidebar functionality."""
    
    # Initialize session state
    if "portfolio" not in st.session_state:
        # Create a sample portfolio for testing
        st.session_state.portfolio = pd.DataFrame({
            'Symbol': ['AAPL', 'MSFT', 'GOOGL', 'TSLA'],
            'Quantity': [10, 5, 3, 2],
            'Purchase_Price': [150.0, 300.0, 2500.0, 200.0],
            'Currency': ['USD', 'USD', 'USD', 'USD']
        })
    
    # Set up page
    setup_page()
    
    # Create sidebar
    create_sidebar()
    
    # Main content
    st.title("🧪 Stock Selection Sidebar Test")
    
    st.write("This is a test to demonstrate the stock selection sidebar functionality.")
    st.write("The sidebar should show:")
    st.write("1. 📈 Stock Selection section")
    st.write("2. Dropdown with portfolio symbols + Custom Symbol option")
    st.write("3. Text input for custom symbols")
    st.write("4. Selected stock display")
    st.write("5. Analysis buttons")
    
    # Show current session state
    st.subheader("Current Session State")
    st.write(f"Selected Stock: {st.session_state.get('selected_stock', 'None')}")
    st.write(f"Current Page: {st.session_state.get('current_page', 'None')}")
    
    # Show portfolio
    st.subheader("Sample Portfolio")
    st.dataframe(st.session_state.portfolio)

if __name__ == "__main__":
    test_sidebar()
