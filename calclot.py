# calelot.py
from __future__ import annotations
import math
import pandas as pd
import streamlit as st

from func import (
    SYMBOL_PRESETS, fetch_price_yf, margin_per_1lot, max_lot, maxlot_theoretical,
    value_per_point_per_lot, value_per_pip_per_lot
)

def render_tab():
    st.subheader("🧮 การออก Lot (Max & Optimal Lot)")

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
            <li>• <b>Leverage</b> — อัตราทด (เช่น 1:1000 → ใส่ 1000)</li>
            <li>• <b>Price</b> — ราคาปัจจุบัน</li>
            <li>• <b>ContractSize</b> — ขนาดสัญญา</li>
            <li>• <b>Free Margin %</b> — กันไว้เพื่อความปลอดภัย</li>
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
    st.markdown("""
    <div style='text-align:center; margin:12px 0 6px 0;'>
    <hr style='width: 360px; border: 1px solid #555; margin: 8px auto;'/>
    </div>
    """, unsafe_allow_html=True)

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
            <li>• <b>ทุน($)</b> — มูลค่าทุนในบัญชี</li>
            <li>• <b>Risk (%)</b> — สัดส่วนความเสี่ยงต่อไม้</li>
            <li>• <b>Distance</b> — ระยะ SL (points/pips)</li>
            <li>• <b>$/point/lot</b> — มูลค่าการเคลื่อนไหวต่อจุด</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)

    distance_points = float(distance_input) * (spec.pip_points if unit == "pips" else 1.0)
    vpp = value_per_point_per_lot(spec)
    st.caption(f"คำนวณจากสูตร: lot = (ทุนที่ยอมเสีย) / (ระยะ {distance_points:.0f} points × ${vpp:.2f}/point/lot)")

    if st.button("คำนวณ OptimalLot"):
        risk_amount = balance * (risk_percent / 100.0) if (mode_safe and risk_percent > 0) else balance
        lots_raw = risk_amount / (distance_points * vpp) if (distance_points > 0 and vpp > 0) else 0.0

        step = getattr(spec, "lot_step", 0.01)
        min_lot = getattr(spec, "min_lot", 0.01)
        lots_adj = max(min_lot, math.floor(lots_raw / step) * step if step > 0 else lots_raw)

        maxlot_theo = maxlot_theoretical(balance, float(leverage), float(price), spec) if (price > 0 and leverage > 0) else 0.0
        lots_final = min(lots_adj, maxlot_theo) if maxlot_theo > 0 else lots_adj

        pnl_stop = - (lots_final * distance_points * vpp)

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
    st.markdown("#### สรุปมูลค่าการเคลื่อนไหว (ต่อ 1 lot)")
    df = pd.DataFrame({
        "รายการ": ["$/point/lot", f"$/pip/lot (1 pip = {spec.pip_points} points)"],
        "Value ($)": [value_per_point_per_lot(spec), value_per_pip_per_lot(spec)]
    })
    st.dataframe(df, use_container_width=True)