# auth.py
import streamlit as st
from firebase_setup import auth, db
from cookie_manager import save_user_to_cookies, clear_user_cookies

# Initialize session state for authentication
def login():
    st.subheader("Login")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    if st.button("Login", key="sidebar_login_btn"):
        try:
            user = auth.sign_in_with_email_and_password(email, password)
            st.session_state["user"] = user
            
            # Save user data to cookies for persistence
            if save_user_to_cookies(user):
                st.success("Logged in successfully! (Session will persist)")
            else:
                st.success("Logged in successfully!")
            
            st.rerun()
        except Exception as e:
            st.error("Login failed. Check your credentials.")

    if st.button("Go to Register", key="sidebar_go_register_btn"):
        st.session_state["auth_mode"] = "register"
        st.rerun()

# Register a new user
def register():
    st.subheader("Register")
    email = st.text_input("Email", key="reg_email")
    password = st.text_input("Password", type="password", key="reg_pass")
    if st.button("Register", key="sidebar_register_btn"):
        try:
            auth.create_user_with_email_and_password(email, password)
            st.success("Registration successful! Please log in.")
            st.session_state["auth_mode"] = "login"
            st.rerun()
        except Exception as e:
            st.error("Registration failed. Try a different email.")

    if st.button("Go to Login", key="sidebar_go_login_btn"):
        st.session_state["auth_mode"] = "login"
        st.rerun()

def logout():
    """Handle user logout and clear cookies"""
    # Clear session state
    st.session_state["user"] = None
    
    # Clear cookies
    if clear_user_cookies():
        st.sidebar.info("Logged out successfully!")
    else:
        st.sidebar.info("Logged out!")
    
    st.rerun()

