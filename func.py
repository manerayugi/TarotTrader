from dataclasses import dataclass
from math import floor
from typing import List, Tuple, Optional

# ======================= Symbol Specs =======================

@dataclass
class SymbolSpec:
    symbol: str
    contract_size: float   # ปริมาณต่อ 1 lot (ทอง = 100 oz)
    price_point: float     # การเปลี่ยนแปลงของ "ราคา" ต่อ 1 point (ทอง = 0.01)
    pip_points: int        # 1 pip = กี่ points (ทอง = 10)
    min_lot: float
    lot_step: float

# สำหรับ XAUUSD ตามนิยามที่ตกลง: 
# 1 lot → 1 point = $1  ⇒ contract_size * price_point = 1  (100 * 0.01 = 1)
XAUUSD_SPEC = SymbolSpec(
    symbol="XAUUSD",
    contract_size=100.0,
    price_point=0.01,
    pip_points=10,
    min_lot=0.01,
    lot_step=0.01,
)

# เผื่อรองรับอนาคต (ใส่เพิ่มได้)
SYMBOL_PRESETS = {
    "XAUUSD": XAUUSD_SPEC,
    # "XAGUSD": SymbolSpec(...),
    # "EURUSD": SymbolSpec(symbol="EURUSD", contract_size=100000, price_point=0.0001, pip_points=10, min_lot=0.01, lot_step=0.01),
}

# ======================= Rounding & Values =======================

def round_lot(lots: float, spec: SymbolSpec) -> float:
    """ปัด lot ตาม step/min ของสัญลักษณ์"""
    if lots < spec.min_lot:
        return 0.0
    steps = floor((lots - spec.min_lot) / spec.lot_step + 1e-9)
    return round(spec.min_lot + steps * spec.lot_step, 4)

def value_per_point_per_lot(spec: SymbolSpec) -> float:
    """$ ต่อ 1 point ต่อ 1 lot (ทอง = 100 * 0.01 = $1)"""
    return spec.contract_size * spec.price_point

def value_per_pip_per_lot(spec: SymbolSpec) -> float:
    """$ ต่อ 1 pip ต่อ 1 lot (ทอง = $1 * 10 = $10)"""
    return value_per_point_per_lot(spec) * spec.pip_points

# ======================= Margin & MaxLot =======================

def margin_per_1lot(price: float, leverage: float, spec: SymbolSpec) -> float:
    """
    Margin/lot เชิงปฏิบัติ ≈ (contract_size * price) / leverage
    หมายเหตุ: อาจต่างเล็กน้อยตามโบรก/บัญชี
    """
    if leverage <= 0 or price <= 0:
        return 0.0
    return (spec.contract_size * price) / leverage

def max_lot(balance: float, price: float, leverage: float, spec: SymbolSpec, buffer_pct: float = 0.0) -> float:
    """
    MaxLot โดยกัน free margin ไว้ตาม buffer_pct (0.0 = ไม่กัน)
    """
    m1 = margin_per_1lot(price, leverage, spec)
    if m1 <= 0:
        return 0.0
    usable = max(0.0, balance * (1.0 - buffer_pct))
    return round_lot(usable / m1, spec)

def maxlot_theoretical(balance: float, leverage: float, price: float, spec: SymbolSpec) -> float:
    """
    สูตรที่ผู้ใช้ยืนยัน: MaxLot = (ทุน * Leverage) / (Price * ContractSize)
    (เป็นเชิงทฤษฎี ไม่กัน buffer)
    """
    if balance <= 0 or leverage <= 0 or price <= 0 or spec.contract_size <= 0:
        return 0.0
    return (balance * leverage) / (price * spec.contract_size)

# ======================= Optimal Lot (จากระยะ) =======================

def optimal_lot_by_points_risk(balance: float, risk_percent: float, distance_points: float, spec: SymbolSpec) -> float:
    """
    lot = (balance * risk%) / (distance_points * $/point/lot)
    """
    vpp = value_per_point_per_lot(spec)
    if distance_points <= 0 or vpp <= 0 or risk_percent <= 0 or balance <= 0:
        return 0.0
    risk_amount = balance * (risk_percent / 100.0)
    return round_lot(risk_amount / (distance_points * vpp), spec)

def optimal_lot_by_points_allin(balance: float, distance_points: float, spec: SymbolSpec) -> float:
    """
    lot = balance / (distance_points * $/point/lot)
    (โหมดเทียบค่า ใช้ทุนทั้งก้อนเป็นความเสี่ยง)
    """
    vpp = value_per_point_per_lot(spec)
    if distance_points <= 0 or vpp <= 0 or balance <= 0:
        return 0.0
    return round_lot(balance / (distance_points * vpp), spec)

