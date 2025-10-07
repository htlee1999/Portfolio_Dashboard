import streamlit as st

# Configure page settings to prevent navigation duplication
st.set_page_config(
    page_title="Portfolio Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Redirect to Portfolio Overview page
st.switch_page("pages/1_Portfolio_Overview.py")