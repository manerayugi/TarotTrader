import streamlit as st
import pandas as pd
import func
import ui  # <<< UI แยกไฟล์

# ========================= App Config =========================
st.set_page_config(page_title="🔮 Tarot Trader 💹", page_icon="🔮", layout="wide")

# ========================= Boot / Session =========================
func.ensure_db()

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
    ui.inject_login_css()        # CSS เฉพาะตอนยังไม่ล็อกอิน
    ui.render_login_form()       # ฟอร์มล็อกอิน (จัดกลาง + ปุ่มกึ่งกลาง)
    st.stop()

# ========================= Sidebar (Branding + Menu + User + Logout) =========================
with st.sidebar:
    ui.render_sidebar(auth=st.session_state.auth)

# ========================= Router =========================
page = st.session_state.page

if page == "port":
    ui.render_port_page()

elif page == "users":
    # ป้องกันผู้ใช้ทั่วไปเข้าเมนูผู้ดูแล
    if st.session_state.auth.get("role") != "admin":
        st.error("หน้าเฉพาะผู้ดูแลระบบ")
        st.stop()
    ui.render_users_admin_page()

else:
    # Money Management
    st.header("💰 Money Management")
    ui.render_mm_tabs()  # ปุ่มเลือกแท็บ

    if st.session_state.mm_tab == "sizing":
        ui.render_mm_position_sizing(func)
    elif st.session_state.mm_tab == "sl":
        ui.render_mm_sl_to_lot(func)
    else:
        st.info("เลือกหน้าฟังก์ชันอื่น ๆ ได้ในอนาคต (ยังไม่เปิดใช้งาน)")