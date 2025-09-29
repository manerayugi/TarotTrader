from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple
import streamlit as st
import re
import pandas as pd

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

# สำหรับ BTCUSD ให้ point = 1 (ราคาเปลี่ยนทีละ 1), contract สมมุติ 1
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
    - สำหรับทองคำ: ใช้ XAUT-USD (ราคาค่อนข้างใกล้เคียงกับตลาด)
    - (ยังไม่ได้ map สำหรับ BTCUSD ตรง ๆ หากต้องการค่อยเพิ่มภายหลัง)
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


# ========== GMK Signal → Lot ==========
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
# ===== (แทนที่ของเดิม) parser รองรับ .mg / SL=/ TP1..TP6= / timeframe =====
def parse_gmk_signal(text: str):
    """
    รองรับตัวอย่าง:
    XAUUSD.mg M5 SELL @3774.03
    SL=3785.34
    TP1=3771.77
    ...
    หรือ
    BTCUSD.mg M15 BUY @108543.65
    SL=108110.15
    TP1=108630.35 ...
    """
    s = text.strip()
    u = s.upper()

    # symbol (+ ตัด .mg ออกถ้ามี)
    m_sym = re.search(r"\b([A-Z]{3,10})(?:\.MG)?\b", u)
    symbol = _norm_symbol(m_sym.group(1)) if m_sym else None

    # timeframe (optional)
    m_tf = re.search(r"\b(M\d+|H\d+|D\d+|W\d+)\b", u)
    timeframe = m_tf.group(1) if m_tf else None

    # direction
    direction = None
    for k, v in _DIR_ALIASES.items():
        if re.search(rf"\b{k}\b", u):
            direction = v
            break

    # entry (หลัง @) เช่น @3774.03
    entry = None
    m_entry = re.search(r"@\s*([0-9]+(?:\.[0-9]+)?)", u)
    if m_entry:
        entry = float(m_entry.group(1))
    else:
        # fallback: หาเลขตัวแรกในสตริง
        m0 = re.search(r"\b([0-9]+(?:\.[0-9]+)?)\b", u)
        entry = float(m0.group(1)) if m0 else None

    # SL รองรับ "SL=xxxx" หรือ "SL xxxx"
    sl = None
    msl = re.search(r"\bSL\s*=?\s*([0-9]+(?:\.[0-9]+)?)", u)
    if msl:
        sl = float(msl.group(1))

    # TP list รองรับ "TP1=xxx" ... "TP6=xxx" และกรณีไม่มี "=" ก็พยายามจับ
    tp_matches = re.findall(r"\bTP\d+\s*=?\s*([0-9]+(?:\.[0-9]+)?)", u)
    tps = [float(x) for x in tp_matches] if tp_matches else []
    # เผื่อ format ไม่มี index (เช่น "TP=xxxx")
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

def _signal_spec(symbol_name: str) -> SymbolSpec:
    return SYMBOL_PRESETS.get(symbol_name, XAUUSD_SPEC)

def _dist_points(a: Optional[float], b: Optional[float], spec: SymbolSpec) -> float:
    if a is None or b is None:
        return 0.0
    return abs(float(a) - float(b)) / float(spec.price_point)


def _tp_points(entry: Optional[float], tp: Optional[float], spec: SymbolSpec) -> float:
    if entry is None or tp is None:
        return 0.0
    return abs(float(tp) - float(entry)) / float(spec.price_point)


_DEFAULT_RISK_SET = [1, 2, 3, 4, 5, 10, 15, 20, 30, 50, 100]


def _risk_table_rows(balance: float, risk_set, dist_points: float, tp_points: float, spec: SymbolSpec):
    rows = []
    vpp = value_per_point_per_lot(spec)  # $/point/lot
    for rp in risk_set:
        risk_amt = balance * (rp / 100.0)
        if dist_points > 0 and vpp > 0:
            lots = risk_amt / (dist_points * vpp)
            pnl_sl = -pnl_usd(lots, dist_points, spec)
            pnl_tp = pnl_usd(lots, tp_points, spec) if tp_points > 0 else None
        else:
            lots, pnl_sl, pnl_tp = 0.0, 0.0, None
        rows.append({
            "Risk (%)": rp,
            "Risk ($) @SL": risk_amt,
            "Lot": lots,
            "P/L @SL ($)": pnl_sl,
            "P/L @TP ($)": pnl_tp
        })
    return rows


