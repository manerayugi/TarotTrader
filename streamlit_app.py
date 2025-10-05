# streamlit_app.py
import os, base64
import pandas as pd
import streamlit as st

# โมดูลภายในโปรเจกต์
import auth
import home
import port
import knowledge_index
import risk_money_index as mm  # มี render_page() และบังคับ public เฉพาะแท็บ 'การออก Lot'

# ========================= App Config =========================
st.set_page_config(page_title="🔮 Tarot Trader 💹", page_icon="🔮", layout="wide")

# ========================= AUTH Bootstrap =====================
auth.ensure_users_table()
first_run = auth.ensure_initial_admin()   # ยังไม่มี user เลย? ให้สร้างแอดมินครั้งแรก
auth.init_auth()                          # เตรียม st.session_state["auth"]

# ========================= Helpers ============================
def _sidebar_logo_and_title():
    if os.path.exists("assets/logo.png"):
        with open("assets/logo.png", "rb") as _f:
            _b64 = base64.b64encode(_f.read()).decode("utf-8")
        st.sidebar.markdown(
            f"<img src='data:image/png;base64,{_b64}' "
            "style='display:block;margin:4px auto 10px auto;width:84px;height:84px;"
            "border-radius:50%;object-fit:cover;border:2px solid #2f3651;'/>",
            unsafe_allow_html=True,
        )
    st.sidebar.markdown(
        "<div style='text-align:center;font-weight:700;'>🔮 Tarot Trader 💹</div>",
        unsafe_allow_html=True,
    )

def _goto(page: str):
    st.session_state.page = page
    st.rerun()

# ค่าเริ่มต้นเพจ
if "page" not in st.session_state:
    st.session_state.page = "home"

# ========================= Sidebar ============================
with st.sidebar:
    _sidebar_logo_and_title()
    st.divider()

    # ===== เมนู (ไปอยู่ที่ Sidebar ตามที่ขอ) =====
    st.markdown("**เมนู**")
    if st.button("🏠 Home", use_container_width=True):
        _goto("home")
    if st.button("📚 Trader’s Wisdom", use_container_width=True):
        _goto("knowledge")
    if st.button("💰 Money Management", use_container_width=True):
        _goto("mm")
    if st.button("📊 Port", use_container_width=True):
        _goto("port")

    # เฉพาะ Admin: Users
    auth_info = st.session_state.get("auth", {})
    if auth_info.get("logged_in") and auth_info.get("role") == "admin":
        if st.button("👤 Users", use_container_width=True):
            _goto("users")

    st.divider()

    # ===== ปุ่ม Login/Logout ไปอยู่ Sidebar =====
    if not auth_info.get("logged_in"):
        # ปุ่ม Login จะพาไปหน้า login (ตามโจทย์)
        if st.button("🔐 Login", use_container_width=True, type="primary"):
            _goto("login")
        st.caption("ยังไม่ได้เข้าสู่ระบบ")
    else:
        st.caption(f"ผู้ใช้: **{auth_info.get('username','?')}** ({auth_info.get('role','user')})")
        if st.button("🚪 ออกจากระบบ", use_container_width=True):
            st.session_state.auth = {"logged_in": False}
            _goto("home")

# ========================= Content Router =====================
page = st.session_state.page

# ---------- หน้า Login (กดจากปุ่มใน Sidebar) ----------
if page == "login":
    # ถ้าล็อกอินอยู่แล้ว ส่งกลับ Home
    if st.session_state.get("auth", {}).get("logged_in"):
        _goto("home")

    # CSS สำหรับหน้า Login (padding + ปุ่มกลาง + โลโก้/ไตเติล)
    st.markdown("""
    <style>
      .block-container{ padding-top: 1 !important; padding-bottom: 0 !important; }
      .login-logo{
        width:120px;height:120px;border-radius:50%;
        object-fit:cover;border:2px solid #2f3651;display:block;margin:0 auto 12px auto;
      }
      .login-title{ text-align:center; margin:6px 0 18px 0; font-size:1.25rem; }
      .login-btn-wrap{ display:flex; justify-content:center; align-items:center; width:100%; margin-top:12px; }
    </style>
    """, unsafe_allow_html=True)

    # ====== สร้าง Admin ครั้งแรก (ถ้ายังไม่มี user) ======
    if first_run:
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
                        st.success("สร้าง Admin สำเร็จ! ลงชื่อเข้าใช้ด้านล่าง")
                    else:
                        st.error("ชื่อผู้ใช้ซ้ำหรือผิดพลาด")

        st.divider()

    # ====== ฟอร์ม Login (จัดกลางแบบ 2–1–2 + ปุ่มกลาง) ======
    col_left, col_center, col_right = st.columns([2, 1.4, 2])
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
            bL, bC, bR = st.columns([5, 6, 5])
            with bC:
                st.markdown("<div class='login-btn-wrap'>", unsafe_allow_html=True)
                submitted = st.form_submit_button("เข้าสู่ระบบ")
                st.markdown("</div>", unsafe_allow_html=True)

        if submitted:
            user = auth.verify_login(u, p)
            if user:
                # เก็บสถานะให้สอดคล้องกับตัว router ที่ใช้อยู่
                st.session_state.auth = {"logged_in": True, **user}
                _goto("home")  # ✅ ล็อกอินสำเร็จ → กลับหน้า Home
            else:
                st.error("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")

# ---------- หน้า Home (สาธารณะ) ----------
elif page == "home":
    home.render_home_page()

# ---------- หน้า Trader’s Wisdom (สาธารณะ) ----------
elif page == "knowledge":
    knowledge_index.render_knowledge_index()

# ---------- หน้า Money Management (สาธารณะเฉพาะแท็บ 'การออก Lot') ----------
elif page == "mm":
    # ภายใน mm.render_page() จะใช้ auth.require_login_or_public("mm_sizing_only")
    mm.render_page()

# ---------- หน้า Port (private ทั้งหน้า) ----------
elif page == "port":
    if auth.require_login_or_public("private"):  # ไม่ล็อกอินจะแจ้งเตือนและไม่เรนเดอร์
        st.subheader("📊 Port")
        port.render_port_page()

# ---------- หน้า Users (admin only) ----------
elif page == "users":
    if not (st.session_state.auth.get("logged_in") and st.session_state.auth.get("role") == "admin"):
        st.error("หน้าเฉพาะผู้ดูแลระบบ")
    else:
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
            if del_user == st.session_state.auth.get("username"):
                st.error("ห้ามลบบัญชีที่กำลังใช้งาน")
            else:
                if auth.delete_user(del_user):
                    st.success("ลบสำเร็จ")
                else:
                    st.error("ไม่พบผู้ใช้หรือผิดพลาด")

# ---------- อื่น ๆ ----------
else:
    st.info("Coming soon…")