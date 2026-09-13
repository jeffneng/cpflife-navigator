"""A simple shared-passphrase gate for the whole app.

This is not real user authentication — just a deterrent against random
public access while the app is deployed, per the assignment's own
recommendation to password-protect the submission. Call require_password()
as the first Streamlit UI action on every page (right after
st.set_page_config()); once entered correctly, st.session_state remembers
it for the rest of that browser session across every page.

If no APP_PASSWORD secret is configured (e.g. local dev without it set),
the gate is skipped entirely rather than locking anyone out.
"""
import streamlit as st


def require_password() -> None:
    if st.session_state.get("authenticated"):
        return

    try:
        correct_password = st.secrets["APP_PASSWORD"]
    except Exception:
        st.session_state["authenticated"] = True
        return

    st.title("🔒 CPF LIFE Navigator")
    st.caption("This app is password-protected. Enter the passphrase to continue.")
    password = st.text_input("Password", type="password", key="app_password_input")
    if st.button("Enter"):
        if password == correct_password:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    st.stop()
