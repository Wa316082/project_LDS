# auth.py
import streamlit as st
from firebase_setup import auth
from streamlit_cookies_manager import EncryptedCookieManager

# Browser cookie manager to store refresh token securely
cookies = EncryptedCookieManager(prefix="legal_analyzer", password="super_secret_key")
if not cookies.ready():
    st.stop()

# ------------------- Authentication Functions ------------------- #
def login():
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

            # Save user in session state with localId
            st.session_state["user"] = {"email": email, "idToken": id_token, "localId": local_id}
            st.success("Logged in successfully!")
            st.rerun()
        except Exception:
            st.error("Login failed. Check your credentials.")

def register():
    st.subheader("Register")
    email = st.text_input("Email", key="reg_email")
    password = st.text_input("Password", type="password", key="reg_pass")
    if st.button("Register", key="register_btn"):
        try:
            auth.create_user_with_email_and_password(email, password)
            st.success("Registration successful! Please log in.")
            st.session_state["auth_mode"] = "login"
            st.rerun()
        except Exception:
            st.error("Registration failed. Try a different email.")

def load_session():
    """Restore user from browser cookie if refresh token exists."""
    if "user" in st.session_state:
        return  # already loaded
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
        except Exception:
            # Invalid token, clear cookie
            cookies["refreshToken"] = ""
            cookies.save()

def logout():
    """Logout user, clear session and cookies."""
    if "user" in st.session_state:
        del st.session_state["user"]
    cookies["refreshToken"] = ""
    cookies.save()
    st.success("Logged out successfully!")
    st.rerun()