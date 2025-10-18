import os
import streamlit as st
from firebase_setup import auth
from streamlit_cookies_manager import EncryptedCookieManager
import logging
import sys
print(sys.path)
# Configure logging for debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Browser cookie manager to store refresh token securely
cookies = EncryptedCookieManager(
    prefix="legal_analyzer_",
    password=os.getenv("COOKIE_PASSWORD", "super_secret_key_change_in_production")
)
if not cookies.ready():
    logger.warning("Cookie manager not ready, stopping Streamlit app")
    st.stop()

# ------------------- Authentication Functions ------------------- #
def login():
    """Handle user login with Firebase authentication."""
    st.subheader("Login")
    email = st.text_input("Email", key="login_email")
    password = st.text_input("Password", type="password", key="login_password")
    if st.button("Login", key="login_btn"):
        try:
            user = auth.sign_in_with_email_and_password(email, password)
            id_token = user["idToken"]
            refresh_token = user["refreshToken"]
            local_id = user["localId"]

            # Save refresh token in browser cookie
            cookies["refreshToken"] = refresh_token
            cookies.save()
            logger.info(f"User logged in: {email}")

            # Save user in session state with localId
            st.session_state["user"] = {"email": email, "idToken": id_token, "localId": local_id}
            st.success("Logged in successfully!")
            st.rerun()
        except Exception as e:
            logger.error(f"Login failed for {email}: {str(e)}")
            st.error("Login failed. Check your credentials or try again later.")

def register():
    """Handle user registration with Firebase authentication."""
    st.subheader("Register")
    email = st.text_input("Email", key="reg_email")
    password = st.text_input("Password", type="password", key="reg_pass")
    if st.button("Register", key="register_btn"):
        try:
            auth.create_user_with_email_and_password(email, password)
            logger.info(f"User registered: {email}")
            st.success("Registration successful! Please log in.")
            st.session_state["auth_mode"] = "login"
            st.rerun()
        except Exception as e:
            logger.error(f"Registration failed for {email}: {str(e)}")
            st.error("Registration failed. Try a different email or check password requirements.")

def load_session():
    """Restore user from browser cookie if refresh token exists."""
    if "user" in st.session_state:
        logger.info("User session already loaded")
        return  # Already loaded
    
    refresh_token = cookies.get("refreshToken")
    if refresh_token:
        try:
            refreshed = auth.refresh(refresh_token)
            id_token = refreshed["idToken"]
            new_refresh = refreshed["refreshToken"]

            acct_info = auth.get_account_info(id_token)
            user_info = acct_info["users"][0]
            email = user_info["email"]
            local_id = user_info["localId"]

            # Restore user in session_state with localId
            st.session_state["user"] = {"email": email, "idToken": id_token, "localId": local_id}

            # Update cookie with new refresh token
            cookies["refreshToken"] = new_refresh
            cookies.save()
            logger.info(f"Session restored for user: {email}")
        except Exception as e:
            logger.warning(f"Failed to restore session: {str(e)}")
            # Invalid token, clear cookie
            cookies["refreshToken"] = ""
            cookies.save()

def logout():
    """Logout user, clear session and cookies."""
    if "user" in st.session_state:
        email = st.session_state["user"].get("email", "unknown")
        del st.session_state["user"]
        logger.info(f"User logged out: {email}")
    cookies["refreshToken"] = ""
    cookies.save()
    st.success("Logged out successfully!")
    st.rerun()