# cookie_manager.py
import json
import streamlit as st
from streamlit_cookies_manager import EncryptedCookieManager
from datetime import datetime, timedelta

# Global variable to store the cookie manager instance
_cookie_manager = None

def get_cookie_manager():
    """Initialize and return the encrypted cookie manager (singleton pattern)"""
    global _cookie_manager
    if _cookie_manager is None:
        _cookie_manager = EncryptedCookieManager(
            prefix="legal_doc_analyzer_",
            password="your_secret_password_here_change_this_in_production"  # Change this in production
        )
    return _cookie_manager

def save_user_to_cookies(user_data):
    """Save user data to cookies"""
    cookies = get_cookie_manager()
    
    # Prepare user data for storage (only store essential info)
    cookie_data = {
        'localId': user_data.get('localId'),
        'email': user_data.get('email'),
        'idToken': user_data.get('idToken'),
        'refreshToken': user_data.get('refreshToken'),
        'expiresIn': user_data.get('expiresIn'),
        'registered': user_data.get('registered', True),
        'login_time': datetime.now().isoformat()
    }
    
    # Set expiration time (default 7 days)
    expires_at = datetime.now() + timedelta(days=7)
    
    try:
        cookies['user_data'] = json.dumps(cookie_data)
        cookies['expires_at'] = expires_at.isoformat()
        cookies.save()
        return True
    except Exception as e:
        st.error(f"Error saving user data to cookies: {e}")
        return False

def load_user_from_cookies():
    """Load user data from cookies"""
    cookies = get_cookie_manager()
    
    try:
        if 'user_data' in cookies and 'expires_at' in cookies:
            # Check if cookie has expired
            expires_at = datetime.fromisoformat(cookies['expires_at'])
            if datetime.now() > expires_at:
                # Cookie expired, clear it
                clear_user_cookies()
                return None
            
            # Load user data
            user_data = json.loads(cookies['user_data'])
            return user_data
        return None
    except Exception as e:
        # st.error(f"Error loading user data from cookies: {e}")
        return None

def clear_user_cookies():
    """Clear user data from cookies"""
    cookies = get_cookie_manager()
    try:
        if 'user_data' in cookies:
            del cookies['user_data']
        if 'expires_at' in cookies:
            del cookies['expires_at']
        cookies.save()
        return True
    except Exception as e:
        st.error(f"Error clearing user cookies: {e}")
        return False

def is_user_logged_in():
    """Check if user is logged in based on cookies and session state"""
    # First check session state
    if st.session_state.get("user"):
        return True
    
    # If not in session state, check cookies
    user_data = load_user_from_cookies()
    if user_data:
        # Restore user to session state
        st.session_state["user"] = user_data
        return True
    
    return False
