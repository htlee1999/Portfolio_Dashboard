# 🔐 Portfolio Dashboard Login System

## Overview
Your Portfolio Dashboard now includes a secure login system that protects your data when deployed to Streamlit Cloud or any public hosting platform.

## Default Login Credentials
- **Username**: `admin`
- **Password**: `admin123`

⚠️ **IMPORTANT**: Change the default password immediately after first login for security!

## Features

### 🔒 Authentication
- Secure password hashing using SHA-256
- Session-based authentication
- Automatic logout protection
- User role management (admin/user)
- **Change password functionality** for all users

### 👥 User Management (Admin Only)
- Create new users
- Change passwords
- View user list and activity
- Role-based access control

### 🛡️ Security Features
- All pages require authentication
- Session state protection
- Secure password storage
- User activity tracking

## How to Use

### First Time Setup
1. Run your Streamlit app: `streamlit run Portfolio.py`
2. Navigate to the Login page (first page in sidebar)
3. Login with default credentials: `admin` / `admin123`
4. Go to Data Management page
5. Create your own user account
6. Change the admin password
7. Delete or modify the default admin account as needed

### Creating New Users
1. Login as admin
2. Go to Data Management page
3. Scroll to "User Management" section
4. Use "Create User" tab to add new users
5. Assign appropriate roles (user/admin)

### Changing Passwords
**Option 1: Change Your Own Password**
1. Login to your account
2. Click "🔑 Change Password" button in the sidebar
3. Enter current and new passwords
4. Click "Change Password"

**Option 2: Admin Change Other Users' Passwords**
1. Login as admin
2. Go to Data Management page
3. Use "Change Password" tab in User Management
4. Enter current and new passwords

## File Structure
```
data/
├── users.json          # User accounts and passwords
├── portfolio.json      # Portfolio data
├── settings.json       # App settings
└── backups/           # Data backups
```

## Deployment Security

### For Streamlit Cloud
1. The login system will automatically protect your app
2. Users must authenticate before accessing any data
3. Each user's session is isolated
4. Admin users can manage other accounts

### For Other Platforms
- The authentication works on any Streamlit deployment
- User data is stored locally in JSON files
- No external database required
- Easy to backup and migrate

## Security Notes
- Passwords are hashed with SHA-256 and salt
- User sessions are managed by Streamlit
- No sensitive data is stored in plain text
- Regular backups are recommended

## Troubleshooting

### Can't Login
- Check username and password spelling
- Ensure you're using the correct credentials
- Try the default admin account first

### Forgot Password
- If you have admin access, create a new user
- If you're locked out, delete `data/users.json` to reset to defaults
- Default admin account will be recreated automatically

### User Management Not Showing
- Ensure you're logged in as an admin user
- Check that your user role is set to "admin"
- Refresh the page after role changes

## Customization
You can modify the authentication system by editing `auth_utils.py`:
- Change password requirements
- Modify user roles
- Add additional security features
- Customize login form appearance
