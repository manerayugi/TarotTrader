# posutionsizing.py
from __future__ import annotations
import pandas as pd
import streamlit as st

from func import (
    XAUUSD_SPEC, maxlot_theoretical, lots_from_stops, loss_to_amount_and_pct
)

def render_tab():
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

        # สูตรสั้น ๆ
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