from __future__ import annotations
from typing import Optional, List, Dict

import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
import bcrypt

_ENGINE: Engine | None = None


# ---------- Engine ----------
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


# ---------- Bootstrap / Schema ----------
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
    True = ยังไม่มีผู้ใช้ → ให้หน้า UI แสดงฟอร์มสร้างแอดมินครั้งแรก
    """
    ensure_users_table()
    with get_engine().connect() as c:
        n = c.execute(text("SELECT COUNT(*) FROM users")).scalar_one()
    return int(n) == 0


# ---------- Password helpers ----------
def _hash_password(raw: str) -> str:
    return bcrypt.hashpw(raw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _check_password(raw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(raw.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


# ---------- CRUD ----------
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