# merlin_atm.py
from __future__ import annotations

import pandas as pd
import streamlit as st

# ------------------------- Helpers -------------------------
def _grid_prices(start_price: float, n: int, step_points: int, price_point: float, side: str) -> list[float]:
    """สร้างราคาออกไม้ทีละช่วง points ตามทิศทาง (LONG = ลง, SHORT = ขึ้น)"""
    if n <= 0:
        return []
    step_price = float(step_points) * float(price_point)
    sgn = -1.0 if side == "LONG" else 1.0
    return [round(start_price + sgn * i * step_price, 2) for i in range(n)]

def _last_feasible_index(values: list[float], budget: float) -> int | None:
    """คืน index สุดท้ายที่ค่าจาก values <= budget (เช่น คุมด้วย balance)"""
    last = None
    for i, v in enumerate(values):
        if v <= budget:
            last = i
    return last

# ------------------------- Main UI -------------------------
def render_atm_tab():
    st.markdown(
        """
        <div style='display:flex;align-items:baseline;gap:10px;'>
          <h3 style='margin:0;'>🏧 ATM — Adaptive Trade Matrix</h3>
          <span style='color:#aaa;font-size:0.9rem;'>Grid-based position planner</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption("ออกแบบแผนออกไม้แบบกริดจากทุน/เลเวอเรจ พร้อมเปรียบเทียบเคส Liquidation Price")

    # ---------------- Inputs ----------------
    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        symbol      = st.text_input("สินค้า (เช่น XAUUSD)", value="XAUUSD", key="atm_symbol")
        balance     = st.number_input("เงินทุน (Balance, $)", min_value=0.0, value=10_000.0, step=100.0, key="atm_balance")
        leverage    = st.number_input("Leverage", min_value=1, value=1000, step=50, format="%d", key="atm_leverage")
    with c2:
        start_price = st.number_input("ราคาเริ่มต้น", min_value=0.0, value=4000.0, step=0.1, key="atm_start_price")
        lot_size    = st.number_input("Lot Size / ไม้", min_value=0.0, value=0.01, step=0.01, key="atm_lot")
        contract_sz = st.number_input("Contract Size", min_value=0.0, value=100.0, step=1.0, key="atm_contract")
    with c3:
        liq_price   = st.number_input("Liquidation Price", min_value=0.0, value=1000.0, step=1.0, key="atm_liq_price")
        range_pts   = st.number_input("Range (points)", min_value=1, value=1000, step=100, key="atm_range")
        price_point = st.number_input("1 point = กี่หน่วยราคา", min_value=0.0001, value=0.01, step=0.0001, format="%.4f", key="atm_price_point")

    side = st.radio("ทิศทางกริด", options=["LONG", "SHORT"], horizontal=True, index=0, key="atm_side")

    # จำนวนไม้สูงสุดให้กว้าง ๆ (คุมด้วยทุน/เลเวอเรจในตาราง)
    max_orders = st.slider("จำลองจำนวนไม้ (สูงสุด)", min_value=1, max_value=300, value=120, step=1, key="atm_max_orders")

    st.markdown("---")

    # ---------------- Validate ----------------
    if lot_size <= 0 or contract_sz <= 0 or price_point <= 0 or range_pts <= 0:
        st.error("กรุณากรอก Lot Size, Contract Size, price/point และ Range (points) ให้มากกว่า 0")
        return

    # ---------------- Generate grid ----------------
    prices = _grid_prices(
        start_price=float(start_price),
        n=int(max_orders),
        step_points=int(range_pts),
        price_point=float(price_point),
        side=side,
    )

    # ---------------- Compute (สองเคส: liq=0 และ liq = ค่าอินพุต) ----------------
    rows = []
    cum_cost_0 = 0.0
    cum_margin_0 = 0.0
    cum_cost_liq = 0.0
    cum_margin_liq = 0.0

    for i, p in enumerate(prices, start=1):
        # เคสปกติ (ไม่มี Liq)
        cost_i_0 = float(p) * float(lot_size) * float(contract_sz)
        margin_i_0 = (cost_i_0 / float(leverage)) if leverage > 0 else 0.0
        cum_cost_0 += cost_i_0
        cum_margin_0 += margin_i_0

        # เคสมี Liq: “ต้นทุน” คิดจาก (ราคาที่ออก - liq_price) * lot * contract (ถ้าติดลบ ปรับเป็น 0)
        span = max(float(p) - float(liq_price), 0.0) if side == "LONG" else max(float(liq_price) - float(p), 0.0)
        cost_i_liq = span * float(lot_size) * float(contract_sz)
        margin_i_liq = (cost_i_liq / float(leverage)) if leverage > 0 else 0.0
        cum_cost_liq += cost_i_liq
        cum_margin_liq += margin_i_liq

        rows.append({
            "ไม้ที่": i,
            "ราคาที่ออกไม้": p,

            # เคส Liq = 0
            "ต้นทุน/ไม้ ($)": cost_i_0,
            "มาร์จิ้น/ไม้ ($)": margin_i_0,
            "ต้นทุนรวม ($)": cum_cost_0,
            "มาร์จิ้นรวม ($)": cum_margin_0,

            # เคส Liq = อินพุต (ใช้ชื่อคอลัมน์แบบคงที่)
            "ต้นทุน/ไม้ @Liq ($)": cost_i_liq,
            "มาร์จิ้น/ไม้ @Liq ($)": margin_i_liq,
            "ต้นทุนรวม @Liq ($)": cum_cost_liq,
            "มาร์จิ้นรวม @Liq ($)": cum_margin_liq,
        })

    df = pd.DataFrame(rows)

    # ---------------- Highlight rule ----------------
    # คุมด้วย “เงินทุนที่ต้องใช้” = “มาร์จิ้นรวม” ไม่ให้เกิน balance
    base_cum_margin_col = "มาร์จิ้นรวม ($)"
    liq_cum_margin_col  = "มาร์จิ้นรวม @Liq ($)"

    base_idx = _last_feasible_index(df[base_cum_margin_col].tolist(), float(balance))
    liq_idx  = _last_feasible_index(df[liq_cum_margin_col].tolist(), float(balance))

    # สีไฮไลท์ (สองกรณี)
    base_color = "background-color: rgba(59,130,246,.25);"   # ฟ้าอ่อน
    liq_color  = "background-color: rgba(239,68,68,.25);"    # แดงอ่อน

    def _hl_row(r):
        styles = [''] * len(r)
        if base_idx is not None and r.name == base_idx:
            styles = [base_color] * len(r)
        if liq_idx is not None and r.name == liq_idx:
            # ถ้าชนทั้งคู่ ใช้ pattern ผสม
            if base_idx is not None and r.name == base_idx:
                styles = ["background: linear-gradient(90deg, rgba(59,130,246,.25) 0%, rgba(239,68,68,.25) 100%);"] * len(r)
            else:
                styles = [liq_color] * len(r)
        return styles

    # ---------------- Render ----------------
    st.markdown(
        f"""
        <div style="display:flex; gap:10px; align-items:center; flex-wrap:wrap;">
          <div><b>Symbol:</b> {symbol}</div>
          <div><b>Direction:</b> {side}</div>
          <div><b>Balance:</b> ${balance:,.2f}</div>
          <div><b>Leverage:</b> {int(leverage):,}×</div>
          <div><b>Start:</b> {start_price:,.2f}</div>
          <div><b>Range:</b> {range_pts:,} pts (1 pt = {price_point:.4f})</div>
          <div><b>Lot/ไม้:</b> {lot_size:.2f}</div>
          <div><b>Contract:</b> {contract_sz:,.0f}</div>
          <div><b>Liq:</b> {liq_price:,.2f}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # legend
    st.caption(
        "🔵 แถวสีน้ำเงิน = จำนวนไม้สูงสุดที่ “มาร์จิ้นรวม” ไม่เกิน Balance (เคส Liq = 0)  •  "
        "🔴 แถวสีแดง = จำนวนไม้สูงสุดที่ “มาร์จิ้นรวม” ไม่เกิน Balance (เคส Liq = ที่กำหนด)"
    )

    # ---- ฟอร์แมตตัวเลข: ใช้ชื่อคอลัมน์ 'แบบใหม่' ที่ไม่มีตัวเลขฝังในชื่อ ----
    fmt = {
        "ราคาที่ออกไม้": "{:,.2f}",
        "ต้นทุน/ไม้ ($)": "{:,.2f}",
        "มาร์จิ้น/ไม้ ($)": "{:,.2f}",
        "ต้นทุนรวม ($)": "{:,.2f}",
        "มาร์จิ้นรวม ($)": "{:,.2f}",
        "ต้นทุน/ไม้ @Liq ($)": "{:,.2f}",
        "มาร์จิ้น/ไม้ @Liq ($)": "{:,.2f}",
        "ต้นทุนรวม @Liq ($)": "{:,.2f}",
        "มาร์จิ้นรวม @Liq ($)": "{:,.2f}",
    }

    sty = (
        df.style
          .format(fmt)
          .apply(_hl_row, axis=1)
          .set_table_styles([{'selector': 'th', 'props': [('text-align', 'center')]}])
          .set_properties(**{'text-align': 'center'})
    )
    st.dataframe(sty, use_container_width=True, height=min(560, (len(df) + 2) * 33))

    # สรุปผลลัพธ์สองกรณี (ตำแหน่งที่แนะนำ)
    st.markdown("---")
    colA, colB = st.columns(2)
    with colA:
        if base_idx is not None:
            st.success(
                f"🔵 เคส Liq=0: เปิดได้สูงสุด **{base_idx+1:,} ไม้**  | "
                f"มาร์จิ้นรวมประมาณ **${df.loc[base_idx, base_cum_margin_col]:,.2f}** (≤ ${balance:,.2f})"
            )
        else:
            st.warning("🔵 เคส Liq=0: มาร์จิ้นของไม้แรกเกิน Balance")
    with colB:
        if liq_idx is not None:
            st.success(
                f"🔴 เคส Liq={liq_price:,.2f}: เปิดได้สูงสุด **{liq_idx+1:,} ไม้**  | "
                f"มาร์จิ้นรวมประมาณ **${df.loc[liq_idx, liq_cum_margin_col]:,.2f}** (≤ ${balance:,.2f})"
            )
        else:
            st.warning(f"🔴 เคส Liq={liq_price:,.2f}: มาร์จิ้นของไม้แรกเกิน Balance")