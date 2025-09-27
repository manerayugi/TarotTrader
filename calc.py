from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

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

SYMBOL_PRESETS: Dict[str, SymbolSpec] = {
    "XAUUSD": XAUUSD_SPEC,
}


# ========== ดึงราคา ==========
def fetch_price_yf(symbol_name: str) -> Optional[float]:
    """
    ดึงราคาโดยประมาณจาก yfinance
    - สำหรับทองคำ: ใช้ XAUT-USD (ราคาค่อนข้างใกล้เคียงกับตลาด)
    """
    if yf is None:
        return None
    mapping = {"XAUUSD": "XAUT-USD"}
    ticker = mapping.get(symbol_name)
    if not ticker:
        return None

    try:
        tk = yf.Ticker(ticker)

        # ทางเร็ว
        fast = getattr(tk, "fast_info", None)
        if isinstance(fast, dict):
            lp = fast.get("last_price")
            if lp:
                return float(lp)

        # fallback
        hist = tk.history(period="1d")
        if hist is not None and not hist.empty:
            return float(hist["Close"].iloc[-1])
    except Exception as e:
        print("fetch_price_yf error:", e)
    return None


# ========== การประเมินมูลค่าการเคลื่อนที่ ==========
def value_per_point_per_lot(_: SymbolSpec) -> float:
    """
    1 lot เคลื่อนที่ 1 จุด = $1  → $/point/lot = 1
    """
    return 1.0


def value_per_pip_per_lot(spec: SymbolSpec) -> float:
    return value_per_point_per_lot(spec) * float(spec.pip_points)


# ========== Margin / Position sizing ==========
def margin_per_1lot(price: float, leverage: float, spec: SymbolSpec) -> float:
    """
    Margin/lot ≈ (Contract × Price) / Leverage
    """
    if leverage <= 0 or price <= 0:
        return 0.0
    return (spec.contract_size * price) / leverage


def max_lot(balance: float, price: float, leverage: float, spec: SymbolSpec, buffer_fraction: float = 0.0) -> float:
    """
    Maxlot = (ทุน * Leverage) / (Price * ContractSize)
    จากนั้นเผื่อ buffer_fraction (0.0–0.9)
    """
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
    """
    โหมด All-in ใช้ balance ทั้งหมดเป็น risk_amount
    """
    if distance_points <= 0:
        return 0.0
    risk_amount = balance
    return risk_amount / (distance_points * value_per_point_per_lot(spec))


# ========== Helpers สำหรับหน้า SL → Lot ==========
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
    """คืนรายการ (stop_points, lots) สำหรับสร้างตารางใน UI"""
    out: List[Tuple[int, float]] = []
    for p in stops_points:
        p = int(p)
        lots = (float(risk_amount) / float(p)) if p > 0 else 0.0
        out.append((p, lots))
    return out