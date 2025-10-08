# risk_money_index.py
from __future__ import annotations
import streamlit as st

from auth import require_login_or_public

# แท็บย่อย
import riskMoney_lot_size            # การออก Lot (public)
import riskMoney_position_sizing     # ระยะ SL → Lot (login)
import riskMoney_gmksizing          # GMK Signal → Lot (login)
import riskMoney_gmkplaning         # GMK Signal Planning (login)


def render_page():
    """
    เปิดสาธารณะเฉพาะแท็บ 'การออก Lot'
    แท็บอื่นต้องล็อกอิน
    """
    # ตรวจสิทธิ์สำหรับหน้า MM: สาธารณะเฉพาะ sizing
    _ = require_login_or_public("mm_sizing_only")

    logged_in = bool(st.session_state.get("auth", {}).get("logged_in", False))

    st.header("💰 Risk & Money Management")

    # ค่าเริ่มต้นแท็บ
    if "mm_tab" not in st.session_state:
        st.session_state.mm_tab = "sizing"

    # ปุ่มแท็บ — disable แท็บที่ไม่ใช่ sizing เมื่อยังไม่ล็อกอิน
    tabs = st.columns([1.6, 1.8, 1.8, 2.2, 1.6])
    with tabs[0]:
        if st.button("🧮 การออก Lot", use_container_width=True):
            st.session_state.mm_tab = "sizing"
    with tabs[1]:
        if st.button("📏 ระยะ SL → Lot", use_container_width=True, disabled=not logged_in):
            st.session_state.mm_tab = "sl"
    with tabs[2]:
        if st.button("📨 GMK Signal → Lot", use_container_width=True, disabled=not logged_in):
            st.session_state.mm_tab = "signal"
    with tabs[3]:
        if st.button("📑 GMK Signal Planning", use_container_width=True, disabled=not logged_in):
            st.session_state.mm_tab = "signal_plan"
    with tabs[4]:
        if st.button("🧪 (สำรองหน้าอื่น)", use_container_width=True, disabled=not logged_in):
            st.session_state.mm_tab = "tbd2"

    st.divider()

    # ถ้ายังไม่ล็อกอิน แต่เผลอคลิกแท็บอื่น -> บังคับกลับมาที่ sizing
    if not logged_in and st.session_state.mm_tab != "sizing":
        st.session_state.mm_tab = "sizing"

    # ---- Route ตามแท็บ ----
    tab = st.session_state.mm_tab
    if tab == "sizing":
        riskMoney_lot_size.render_tab()  # public
        st.info("หน้านี้เปิดให้ผู้เยี่ยมชมใช้งานได้โดยไม่ต้องล็อกอิน ✅")

    elif tab == "sl":
        if not logged_in:
            _need_login_notice()
            return
        riskMoney_position_sizing.render_tab()

    elif tab == "signal":
        if not logged_in:
            _need_login_notice()
            return
        riskMoney_gmksizing.render_tab()

    elif tab == "signal_plan":
        if not logged_in:
            _need_login_notice()
            return
        riskMoney_gmkplaning.render_tab()

    else:
        st.info("เลือกหน้าฟังก์ชันอื่น ๆ ได้ในอนาคต (ยังไม่เปิดใช้งาน)")


def _need_login_notice():
    st.markdown(
        """
        <div style='border:2px dashed #eab308; padding:16px; border-radius:12px; background:#18181b;'>
          <h3 style='margin:0 0 8px 0;'>🔒 หน้านี้เปิดเฉพาะผู้ใช้ที่ล็อกอิน</h3>
          <div>กรุณาล็อกอิน หรือติดต่อ
            <a href='https://facebook.com/TarotTrader162' target='_blank'>FB: Tarot Trader - หมอดูพาเทรด</a>
            เพื่อขอสิทธิ์เข้าถึง</div>
        </div>
        """,
        unsafe_allow_html=True
    )