def pnl_usd(lots: float, move_points: float, spec: SymbolSpec) -> float:
    """คำนวณกำไร/ขาดทุน $ จากจำนวนจุดที่เคลื่อนที่"""
    return lots * move_points * value_per_point_per_lot(spec)

# ======================= SL → Lot Helpers =======================

def loss_to_amount_and_pct(balance: float, mode: str, value: float) -> Tuple[float, float]:
    """
    mode: '%' หรือ '$'
    return: (risk_amount_usd, loss_pct_of_balance)
    """
    if balance <= 0:
        return (0.0, 0.0)
    if mode == "%":
        risk_amount = balance * (value / 100.0)
        loss_pct = value
    else:
        risk_amount = value
        loss_pct = (value / balance) * 100.0
    return (risk_amount, loss_pct)

def lots_from_stops(risk_amount: float, stops: List[int]) -> List[Tuple[int, float]]:
    """
    สำหรับแต่ละ stop (points): lot = ทุนที่มี / จำนวนจุด
    """
    out: List[Tuple[int, float]] = []
    for pts in stops:
        lots = (risk_amount / pts) if pts > 0 else 0.0
        out.append((pts, lots))
    return out

# ======================= Price Fetch (demo) =======================

def fetch_price_yf(symbol_hint: str) -> Optional[float]:
    """
    พยายามดึงราคาจาก yfinance:
      - ใช้ 'XAUT-USD' ก่อน (ใกล้ราคาทองจริงตามที่ตกลง)
      - จากนั้นลอง 'XAUUSD=X' และ 'GC=F' เป็นสำรอง
    หากไม่สำเร็จ คืน None (ให้กรอกเองใน UI)
    """
    try:
        import yfinance as yf
        hint = symbol_hint.upper()
        candidates = []
        if hint == "XAUUSD":
            candidates = ["XAUT-USD", "XAUUSD=X", "GC=F"]
        else:
            # สำหรับสัญลักษณ์อื่นให้ลองตรง ๆ
            candidates = [hint]

        for tkr in candidates:
            data = yf.Ticker(tkr).history(period="1d")
            if not data.empty:
                return float(data["Close"].iloc[-1])
        return None
    except Exception:
        return None

# ======== Auth (SQLite + PBKDF2-HMAC) ========
import sqlite3, os, hashlib, secrets, time
from typing import Optional, Dict, Any

DB_PATH = os.path.join(os.path.dirname(__file__), "users.db")

def _conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def ensure_db():
    with _conn() as con:
        con.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash BLOB NOT NULL,
            salt BLOB NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            created_at REAL NOT NULL
        )
        """)
        con.commit()

def _hash_pw(password: str, salt: bytes) -> bytes:
    # 200k rounds PBKDF2-HMAC-SHA256
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)

def create_user(username: str, password: str, role: str = "user") -> bool:
    salt = secrets.token_bytes(16)
    pw_hash = _hash_pw(password, salt)
    try:
        with _conn() as con:
            con.execute("INSERT INTO users(username,password_hash,salt,role,created_at) VALUES(?,?,?,?,?)",
                        (username, pw_hash, salt, role, time.time()))
            con.commit()
        return True
    except sqlite3.IntegrityError:
        return False

def verify_login(username: str, password: str) -> Optional[Dict[str, Any]]:
    with _conn() as con:
        cur = con.execute("SELECT id,username,password_hash,salt,role FROM users WHERE username=?", (username,))
        row = cur.fetchone()
    if not row:
        return None
    uid, uname, pw_hash_db, salt, role = row
    if _hash_pw(password, salt) == pw_hash_db:
        return {"id": uid, "username": uname, "role": role}
    return None

def list_users() -> list[tuple]:
    with _conn() as con:
        cur = con.execute("SELECT id,username,role,datetime(created_at,'unixepoch') FROM users ORDER BY id")
        return cur.fetchall()

def delete_user(username: str) -> bool:
    with _conn() as con:
        cur = con.execute("DELETE FROM users WHERE username=?", (username,))
        con.commit()
        return cur.rowcount > 0

def change_password(username: str, new_password: str) -> bool:
    salt = secrets.token_bytes(16)
    pw_hash = _hash_pw(new_password, salt)
    with _conn() as con:
        cur = con.execute("UPDATE users SET password_hash=?, salt=? WHERE username=?", (pw_hash, salt, username))
        con.commit()
        return cur.rowcount > 0

def ensure_initial_admin() -> bool:
    """ถ้ายังไม่มีผู้ใช้เลย ให้คืน True เพื่อให้หน้าแรกสร้าง admin ได้"""
    with _conn() as con:
        cur = con.execute("SELECT COUNT(*) FROM users")
        n = cur.fetchone()[0]
    return n == 0