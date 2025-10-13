# gtt_pro_grd.py
from __future__ import annotations

import math
from typing import List, Dict

import pandas as pd
import streamlit as st

from func import hr, header, round_to, grid_levels, last_feasible_index

# ---------------- Presets ----------------
SYMBOL_PRESETS: Dict[str, Dict[str, float]] = {
    # XAUUSD: 1 point = 0.01 USD, contract 100 oz
    "XAUUSD": {"point_value": 0.01, "contract_size": 100.0},
    # "BTCUSD": {"point_value": 1.0, "contract_size": 1.0},  # ตัวอย่าง
}

# $/point/lot (ต้องสอดคล้องกับหน้า MM) — ของคุณ = 1
VPP_PER_LOT = 1.0


def _max_orders_by_buffer(balance: float, lot: float, buffer_pts: float, spacing_pts: float, vpp: float) -> int:
    """
    เติมครบ N ไม้แล้วยังต้องทนได้อีก buffer_pts จุด:
      L(N) = lot * vpp * [ N*buffer_pts + spacing_pts * N(N-1)/2 ] <= balance
    หา N สูงสุดแบบควอดราติก (ปัดลง)
    """
    if min(balance, lot, buffer_pts, spacing_pts, vpp) <= 0:
        return 0

    A = (lot * vpp) * (spacing_pts / 2.0)            # > 0
    B = (lot * vpp) * (buffer_pts - spacing_pts/2.0) # อาจบวก/ลบได้ แต่ในทางปฏิบัติมักบวก
    C = - balance

    disc = B*B - 4*A*C
    if disc < 0:
        return 0

    n_pos = (-B + math.sqrt(disc)) / (2*A)  # A>0 → ขอบบน
    return max(0, math.floor(n_pos)) if n_pos > 0 else 0


def _remaining_buffer_points(balance: float, lot: float, spacing_pts: float, n_orders: int, vpp_per_lot: float = VPP_PER_LOT) -> float:
    """
    จำนวน 'จุด' ที่พอร์ตยังพอทนได้หลังจาก 'เปิดครบ n_orders ไม้' (ทางเสียเปรียบต่อ)
    จากอสมการ:
      L(N) = lot * vpp * [ N*X + S * N(N-1)/2 ]  <= balance
      ⇒ X_max = ( balance/(lot*vpp) - S*N*(N-1)/2 ) / N
    """
    if min(balance, lot, spacing_pts, n_orders, vpp_per_lot) <= 0:
        return 0.0
    cap = balance / (lot * vpp_per_lot)
    x = (cap - spacing_pts * n_orders * (n_orders - 1) / 2.0) / float(n_orders)
    return max(0.0, x)


def _buffer_badge_html(remain_pts: float, required_pts: float) -> str:
    """
    Badge สี:
      - เขียว: remain >= required
      - เหลือง: remain >= 0.3 * required (แต่ < required)
      - แดง: น้อยกว่านั้น
    """
    if required_pts <= 0:
        color = "linear-gradient(0deg,#374151,#374151)"
        txt = f"{remain_pts:,.0f} pts"
    else:
        if remain_pts >= required_pts:
            color = "linear-gradient(0deg,#16a34a,#16a34a)"  # green-600
        elif remain_pts >= 0.3 * required_pts:
            color = "linear-gradient(0deg,#f59e0b,#f59e0b)"  # amber-500
        else:
            color = "linear-gradient(0deg,#ef4444,#ef4444)"  # red-500
        txt = f"{remain_pts:,.0f} / {required_pts:,.0f} pts"
    return (
        f"<span style='display:inline-block;padding:4px 10px;border-radius:999px;"
        f"color:white;background:{color};font-weight:600;font-size:0.9rem'>{txt}</span>"
    )


