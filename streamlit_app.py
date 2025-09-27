import os, base64
import streamlit as st
import pandas as pd

import auth
import calc as mm

# ========================= App Config =========================
st.set_page_config(page_title="🔮 Tarot Trader 💹", page_icon="🔮", layout="wide")

# ---------- CSS ----------
st.markdown("""
<style>
/* จัด layout หน้า login: กลางแนวนอน + ชิดบน (ไม่ต้องสกรอล์) */
.login-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;          /* กลางแนวนอน */
  justify-content: flex-start;  /* ชิดบน */
  min-height: 10vh;             /* ตามที่ต้องการ */
  padding-top: 60px;            /* เว้นระยะจากขอบบน */
}

/* Logo บนหน้า Login */
.login-logo{
  width:120px; height:120px; border-radius:50%;
  object-fit:cover; border:2px solid #2f3651; display:block; margin:0 auto 12px auto;
}

/* ชื่อเพจ หน้า Login */
.login-title{ text-align:center; margin:6px 0 18px 0; font-size:1.25rem; }

/* Sidebar: title center + โลโก้ตรงกลาง */
.sidebar-title{ text-align:center; font-weight:700; }
.sidebar-logo{ display:block; margin:0 auto 8px auto; border-radius:8px; }

/* ตาราง: จัดให้ตัวอักษรอยู่กลางช่อง */
[data-testid="stDataFrame"] table td, 
[data-testid="stDataFrame"] table th { text-align: center; }

/* --- ปุ่ม Login ให้อยู่กลาง column --- */
.login-btn-wrap {
  display: flex;
  justify-content: center;  /* จัดกลางแนวนอน */
  align-items: center;      /* จัดกลางแนวตั้ง */
  width: 100%;
  margin-top: 12px;
}

/* โลโก้ใน Sidebar: ให้อยู่กลางและเป็นวงกลมจริง */
.sidebar-logo-circle{
  display:block;
  margin:0 auto 10px auto;   /* จัดกลางแนวนอน */
  width: 84px; 
  height: 84px;
  border-radius: 50%;         /* ทำให้กลม */
  object-fit: cover;          /* ครอบรูปให้พอดีกรอบวงกลม */
  border: 2px solid #2f3651;  /* เส้นขอบบาง ๆ */
}
</style>
""", unsafe_allow_html=True)

# ---------- AUTH ----------
if "auth" not in st.session_state:
    st.session_state.auth = None

auth.ensure_users_table()

