# auth.py
import streamlit as st
from firebase_setup import auth, db

# Initialize session state for authentication
def login():
    st.subheader("Login")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    if st.button("Login", key="sidebar_login_btn"):
        try:
            user = auth.sign_in_with_email_and_password(email, password)
            st.session_state["user"] = user
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

