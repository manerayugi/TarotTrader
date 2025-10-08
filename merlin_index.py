# merlin_index.py
import streamlit as st
import auth

from merlin_jarvis import render_jarvis_tab
from merlin_gtt import render_gtt_tab

def _hr(width: int = 360):
    st.markdown(
        f"""
        <div style='text-align:center; margin:14px 0;'>
          <hr style='width: {width}px; border: 1px solid #666; margin: 8px auto;'/>
        </div>
        """,
        unsafe_allow_html=True
    )

def render_page():
    # ต้องเป็นแอดมินเท่านั้น
    info = st.session_state.get("auth", {})
    if not info.get("logged_in"):
        st.warning("หน้านี้สำหรับผู้ดูแลระบบ กรุณาเข้าสู่ระบบก่อน")
        return
    if info.get("user", {}).get("role") != "admin":
        st.error("หน้านี้สงวนสิทธิ์สำหรับผู้ดูแลระบบ (admin)")
        return

    st.header("🧙‍♂️ เมอร์ลิน – Admin Utilities")
    st.caption("ศูนย์รวมเครื่องมือผู้ดูแลระบบ: แชทผู้ช่วย และคาล์กูลัสเฉพาะกิจ")
    _hr()

    tab1, tab2 = st.tabs(["🤖 จาวิส", "🜏 Gemini Tenebris Theoria (GTT)"])
    with tab1:
        render_jarvis_tab()
    with tab2:
        render_gtt_tab()