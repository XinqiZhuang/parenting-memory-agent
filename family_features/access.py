import hashlib
import hmac
import os
import time


def require_web_access(show_logout=True):
    import streamlit as st
    password = os.getenv("WEB_PASSWORD", "")
    production = os.getenv("APP_ENV", "local") == "production"
    if production and len(password) < 16:
        st.error("线上模式必须配置至少16位的WEB_PASSWORD。")
        st.stop()
    if not password:
        return
    expected = hashlib.sha256(password.encode()).hexdigest()
    if hmac.compare_digest(st.session_state.get("_web_auth", ""), expected):
        if show_logout and st.sidebar.button("退出登录"):
            st.session_state.clear()
            st.rerun()
        return
    st.title("玖玖的成长日记")
    st.caption("欢迎回家。请输入家庭访问密码，打开成长档案。")
    with st.form("family_login"):
        entered = st.text_input("家庭访问密码", type="password")
        submitted = st.form_submit_button("打开档案")
    if submitted:
        now = time.time()
        if now < st.session_state.get("_login_after", 0):
            st.warning("请稍候再试。")
        elif hmac.compare_digest(entered, password):
            st.session_state["_web_auth"] = expected
            st.rerun()
        else:
            st.session_state["_login_after"] = now + 3
            st.error("密码不正确。")
    st.stop()