def render_signal_tab():
    st.subheader("📨 GMK Signal → Lot (คำนวณจากความเสี่ยง)")

    # ---------- Layout: ซ้ายกรอก | ขวาตาราง ----------
    left, right = st.columns([1, 1.2])

    with left:
        st.markdown("#### ข้อความสัญญาณ")
        sig_text = st.text_area(
            "วางสัญญาณที่นี่",
            value=("XAUUSD.mg M5 SELL @3774.03\n"
                   "SL=3785.34\n"
                   "TP1=3771.77\nTP2=3769.51\nTP3=3764.98\nTP4=3760.46\nTP5=3755.93\nTP6=3751.41"),
            height=140,
            help="รองรับรูปแบบ .mg / SL=... / TP1..TP6=... (ค่าที่พาร์สได้สามารถแก้ไขในฟอร์มด้านล่าง)"
        )
        parsed = parse_gmk_signal(sig_text)

        # เลือกสัญลักษณ์/ทิศทาง
        c1, c2 = st.columns(2)
        with c1:
            symbol_name = st.selectbox(
                "Symbol",
                options=list(SYMBOL_PRESETS.keys()),
                index=list(SYMBOL_PRESETS.keys()).index(parsed["symbol"]) if parsed.get("symbol") in SYMBOL_PRESETS else 0
            )
        with c2:
            direction = st.selectbox(
                "Direction",
                options=["LONG", "SHORT"],
                index=0 if parsed.get("direction") == "LONG" else 1 if parsed.get("direction") == "SHORT" else 0
            )

        spec = _signal_spec(symbol_name)

        # Entry / SL / TP (ให้แก้เองได้)
        c3, c4 = st.columns(2)
        with c3:
            entry = st.number_input("Entry", value=float(parsed.get("entry") or 0.0), step=0.01, min_value=0.0)
            sl    = st.number_input("SL",    value=float(parsed.get("sl")    or 0.0), step=0.01, min_value=0.0)
        with c4:
            tp_list = parsed.get("tps") or []
            selected_tp_val: Optional[float] = None
            if tp_list:
                options = [f"TP{i+1} — {tp_list[i]:,.2f}" for i in range(len(tp_list))]
                idx = st.selectbox("TP ที่ต้องการ", options=list(range(len(tp_list))), format_func=lambda i: options[i])
                selected_tp_val = tp_list[idx]
            # ช่องให้กรอก TP เอง (override)
            manual_tp = st.number_input("หรือกรอก TP เอง (ถ้าต้องการ)", value=0.0, step=0.01, min_value=0.0)
            if manual_tp > 0:
                selected_tp_val = manual_tp

            balance = st.number_input("ทุน ($)", value=1000.0, step=100.0, min_value=0.0)

        # กำหนด Risk
        loss_mode = st.selectbox("กรอก Risk เป็น", ["%", "$"], index=0)
        if loss_mode == "%":
            loss_val = st.number_input("Risk (%)", value=1.0, step=0.25, min_value=0.0)
            risk_amount = balance * (loss_val / 100.0)
            st.caption(f"Risk ที่ใช้คำนวณ ≈ **${risk_amount:,.2f}**")
        else:
            loss_val = st.number_input("Risk ($)", value=10.0, step=5.0, min_value=0.0)
            risk_amount = loss_val
            st.caption(f"คิดเป็นสัดส่วน ≈ **{(risk_amount/balance*100 if balance>0 else 0):.2f}%**")

        # สูตร + ข้อมูลประกอบ
        st.markdown("""
        <div style='text-align:center; margin:12px 0 8px 0;'>
          <hr style='width: 360px; border: 1px solid #666; margin: 8px auto;'/>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("<div style='text-align:center; color:#FFD700; font-size:1.2rem;'>", unsafe_allow_html=True)
        st.latex(r'''
            \color{purple}{\text{Lot} = \frac{\text{Risk Amount}}{\text{Distance to SL (points)} \times (\$/\text{point}/\text{lot})}}
        ''')
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("""
        <div style='text-align:center; margin:8px 0;'>
          <hr style='width: 360px; border: 1px solid #666; margin: 8px auto;'/>
        </div>
        """, unsafe_allow_html=True)

        # ค่าที่ใช้คำนวณ (จากค่าปัจจุบันในฟอร์ม)
        dist_points_sl = _dist_points(entry, sl, spec)
        vpp = value_per_point_per_lot(spec)
        st.caption(
            f"Distance @SL ≈ **{dist_points_sl:,.0f} points**, "
            f"Value ≈ **${vpp:.2f}/point/lot**"
        )

        # ปุ่มคำนวณ
        lots_calc = 0.0
        if st.button("คำนวณ Lot ตาม Risk ที่กรอก", type="primary"):
            # ตรวจสอบอินพุตพื้นฐาน
            spec = _signal_spec(symbol_name)
            vpp = value_per_point_per_lot(spec)
            dist_points_sl = _dist_points(entry, sl, spec)
            dist_points_sel_tp = _dist_points(entry, selected_tp_val, spec) if selected_tp_val else 0.0

            if dist_points_sl <= 0 or vpp <= 0:
                st.error("กรุณาตรวจสอบ Entry/SL ให้ถูกต้อง (ระยะไป SL ต้องมากกว่า 0)")
            else:
                # 1) คำนวณ lots จาก Risk ที่กรอก
                lots = risk_amount / (dist_points_sl * vpp)

                # 2) P/L @SL (ติดลบ)
                pnl_stop = -pnl_usd(lots, dist_points_sl, spec)

                # 3) P/L @TP (ที่ผู้ใช้เลือก/กรอกเอง)
                pnl_take_sel = (
                    pnl_usd(lots, dist_points_sel_tp, spec)
                    if dist_points_sel_tp and dist_points_sel_tp > 0 else None
                )

                # แสดงสรุป lot + metrics SL/TP(เลือก)
                st.success(f"Lot ที่ควรออก ≈ **{lots:.2f} lot**")
                st.caption(f"Risk = **${risk_amount:,.2f}**, Distance @SL = **{dist_points_sl:,.0f} points**, $/pt/lot = **${vpp:.2f}**")

                m1, m2 = st.columns(2)
                with m1:
                    st.metric("P/L @SL ($)", f"{pnl_stop:,.2f}")
                with m2:
                    if pnl_take_sel is not None:
                        st.metric(f"P/L @TP (เลือก {selected_tp_val:,.2f})", f"{pnl_take_sel:,.2f}")
                    else:
                        st.metric("P/L @TP (เลือก)", "-")

                # 4) P/L @TP1..TP6 (ถ้ามีในสัญญาณ)
                tp_values = (parsed.get("tps") or [])[:6]
                if tp_values:
                    rows = []
                    for i, tpv in enumerate(tp_values, start=1):
                        d_tp = _dist_points(entry, tpv, spec)
                        pnl_tp = pnl_usd(lots, d_tp, spec) if d_tp > 0 else 0.0
                        rows.append({
                            "TP": f"TP{i}",
                            "Price": tpv,
                            "Distance (pts)": d_tp,
                            "P/L ($)": pnl_tp
                        })
                    df_tp = pd.DataFrame(rows)
                    sty = (
                        df_tp.style
                            .format({
                                "Price": "{:,.2f}",
                                "Distance (pts)": "{:,.0f}",
                                "P/L ($)": "{:,.2f}",
                            })
                            .set_table_styles([{'selector': 'th', 'props': [('text-align', 'center')]}])
                            .set_properties(**{'text-align': 'center'})
                    )
                    st.markdown("**P/L @TP1–TP6 (ตามสัญญาณ)**")
                    st.dataframe(sty, use_container_width=True, height=min(330, (len(df_tp) + 2) * 33))

        # เก็บค่า lot ไปใช้ฝั่งขวา
        st.session_state.setdefault("signal_lot_calc", 0.0)
        st.session_state["signal_lot_calc"] = lots_calc

    # ตารางฝั่งขวา: แสดง P/L ที่ TP1..TP6 ตาม lot ที่คำนวณได้ (เอา P/L SL ออก)
        # ตารางฝั่งขวา: คำนวณ lot ตามความเสี่ยง (Risk set) + P/L @TP1..TP6
    with right:
        st.markdown("#### ตารางคำนวณ Lot ตามความเสี่ยง + ผลลัพธ์ที่ TP แต่ละระดับ")

        # ใช้ค่าจากฝั่งซ้าย (entry/sl/spec/balance/…)
        dist_points_sl = _dist_points(entry, sl, spec)
        vpp = value_per_point_per_lot(spec)
        tp_values = parsed.get("tps") or []   # ตามสัญญาณที่วาง (สูงสุด 6 ค่า)
        tp_values = tp_values[:6]

        # เตรียมคอลัมน์ TP (หัวตาราง)
        tp_cols = [f"P/L @TP{i+1} ($)" for i in range(len(tp_values))]

        rows = []
        # ชุดความเสี่ยงมาตรฐาน
        for rp in _DEFAULT_RISK_SET:
            risk_amt = balance * (rp / 100.0)
            if dist_points_sl > 0 and vpp > 0:
                lots = risk_amt / (dist_points_sl * vpp)
            else:
                lots = 0.0

            # คำนวณ P/L แต่ละ TP จาก lot เดียวกัน (ระยะ = |TP - Entry|)
            pl_tps = []
            for tp in tp_values:
                tp_pts = _tp_points(entry, tp, spec)
                pnl_tp = pnl_usd(lots, tp_pts, spec) if lots > 0 else 0.0
                pl_tps.append(pnl_tp)

            row = {
                "Risk (%)": rp,
                "Risk ($)": risk_amt,
                "Lot": lots,
            }
            for i, pnl in enumerate(pl_tps):
                row[tp_cols[i]] = pnl
            rows.append(row)

        if rows:
            df = pd.DataFrame(rows)

            # ฟอร์แมตตัวเลข
            fmt_map = {"Risk (%)": "{:.0f}", "Risk ($)": "{:,.2f}", "Lot": "{:.2f}"}
            for c in tp_cols:
                fmt_map[c] = "{:,.2f}"

            sty = (
                df.style
                  .format(fmt_map, na_rep="-")
                  .set_table_styles([{'selector': 'th', 'props': [('text-align', 'center')]}])
                  .set_properties(**{'text-align': 'center'})
            )
            st.dataframe(sty, use_container_width=True, height=(len(df)+2)*33)
        else:
            st.info("ไม่มี TP ในสัญญาณที่วาง — ใส่ TP ในข้อความ หรือกรอก TP เองทางซ้าย (ตารางฝั่งขวาแสดงตาม TP ของสัญญาณ)")

# ===== UI helper (เรียกจาก streamlit_app.py) =====
def render_money_management_page():
    import pandas as pd

    st.header("💰 Money Management")

    if "mm_tab" not in st.session_state:
        st.session_state.mm_tab = "sizing"

    tabs = st.columns([1.6, 1.6, 1.6, 2, 1.6])
    with tabs[0]:
        if st.button("🧮 การออก Lot", use_container_width=True):
            st.session_state.mm_tab = "sizing"
    with tabs[1]:
        if st.button("📏 ระยะ SL → Lot", use_container_width=True):
            st.session_state.mm_tab = "sl"
    with tabs[2]:
        if st.button("📨 GMK Signal → Lot", use_container_width=True):
            st.session_state.mm_tab = "signal"
    with tabs[3]:
        if st.button("📑 GMK Signal Planning", use_container_width=True):
            st.session_state.mm_tab = "signal_plan"
    with tabs[4]:
        if st.button("🧪 (สำรองหน้าอื่น)", use_container_width=True):
            st.session_state.mm_tab = "tbd2"

    st.divider()

    # ---------------- Tab 1: การออก Lot ----------------
    if st.session_state.mm_tab == "sizing":
        st.subheader("🧮 การออก Lot (Position Sizing – Max & Optimal)")

        # 1) เลือกสินค้า
        preset_names = list(SYMBOL_PRESETS.keys())
        left, right = st.columns([2, 1])
        with left:
            symbol_name = st.selectbox(
                "สินค้า",
                preset_names,
                index=preset_names.index("XAUUSD") if "XAUUSD" in preset_names else 0
            )
        spec = SYMBOL_PRESETS[symbol_name]

        with right:
            st.write("Contract Info")
            st.caption(
                f"- Contract size: {spec.contract_size}\n"
                f"- Min lot: {spec.min_lot} | Step: {spec.lot_step}\n"
                f"- 1 point = ราคาเปลี่ยน {spec.price_point}\n"
                f"- 1 pip = {spec.pip_points} points"
            )

        # 2) ราคา
        st.markdown("#### ราคา")
        c1, c2, _ = st.columns([1, 1, 2])
        with c1:
            use_fetch = st.toggle("ดึงราคา realtime", value=False)
        with c2:
            default_price = 0.0
            if use_fetch:
                fetched = fetch_price_yf(symbol_name)
                if fetched:
                    default_price = fetched
                    st.success(f"ราคาโดยประมาณ: {fetched:,.2f}")
                else:
                    st.warning("ดึงราคาไม่สำเร็จ กรุณากรอกเอง")
            price = st.number_input("ราคา (USD)", value=float(default_price), step=0.1, min_value=0.0)

        st.divider()

        # 3) Max Lot
        st.markdown("### 1) Max Lot จากทุน + Leverage")
        st.markdown("""
        <div style='text-align:center; margin:20px 0;'>
        <hr style='width: 320px; border: 1px solid #666; margin: 10px auto;'/>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<div style='text-align:center; color:#FFD700; font-size:1.4rem;'>", unsafe_allow_html=True)
        st.latex(r'''
            \color{purple}{\text{MaxLot} = \frac{\text{ทุน(USD)} \times \text{Leverage}}{\text{Price} \times \text{ContractSize}}}
        ''')
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("""
        <div style='text-align:center; margin:10px 0;'>
        <hr style='width: 320px; border: 1px solid #666; margin: 10px auto;'/>
        </div>
        """, unsafe_allow_html=True)
        cA, cB, cC, cD = st.columns([1, 1, 1, 1.6])
        with cA:
            balance = st.number_input("ทุน ($)", value=1000.0, step=100.0, min_value=0.0)
        with cB:
            leverage = st.number_input("Leverage", value=1000, step=50, min_value=1, format="%d")
        with cC:
            buffer_pct_ui = st.number_input("กันไว้ (Free Margin %)", value=0.0, step=1.0, min_value=0.0, max_value=90.0)
            buffer_pct = buffer_pct_ui / 100.0
        with cD:
            st.markdown("""
            <div style='display:flex; align-items:center; height:100%; justify-content:center;'>
            <ul style='list-style-type:none; font-size:1rem; line-height:1.8; margin: 0; padding: 0; color:#9CA3AF;'>
                <li>• <b>ทุน($)</b> — มูลค่าทุนในบัญชี (Balance)</li>
                <li>• <b>Leverage</b> — อัตราทดที่ใช้ (เช่น 1:1000 → ใส่ค่า 1000)</li>
                <li>• <b>Price</b> — ราคาปัจจุบันของสินค้าที่เทรด</li>
                <li>• <b>ContractSize</b> — ขนาดสัญญาของสินค้านั้น (เช่น XAUUSD = 100)</li>
                <li>• <b>Free Margin %</b> — เปอร์เซ็นต์กันไว้เพื่อความปลอดภัย</li>
            </ul>
            </div>
            """, unsafe_allow_html=True)

        if st.button("คำนวณ MaxLot", type="primary"):
            m1 = margin_per_1lot(price, float(leverage), spec) if (price > 0 and leverage > 0) else 0.0
            maxlot_val = max_lot(balance, float(price), float(leverage), spec, buffer_pct)
            st.success(f"MaxLot โดยประมาณ: **{maxlot_val:.2f} lot**")
            if m1 > 0:
                st.caption(f"(Margin/lot ≈ (Contract × Price) / Leverage = ${m1:,.2f}/lot)")

        st.divider()

        # 4) Optimal Lot
        st.markdown("### 2) Optimal Lot จากระยะที่ทนได้")
        # เส้นคั่นบน (สั้นและอยู่กึ่งกลาง)
        st.markdown("""
        <div style='text-align:center; margin:12px 0 6px 0;'>
        <hr style='width: 360px; border: 1px solid #555; margin: 8px auto;'/>
        </div>
        """, unsafe_allow_html=True)

        # สูตร
        st.markdown("<div style='text-align:center; font-size:1.25rem;'>", unsafe_allow_html=True)
        st.latex(r'''
        \color{purple}{
        \text{OptimalLot}
        =
        \frac{\text{ทุน(USD)}}
            {\text{Distance(points)} \times (\$/\text{point}/\text{lot})}
        }
        ''')
        st.markdown("</div>", unsafe_allow_html=True)

        # เส้นคั่นล่าง
        st.markdown("""
        <div style='text-align:center; margin:6px 0 12px 0;'>
        <hr style='width: 360px; border: 1px solid #555; margin: 8px auto;'/>
        </div>
        """, unsafe_allow_html=True) 
        
        u1, u2, u3, u4 = st.columns([1, 1, 1, 1.6])
        with u1:
            unit = st.selectbox("หน่วยระยะ", ["points", "pips"], index=0)
        with u2:
            distance_input = st.number_input(
                f"ระยะ Stop Loss ({unit})",
                value=10000,
                step=1,
                min_value=0,
                format="%d"
            )
        with u3:
            mode_safe = st.toggle("โหมดปลอดภัย (Risk%)", value=True)
            risk_percent = st.number_input(
                "Risk ต่อไม้ (%)", 
                value=1.0, 
                step=0.25, 
                min_value=0.0, 
                disabled=not mode_safe
            )
        with u4:
            st.markdown("""
            <div style='display:flex; align-items:center; height:100%; justify-content:left;'>
            <ul style='list-style-type:none; font-size:1rem; line-height:1.8; margin: 0; padding: 0; color:#9CA3AF;'>
                <li>• <b>ทุน($)</b> — มูลค่าทุนในบัญชี (Balance)</li>
                <li>• <b>Risk (%)</b>: สัดส่วนความเสี่ยงต่อไม้</li>
                <li>• <b>Distance</b>: ระยะ Stop Loss (points/pips)</li>
                <li>• <b>$/point/lot</b>: มูลค่าการเคลื่อนไหวต่อจุด</li>
            </ul>
            </div>
            """, unsafe_allow_html=True)

        distance_points = float(distance_input) * (spec.pip_points if unit == "pips" else 1.0)
        vpp = value_per_point_per_lot(spec)
        st.caption(f"คำนวณจากสูตร: lot = (ทุนที่ยอมเสีย) / (ระยะ {distance_points:.0f} points × ${vpp:.2f}/point/lot)")

        if st.button("คำนวณ OptimalLot"):
            risk_amount = balance * (risk_percent / 100.0) if (mode_safe and risk_percent > 0) else balance
            lots_raw = risk_amount / (distance_points * vpp) if (distance_points > 0 and vpp > 0) else 0.0

            import math
            step = getattr(spec, "lot_step", 0.01)
            min_lot = getattr(spec, "min_lot", 0.01)
            lots_adj = max(min_lot, math.floor(lots_raw / step) * step if step > 0 else lots_raw)

            maxlot_theo = maxlot_theoretical(balance, float(leverage), float(price), spec) if (price > 0 and leverage > 0) else 0.0
            lots_final = min(lots_adj, maxlot_theo) if maxlot_theo > 0 else lots_adj

            pnl_stop = -pnl_usd(lots_final, distance_points, spec)

            st.info(f"Risk Amount: ${risk_amount:,.2f} | Distance: {distance_points:,.0f} points | $/pt/lot: ${vpp:.2f}")
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Lot (สูตรดิบ)", f"{lots_raw:.4f}")
            with c2:
                st.metric("Lot (ปรับตาม Step/Min)", f"{lots_adj:.2f}")
            with c3:
                st.metric("MaxLot (เพดาน)", f"{maxlot_theo:.2f}")

            if maxlot_theo > 0 and lots_adj > maxlot_theo:
                st.warning("ค่าที่คำนวณเกิน MaxLot ที่เปิดได้ — ระบบปรับลงให้อยู่ภายใต้เพดานแล้ว")

            st.success(f"**OptimalLot ที่ใช้จริง** ≈ **{lots_final:.2f} lot**")
            st.caption(f"ถ้าโดน Stop (−{distance_points:,.0f} points) ≈ **${pnl_stop:,.2f}**")

        st.divider()
        st.markdown("#### สรุปมูลค่าการเคลื่อนที่ (ต่อ 1 lot)")
        df = pd.DataFrame({
            "รายการ": ["$/point/lot", f"$/pip/lot (1 pip = {spec.pip_points} points)"],
            "Value ($)": [value_per_point_per_lot(spec), value_per_pip_per_lot(spec)]
        })
        st.dataframe(df, use_container_width=True)

    # ---------------- Tab 2: ระยะ SL → Lot ----------------
    elif st.session_state.mm_tab == "sl":
        st.subheader("📏 ระยะ SL → คำนวณ Lot")

        left, right = st.columns([1, 1.2])
        with left:
            price = st.number_input("ราคาปัจจุบัน (USD)", value=0.0, step=0.1, min_value=0.0)
            balance = st.number_input("ทุน ($)", value=1000.0, step=100.0, min_value=0.0)

            loss_mode = st.selectbox("กรอก Loss เป็น", ["%", "$"], index=0)
            if loss_mode == "%":
                loss_val = st.number_input("Loss (%)", value=10.0, step=0.5, min_value=0.0)
            else:
                loss_val = st.number_input("Loss ($)", value=100.0, step=10.0, min_value=0.0)

            risk_amount, loss_pct = loss_to_amount_and_pct(balance, loss_mode, loss_val)
            if loss_mode == "%":
                st.caption(f"Loss ที่ใช้คำนวณ ≈ **${risk_amount:,.2f}**")
            else:
                st.caption(f"Loss ที่ใช้คำนวณ ≈ **{loss_pct:.2f}%** ของทุน")

            leverage = st.number_input("Leverage", value=1000, step=50, min_value=1, format="%d")
            custom_points = st.number_input("Stop Loss (Point) - กำหนดเอง", value=1000, step=1, min_value=0, format="%d")

            # สูตร
            st.markdown("""
            <div style='text-align:center; margin:12px 0 6px 0;'>
            <hr style='width: 360px; border: 1px solid #555; margin: 8px auto;'/>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("<div style='text-align:center; font-size:1.25rem;'>", unsafe_allow_html=True)
            st.latex(r'''
            \color{purple}{
            \text{Lot}
            =
            \frac{\text{RiskAmount}}
                {\text{Distance(points)}}
            }
            ''')
            st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("""
            <div style='text-align:center; margin:6px 0 12px 0;'>
            <hr style='width: 360px; border: 1px solid #555; margin: 8px auto;'/>
            </div>
            """, unsafe_allow_html=True) 

        with right:
            max_lot_val = maxlot_theoretical(balance, float(leverage), float(price), XAUUSD_SPEC)

            std_points = [10, 50, 100, 200, 300, 500, 1000, 1500, 2000, 5000, 10000, 20000]
            if custom_points and custom_points not in std_points:
                std_points.append(int(custom_points))
            std_points = sorted(std_points)

            rows = []
            for pts, lots in lots_from_stops(risk_amount, std_points):
                exceeds = lots > max_lot_val if max_lot_val > 0 else False
                rows.append({"Stop Loss (Point)": pts, "Lot (คำนวณ)": lots, "เกิน MaxLot?": "⚠️ ใช่" if exceeds else ""})
            df = pd.DataFrame(rows)

            def _hl(row):
                return [
                    'background-color: #f3e8ff; color: #111; font-weight: 600;' if row["เกิน MaxLot?"] else ''
                    for _ in row
                ]
            sty = (
                df.style
                  .apply(_hl, axis=1)
                  .set_table_styles([{'selector': 'th', 'props': [('text-align', 'center')]}])
                  .set_properties(**{'text-align': 'center'})
                  .format({"Stop Loss (Point)": "{:,.0f}", "Lot (คำนวณ)": "{:.2f}"})
            )

            st.markdown(f"**MaxLot (ด้วยราคาปัจจุบัน):** {max_lot_val:.2f} lot")
            st.dataframe(sty, use_container_width=True, height=(len(df) + 2) * 33)

            if custom_points > 0:
                custom_lot = risk_amount / float(custom_points)
                exceeds_custom = custom_lot > max_lot_val if max_lot_val > 0 else False

                st.subheader("ผลลัพธ์จากระยะที่กำหนดเอง")
                st.write(f"Stop Loss (Point): **{custom_points:,}** → Lot ที่ควรออก ≈ **{custom_lot:.2f} lot**")
                if exceeds_custom:
                    st.warning("ค่าที่คำนวณเกิน MaxLot ที่เปิดได้ในตอนนี้")

    # ---------------- Tab 3: GMK Signal → Lot ----------------
    elif st.session_state.mm_tab == "signal":
        render_signal_tab()
        
    # ---------------- Tab 4: GMK Signal Planning ----------------
    elif st.session_state.mm_tab == "signal_plan":
        render_signal_planning_tab()

    else:
        st.info("เลือกหน้าฟังก์ชันอื่น ๆ ได้ในอนาคต (ยังไม่เปิดใช้งาน)")
        
def render_signal_planning_tab():
    """แท็บ GMK Signal Planning (Grid Planner แบบใหม่):
       อินพุต: สัญญาณ GMK + ทุน + Risk (% หรือ $)
       เลือกจำนวนไม้จากตัวหารของ TotalLot (หลังปัดตาม lot_step)
       ผลลัพธ์ฝั่งขวา:
         - สรุป per-lot / total-lot / step (points) / P/L @SL
         - ตาราง: แถว = จำนวนไม้ที่ถูก Fill จริง (1..N) / คอลัมน์ = P/L @TP1..TP6
         - รายการราคาเข้าแต่ละไม้ (ของกริด N ไม้)
    """
    st.subheader("📑 GMK Signal Planning")

    tab_mtg, tab_grid = st.tabs(["มาติงเกล (coming soon)", "กริด (Grid Planner)"])

    # ---------------- Martingale (coming soon) ----------------
    with tab_mtg:
        st.info("ฟีเจอร์มาติงเกลกำลังมาเร็วๆ นี้ ✨")

    # ---------------- Grid Planner ----------------
    with tab_grid:
        # ===== สูตร (Lot และ Total Lot) =====
        st.markdown("""
        <div style='text-align:center; margin:8px 0 6px 0;'>
          <hr style='width: 360px; border: 1px solid #555; margin: 6px auto;'/>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("<div style='text-align:center; font-size:1.1rem;'>", unsafe_allow_html=True)
        st.latex(r'''
        \color{purple}{
        \text{Lot} = \frac{\text{Risk Amount}}{\text{Distance to SL (points)} \times (\$/\text{point}/\text{lot})}
        }
        ''')
        st.latex(r'''
        \color{purple}{
        \text{Total Lot} = \text{Lot (จากสูตรข้างบน)}
        }
        ''')
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("""
        <div style='text-align:center; margin:6px 0 12px 0;'>
          <hr style='width: 360px; border: 1px solid #555; margin: 6px auto;'/>
        </div>
        """, unsafe_allow_html=True)

        # ===== Layout: ซ้าย (อินพุต) | ขวา (ผลลัพธ์) =====
        left, right = st.columns([1, 1.15])

        # -------- ซ้าย: อินพุตทั้งหมด --------
        with left:
            st.markdown("#### ข้อความสัญญาณ")
            sig_text = st.text_area(
                "วางสัญญาณที่นี่",
                value=("XAUUSD.mg M5 SELL @3774.03\n"
                       "SL=3785.34\n"
                       "TP1=3771.77\nTP2=3769.51\nTP3=3764.98\nTP4=3760.46\nTP5=3755.93\nTP6=3751.41"),
                height=140,
                help="รองรับรูปแบบ .mg / SL=... / TP1..TP6=... (ใช้ข้อมูลจากสัญญาณเท่านั้น)"
            )
            parsed = parse_gmk_signal(sig_text)

            symbol_name = parsed.get("symbol") or "XAUUSD"
            direction   = parsed.get("direction")
            entry       = parsed.get("entry")
            sl          = parsed.get("sl")
            tp_values   = (parsed.get("tps") or [])[:6]

            spec = _signal_spec(symbol_name)
            vpp  = value_per_point_per_lot(spec)
            dist_pts = _dist_points(entry, sl, spec)

            if entry and sl:
                st.caption(f"Distance Entry→SL ≈ **{dist_pts:,.0f} points**, $/pt/lot ≈ **${vpp:.2f}**")
            else:
                st.warning("สัญญาณไม่ครบถ้วน (ต้องมี Entry และ SL) — โปรดตรวจสอบข้อความสัญญาณ")

            # แถวเดียว: ทุน + โหมด Risk + ค่า Risk
            c1, c2, c3 = st.columns([1, 1, 1])
            with c1:
                balance = st.number_input("ทุน ($)", value=1000.0, step=100.0, min_value=0.0)
            with c2:
                loss_mode = st.selectbox("กรอก Risk เป็น", ["%", "$"], index=0)
            with c3:
                if loss_mode == "%":
                    loss_val = st.number_input("Risk (%)", value=1.0, step=0.25, min_value=0.0)
                    risk_amount = balance * (loss_val / 100.0) if balance > 0 else 0.0
                else:
                    loss_val = st.number_input("Risk ($)", value=10.0, step=5.0, min_value=0.0)
                    risk_amount = float(loss_val)
            st.caption(f"Risk Amount ≈ **${risk_amount:,.2f}**")

            # เตรียมคำนวณ Total Lot และ “จำนวนไม้” ที่เป็นตัวหารลงตัว
            lot_step = max(spec.lot_step, 0.01)
            min_lot  = max(spec.min_lot, lot_step)

            n_orders_options = []
            total_units = 0
            quant_total_lot = 0.0

            if all([entry, sl, direction in ("LONG", "SHORT"), dist_pts > 0, vpp > 0, risk_amount > 0]):
                import math

                # total lot แบบดิบจากสูตร 1 ไม้
                total_lot_raw = risk_amount / (dist_pts * vpp)

                # กรณี 1 ไม้ min lot ยังเกิน Risk
                loss_one_min = min_lot * vpp * dist_pts
                if risk_amount < loss_one_min - 1e-12:
                    st.warning("แม้เพียง 1 ไม้ (min lot) ก็เกิน Risk ที่ตั้งไว้ → เปิดได้เพียง 1 ไม้ขนาดขั้นต่ำ")
                    quant_total_lot = min_lot
                    total_units = int(round(min_lot / lot_step))  # 1 unit = lot_step
                else:
                    total_units = int(math.floor(total_lot_raw / lot_step + 1e-9))
                    quant_total_lot = total_units * lot_step

                # สร้างชุด “จำนวนไม้” จากตัวหารของ total_units (1..total_units ที่หารลงตัว)
                if total_units > 0:
                    def divisors(n: int):
                        ds = set()
                        i = 1
                        while i * i <= n:
                            if n % i == 0:
                                ds.add(i); ds.add(n // i)
                            i += 1
                        return sorted(ds)
                    n_orders_options = divisors(total_units)

                st.info(
                    f"Total Lot (ตาม Risk, ปัดตาม step) ≈ **{quant_total_lot:.2f} lot**  |  "
                    f"Distance @SL ≈ **{dist_pts:,.0f} pts**  |  Lot step = **{lot_step:.2f}**"
                )

            # เลือกจำนวนไม้ (เฉพาะค่าที่หาร TotalLot ลงตัว)
            sel_orders = None
            if n_orders_options:
                sel_orders = st.selectbox(
                    "จำนวนไม้ (เฉพาะค่าที่หาร Total Lot ลงตัว)",
                    options=n_orders_options,
                    index=min(len(n_orders_options)-1, 0)
                )

            # ปุ่มวางแผน “หลังจากเลือกจำนวนไม้แล้ว”
            go = False
            if sel_orders is not None:
                go = st.button("🔧 วางแผนกริดตาม Risk", type="primary", use_container_width=True)

        # -------- ขวา: แสดงผลทั้งหมด --------
        with right:
            st.markdown("#### ผลการวางแผนกริด")

            # เงื่อนไขเบื้องต้น
            if not (entry and sl and direction in ("LONG", "SHORT")):
                st.info("กรุณาวางสัญญาณที่มี Entry / SL และทิศทางให้ครบ ก่อนทำการวางแผน")
                return
            if dist_pts <= 0 or vpp <= 0:
                st.error("ระยะจาก Entry ถึง SL ต้องมากกว่า 0 และ $/pt/lot ต้องมากกว่า 0")
                return
            if not n_orders_options:
                st.info("กำหนดทุน/Risk ให้เหมาะสมเพื่อให้ได้ Total Lot > 0 และเลือกจำนวนไม้ที่หารลงตัว")
                return
            if not go:
                st.info("เลือกจำนวนไม้ทางซ้าย แล้วกด **วางแผนกริดตาม Risk** เพื่อดูผลลัพธ์ที่นี่")
                return

            # ==== กำหนดกริด N ไม้ ====
            N = int(sel_orders)
            per_lot = (quant_total_lot / N) if N > 0 else 0.0

            # “ราคาเข้าแต่ละไม้” ต้องเป็น “แบ่งช่วง Entry→SL เท่ากัน N ส่วน” และไม่วางทับ SL:
            # positions_k = Entry + (SL - Entry) * (k/N), k = 0..N-1
            sgn = 1 if direction == "LONG" else -1
            entries = [entry + (sl - entry) * (k / N) for k in range(N)]
            step_pts = dist_pts / N  # ความห่างระหว่างไม้ (points) ตามสูตรด้านบน

            # P/L รวมเมื่อถึง SL (ถ้าเข้าครบ N ไม้)
            total_pl_sl = 0.0
            for eprice in entries:
                move_pts = (sl - eprice) / spec.price_point * sgn  # จะติดลบ (ขาดทุน)
                total_pl_sl += per_lot * vpp * move_pts

            # BE (เฉลี่ยต้นทุน) เมื่อเข้าครบ N ไม้
            be_price = sum(entries) / len(entries) if N >= 2 else None

            # ---- สรุปย่อ ---
            df_plan = pd.DataFrame([{
                "Lot/Order": per_lot,
                "Orders": N,
                "Total Lot": quant_total_lot,
                "Step (pts)": step_pts,
                "P/L @SL ($)": total_pl_sl,
            }])
            st.dataframe(
                df_plan.style.format({
                    "Lot/Order": "{:.2f}",
                    "Orders": "{:,.0f}",
                    "Total Lot": "{:.2f}",
                    "Step (pts)": "{:,.0f}",
                    "P/L @SL ($)": "{:,.2f}",
                }).set_properties(**{"text-align": "center"}),
                use_container_width=True,
                height=90
            )
            if be_price is not None:
                st.info(f"📍 จุดปิดรวบ (Break-even) ≈ **{be_price:,.2f}**")

            # ---- ตาราง P/L @TP1..TP6 ตาม “จำนวนไม้ที่ถูก Fill จริง” 1..N ----
            if not tp_values:
                st.warning("สัญญาณไม่มี TP — ตารางกำไร TP1..TP6 แสดงไม่ได้")
            else:
                rows = []
                # เตรียมคอลัมน์ TP
                tp_cols = [f"TP{i+1}" for i in range(len(tp_values))]

                for k_fill in range(1, N + 1):
                    # ใช้ “ชุดกริด N ไม้” เดิม แต่พิจารณาเฉพาะไม้ที่ถูก Fill มาแล้ว k_fill ไม้แรก
                    filled_entries = entries[:k_fill]
                    row = {"Filled Orders": k_fill}

                    for i, tp in enumerate(tp_values, start=1):
                        pl = 0.0
                        for eprice in filled_entries:
                            move_pts = (tp - eprice) / spec.price_point * sgn
                            pl += per_lot * vpp * move_pts
                        row[f"P/L @{ 'TP'+str(i) } ($)"] = pl
                    rows.append(row)

                df_tp = pd.DataFrame(rows)
                fmt = {"Filled Orders": "{:.0f}"}
                for i in range(len(tp_values)):
                    fmt[f"P/L @TP{i+1} ($)"] = "{:,.2f}"
                st.dataframe(
                    df_tp.style.format(fmt).set_properties(**{"text-align":"center"}),
                    use_container_width=True,
                    height=min(420, (len(df_tp)+2)*33)
                )

            # ---- ราคาเข้าแต่ละไม้ (ของกริด N ไม้) ----
            with st.expander("ดูราคาเข้าแต่ละไม้ (กริดที่เลือก)"):
                df_orders = pd.DataFrame({
                    "#": list(range(1, N + 1)),
                    "Entry": [round(x, 2) for x in entries]
                })
                st.dataframe(
                    df_orders.style.format({"Entry": "{:,.2f}"}).set_properties(**{"text-align":"center"}),
                    use_container_width=True,
                    height=min(400, (len(df_orders)+2)*33)
                )