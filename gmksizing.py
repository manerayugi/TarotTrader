# gmksizing.py
from __future__ import annotations
import pandas as pd
import streamlit as st

from func import (
    SYMBOL_PRESETS, parse_gmk_signal, _dist_points, _tp_points,
    value_per_point_per_lot, pnl_usd, _DEFAULT_RISK_SET
)

def render_tab():
    st.subheader("📨 GMK Signal → Lot (คำนวณจากความเสี่ยง)")

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

        spec = SYMBOL_PRESETS[symbol_name]

        c3, c4 = st.columns(2)
        with c3:
            entry = st.number_input("Entry", value=float(parsed.get("entry") or 0.0), step=0.01, min_value=0.0)
            sl    = st.number_input("SL",    value=float(parsed.get("sl")    or 0.0), step=0.01, min_value=0.0)
        with c4:
            tp_list = parsed.get("tps") or []
            selected_tp_val = None
            if tp_list:
                options = [f"TP{i+1} — {tp_list[i]:,.2f}" for i in range(len(tp_list))]
                idx = st.selectbox("TP ที่ต้องการ", options=list(range(len(tp_list))), format_func=lambda i: options[i])
                selected_tp_val = tp_list[idx]
            manual_tp = st.number_input("หรือกรอก TP เอง (ถ้าต้องการ)", value=0.0, step=0.01, min_value=0.0)
            if manual_tp > 0:
                selected_tp_val = manual_tp

            balance = st.number_input("ทุน ($)", value=1000.0, step=100.0, min_value=0.0)

        loss_mode = st.selectbox("กรอก Risk เป็น", ["%", "$"], index=0)
        if loss_mode == "%":
            loss_val = st.number_input("Risk (%)", value=1.0, step=0.25, min_value=0.0)
            risk_amount = balance * (loss_val / 100.0)
            st.caption(f"Risk ที่ใช้คำนวณ ≈ **${risk_amount:,.2f}**")
        else:
            loss_val = st.number_input("Risk ($)", value=10.0, step=5.0, min_value=0.0)
            risk_amount = loss_val
            st.caption(f"คิดเป็นสัดส่วน ≈ **{(risk_amount/balance*100 if balance>0 else 0):.2f}%**")

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

        dist_points_sl = _dist_points(entry, sl, spec)
        vpp = value_per_point_per_lot(spec)
        st.caption(
            f"Distance @SL ≈ **{dist_points_sl:,.0f} points**, "
            f"Value ≈ **${vpp:.2f}/point/lot**"
        )

        # ตัวแปรส่งต่อ (ตารางฝั่งขวา)
        shared = {
            "entry": entry, "sl": sl, "spec": spec, "balance": balance,
            "tp_values": (parsed.get("tps") or [])[:6]
        }

        if st.button("คำนวณ Lot ตาม Risk ที่กรอก", type="primary"):
            if dist_points_sl <= 0 or vpp <= 0:
                st.error("กรุณาตรวจสอบ Entry/SL ให้ถูกต้อง (ระยะไป SL ต้อง > 0)")
            else:
                lots = risk_amount / (dist_points_sl * vpp)
                pnl_stop = -lots * dist_points_sl * vpp
                dist_points_sel_tp = _dist_points(entry, selected_tp_val, spec) if selected_tp_val else 0.0
                pnl_take_sel = lots * dist_points_sel_tp * vpp if dist_points_sel_tp > 0 else None

                st.success(f"Lot ที่ควรออก ≈ **{lots:.2f} lot**")
                st.caption(f"Risk = **${risk_amount:,.2f}**, Distance @SL = **{dist_points_sl:,.0f} points**, $/pt/lot = **${vpp:.2f}**")
                m1, m2 = st.columns(2)
                with m1:
                    st.metric("P/L @SL ($)", f"{pnl_stop:,.2f}")
                with m2:
                    st.metric(f"P/L @TP (เลือก)", f"{pnl_take_sel:,.2f}" if pnl_take_sel is not None else "-")

                tp_values = shared["tp_values"]
                if tp_values:
                    rows = []
                    for i, tpv in enumerate(tp_values, start=1):
                        d_tp = _dist_points(entry, tpv, spec)
                        pnl_tp = lots * d_tp * vpp if d_tp > 0 else 0.0
                        rows.append({"TP": f"TP{i}", "Price": tpv, "Distance (pts)": d_tp, "P/L ($)": pnl_tp})
                    df_tp = pd.DataFrame(rows).style.format({
                        "Price": "{:,.2f}", "Distance (pts)": "{:,.0f}", "P/L ($)": "{:,.2f}"
                    }).set_properties(**{'text-align':'center'})
                    st.markdown("**P/L @TP1–TP6 (ตามสัญญาณ)**")
                    st.dataframe(df_tp, use_container_width=True, height=min(330, (len(rows)+2)*33))

    with right:
        st.markdown("#### ตารางคำนวณ Lot ตามความเสี่ยง + ผลลัพธ์ที่ TP แต่ละระดับ")

        entry = shared.get("entry")
        sl    = shared.get("sl")
        spec  = shared.get("spec")
        balance = shared.get("balance")
        tp_values = shared.get("tp_values")

        if not (entry and sl):
            st.info("ใส่ Entry/SL ทางซ้ายเพื่อดูตารางนี้")
            return

        dist_points_sl = _dist_points(entry, sl, spec)
        vpp = value_per_point_per_lot(spec)
        tp_values = tp_values[:6] if tp_values else []

        tp_cols = [f"P/L @TP{i+1} ($)" for i in range(len(tp_values))]

        rows = []
        for rp in _DEFAULT_RISK_SET:
            risk_amt = balance * (rp / 100.0)
            lots = risk_amt / (dist_points_sl * vpp) if (dist_points_sl > 0 and vpp > 0) else 0.0

            pl_tps = []
            for tp in tp_values:
                tp_pts = _tp_points(entry, tp, spec)
                pnl_tp = pnl_usd(lots, tp_pts, spec) if lots > 0 else 0.0
                pl_tps.append(pnl_tp)

            row = {"Risk (%)": rp, "Risk ($)": risk_amt, "Lot": lots}
            for i, pnl in enumerate(pl_tps):
                row[tp_cols[i]] = pnl
            rows.append(row)

        if rows:
            df = pd.DataFrame(rows)
            fmt_map = {"Risk (%)": "{:.0f}", "Risk ($)": "{:,.2f}", "Lot": "{:.2f}"}
            for c in tp_cols:
                fmt_map[c] = "{:,.2f}"
            sty = df.style.format(fmt_map, na_rep="-") \
                          .set_table_styles([{'selector':'th','props':[('text-align','center')]}]) \
                          .set_properties(**{'text-align':'center'})
            st.dataframe(sty, use_container_width=True, height=(len(df)+2)*33)
        else:
            st.info("ไม่มี TP ในสัญญาณ — ตารางด้านขวาจะแสดงเมื่อมี TP")