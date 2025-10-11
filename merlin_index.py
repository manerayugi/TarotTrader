# merlin_index.py
import streamlit as st
import auth
from func import _hr

from merlin_jarvis import render_jarvis_tab
from merlin_gtt import render_gtt_tab


def _go_login():
    st.session_state.page = "login"
    st.rerun()


def render_page():
    # เตรียม state auth (กันเคสยังไม่ถูก init)
    auth.init_auth()
    info = st.session_state.get("auth", {})

    # --- Gate: ต้องล็อกอินก่อน ---
    if not info.get("logged_in"):
        st.warning("หน้านี้สำหรับผู้ดูแลระบบ (Admin) — กรุณาเข้าสู่ระบบก่อน")
        if st.button("🔐 ไปหน้าเข้าสู่ระบบ", use_container_width=True):
            _go_login()
        return

    # --- Gate: ต้องเป็นแอดมินเท่านั้น ---
    user = info.get("user") or {}
    if user.get("role") != "admin":
        st.error("หน้านี้สงวนสิทธิ์สำหรับผู้ดูแลระบบ (Admin) เท่านั้น")
        return

    # --- UI ---
    st.header("🧙‍♂️ เมอร์ลิน – Admin Utilities")
    st.caption("ศูนย์รวมเครื่องมือผู้ดูแลระบบ: แชทผู้ช่วย และคาล์กูลัสเฉพาะกิจ")
    _hr(420)

    # Tabs
    tab1, tab2 = st.tabs(["🤖 จาวิส", "🜏 GTT — Gemini Tenebris Theoria"])
    with tab1:
        render_jarvis_tab()
    with tab2:
        render_gtt_tab(default_mode="Normal")  # 👉 เปิด GTT แบบ Normal ก่อน