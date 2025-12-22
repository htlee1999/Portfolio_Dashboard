"""
Page initialization utilities.
Consolidates common page setup patterns to reduce boilerplate.
"""

import streamlit as st
from app_utils import setup_page, inject_css, init_session_state, create_sidebar
from auth_utils import init_auth_session, show_user_menu


def init_protected_page(show_login_form: bool = False) -> bool:
    """
    Initialize a protected page that requires authentication.

    This function handles the common initialization sequence:
    1. Initialize authentication session
    2. Check if user is authenticated (stops execution if not)
    3. Setup page configuration
    4. Inject CSS styles
    5. Initialize session state
    6. Create sidebar
    7. Show user menu

    Args:
        show_login_form: If True, shows the login form when not authenticated.
                        If False, just shows warning message.

    Returns:
        bool: True if initialization completed (user is authenticated).
              Note: If not authenticated, this function calls st.stop()
              and never returns.
    """
    # Initialize authentication
    init_auth_session()

    # Check authentication
    if not st.session_state.get("authenticated", False):
        st.warning("Please log in to access this page")
        st.info("Use the Login page in the sidebar to authenticate")

        if show_login_form:
            from auth_utils import login_form
            login_form()

        st.stop()
        return False  # Never reached, but for type checking

    # Setup page
    setup_page()
    inject_css()
    init_session_state()
    create_sidebar()
    show_user_menu()

    return True


def init_public_page() -> None:
    """
    Initialize a public page that doesn't require authentication.

    This function handles initialization for public pages like signup:
    1. Setup page configuration
    2. Inject CSS styles
    3. Initialize authentication session (but no check)
    4. Show user menu (for logged-in users who navigate here)
    """
    setup_page()
    inject_css()
    init_auth_session()
    show_user_menu()
