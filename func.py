# func.py
from __future__ import annotations
import os, base64, mimetypes
import streamlit as st
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple
import re

def center_image_safe(path: str, caption: str = None, width: int = 480):
    """แสดงรูปแบบกึ่งกลาง + แคปชันกึ่งกลาง (เรนเดอร์ครั้งเดียว)"""
    def _data_uri(p: str):
        mime, _ = mimetypes.guess_type(p)
        if mime is None:
            ext = os.path.splitext(p)[1].lower()
            mime = {
                ".jpg": "image/jpeg", 
                ".jpeg": "image/jpeg",
                ".png": "image/png", 
                ".gif": "image/gif", 
                ".webp": "image/webp",
            }.get(ext, "image/jpeg")
        with open(p, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        return f"data:{mime};base64,{b64}"

    # สร้าง HTML เดียวที่มีทั้งรูปและแคปชันภายใน <figure>
    if path and os.path.exists(path):
        src = _data_uri(path)
        img_html = f"<img src='{src}' width='{width}' style='display:block;margin:0 auto;border-radius:8px;'/>"
    else:
        h = int(width * 0.62)
        img_html = (
            f"<div style='display:inline-flex;width:{width}px;height:{h}px;"
            "align-items:center;justify-content:center;background:#1f2937;"
            "border:1px dashed #4b5563;border-radius:10px;color:#9ca3af;"
            "font-size:0.9rem;text-align:center;padding:10px;'>"
            f"📷 ไม่พบรูปภาพ</div>"
            # f"📷 ไม่พบรูปภาพ<br><small>{path}</small></div>"
        )

    caption_html = (
        f"<figcaption style='font-size:0.9rem;color:#9ca3af;margin-top:6px;'>{caption}</figcaption>"
        if caption else ""
    )

    st.markdown(
        "<div style='display:flex;justify-content:center;margin:16px 0;'>"
        f"<figure style='margin:0;text-align:center'>{img_html}{caption_html}</figure>"
        "</div>",
        unsafe_allow_html=True,
    )

# ดึงราคาแบบ optional
try:
    import yfinance as yf
except Exception:
    yf = None


# ========== สเปกสินค้า ==========
@dataclass(frozen=True)
class SymbolSpec:
    name: str
    contract_size: float = 100.0   # XAUUSD ใช้ 100
    min_lot: float = 0.01
    lot_step: float = 0.01
    price_point: float = 0.01      # ใช้เพื่อแสดงผล "1 point = ราคาเปลี่ยนเท่าไร"
    pip_points: int = 10           # 1 pip = 10 points


XAUUSD_SPEC = SymbolSpec(
    name="XAUUSD",
    contract_size=100.0,
    min_lot=0.01,
    lot_step=0.01,
    price_point=0.01,
    pip_points=10
)

# BTCUSD: สมมุติ 1 point = 1 USD, contract 1
BTCUSD_SPEC = SymbolSpec(
    name="BTCUSD",
    contract_size=1.0,
    min_lot=0.01,
    lot_step=0.01,
    price_point=1.0,
    pip_points=1
)

SYMBOL_PRESETS: Dict[str, SymbolSpec] = {
    "XAUUSD": XAUUSD_SPEC,
    "BTCUSD": BTCUSD_SPEC,
}


# ========== ดึงราคา ==========
def fetch_price_yf(symbol_name: str) -> Optional[float]:
    """
    ดึงราคาโดยประมาณจาก yfinance
    - ทองคำ: ใช้ XAUT-USD
    """
    if yf is None:
        return None
    mapping = {"XAUUSD": "XAUT-USD"}
    ticker = mapping.get(symbol_name)
    if not ticker:
        return None

    try:
        tk = yf.Ticker(ticker)

        fast = getattr(tk, "fast_info", None)
        if isinstance(fast, dict):
            lp = fast.get("last_price")
            if lp:
                return float(lp)

        hist = tk.history(period="1d")
        if hist is not None and not hist.empty:
            return float(hist["Close"].iloc[-1])
    except Exception:
        pass
    return None


# ========== การประเมินมูลค่าการเคลื่อนที่ ==========
def value_per_point_per_lot(_: SymbolSpec) -> float:
    """สมมุติ 1 lot เคลื่อนที่ 1 point = $1"""
    return 1.0


def value_per_pip_per_lot(spec: SymbolSpec) -> float:
    return value_per_point_per_lot(spec) * float(spec.pip_points)


# ========== Margin / Position sizing ==========
def margin_per_1lot(price: float, leverage: float, spec: SymbolSpec) -> float:
    """Margin/lot ≈ (Contract × Price) / Leverage"""
    if leverage <= 0 or price <= 0:
        return 0.0
    return (spec.contract_size * price) / leverage


def max_lot(balance: float, price: float, leverage: float, spec: SymbolSpec, buffer_fraction: float = 0.0) -> float:
    """Maxlot = (ทุน * Leverage) / (Price * ContractSize) × (1 - buffer)"""
    if price <= 0 or leverage <= 0:
        return 0.0
    raw = (balance * leverage) / (price * spec.contract_size)
    raw *= max(0.0, 1.0 - float(buffer_fraction))
    return max(0.0, raw)


def maxlot_theoretical(balance: float, leverage: float, price: float, spec: SymbolSpec) -> float:
    return max_lot(balance, price, leverage, spec, buffer_fraction=0.0)


# ========== PnL / Optimal lots ==========
def pnl_usd(lots: float, move_points: float, spec: SymbolSpec) -> float:
    return float(lots) * float(move_points) * value_per_point_per_lot(spec)


def optimal_lot_by_points_risk(balance: float, risk_percent: float, distance_points: float, spec: SymbolSpec) -> float:
    """
    lot = (ทุนที่ยอมเสีย) / (ระยะ(points) × $/point/lot)
    โดย ทุนที่ยอมเสีย = balance * (risk_percent/100)
    """
    if distance_points <= 0:
        return 0.0
    risk_amount = balance * (float(risk_percent) / 100.0)
    return risk_amount / (distance_points * value_per_point_per_lot(spec))


def optimal_lot_by_points_allin(balance: float, distance_points: float, spec: SymbolSpec) -> float:
    """โหมด All-in ใช้ balance ทั้งหมดเป็น risk_amount"""
    if distance_points <= 0:
        return 0.0
    risk_amount = balance
    return risk_amount / (distance_points * value_per_point_per_lot(spec))


# ========== Helpers (SL → Lot) ==========
def loss_to_amount_and_pct(balance: float, mode: str, val: float) -> Tuple[float, float]:
    """
    - mode == "%"  -> val = เปอร์เซ็นต์  → คืน (amount, pct)
    - mode == "$"  -> val = ดอลล่าร์     → คืน (amount, pct)
    """
    balance = float(balance)
    if balance <= 0:
        return (0.0, 0.0)
    if mode == "%":
        amount = balance * (float(val) / 100.0)
        return (amount, float(val))
    else:
        amount = float(val)
        pct = (amount / balance) * 100.0 if balance > 0 else 0.0
        return (amount, pct)


def lots_from_stops(risk_amount: float, stops_points: Iterable[int]) -> List[Tuple[int, float]]:
    """คืนรายการ (stop_points, lots) สำหรับสร้างตาราง"""
    out: List[Tuple[int, float]] = []
    for p in stops_points:
        p = int(p)
        lots = (float(risk_amount) / float(p)) if p > 0 else 0.0
        out.append((p, lots))
    return out


# ========== GMK Signal Parser ==========
_SYMBOL_ALIASES = {
    "XAUUSD": "XAUUSD",
    "XAU": "XAUUSD",
    "GOLD": "XAUUSD",
    "GOLDUSD": "XAUUSD",
    "BTCUSD": "BTCUSD",
    "BTC": "BTCUSD",
    "XBTUSD": "BTCUSD",
}
_DIR_ALIASES = {"BUY": "LONG", "LONG": "LONG", "SELL": "SHORT", "SHORT": "SHORT"}

def _norm_symbol(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    s = raw.upper().replace(".MG", "")
    return _SYMBOL_ALIASES.get(s, s if s in SYMBOL_PRESETS else None)

def parse_gmk_signal(text: str):
    """
    รองรับตัวอย่าง:
    XAUUSD.mg M5 SELL @3774.03
    SL=3785.34
    TP1=3771.77 ...
    """
    s = text.strip()
    u = s.upper()

    m_sym = re.search(r"\b([A-Z]{3,10})(?:\.MG)?\b", u)
    symbol = _norm_symbol(m_sym.group(1)) if m_sym else None

    m_tf = re.search(r"\b(M\d+|H\d+|D\d+|W\d+)\b", u)
    timeframe = m_tf.group(1) if m_tf else None

    direction = None
    for k, v in _DIR_ALIASES.items():
        if re.search(rf"\b{k}\b", u):
            direction = v
            break

    entry = None
    m_entry = re.search(r"@\s*([0-9]+(?:\.[0-9]+)?)", u)
    if m_entry:
        entry = float(m_entry.group(1))
    else:
        m0 = re.search(r"\b([0-9]+(?:\.[0-9]+)?)\b", u)
        entry = float(m0.group(1)) if m0 else None

    sl = None
    msl = re.search(r"\bSL\s*=?\s*([0-9]+(?:\.[0-9]+)?)", u)
    if msl:
        sl = float(msl.group(1))

    tp_matches = re.findall(r"\bTP\d+\s*=?\s*([0-9]+(?:\.[0-9]+)?)", u)
    tps = [float(x) for x in tp_matches] if tp_matches else []
    if not tps:
        tp_single = re.findall(r"\bTP\s*=?\s*([0-9]+(?:\.[0-9]+)?)", u)
        tps = [float(x) for x in tp_single] if tp_single else []

    return {
        "symbol": symbol,
        "direction": direction,    # "LONG" | "SHORT"
        "entry": entry,
        "sl": sl,
        "tps": tps,                # list[float]
        "timeframe": timeframe,
        "raw": text,
    }


# ========== ระยะ (points) ==========
def _dist_points(a: Optional[float], b: Optional[float], spec: SymbolSpec) -> float:
    if a is None or b is None:
        return 0.0
    return abs(float(a) - float(b)) / float(spec.price_point)

def _tp_points(entry: Optional[float], tp: Optional[float], spec: SymbolSpec) -> float:
    if entry is None or tp is None:
        return 0.0
    return abs(float(tp) - float(entry)) / float(spec.price_point)


# ========== ค่ามาตรฐานอื่น ==========
_DEFAULT_RISK_SET = [1, 2, 3, 4, 5, 10, 15, 20, 30, 50, 100]

def _hr(width: int = 360):
    st.markdown(
        f"""
        <div style='text-align:center; margin:14px 0;'>
          <hr style='width: {width}px; border: 1px solid #666; margin: 8px auto;'/>
        </div>
        """,
        unsafe_allow_html=True
    )

def _hrr():
    st.markdown(
        "<div style='text-align:center; margin:10px 0;'>"
        "<hr style='width:360px; border:1px solid #555; margin:8px auto;'/>"
        "</div>",
        unsafe_allow_html=True
    )

# --- ใหม่: ใช้ได้ทุกหน้า ---
def center_latex(expr: str) -> None:
    """แสดง LaTeX แบบจัดกลาง (ใช้ซ้ำได้ทุกหน้า)"""
    st.markdown("<div style='text-align:center;'>", unsafe_allow_html=True)
    st.latex(expr)
    st.markdown("</div>", unsafe_allow_html=True)

def info_box(html: str) -> None:
    """กล่องข้อความสรุป/คำอธิบาย (รับ HTML markdown)"""
    st.markdown(
        f"""
        <div style="border:1px solid #666;padding:12px 14px;border-radius:10px;
                    background:#202020;color:#e5e7eb;">
          {html}
        </div>
        """,
        unsafe_allow_html=True,
    )

def grid_entries(
    current_price: float,
    n_orders: int,
    step_points: float,
    price_point: float,
    side: str,
) -> List[float]:
    """
    สร้างราคาเข้าแบบกริดคงที่ N ไม้ เว้นระยะเท่ากัน:
      - side="LONG"  → ลดลงทีละ step
      - side="SHORT" → เพิ่มขึ้นทีละ step
    """
    if n_orders <= 0:
        return []
    step_price = float(step_points) * float(price_point)
    sgn = -1.0 if side.upper() == "LONG" else 1.0
    return [round(float(current_price) + sgn * i * step_price, 2) for i in range(n_orders)]