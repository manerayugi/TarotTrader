# auth.py
from __future__ import annotations
from typing import Optional, Dict, List

import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
import bcrypt
import datetime

# ---------------------------------------------
# CONFIG
# ---------------------------------------------
PUBLIC_PAGES = {"home", "knowledge", "mm_sizing_only"}  # เพจที่ไม่ต้องล็อกอินก็เข้าได้
FB_LINK = "https://facebook.com/TarotTrader162"

# ---------------------------------------------
# DB ENGINE (ใช้ของเดิม)
# ---------------------------------------------
_ENGINE: Engine | None = None

def get_engine() -> Engine:
    """
    ใช้ค่า connection จาก Streamlit secrets:
    [neon]
    connection_string = "postgresql://USER:PASS@HOST/DB?sslmode=require"
    """
    global _ENGINE
    if _ENGINE is None:
        conn = st.secrets["neon"]["connection_string"]
        _ENGINE = create_engine(conn, pool_pre_ping=True)
    return _ENGINE

# ---------------------------------------------
# SCHEMA + BOOTSTRAP
# ---------------------------------------------
def ensure_users_table() -> None:
    with get_engine().begin() as conn:
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS users(
            id SERIAL PRIMARY KEY,
            username VARCHAR(64) UNIQUE NOT NULL,
            password_hash VARCHAR(200) NOT NULL,
            role VARCHAR(20) NOT NULL DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """))

def ensure_initial_admin() -> bool:
    """
    True = ยังไม่มีผู้ใช้ → UI ควรแสดงฟอร์มสร้างแอดมินครั้งแรก
    """
    ensure_users_table()
    with get_engine().connect() as c:
        n = c.execute(text("SELECT COUNT(*) FROM users")).scalar_one()
    return int(n) == 0

# ---------------------------------------------
# PASSWORD HELPERS
# ---------------------------------------------
def _hash_password(raw: str) -> str:
    return bcrypt.hashpw(raw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def _check_password(raw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(raw.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False

# ---------------------------------------------
# CRUD (เหมือนเดิม)
# ---------------------------------------------
def create_user(username: str, password: str, role: str = "user") -> bool:
    if not username.strip() or not password:
        return False
    try:
        with get_engine().begin() as conn:
            conn.execute(
                text("INSERT INTO users (username, password_hash, role) VALUES (:u,:p,:r)"),
                {"u": username.strip(), "p": _hash_password(password), "r": role}
            )
        return True
    except Exception as e:
        print("create_user error:", e)
        return False

def change_password(username: str, new_password: str) -> bool:
    if not new_password:
        return False
    with get_engine().begin() as conn:
        res = conn.execute(
            text("UPDATE users SET password_hash=:p WHERE username=:u"),
            {"u": username.strip(), "p": _hash_password(new_password)}
        )
    return res.rowcount > 0

def delete_user(username: str) -> bool:
    with get_engine().begin() as conn:
        res = conn.execute(text("DELETE FROM users WHERE username=:u"), {"u": username.strip()})
    return res.rowcount > 0

def get_user(username: str) -> Optional[Dict]:
    with get_engine().connect() as c:
        row = c.execute(
            text("SELECT id, username, password_hash, role, created_at FROM users WHERE username=:u"),
            {"u": username.strip()}
        ).mappings().first()
    return dict(row) if row else None

def verify_login(username: str, password: str) -> Optional[Dict]:
    u = get_user(username)
    if not u:
        return None
    if _check_password(password, u["password_hash"]):
        return {"id": u["id"], "username": u["username"], "role": u["role"]}
    return None

def list_users() -> List[tuple]:
    with get_engine().connect() as c:
        rows = c.execute(text("SELECT id, username, role, created_at FROM users ORDER BY id ASC")).all()
    return [tuple(r) for r in rows]

# ---------------------------------------------
# SESSION & UI HELPERS (ใหม่)
# ---------------------------------------------
def init_auth() -> None:
    """เตรียม session_state สำหรับ auth"""
    if "auth" not in st.session_state:
        st.session_state.auth = {
            "logged_in": False,
            "user": None,     # {"id","username","role"}
            "at": None,       # login time
        }

def is_logged_in() -> bool:
    init_auth()
    return bool(st.session_state.auth["logged_in"])

def current_user() -> Optional[Dict]:
    init_auth()
    return st.session_state.auth["user"]

def has_role(*roles: str) -> bool:
    init_auth()
    user = st.session_state.auth["user"]
    if not user:
        return False
    return user.get("role") in roles

def logout():
    init_auth()
    st.session_state.auth = {"logged_in": False, "user": None, "at": None}
    st.rerun()

# ---------------------------------------------
# UI BLOCKS
# ---------------------------------------------
def _show_login_required():
    st.markdown(
        f"""
        <div style='border:2px dashed #eab308; padding:16px; border-radius:12px; background:#18181b;'>
          <h3 style='margin:0 0 8px 0;'>⚠️ กรุณาล็อกอินเพื่อเข้าถึงหน้านี้</h3>
          <div>หรือติดต่อ <a href='{FB_LINK}' target='_blank'>FB: Tarot Trader</a> เพื่อขอสิทธิ์เข้าถึง</div>
        </div>
        """,
        unsafe_allow_html=True
    )

def require_login_or_public(allow_flag: str) -> bool:
    """
    - allow_flag = "home" | "knowledge" | "mm_sizing_only" | "private"
    - ถ้าอยู่ใน PUBLIC_PAGES → ผ่านเสมอ
    - ถ้าไม่ใช่ public และยังไม่ล็อกอิน → โชว์เตือนและบล็อค
    """
    init_auth()
    if allow_flag in PUBLIC_PAGES:
        return True
    if is_logged_in():
        return True
    _show_login_required()
    return False

def login_box():
    """
    กล่องล็อกอินกะทัดรัด:
    - ถ้ายังไม่ล็อกอิน → แสดงฟอร์ม
    - ถ้าล็อกอินแล้ว → แสดงสถานะ + ปุ่มออกจากระบบ
    - ฟอร์มจะมี “สร้างแอดมินครั้งแรก” อัตโนมัติ หาก DB ว่าง
    """
    init_auth()

    if is_logged_in():
        left, right = st.columns([4,1])
        with left:
            u = current_user()
            st.caption(f"👤 {u['username']} ({u['role']})")
        with right:
            if st.button("ออกจากระบบ"):
                logout()
        return

    # แถบหัวเล็ก ๆ
    st.markdown(
        "<div style='padding:8px 10px; border:1px solid #333; border-radius:10px; margin:8px 0;'>"
        "<b>🔐 Login</b> เพื่อเข้าถึงฟีเจอร์ทั้งหมด</div>",
        unsafe_allow_html=True
    )

    # ถ้ายังไม่มีผู้ใช้ → ฟอร์มสร้างแอดมินครั้งแรก
    try:
        need_admin = ensure_initial_admin()
    except Exception as e:
        need_admin = False
        st.error("เชื่อมต่อฐานข้อมูลไม่สำเร็จ โปรดตรวจ secrets[\"neon\"][\"connection_string\"]")
        st.stop()

    if need_admin:
        st.warning("ยังไม่มีผู้ใช้ในระบบ สร้างผู้ดูแลระบบ (admin) ครั้งแรก")
        u = st.text_input("Username (อีเมลหรือชื่อผู้ใช้)", key="__admu")
        p1 = st.text_input("รหัสผ่าน", type="password", key="__admp1")
        p2 = st.text_input("ยืนยันรหัสผ่าน", type="password", key="__admp2")
        if st.button("สร้างแอดมิน"):
            if not u.strip() or not p1 or p1 != p2:
                st.error("กรุณากรอกข้อมูลให้ครบ และรหัสผ่านตรงกัน")
            else:
                if create_user(u.strip(), p1, role="admin"):
                    st.success("สร้างแอดมินสำเร็จ! กรุณาเข้าสู่ระบบ")
                    st.rerun()
                else:
                    st.error("สร้างผู้ใช้ไม่สำเร็จ (อาจมีชื่อผู้ใช้อยู่แล้ว)")
        return

    # ฟอร์มล็อกอินปกติ
    c1, c2, c3 = st.columns([1,1,2])
    with c1:
        username = st.text_input("Username", key="__login_user")
    with c2:
        password = st.text_input("Password", type="password", key="__login_pass")
    with c3:
        st.write("")  # spacer
        if st.button("เข้าสู่ระบบ", type="primary"):
            user = verify_login(username.strip(), password)
            if user:
                st.session_state.auth["logged_in"] = True
                st.session_state.auth["user"] = user
                st.session_state.auth["at"] = datetime.datetime.utcnow().isoformat()
                st.success("เข้าสู่ระบบสำเร็จ")
                st.rerun()
            else:
                st.error("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")