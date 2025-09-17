import streamlit as st
from auth_utils import init_auth_session, signup_form, show_user_menu
from app_utils import setup_page, inject_css

# Use the app's setup functions for consistent styling
setup_page()
inject_css()

# Initialize authentication
init_auth_session()

# Show user menu if already logged in
show_user_menu()

# Main signup page content
st.markdown('<h1 class="main-header">📝 Create Account</h1>', unsafe_allow_html=True)

# Check if user is already authenticated
if st.session_state.get("authenticated", False):
    st.success(f"✅ You are already logged in as **{st.session_state.username}**")
    st.info("Use the navigation menu to access different sections of the dashboard.")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🚀 Go to Dashboard", use_container_width=True):
            st.switch_page("Portfolio.py")
else:
    # Show signup form directly (login is handled on main page)
    st.markdown("""
    <div style='text-align: center; margin-bottom: 2rem;'>
        <p style='font-size: 1.2rem; color: #666;'>
            Create a new account to access the portfolio dashboard
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Create centered signup form
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        signup_form()
    
    # Show login info
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666;'>
        <h4>Already have an account?</h4>
        <p>Go to the main Portfolio page to log in</p>
        <p style='font-size: 0.9rem; margin-top: 1rem;'>
            <strong>Default Admin:</strong> admin / admin123
        </p>
    </div>
    """, unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray;'>
        Portfolio Analysis Dashboard | Create Your Account
    </div>
    """, 
    unsafe_allow_html=True,
)
