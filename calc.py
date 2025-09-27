from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple
import streamlit as st

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

# ===== UI helper (เรียกจาก streamlit_app.py) =====
def render_money_management_page():
    import streamlit as st
    import pandas as pd

    st.header("💰 Money Management")

    if "mm_tab" not in st.session_state:
        st.session_state.mm_tab = "sizing"

    tabs = st.columns([1.6, 1.4, 1.4, 3])
    with tabs[0]:
        if st.button("🧮 การออก Lot", use_container_width=True):
            st.session_state.mm_tab = "sizing"
    with tabs[1]:
        if st.button("📏 ระยะ SL → Lot", use_container_width=True):
            st.session_state.mm_tab = "sl"
    with tabs[2]:
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
                <li>• <b>Free Margin %</b> — เปอร์เซ็นต์ทุนที่กันไว้เพื่อความปลอดภัย ( 20 คือ ใช้ทุนจริง 80% และอีก 20% จะถูกเก็บเป็น Free Margin เพื่อความปลอดภัย)</li>
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

        # สูตร (ใช้ st.latex เพื่อให้เรนเดอร์แน่นอน)
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

        # เส้นคั่นล่าง (สั้นและอยู่กึ่งกลาง)
        st.markdown("""
        <div style='text-align:center; margin:6px 0 12px 0;'>
        <hr style='width: 360px; border: 1px solid #555; margin: 8px auto;'/>
        </div>
        """, unsafe_allow_html=True) 
        
        u1, u2, u3, u4 = st.columns([1, 1, 1, 1.6])
        # --- Column 1: เลือกหน่วย ---
        with u1:
            unit = st.selectbox("หน่วยระยะ", ["points", "pips"], index=0)
        # --- Column 2: ระยะ Stop ---
        with u2:
            distance_input = st.number_input(
                f"ระยะ Stop Loss ({unit})",
                value=10000,
                step=1,
                min_value=0,
                format="%d"
            )
        # --- Column 3: Risk Setting ---
        with u3:
            mode_safe = st.toggle("โหมดปลอดภัย (Risk%)", value=True)
            risk_percent = st.number_input(
                "Risk ต่อไม้ (%)", 
                value=1.0, 
                step=0.25, 
                min_value=0.0, 
                disabled=not mode_safe
            )
        
        # --- Column 4: คำอธิบายตัวแปร ---
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


        # --- แปลงหน่วยและสูตร ---
        distance_points = float(distance_input) * (spec.pip_points if unit == "pips" else 1.0)
        vpp = value_per_point_per_lot(spec)
        
        st.caption(f"คำนวณจากสูตร: lot = (ทุนที่ยอมเสีย) / (ระยะ {distance_points:.0f} points × ${vpp:.2f}/point/lot)")

        if st.button("คำนวณ OptimalLot"):
            # 1) คำนวณ Risk Amount
            risk_amount = balance * (risk_percent / 100.0) if (mode_safe and risk_percent > 0) else balance

            # 2) lot แบบดิบจากสูตร
            lots_raw = risk_amount / (distance_points * vpp) if (distance_points > 0 and vpp > 0) else 0.0

            # 3) ปัดให้เข้ากับ lot_step และไม่ต่ำกว่า min_lot
            import math
            step = getattr(spec, "lot_step", 0.01)
            min_lot = getattr(spec, "min_lot", 0.01)
            lots_adj = max(min_lot, math.floor(lots_raw / step) * step if step > 0 else lots_raw)

            # 4) จำกัดไม่ให้เกิน MaxLot เชิงทฤษฎี (ต้องมีตัวแปร price/leverage อยู่ในสโคปเดียวกัน)
            maxlot_theo = maxlot_theoretical(balance, float(leverage), float(price), spec) if (price > 0 and leverage > 0) else 0.0
            lots_final = min(lots_adj, maxlot_theo) if maxlot_theo > 0 else lots_adj

            pnl_stop = -pnl_usd(lots_final, distance_points, spec)

            # แสดงผลแบบโปร่งใส
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

            st.caption("สูตร MaxLot = (ทุน × Leverage) / (Price × ContractSize)")
            st.caption("สูตร Lot (ต่อระยะที่กำหนด) = ทุนที่มี / จำนวนจุด")

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
    else:
        st.info("เลือกหน้าฟังก์ชันอื่น ๆ ได้ในอนาคต (ยังไม่เปิดใช้งาน)")