def render_grd_tab(default_symbol: str = "XAUUSD"):
    header("🧮 GRD — Grid Risk Designer", "Manual Mean/SD + Risk presets")
    st.caption("กำหนด Mean / SD เอง แล้วเลือกระดับความเสี่ยงเพื่อแนะนำ Spacing & Coverage (TP = Spacing)")
    hr()

    # ---------- หลัก (4 คอลัมน์ / 1 แถว) ----------
    c0a, c0b, c0c, c0d = st.columns(4)
    with c0a:
        symbol = st.selectbox(
            "สัญลักษณ์ (Preset)",
            options=list(SYMBOL_PRESETS.keys()),
            index=list(SYMBOL_PRESETS.keys()).index(default_symbol) if default_symbol in SYMBOL_PRESETS else 0,
            key="grd_symbol",
        )
    with c0b:
        balance = st.number_input("Balance ($)", min_value=0.0, value=10_000.0, step=100.0, key="grd_balance")
    with c0c:
        leverage = st.number_input("Leverage", min_value=1, value=1000, step=50, format="%d", key="grd_leverage")
    with c0d:
        lot_size = st.number_input("Lot/Order", min_value=0.0, value=0.01, step=0.01, key="grd_lot")

    # ดึงค่าจาก preset
    pv = SYMBOL_PRESETS[symbol]["point_value"]
    contract_sz = SYMBOL_PRESETS[symbol]["contract_size"]
    st.caption(f"Preset: 1 pt = {pv:.4f} • Contract size = {contract_sz:,.0f}")

    st.markdown("---")
    colm1, colm2, colm3 = st.columns([1, 1, 1])
    with colm1:
        mean_pts = st.number_input("Mean range (points)", min_value=0.0, value=2000.0, step=50.0, key="grd_mean")
    with colm2:
        sd_pts = st.number_input("SD of range (points)", min_value=0.0, value=1000.0, step=50.0, key="grd_sd")
    with colm3:
        buffer_pts = st.number_input(
            "Buffer (points)",
            min_value=0,
            value=50_000,  # ✅ ค่าตั้งต้น 50,000 และ “นำมาคิดจริง”
            step=1000,
            help="หลังเติมครบ N ไม้ ยังต้องทนได้อีกเท่านี้ (เช่น 50,000 points)",
            key="grd_buffer",
        )

    st.markdown("---")
    st.markdown("### 🎛️ Risk presets")
    risk_mode = st.radio("ระดับความเสี่ยง", ["Low", "Medium", "High"], horizontal=True, index=1, key="grd_risk")

    # ---------- ค่าที่แนะนำจาก Risk Presets ----------
    if risk_mode == "Low":
        spacing_suggest  = round_to(max(50, mean_pts * 1.00), 50)
        coverage_suggest = round_to(max(1000, mean_pts + 3.0 * sd_pts), 500)
    elif risk_mode == "High":
        spacing_suggest  = round_to(max(50, mean_pts * 0.25), 50)
        coverage_suggest = round_to(max(1000, mean_pts + 1.0 * sd_pts), 500)
    else:  # Medium
        spacing_suggest  = round_to(max(50, mean_pts * 0.50), 50)
        coverage_suggest = round_to(max(1000, mean_pts + 2.0 * sd_pts), 500)

    colr1, colr2, colr3 = st.columns(3)
    with colr1:
        spacing_pts = int(st.number_input("Spacing (points)", min_value=50, value=int(spacing_suggest), step=50, key="grd_spacing"))
    with colr2:
        coverage_pts = int(st.number_input("Coverage (points)", min_value=spacing_pts, value=int(coverage_suggest), step=100, key="grd_coverage"))
    with colr3:
        ref_price = st.number_input("ราคาเริ่มต้น (USD)", value=4000.0, step=0.1, format="%.2f", key="grd_ref")  # ราคาอ้างอิงบนสุด

    # TP = Spacing (ตัด input ออก)
    tp_points = spacing_pts

    direction = st.radio("Direction", options=["LONG", "SHORT"], horizontal=True, index=0, key="grd_dir")

    # จำนวนไม้แปรผันตาม coverage/spacing (ไม่มี input max orders อีกแล้ว)
    max_orders_cov = int(math.floor(coverage_pts / spacing_pts) + 1)
    max_orders_cov = min(max_orders_cov, 400)  # กันตารางใหญ่เกินไป

    # ---------- สร้างกริด ----------
    side_flag = "LONG" if direction.startswith("LONG") else "SHORT"
    levels = grid_levels(ref_price, max_orders_cov, spacing_pts, direction=side_flag, point_value=pv)

    # ---------- ตารางต้นทุน/มาร์จิ้น ----------
    rows: List[Dict] = []
    cum_cost = 0.0
    cum_margin = 0.0
    for i, price in enumerate(levels, start=1):
        cost_i = float(price) * float(lot_size) * float(contract_sz)
        margin_i = (cost_i / float(leverage)) if leverage > 0 else 0.0
        cum_cost += cost_i
        cum_margin += margin_i

        tp_price = round(price + (tp_points * pv) * (1 if side_flag == "LONG" else -1), 2)

        rows.append({
            "Order #": i,
            "Price": price,
            "Lot": lot_size,
            "TP (pts)": tp_points,
            "TP price": tp_price,
            "Cost/Order ($)": cost_i,
            "Margin/Order ($)": margin_i,
            "Cum Cost ($)": cum_cost,
            "Cum Margin ($)": cum_margin,
        })

    df_manual = pd.DataFrame(rows)

    # ---------- ไฮไลท์ 2 เงื่อนไข ----------
    # 1) จำกัดด้วยทุน/มาร์จิ้นรวม ≤ balance (ฟ้า)
    idx_by_margin = last_feasible_index(df_manual["Cum Margin ($)"].tolist(), float(balance))

    # 2) จำกัดด้วย Buffer: L(N) ≤ balance (แดง)
    n_max_buffer = _max_orders_by_buffer(
        balance=float(balance),
        lot=float(lot_size),
        buffer_pts=float(buffer_pts),
        spacing_pts=float(spacing_pts),
        vpp=float(VPP_PER_LOT),
    )
    # ให้ไม่เกินจำนวนแถวที่มี (coverage)
    idx_by_buffer = (n_max_buffer - 1) if n_max_buffer > 0 else None
    if idx_by_buffer is not None and idx_by_buffer >= len(df_manual):
        idx_by_buffer = len(df_manual) - 1 if len(df_manual) > 0 else None
    if idx_by_buffer is not None and idx_by_buffer < 0:
        idx_by_buffer = None

    # สีไฮไลท์
    base_color = "background-color: rgba(59,130,246,.25);"   # ฟ้า
    buf_color  = "background-color: rgba(239,68,68,.25);"    # แดง

    def _hl_row(r):
        styles = [''] * len(r)
        i = r.name
        both = (idx_by_margin is not None and i == idx_by_margin) and (idx_by_buffer is not None and i == idx_by_buffer)
        if both:
            styles = ["background: linear-gradient(90deg, rgba(59,130,246,.25) 0%, rgba(239,68,68,.25) 100%); font-weight:600;"] * len(r)
        else:
            if idx_by_margin is not None and i == idx_by_margin:
                styles = [base_color] * len(r)
            if idx_by_buffer is not None and i == idx_by_buffer:
                styles = [buf_color] * len(r)
        return styles

    st.dataframe(
        df_manual.style
            .format({
                "Price": "{:,.2f}",
                "Lot": "{:.2f}",
                "TP (pts)": "{:,.0f}",
                "TP price": "{:,.2f}",
                "Cost/Order ($)": "{:,.2f}",
                "Margin/Order ($)": "{:,.2f}",
                "Cum Cost ($)": "{:,.2f}",
                "Cum Margin ($)": "{:,.2f}",
            })
            .apply(_hl_row, axis=1)
            .set_table_styles([{'selector': 'th', 'props': [('text-align', 'center')]}])
            .set_properties(**{'text-align': 'center'}),
        use_container_width=True,
        height=min(560, (len(df_manual)+2)*33)
    )

    # ---------- สรุปผลลัพธ์ + แสดง Buffer ที่ยังทนได้ ----------
    st.markdown("---")
    colA, colB, colC = st.columns(3)

    with colA:
        if idx_by_margin is not None:
            nA = idx_by_margin + 1
            cum_margin_A = float(df_manual.loc[idx_by_margin, "Cum Margin ($)"])
            remain_A = _remaining_buffer_points(
                balance=float(balance),
                lot=float(lot_size),
                spacing_pts=int(spacing_pts),
                n_orders=int(nA),
                vpp_per_lot=float(VPP_PER_LOT),
            )
            badge_A = _buffer_badge_html(remain_A, float(buffer_pts))
            st.success(
                f"🔵 ตามมาร์จิ้น: เปิดได้ **{nA:,} ไม้** | "
                f"Cum Margin ≈ **${cum_margin_A:,.2f}** (≤ ${balance:,.2f})"
            )
            st.markdown(f"🛡️ <b>Buffer ที่ยังทนได้</b>: {badge_A}", unsafe_allow_html=True)
        else:
            st.warning("🔵 ตามมาร์จิ้น: ทุนไม่พอสำหรับไม้แรก")

    with colB:
        if idx_by_buffer is not None:
            nB = idx_by_buffer + 1
            # สำหรับกรณี buffer constraint, remain_B โดยนิยามควร ≥ buffer_pts เสมอ
            remain_B = _remaining_buffer_points(
                balance=float(balance),
                lot=float(lot_size),
                spacing_pts=int(spacing_pts),
                n_orders=int(nB),
                vpp_per_lot=float(VPP_PER_LOT),
            )
            badge_B = _buffer_badge_html(remain_B, float(buffer_pts))
            st.info(
                f"🔴 ตาม Buffer: เปิดได้ **{nB:,} ไม้** | "
                f"L(N) ≤ Balance เมื่อ B = {int(buffer_pts):,} pts, S = {int(spacing_pts):,} pts"
            )
            st.markdown(f"🛡️ <b>Buffer ที่ยังทนได้</b>: {badge_B}", unsafe_allow_html=True)
        else:
            st.warning("🔴 ตาม Buffer: เงื่อนไข B/S ทำให้เปิดไม่ได้แม้ 1 ไม้ (ลองลด lot หรือเพิ่ม spacing)")

    with colC:
        # คำแนะนำสุดท้าย = min(สองเงื่อนไขที่มีค่า)
        candidates = [x for x in [idx_by_margin, idx_by_buffer] if x is not None]
        if candidates:
            best_idx = min(candidates)
            st.markdown(
                f"""
                <div style='border:1px solid #444; padding:10px 12px; border-radius:10px;'>
                  <b>✅ แนะนำ:</b> เปิด <b>{best_idx+1:,} ไม้</b> 
                  (ค่าน้อยสุดของข้อจำกัด “ทุน/มาร์จิ้น” และ “Buffer”)
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            st.error("ไม่มีจำนวนไม้ที่ผ่านทั้งสองข้อจำกัด — ปรับพารามิเตอร์ใหม่")