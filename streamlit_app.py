import os
import base64
import pandas as pd
import streamlit as st

import func           # ตรรกะ: DB/User + คำนวณต่าง ๆ
import ui             # ส่วน UI ที่แยกออกมา

func.ensure_db()

# ========================= App Config =========================
st.set_page_config(page_title="🔮 Tarot Trader 💹", page_icon="🔮", layout="wide")

# ========================= Session =========================
if "auth" not in st.session_state:
    st.session_state.auth = None
if "page" not in st.session_state:
    st.session_state.page = "money"
if "mm_tab" not in st.session_state:
    st.session_state.mm_tab = "sizing"

# ========================= First-run Admin Creation =========================
if func.ensure_initial_admin() and not st.session_state.auth:
    ui.render_initial_admin_form()

# ========================= Login Gate =========================
if not st.session_state.auth:
    # ฉีด CSS เฉพาะตอน “ยังไม่ล็อคอิน”
    ui.inject_login_css()
    ui.render_login_form()
    st.stop()

# ========================= Topbar (User + Logout) =========================
ui.render_topbar_user(st.session_state.auth)

# ========================= Sidebar =========================
ui.render_sidebar()

page = st.session_state.page

# ========================= Router =========================
if page == "port":
    st.header("📊 พอร์ตลงทุน")
    st.info("หน้านี้จะเติมภายหลัง")

elif page == "users":
    if st.session_state.auth.get("role") != "admin":
        st.error("หน้าเฉพาะผู้ดูแลระบบ")
        st.stop()
    ui.render_user_admin_page()

else:
    # ---------------- Money Management ----------------
    st.header("💰 Money Management")

    # แถบปุ่มเลือกแท็บ
    ui.render_mm_tabs()

    if st.session_state.mm_tab == "sizing":
        ui.render_mm_position_sizing(func)
    elif st.session_state.mm_tab == "sl":
        ui.render_mm_sl_to_lot(func)
    else:
        st.info("เลือกหน้าฟังก์ชันอื่น ๆ ได้ในอนาคต (ยังไม่เปิดใช้งาน)")