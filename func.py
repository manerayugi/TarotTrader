# func.py
from __future__ import annotations

import os
import re
import base64
import mimetypes
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd
import streamlit as st


# ============================================================
# UI Helpers
# ============================================================

def show_centered_image(path: str, caption: Optional[str] = None, width: int = 480) -> None:
    """แสดงรูปกึ่งกลาง + แคปชันกึ่งกลาง (กรณีไม่พบไฟล์จะแสดง placeholder)"""
    def _data_uri(p: str) -> str:
        mime, _ = mimetypes.guess_type(p)
        if mime is None:
            ext = os.path.splitext(p)[1].lower()
            mime = {
                ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                ".png": "image/png", ".gif": "image/gif", ".webp": "image/webp",
            }.get(ext, "image/jpeg")
        with open(p, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        return f"data:{mime};base64,{b64}"

    if path and os.path.exists(path):
        src = _data_uri(path)
        img_html = (
            f"<img src='{src}' width='{width}' "
            "style='display:block;margin:0 auto;border-radius:8px;'/>"
        )
    else:
        h = int(width * 0.62)
        img_html = (
            f"<div style='display:inline-flex;width:{width}px;height:{h}px;"
            "align-items:center;justify-content:center;background:#1f2937;"
            "border:1px dashed #4b5563;border-radius:10px;color:#9ca3af;"
            "font-size:0.9rem;text-align:center;padding:10px;'>📷 ไม่พบรูปภาพ</div>"
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


def render_divider(width: int = 360) -> None:
    """เส้นคั่นบาง ๆ (ใช้คั่นหัวข้อย่อย)"""
    st.markdown(
        f"<div style='text-align:center;margin:14px 0;'>"
        f"<hr style='width:{width}px;border:1px solid #666;margin:8px auto;'/></div>",
        unsafe_allow_html=True,
    )


def render_divider_wide() -> None:
    """เส้นคั่นมาตรฐาน (ใช้ในส่วนสูตร/บล็อกสำคัญ)"""
    st.markdown(
        "<div style='text-align:center;margin:10px 0;'>"
        "<hr style='width:360px;border:1px solid #555;margin:8px auto;'/></div>",
        unsafe_allow_html=True,
    )


def render_latex_centered(expr: str) -> None:
    """แสดง LaTeX แบบจัดกึ่งกลาง"""
    st.markdown("<div style='text-align:center;'>", unsafe_allow_html=True)
    st.latex(expr)
    st.markdown("</div>", unsafe_allow_html=True)


def render_info_box(html: str) -> None:
    """กล่องสรุป/คำอธิบาย (รองรับ HTML/Markdown)"""
    st.markdown(
        f"""
        <div style="border:1px solid #666;padding:12px 14px;border-radius:10px;
                    background:#202020;color:#e5e7eb;">
          {html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_header(title: str, subtitle: str = "") -> None:
    """ส่วนหัวแบบมีไตเติลย่อย (สไตล์เดียวกันทั้งแอป)"""
    st.markdown(
        f"""
        <div style='display:flex;align-items:baseline;gap:10px;'>
          <h3 style='margin:0;'>{title}</h3>
          <span style='color:#aaa;font-size:0.9rem;'>{subtitle}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# สเปกสินค้า / Presets
# ============================================================

@dataclass(frozen=True)
class SymbolSpec:
    name: str
    contract_size: float = 100.0   # XAUUSD: 100
    min_lot: float = 0.01
    lot_step: float = 0.01
    price_point: float = 0.01      # 1 point = เท่ากับกี่หน่วยราคา
    pip_points: int = 10           # 1 pip = กี่ points


XAUUSD_SPEC = SymbolSpec(
    name="XAUUSD",
    contract_size=100.0,
    min_lot=0.01,
    lot_step=0.01,
    price_point=0.01,
    pip_points=10,
)

BTCUSD_SPEC = SymbolSpec(
    name="BTCUSD",
    contract_size=1.0,
    min_lot=0.01,
    lot_step=0.01,
    price_point=1.0,  # สมมุติ 1 point = 1 USD
    pip_points=1,
)

SYMBOL_PRESETS: Dict[str, SymbolSpec] = {
    "XAUUSD": XAUUSD_SPEC,
    "BTCUSD": BTCUSD_SPEC,
}


# ============================================================
# Data fetch (optional)
# ============================================================

def fetch_proxy_price(symbol_name: str) -> Optional[float]:
    """
    ดึงราคาโดยประมาณจาก yfinance (ถ้ามี)
    - XAUUSD → ใช้สัญลักษณ์ 'XAUT-USD' เป็น proxy
    """
    try:
        import yfinance as yf
    except Exception:
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
        return None
    return None


# ============================================================
# มูลค่าการเคลื่อนที่ / PnL utilities
# ============================================================

def dollars_per_point_per_lot(_: SymbolSpec) -> float:
    """นิยามพื้นฐาน: 1 lot เคลื่อนที่ 1 point = $1 (สอดคล้องหน้า MM)"""
    return 1.0


def dollars_per_pip_per_lot(spec: SymbolSpec) -> float:
    return dollars_per_point_per_lot(spec) * float(spec.pip_points)


def calc_pnl_usd(lots: float, move_points: float, spec: SymbolSpec) -> float:
    """คำนวณ P/L (USD) จากจำนวน lots และการเคลื่อนที่ (points)"""
    return float(lots) * float(move_points) * dollars_per_point_per_lot(spec)


# ============================================================
# Margin / Sizing
# ============================================================

def calc_margin_per_lot(price: float, leverage: float, spec: SymbolSpec) -> float:
    """Margin/lot ≈ (Contract × Price) / Leverage"""
    if leverage <= 0 or price <= 0:
        return 0.0
    return (spec.contract_size * price) / leverage


def calc_max_lot(
    balance: float,
    price: float,
    leverage: float,
    spec: SymbolSpec,
    buffer_fraction: float = 0.0
) -> float:
    """
    MaxLot ~ (Balance * Leverage) / (Price * ContractSize) × (1 - buffer_fraction)
    """
    if price <= 0 or leverage <= 0:
        return 0.0
    raw = (balance * leverage) / (price * spec.contract_size)
    raw *= max(0.0, 1.0 - float(buffer_fraction))
    return max(0.0, raw)


def calc_max_lot_theoretical(balance: float, leverage: float, price: float, spec: SymbolSpec) -> float:
    return calc_max_lot(balance, price, leverage, spec, buffer_fraction=0.0)


# ============================================================
# Risk sizing by stop distance
# ============================================================

def calc_optimal_lot_by_points_risk(balance: float, risk_percent: float, distance_points: float, spec: SymbolSpec) -> float:
    """
    Lot = (Balance * risk%) / (distance_points * $/point/lot)
    """
    if distance_points <= 0:
        return 0.0
    risk_amount = balance * (float(risk_percent) / 100.0)
    return risk_amount / (distance_points * dollars_per_point_per_lot(spec))


def calc_optimal_lot_by_points_allin(balance: float, distance_points: float, spec: SymbolSpec) -> float:
    """All-in mode: ใช้ balance ทั้งหมดเป็น risk_amount"""
    if distance_points <= 0:
        return 0.0
    risk_amount = balance
    return risk_amount / (distance_points * dollars_per_point_per_lot(spec))


def normalize_risk_value(balance: float, mode: str, val: float) -> Tuple[float, float]:
    """
    แปลงค่าความเสี่ยงเป็น (amount, pct)
    - mode == "%"  → val = เปอร์เซ็นต์
    - mode == "$"  → val = ดอลลาร์
    """
    balance = float(balance)
    if balance <= 0:
        return (0.0, 0.0)
    if mode == "%":
        amount = balance * (float(val) / 100.0)
        return (amount, float(val))
    amount = float(val)
    pct = (amount / balance) * 100.0 if balance > 0 else 0.0
    return (amount, pct)


def lots_for_stop_distances(risk_amount: float, stops_points: Iterable[int]) -> List[Tuple[int, float]]:
    """คืนรายการ (stop_points, lots) เพื่อทำตาราง quick-calc"""
    out: List[Tuple[int, float]] = []
    for p in stops_points:
        p = int(p)
        lots = (float(risk_amount) / float(p)) if p > 0 else 0.0
        out.append((p, lots))
    return out


# ============================================================
# GMK Signal Parser (utility)
# ============================================================

_SYMBOL_ALIASES = {
    "XAUUSD": "XAUUSD", "XAU": "XAUUSD", "GOLD": "XAUUSD", "GOLDUSD": "XAUUSD",
    "BTCUSD": "BTCUSD", "BTC": "BTCUSD", "XBTUSD": "BTCUSD",
}
_DIR_ALIASES = {"BUY": "LONG", "LONG": "LONG", "SELL": "SHORT", "SHORT": "SHORT"}

def _normalize_symbol(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    s = raw.upper().replace(".MG", "")
    return _SYMBOL_ALIASES.get(s, s if s in SYMBOL_PRESETS else None)


def parse_gmk_signal(text: str) -> Dict[str, Optional[object]]:
    """
    รองรับตัวอย่าง:
      XAUUSD.mg M5 SELL @3774.03
      SL=3785.34
      TP1=3771.77 ...
    """
    s = text.strip()
    u = s.upper()

    m_sym = re.search(r"\b([A-Z]{3,10})(?:\.MG)?\b", u)
    symbol = _normalize_symbol(m_sym.group(1)) if m_sym else None

    m_tf = re.search(r"\b(M\d+|H\d+|D\d+|W\d+)\b", u)
    timeframe = m_tf.group(1) if m_tf else None

    direction = None
    for k, v in _DIR_ALIASES.items():
        if re.search(rf"\b{k}\b", u):
            direction = v
            break

    m_entry = re.search(r"@\s*([0-9]+(?:\.[0-9]+)?)", u)
    if m_entry:
        entry = float(m_entry.group(1))
    else:
        m0 = re.search(r"\b([0-9]+(?:\.[0-9]+)?)\b", u)
        entry = float(m0.group(1)) if m0 else None

    msl = re.search(r"\bSL\s*=?\s*([0-9]+(?:\.[0-9]+)?)", u)
    sl = float(msl.group(1)) if msl else None

    tp_matches = re.findall(r"\bTP\d+\s*=?\s*([0-9]+(?:\.[0-9]+)?)", u)
    tps = [float(x) for x in tp_matches] if tp_matches else []
    if not tps:
        tp_single = re.findall(r"\bTP\s*=?\s*([0-9]+(?:\.[0-9]+)?)", u)
        tps = [float(x) for x in tp_single] if tp_single else []

    return {
        "symbol": symbol,
        "direction": direction,      # "LONG" | "SHORT"
        "entry": entry,
        "sl": sl,
        "tps": tps,                  # list[float]
        "timeframe": timeframe,
        "raw": text,
    }


# ============================================================
# ระยะ / จุด (points & pips)
# ============================================================

def points_distance(a: Optional[float], b: Optional[float], spec: SymbolSpec) -> float:
    """ระยะ (points) ระหว่างราคา a และ b"""
    if a is None or b is None:
        return 0.0
    return abs(float(a) - float(b)) / float(spec.price_point)


def tp_points_distance(entry: Optional[float], tp: Optional[float], spec: SymbolSpec) -> float:
    """ระยะ TP (points) จาก entry → tp"""
    if entry is None or tp is None:
        return 0.0
    return abs(float(tp) - float(entry)) / float(spec.price_point)


# ============================================================
# Grid builders
# ============================================================

def build_grid_entries(
    current_price: float,
    n_orders: int,
    step_points: float,
    price_point: float,
    side: str,
) -> List[float]:
    """
    สร้างราคาเข้าแบบกริดคงที่ N ไม้ (เว้นระยะเท่ากัน):
      - LONG  → ลดลงทีละ step
      - SHORT → เพิ่มขึ้นทีละ step
    """
    if n_orders <= 0:
        return []
    step_price = float(step_points) * float(price_point)
    sgn = -1.0 if side.upper() == "LONG" else 1.0
    return [round(float(current_price) + sgn * i * step_price, 2) for i in range(int(n_orders))]


def build_grid_levels(
    ref_price: float,
    n_orders: int,
    spacing_pts: int,
    direction: str = "LONG",
    point_value: float = 0.01
) -> List[float]:
    """อีกเวอร์ชัน: ใช้ชื่ออาร์กิวเมนต์สไตล์ GRD"""
    if n_orders <= 0:
        return []
    step = float(spacing_pts) * float(point_value)
    sgn = -1.0 if direction.upper().startswith("LONG") else 1.0
    return [round(ref_price + sgn * i * step, 2) for i in range(int(n_orders))]


def find_last_feasible_index(values: List[float], budget: float) -> Optional[int]:
    """คืน index สุดท้ายที่ค่า <= budget (ไว้ดูว่ามาร์จิ้นรวมไม่เกินทุนได้กี่ไม้)"""
    last: Optional[int] = None
    for i, v in enumerate(values):
        if v <= budget:
            last = i
    return last


def round_to_step(x: float, step: int) -> int:
    """ปัดค่าเป็น step ที่ต้องการ เช่น step=50 → 50, 100, 150,..."""
    if step <= 0:
        return int(round(x))
    return int(round(x / step) * step)


# ============================================================
# Data prep / Volatility (CSV โหมด)
# ============================================================

def ensure_ohlc_derived_columns(df: pd.DataFrame, point_value: float = 0.01) -> pd.DataFrame:
    """
    เติมคอลัมน์พื้นฐานที่ต้องใช้ (date, range_point, TR_point) สำหรับไฟล์ OHLC
    - รองรับคอลัมน์: date|time|Date|datetime|timestamp
    - คำนวณ range_point และ TR_point ให้อยู่ใน 'points'
    """
    df = df.copy()

    # date
    if "date" not in df.columns:
        if "time" in df.columns:
            df["date"] = pd.to_datetime(df["time"], unit="s")
        else:
            for cand in ["Date", "datetime", "timestamp"]:
                if cand in df.columns:
                    df["date"] = pd.to_datetime(df[cand])
                    break
            if "date" not in df.columns:
                raise ValueError("ไม่พบคอลัมน์วันที่ (date/time/Date/datetime/timestamp)")

    # ตรวจ OHLC
    required = {"high", "low", "close"}
    if not required.issubset(df.columns):
        miss = ", ".join(sorted(list(required - set(df.columns))))
        raise ValueError(f"ไฟล์ต้องมีคอลัมน์: {miss}")

    # range → points
    if "range" not in df.columns:
        df["range"] = df["high"] - df["low"]
    if "range_point" not in df.columns:
        df["range_point"] = (df["range"] / float(point_value)).astype(float)

    # True Range → points
    if "prev_close" not in df.columns:
        df["prev_close"] = df["close"].shift(1)
    tr = np.maximum.reduce([
        (df["high"] - df["low"]).abs(),
        (df["high"] - df["prev_close"]).abs(),
        (df["low"] - df["prev_close"]).abs()
    ])
    df["TR_point"] = (tr / float(point_value)).astype(float)
    return df


def compute_atr_points(df: pd.DataFrame, window: int = 14, method: str = "RMA") -> pd.Series:
    """
    คืนค่า ATR (หน่วย points)
    - method: 'SMA' | 'EMA' | 'RMA' (Wilder)
    """
    s = df["TR_point"]
    m = method.upper()
    if m == "EMA":
        return s.ewm(span=window, adjust=False).mean()
    if m == "RMA":
        return s.ewm(alpha=1 / window, adjust=False).mean()  # Wilder's smoothing
    return s.rolling(window=window, min_periods=1).mean()


# ============================================================
# Defaults
# ============================================================

DEFAULT_RISK_SET = [1, 2, 3, 4, 5, 10, 15, 20, 30, 50, 100]


# ============================================================
# Backward-compatible aliases (DEPRECATED names)
# ============================================================

# UI
center_image_safe   = show_centered_image
_hr                 = render_divider
_hrr                = render_divider_wide
center_latex        = render_latex_centered
info_box            = render_info_box
header              = render_header
hr                  = render_divider  # alias เก่า

# Data fetch
fetch_price_yf      = fetch_proxy_price

# Move value / PnL
value_per_point_per_lot = dollars_per_point_per_lot
value_per_pip_per_lot   = dollars_per_pip_per_lot
pnl_usd                 = calc_pnl_usd

# Margin/sizing
margin_per_1lot        = calc_margin_per_lot
max_lot                = calc_max_lot
maxlot_theoretical     = calc_max_lot_theoretical

# Risk sizing
optimal_lot_by_points_risk   = calc_optimal_lot_by_points_risk
optimal_lot_by_points_allin  = calc_optimal_lot_by_points_allin
loss_to_amount_and_pct       = normalize_risk_value
lots_from_stops              = lots_for_stop_distances

# Distances
_dist_points          = points_distance
_tp_points            = tp_points_distance

# Grid
grid_entries          = build_grid_entries
grid_levels           = build_grid_levels
last_feasible_index   = find_last_feasible_index
round_to              = round_to_step

# CSV / Volatility
ensure_ohlc_columns   = ensure_ohlc_derived_columns
atr_points            = compute_atr_points

# Defaults
_DEFAULT_RISK_SET     = DEFAULT_RISK_SET


# ============================================================
# Export list
# ============================================================

__all__ = [
    # UI
    "show_centered_image", "render_divider", "render_divider_wide",
    "render_latex_centered", "render_info_box", "render_header", "hr",
    # Spec/presets
    "SymbolSpec", "SYMBOL_PRESETS", "XAUUSD_SPEC", "BTCUSD_SPEC",
    # Data fetch
    "fetch_proxy_price",
    # Move value / pnl
    "dollars_per_point_per_lot", "dollars_per_pip_per_lot", "calc_pnl_usd",
    # Margin/sizing
    "calc_margin_per_lot", "calc_max_lot", "calc_max_lot_theoretical",
    # Risk sizing
    "calc_optimal_lot_by_points_risk", "calc_optimal_lot_by_points_allin",
    "normalize_risk_value", "lots_for_stop_distances",
    # Parser
    "parse_gmk_signal",
    # Distances
    "points_distance", "tp_points_distance",
    # Grid
    "build_grid_entries", "build_grid_levels", "find_last_feasible_index", "round_to_step",
    # CSV / Volatility
    "ensure_ohlc_derived_columns", "compute_atr_points",
    # Defaults
    "DEFAULT_RISK_SET",
    # Backward-compatible (optional to expose)
    "center_image_safe", "_hr", "_hrr", "center_latex", "info_box", "header",
    "fetch_price_yf", "value_per_point_per_lot", "value_per_pip_per_lot", "pnl_usd",
    "margin_per_1lot", "max_lot", "maxlot_theoretical",
    "optimal_lot_by_points_risk", "optimal_lot_by_points_allin",
    "loss_to_amount_and_pct", "lots_from_stops",
    "_dist_points", "_tp_points", "grid_entries", "grid_levels",
    "last_feasible_index", "round_to", "ensure_ohlc_columns", "atr_points",
    "_DEFAULT_RISK_SET",
]