# ---------- First-run: create admin (กรณียังไม่มี user) ----------
if auth.ensure_initial_admin() and not st.session_state.auth:
    st.markdown("<div style='text-align:center'>", unsafe_allow_html=True)
    if os.path.exists("assets/logo.png"):
        st.image("assets/logo.png", width=120)
    st.header("🔐 สร้างผู้ใช้แอดมิน (ครั้งแรก)")
    st.markdown("</div>", unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        new_admin_user = st.text_input("Admin Username", key="init_admin_user")
        new_admin_pass = st.text_input("Admin Password", type="password", key="init_admin_pass")
    with c2:
        new_admin_pass2 = st.text_input("Confirm Password", type="password", key="init_admin_pass2")
        if st.button("สร้างแอดมิน"):
            if not new_admin_user or not new_admin_pass:
                st.error("กรอกให้ครบ")
            elif new_admin_pass != new_admin_pass2:
                st.error("รหัสผ่านไม่ตรงกัน")
            else:
                if auth.create_user(new_admin_user, new_admin_pass, role="admin"):
                    st.success("สร้าง Admin สำเร็จ! โปรดล็อกอินด้านล่าง")
                else:
                    st.error("ชื่อผู้ใช้ซ้ำหรือผิดพลาด")

# ---------- Login Gate ----------
if not st.session_state.auth:
    st.markdown("""
    <style>
      .block-container{ padding-top: 1 !important; padding-bottom: 0 !important; }
    </style>
    """, unsafe_allow_html=True)
    
    # กลางแนวนอนแบบ 2-1-2
    col_left, col_center, col_right = st.columns([2, 1, 2])
    with col_center:
        # โลโก้ + ชื่อเพจ
        logo_path = "assets/logo.png"
        if os.path.exists(logo_path):
            with open(logo_path, "rb") as f:
                _b64 = base64.b64encode(f.read()).decode("utf-8")
            st.markdown(f"<img src='data:image/png;base64,{_b64}' class='login-logo' />", unsafe_allow_html=True)
        st.markdown("<div class='login-title'>🔮 Tarot Trader 💹</div>", unsafe_allow_html=True)

        # ฟอร์ม Login (ปุ่มอยู่กลางด้วย .login-btn-wrap)
        with st.form("login_form", clear_on_submit=False):
            u = st.text_input("Username", key="login_user")
            p = st.text_input("Password", type="password", key="login_pass")
            # ใหม่: จัดปุ่มให้อยู่กลางด้วยคอลัมน์ 2–1–2
            bL, bC, bR = st.columns([5, 6, 5])
            with bC:
                st.markdown("<div class='login-btn-wrap'>", unsafe_allow_html=True)
                login_clicked = st.form_submit_button("เข้าสู่ระบบ")
                st.markdown("</div>", unsafe_allow_html=True)

        if login_clicked:
            user = auth.verify_login(u, p)
            if user:
                st.session_state.auth = user
                st.rerun()
            else:
                st.error("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")

    st.markdown("</div>", unsafe_allow_html=True)  # .login-wrapper
    st.stop()

# ========================= Sidebar =========================
with st.sidebar:
    # โลโก้ + ชื่อเพจ
    if os.path.exists("assets/logo.png"):
        with open("assets/logo.png", "rb") as _f:
            _b64 = base64.b64encode(_f.read()).decode("utf-8")
            st.markdown(f"<img src='data:image/png;base64,{_b64}' class='sidebar-logo-circle' />", unsafe_allow_html=True)
    st.markdown("<div class='sidebar-title'>🔮 Tarot Trader 💹</div>", unsafe_allow_html=True)
    st.divider()

    # เมนู
    if "page" not in st.session_state:
        st.session_state.page = "money"

    if st.button("📊 Port", use_container_width=True):
        st.session_state.page = "port"
    if st.button("💰 Money Management", use_container_width=True):
        st.session_state.page = "money"
    if st.session_state.auth.get("role") == "admin":
        if st.button("👤 Users", use_container_width=True):
            st.session_state.page = "users"

    st.divider()
    # ผู้ใช้ + Logout (อยู่ใน sidebar)
    st.caption(f"ผู้ใช้: **{st.session_state.auth['username']}** ({st.session_state.auth['role']})")
    if st.button("🚪 ออกจากระบบ", use_container_width=True, type="primary"):
        st.session_state.auth = None
        st.rerun()

# ========================= Content =========================
page = st.session_state.page

if page == "port":
    st.header("📊 พอร์ตลงทุน")
    st.info("หน้านี้จะเติมภายหลัง")

elif page == "users":
    # เฉพาะแอดมินเท่านั้น
    if st.session_state.auth.get("role") != "admin":
        st.error("หน้าเฉพาะผู้ดูแลระบบ")
        st.stop()

    st.header("👤 จัดการผู้ใช้")

    c1, c2 = st.columns([1, 1])
    with c1:
        st.markdown("**สร้างผู้ใช้ใหม่**")
        nuser = st.text_input("Username ใหม่")
        npass = st.text_input("Password", type="password")
        nrole = st.selectbox("Role", ["user", "admin"])
        if st.button("สร้างผู้ใช้"):
            if not nuser or not npass:
                st.error("กรอกให้ครบ")
            else:
                if auth.create_user(nuser, npass, role=nrole):
                    st.success("สร้างผู้ใช้สำเร็จ")
                else:
                    st.error("ชื่อผู้ใช้ซ้ำหรือผิดพลาด")

    with c2:
        st.markdown("**เปลี่ยนรหัสผ่าน**")
        ch_user = st.text_input("Username ที่จะเปลี่ยนรหัส")
        ch_pass = st.text_input("รหัสผ่านใหม่", type="password")
        if st.button("เปลี่ยนรหัสผ่าน"):
            if not ch_user or not ch_pass:
                st.error("กรอกให้ครบ")
            else:
                if auth.change_password(ch_user, ch_pass):
                    st.success("เปลี่ยนรหัสผ่านสำเร็จ")
                else:
                    st.error("ไม่พบผู้ใช้")

    st.divider()
    st.markdown("**รายการผู้ใช้ทั้งหมด**")
    users = auth.list_users()
    if users:
        dfu = pd.DataFrame(users, columns=["id", "username", "role", "created_at"])
        st.dataframe(dfu, use_container_width=True, height=min(400, (len(dfu)+2)*33))
    else:
        st.info("ยังไม่มีผู้ใช้")

    st.divider()
    st.markdown("**ลบผู้ใช้**")
    del_user = st.text_input("Username ที่จะลบ")
    if st.button("ลบผู้ใช้"):
        if del_user == st.session_state.auth["username"]:
            st.error("ห้ามลบบัญชีที่กำลังใช้งาน")
        else:
            if auth.delete_user(del_user):
                st.success("ลบสำเร็จ")
            else:
                st.error("ไม่พบผู้ใช้หรือผิดพลาด")

else:
    # ---------------- Money Management ----------------
    st.header("💰 Money Management")
    # ใช้ renderer รวมจาก calc.py (แยกความรับผิดชอบชัดเจน)
    mm.render_money_management_page() 