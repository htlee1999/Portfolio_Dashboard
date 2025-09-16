import streamlit as st
import hashlib
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
import secrets


class AuthManager:
    """Simple authentication manager for Streamlit apps."""
    
    def __init__(self, users_file: str = "data/users.json"):
        self.users_file = users_file
        self.ensure_users_file_exists()
    
    def ensure_users_file_exists(self):
        """Create users file with default admin user if it doesn't exist."""
        if not os.path.exists(self.users_file):
            os.makedirs(os.path.dirname(self.users_file), exist_ok=True)
            
            # Create default admin user
            default_users = {
                "admin": {
                    "password_hash": self._hash_password("admin123"),
                    "role": "admin",
                    "created_at": datetime.now().isoformat(),
                    "last_login": None
                }
            }
            
            with open(self.users_file, 'w') as f:
                json.dump(default_users, f, indent=2)
    
    def _hash_password(self, password: str) -> str:
        """Hash password using SHA-256 with salt."""
        salt = "portfolio_dashboard_salt_2024"  # In production, use random salt per user
        return hashlib.sha256((password + salt).encode()).hexdigest()
    
    def _load_users(self) -> Dict:
        """Load users from file."""
        try:
            with open(self.users_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def _save_users(self, users: Dict):
        """Save users to file."""
        with open(self.users_file, 'w') as f:
            json.dump(users, f, indent=2)
    
    def authenticate_user(self, username: str, password: str) -> Tuple[bool, str]:
        """Authenticate user with username and password."""
        users = self._load_users()
        
        if username not in users:
            return False, "Invalid username or password"
        
        password_hash = self._hash_password(password)
        if users[username]["password_hash"] != password_hash:
            return False, "Invalid username or password"
        
        # Update last login
        users[username]["last_login"] = datetime.now().isoformat()
        self._save_users(users)
        
        return True, "Login successful"
    
    def create_user(self, username: str, password: str, role: str = "user") -> Tuple[bool, str]:
        """Create a new user."""
        users = self._load_users()
        
        if username in users:
            return False, "Username already exists"
        
        if len(password) < 6:
            return False, "Password must be at least 6 characters long"
        
        users[username] = {
            "password_hash": self._hash_password(password),
            "role": role,
            "created_at": datetime.now().isoformat(),
            "last_login": None
        }
        
        self._save_users(users)
        return True, "User created successfully"
    
    def change_password(self, username: str, old_password: str, new_password: str) -> Tuple[bool, str]:
        """Change user password."""
        users = self._load_users()
        
        if username not in users:
            return False, "User not found"
        
        # Verify old password
        if users[username]["password_hash"] != self._hash_password(old_password):
            return False, "Current password is incorrect"
        
        if len(new_password) < 6:
            return False, "New password must be at least 6 characters long"
        
        users[username]["password_hash"] = self._hash_password(new_password)
        self._save_users(users)
        
        return True, "Password changed successfully"
    
    def get_user_info(self, username: str) -> Optional[Dict]:
        """Get user information."""
        users = self._load_users()
        return users.get(username)
    
    def list_users(self) -> Dict:
        """List all users (admin only)."""
        return self._load_users()


def init_auth_session():
    """Initialize authentication session state."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "username" not in st.session_state:
        st.session_state.username = None
    if "user_role" not in st.session_state:
        st.session_state.user_role = None


def login_form() -> bool:
    """Display login form and handle authentication."""
    st.markdown("### 🔐 Login to Portfolio Dashboard")
    
    with st.form("login_form"):
        username = st.text_input("Username", placeholder="Enter your username")
        password = st.text_input("Password", type="password", placeholder="Enter your password")
        submit_button = st.form_submit_button("Login", use_container_width=True)
        
        if submit_button:
            if not username or not password:
                st.error("Please enter both username and password")
                return False
            
            auth_manager = AuthManager()
            success, message = auth_manager.authenticate_user(username, password)
            
            if success:
                st.session_state.authenticated = True
                st.session_state.username = username
                user_info = auth_manager.get_user_info(username)
                st.session_state.user_role = user_info.get("role", "user")
                st.success(f"Welcome back, {username}!")
                st.rerun()
            else:
                st.error(message)
                return False
    
    return False


def signup_form() -> bool:
    """Display signup form and handle user registration."""
    st.markdown("### 📝 Create New Account")
    
    with st.form("signup_form"):
        username = st.text_input("Username", placeholder="Choose a username")
        password = st.text_input("Password", type="password", placeholder="Choose a password")
        confirm_password = st.text_input("Confirm Password", type="password", placeholder="Confirm your password")
        
        # Password requirements
        st.markdown("""
        <div style='font-size: 0.9rem; color: #666; margin-bottom: 1rem;'>
            <strong>Password Requirements:</strong><br>
            • At least 6 characters long<br>
            • Use a combination of letters and numbers for better security
        </div>
        """, unsafe_allow_html=True)
        
        submit_button = st.form_submit_button("Create Account", use_container_width=True)
        
        if submit_button:
            if not username or not password or not confirm_password:
                st.error("Please fill in all fields")
                return False
            
            if password != confirm_password:
                st.error("Passwords do not match")
                return False
            
            if len(password) < 6:
                st.error("Password must be at least 6 characters long")
                return False
            
            auth_manager = AuthManager()
            success, message = auth_manager.create_user(username, password, "user")
            
            if success:
                st.success(f"Account created successfully! Welcome, {username}!")
                st.info("You can now log in with your new credentials.")
                st.rerun()
            else:
                st.error(message)
                return False
    
    return False


def change_password_form() -> bool:
    """Display change password form for logged-in users."""
    st.markdown("### 🔑 Change Password")
    st.markdown(f"**Changing password for:** {st.session_state.username}")
    
    with st.form("change_password_form"):
        current_password = st.text_input("Current Password", type="password", placeholder="Enter your current password")
        new_password = st.text_input("New Password", type="password", placeholder="Enter your new password")
        confirm_password = st.text_input("Confirm New Password", type="password", placeholder="Confirm your new password")
        
        # Password requirements
        st.markdown("""
        <div style='font-size: 0.9rem; color: #666; margin-bottom: 1rem;'>
            <strong>Password Requirements:</strong><br>
            • At least 6 characters long<br>
            • Use a combination of letters and numbers for better security
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            submit_button = st.form_submit_button("Change Password", use_container_width=True)
        with col2:
            cancel_button = st.form_submit_button("Cancel", use_container_width=True)
        
        if cancel_button:
            st.session_state.show_change_password = False
            st.rerun()
        
        if submit_button:
            if not current_password or not new_password or not confirm_password:
                st.error("Please fill in all fields")
                return False
            
            if new_password != confirm_password:
                st.error("New passwords do not match")
                return False
            
            if len(new_password) < 6:
                st.error("New password must be at least 6 characters long")
                return False
            
            if current_password == new_password:
                st.error("New password must be different from current password")
                return False
            
            auth_manager = AuthManager()
            success, message = auth_manager.change_password(
                st.session_state.username, current_password, new_password
            )
            
            if success:
                st.success("Password changed successfully!")
                st.session_state.show_change_password = False
                st.rerun()
            else:
                st.error(message)
                return False
    
    return False


def logout():
    """Logout current user."""
    st.session_state.authenticated = False
    st.session_state.username = None
    st.session_state.user_role = None
    st.rerun()


def require_auth(func):
    """Decorator to require authentication for a function."""
    def wrapper(*args, **kwargs):
        if not st.session_state.get("authenticated", False):
            st.warning("Please log in to access this page.")
            login_form()
            return
        return func(*args, **kwargs)
    return wrapper


def show_user_menu():
    """Show user menu in sidebar."""
    if st.session_state.get("authenticated", False):
        with st.sidebar:
            st.markdown("---")
            st.markdown(f"**Logged in as:** {st.session_state.username}")
            st.markdown(f"**Role:** {st.session_state.user_role}")
            
            # Change password button
            if st.button("🔑 Change Password", use_container_width=True):
                st.session_state.show_change_password = True
            
            if st.button("🚪 Logout", use_container_width=True):
                logout()


def admin_only(func):
    """Decorator to require admin role for a function."""
    def wrapper(*args, **kwargs):
        if not st.session_state.get("authenticated", False):
            st.warning("Please log in to access this page.")
            login_form()
            return
        
        if st.session_state.get("user_role") != "admin":
            st.error("Access denied. Admin privileges required.")
            return
        
        return func(*args, **kwargs)
    return wrapper


def create_user_management_page():
    """Create user management page for admins."""
    st.markdown('<h1 class="main-header">👥 User Management</h1>', unsafe_allow_html=True)
    
    auth_manager = AuthManager()
    
    tab1, tab2, tab3 = st.tabs(["Create User", "Change Password", "User List"])
    
    with tab1:
        st.subheader("Create New User")
        with st.form("create_user_form"):
            new_username = st.text_input("Username", placeholder="Enter username")
            new_password = st.text_input("Password", type="password", placeholder="Enter password")
            new_role = st.selectbox("Role", ["user", "admin"])
            
            if st.form_submit_button("Create User"):
                if new_username and new_password:
                    success, message = auth_manager.create_user(new_username, new_password, new_role)
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
                else:
                    st.error("Please fill in all fields")
    
    with tab2:
        st.subheader("Change Password")
        with st.form("change_password_form"):
            current_password = st.text_input("Current Password", type="password")
            new_password = st.text_input("New Password", type="password")
            confirm_password = st.text_input("Confirm New Password", type="password")
            
            if st.form_submit_button("Change Password"):
                if new_password == confirm_password:
                    success, message = auth_manager.change_password(
                        st.session_state.username, current_password, new_password
                    )
                    if success:
                        st.success(message)
                    else:
                        st.error(message)
                else:
                    st.error("New passwords do not match")
    
    with tab3:
        st.subheader("User List")
        users = auth_manager.list_users()
        
        if users:
            user_data = []
            for username, info in users.items():
                user_data.append({
                    "Username": username,
                    "Role": info.get("role", "user"),
                    "Created": info.get("created_at", "Unknown")[:10],
                    "Last Login": info.get("last_login", "Never")[:10] if info.get("last_login") else "Never"
                })
            
            st.dataframe(user_data, use_container_width=True)
        else:
            st.info("No users found")
