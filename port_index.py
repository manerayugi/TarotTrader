# port.py
import streamlit as st
from port_performance import render_performance_tab
from port_advanced import render_advanced_tab
import auth  # ใช้เช็ค role

def _admin_gate_ui():
    st.markdown(
        """
        <div style='border:2px dashed #eab308; padding:16px; border-radius:12px; background:#18181b;'>
          <h3 style='margin:0 0 8px 0;'>🔒 แท็บนี้สำหรับผู้ดูแลระบบ (Admin) เท่านั้น</h3>
          <div>หากต้องการสิทธิ์เข้าถึง โปรดติดต่อ
            <a href='https://facebook.com/TarotTrader162' target='_blank'>FB: Tarot Trader</a>
          </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    st.button("เข้าใช้งาน (Admin เท่านั้น)", disabled=True, use_container_width=True)

def render_port_page():
    st.header("📊 Portfolio")

    tab_perf, tab_adv = st.tabs(["📈 Performance", "📐 Elite Portfolio"])
    with tab_perf:
        # ทุกคนใช้ได้
        render_performance_tab()

    with tab_adv:
        # โชว์แท็บ แต่ถ้าไม่ใช่ admin ให้ขึ้น Gate UI
        if auth.has_role("admin"):
            render_advanced_tab()
        else:
            _admin_gate_ui()