# gmkplaning.py
from __future__ import annotations
import math
import pandas as pd
import streamlit as st

from func import (
    SYMBOL_PRESETS, parse_gmk_signal, _dist_points, value_per_point_per_lot
)

def render_tab():
    st.subheader("📑 GMK Signal Planning")

    tab_mtg, tab_grid = st.tabs(["มาติงเกล (coming soon)", "กริด (Grid Planner)"])

    with tab_mtg:
        st.info("ฟีเจอร์มาติงเกลกำลังมาเร็วๆ นี้ ✨")

    with tab_grid:
        # สูตร
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

        left, right = st.columns([1, 1.15])

        with left:
            st.markdown("#### ข้อความสัญญาณ")
            sig_text = st.text_area(
                "วางสัญญาณที่นี่",
                value=("XAUUSD.mg M5 SELL @3774.03\n"
                       "SL=3785.34\n"
                       "TP1=3771.77\nTP2=3769.51\nTP3=3764.98\nTP4=3760.46\nTP5=3755.93\nTP6=3751.41"),
                height=140,
                help="รองรับ .mg / SL=... / TP1..TP6=... (ใช้ข้อมูลจากสัญญาณเท่านั้น)"
            )
            parsed = parse_gmk_signal(sig_text)

            symbol_name = parsed.get("symbol") or "XAUUSD"
            direction   = parsed.get("direction")
            entry       = parsed.get("entry")
            sl          = parsed.get("sl")
            tp_values   = (parsed.get("tps") or [])[:6]

            spec = SYMBOL_PRESETS.get(symbol_name)
            vpp  = value_per_point_per_lot(spec)
            dist_pts = _dist_points(entry, sl, spec)

            if entry and sl:
                st.caption(f"Distance Entry→SL ≈ **{dist_pts:,.0f} points**, $/pt/lot ≈ **${vpp:.2f}**")
            else:
                st.warning("สัญญาณไม่ครบ (ต้องมี Entry และ SL) — โปรดตรวจสอบ")

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

            lot_step = max(spec.lot_step, 0.01)
            min_lot  = max(spec.min_lot, lot_step)

            n_orders_options = []
            total_units = 0
            quant_total_lot = 0.0

            if all([entry, sl, direction in ("LONG", "SHORT"), dist_pts > 0, vpp > 0, risk_amount > 0]):
                total_lot_raw = risk_amount / (dist_pts * vpp)

                loss_one_min = min_lot * vpp * dist_pts
                if risk_amount < loss_one_min - 1e-12:
                    st.warning("แม้เพียง 1 ไม้ (min lot) ก็เกิน Risk → เปิดได้เพียง 1 ไม้ขนาดขั้นต่ำ")
                    quant_total_lot = min_lot
                    total_units = int(round(min_lot / lot_step))
                else:
                    total_units = int(math.floor(total_lot_raw / lot_step + 1e-9))
                    quant_total_lot = total_units * lot_step

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

            sel_orders = None
            if n_orders_options:
                sel_orders = st.selectbox(
                    "จำนวนไม้ (เฉพาะค่าที่หาร Total Lot ลงตัว)",
                    options=n_orders_options,
                    index=min(len(n_orders_options)-1, 0)
                )

            go = False
            if sel_orders is not None:
                go = st.button("🔧 วางแผนกริดตาม Risk", type="primary", use_container_width=True)

        with right:
            st.markdown("#### ผลการวางแผนกริด")

            if not (entry and sl and direction in ("LONG", "SHORT")):
                st.info("กรุณาวางสัญญาณที่มี Entry / SL และทิศทางให้ครบ")
                return
            if dist_pts <= 0 or vpp <= 0:
                st.error("Distance Entry→SL ต้อง > 0 และ $/pt/lot ต้อง > 0")
                return
            if not n_orders_options:
                st.info("ปรับทุน/Risk ให้ได้ Total Lot > 0 แล้วเลือกจำนวนไม้ที่หารลงตัว")
                return
            if not go:
                st.info("เลือกจำนวนไม้ทางซ้าย แล้วกดปุ่มเพื่อดูผลลัพธ์")
                return

            N = int(sel_orders)
            per_lot = (quant_total_lot / N) if N > 0 else 0.0

            sgn = 1 if direction == "LONG" else -1
            entries = [entry + (sl - entry) * (k / N) for k in range(N)]
            step_pts = dist_pts / N

            total_pl_sl = 0.0
            for eprice in entries:
                move_pts = (sl - eprice) / spec.price_point * sgn
                total_pl_sl += per_lot * vpp * move_pts

            be_price = sum(entries) / len(entries) if N >= 2 else None

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

            if not tp_values:
                st.warning("สัญญาณไม่มี TP — ตารางกำไร TP1..TP6 แสดงไม่ได้")
            else:
                rows = []
                for k_fill in range(1, N + 1):
                    filled_entries = entries[:k_fill]
                    row = {"Filled Orders": k_fill}
                    for i, tp in enumerate(tp_values, start=1):
                        pl = 0.0
                        for eprice in filled_entries:
                            move_pts = (tp - eprice) / spec.price_point * sgn
                            pl += per_lot * vpp * move_pts
                        row[f"P/L @TP{i} ($)"] = pl
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