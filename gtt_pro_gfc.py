# gtt_pro_gfc.py
from __future__ import annotations

import io
import math
from typing import List, Dict

import pandas as pd
import streamlit as st

from func import hr, header, ensure_ohlc_columns, atr_points, round_to, grid_levels, last_feasible_index


def render_gfc_tab(default_symbol: str = "XAUUSD"):
    header("🧮 GTT PRO — Generate From CSV", "คำนวณ Mean/SD/ATR จากไฟล์ราคา แล้วออกแบบกริด")
    st.caption("อัปโหลดไฟล์ OHLC (daily) → เลือกช่วงเวลา → สร้างกริดด้วยสถิติที่ได้")
    hr()

    # ------ พารามิเตอร์ร่วม ------
    c0a, c0b, c0c = st.columns(3)
    with c0a:
        symbol = st.text_input("Symbol", value=default_symbol, key="gfc_symbol")
        point_value = st.number_input("1 point = ? price unit", min_value=0.0001, value=0.01,
                                      step=0.0001, format="%.4f", key="gfc_point")
    with c0b:
        balance = st.number_input("Balance ($)", min_value=0.0, value=10_000.0, step=100.0, key="gfc_balance")
        leverage = st.number_input("Leverage", min_value=1, value=1000, step=50, format="%d", key="gfc_leverage")
    with c0c:
        lot_size = st.number_input("Lot/Order", min_value=0.0, value=0.01, step=0.01, key="gfc_lot")
        contract_sz = st.number_input("Contract Size", min_value=0.0, value=100.0, step=1.0, key="gfc_contract")

    st.markdown("---")
    st.markdown("### 📂 Upload CSV (OHLC)")
    up = st.file_uploader("ต้องมีคอลัมน์: date หรือ time, และ high/low/close", type=["csv"], key="gfc_csv")
    if not up:
        st.info("อัปโหลดไฟล์เพื่อเริ่มคำนวณ")
        return

    # ------ เตรียมข้อมูล ------
    try:
        df_raw = pd.read_csv(io.BytesIO(up.read()))
        df = ensure_ohlc_columns(df_raw, point_value=point_value)
    except Exception as e:
        st.error(f"อ่านไฟล์ไม่สำเร็จ: {e}")
        return

    # default date range: since 2025-01-01
    st.markdown("#### Data filters")
    min_date = df["date"].min().date()
    max_date = df["date"].max().date()
    default_start = max(min_date, pd.to_datetime("2025-01-01").date())
    start_date, end_date = st.date_input(
        "Use date range",
        value=(default_start, max_date),
        min_value=min_date, max_value=max_date,
        key="gfc_daterange"
    )
    mask = (df["date"].dt.date >= start_date) & (df["date"].dt.date <= end_date)
    df = df.loc[mask].reset_index(drop=True)
    st.caption(f"Rows after filter: {len(df):,}")
    hr(300)

    # ------ Volatility ------
    st.markdown("### 📊 Volatility (from file)")
    colm1, colm2, colm3, colm4 = st.columns(4)
    window = int(colm1.number_input("ATR window", value=14, min_value=2, max_value=300, step=1, key="gfc_win"))
    atr_method = colm2.selectbox("ATR method", ["RMA", "EMA", "SMA"], index=0, key="gfc_method")
    atr_mult_for_spacing = colm3.number_input("ATR× for spacing", value=0.40, step=0.05, min_value=0.05, key="gfc_atrx")
    step_round = int(colm4.number_input("Round spacing to (pts)", value=50, step=50, min_value=10, key="gfc_round"))

    df["ATR_point"] = atr_points(df, window=window, method=atr_method)
    mean_pts = float(df["range_point"].mean())
    sd_pts = float(df["range_point"].std())
    atr_med = float(df["ATR_point"].median())

    colx1, colx2, colx3 = st.columns(3)
    colx1.metric("Mean range (pts)", f"{mean_pts:,.0f}")
    colx2.metric("SD (pts)", f"{sd_pts:,.0f}")
    colx3.metric(f"ATR{window} median (pts)", f"{atr_med:,.0f}")

    # ------ Grid design ------
    st.markdown("### 🧩 Grid design (from volatility)")
    ref_price = st.number_input("Reference price (USD)", value=float(df['close'].iloc[-1]),
                                step=0.1, format="%.2f", key="gfc_ref")
    direction = st.radio("Direction", options=["LONG (Buy-only)", "SHORT"], horizontal=True, index=0, key="gfc_dir")

    spacing_from_atr = round_to(atr_med * atr_mult_for_spacing, step_round)
    k = st.slider("k for Mean ± k·SD coverage", 1.0, 3.0, 2.5, 0.5, key="gfc_k")
    coverage_from_stats = round_to((mean_pts + k * sd_pts), 500)

    colg1, colg2, colg3 = st.columns(3)
    spacing_pts = int(colg1.number_input("Spacing (points)", value=max(50, spacing_from_atr),
                                         step=step_round, min_value=step_round, key="gfc_spacing"))
    coverage_pts = int(colg2.number_input("Coverage downwards (points)", value=max(1000, coverage_from_stats),
                                          step=500, min_value=spacing_pts, key="gfc_coverage"))
    max_orders_cov = int(math.floor(coverage_pts / spacing_pts) + 1)
    max_show = int(colg3.number_input("Max orders to show", value=min(120, max_orders_cov),
                                      min_value=1, step=1, key="gfc_show"))

    tp_points = int(st.number_input("TP per order (points)", value=int(spacing_pts),
                                    step=step_round, min_value=step_round, key="gfc_tp"))

    # ------ Compute ------
    side_flag = "LONG" if direction.startswith("LONG") else "SHORT"
    levels = grid_levels(ref_price, min(max_orders_cov, max_show), spacing_pts, direction=side_flag, point_value=point_value)

    rows: List[Dict] = []
    cum_cost = 0.0
    cum_margin = 0.0
    for i, price in enumerate(levels, start=1):
        cost_i = float(price) * float(lot_size) * float(contract_sz)
        margin_i = (cost_i / float(leverage)) if leverage > 0 else 0.0
        cum_cost += cost_i
        cum_margin += margin_i

        tp_price = round(price + (tp_points * point_value) * (1 if side_flag == "LONG" else -1), 2)

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
    df_grid = pd.DataFrame(rows)

    last_idx = last_feasible_index(df_grid["Cum Margin ($)"].tolist(), float(balance))

    def _hl_row(r):
        if last_idx is not None and r.name == last_idx:
            return ['background-color: rgba(59,130,246,.25); font-weight: 600;'] * len(r)
        return [''] * len(r)

    st.dataframe(
        df_grid.style
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
        height=min(560, (len(df_grid)+2)*33)
    )

    st.markdown("---")
    if last_idx is not None:
        st.success(
            f"แนะนำเปิดได้ **{last_idx+1:,} ไม้** ภายใต้ทุน ${balance:,.2f} → "
            f"มาร์จิ้นรวมประมาณ **${df_grid.loc[last_idx, 'Cum Margin ($)']:,.2f}**"
        )
    else:
        st.warning("ทุนไม่พอสำหรับแม้แต่ไม้แรก (ลองลด lot/ไม้ หรือเพิ่ม spacing)")

    st.download_button(
        "ดาวน์โหลดตาราง (CSV)",
        data=df_grid.to_csv(index=False).encode("utf-8"),
        file_name=f"gttpro_{symbol}_{side_flag.lower()}.csv",
        mime="text/csv",
        use_container_width=True
    )

    st.caption(
        f"Symbol: {symbol} • Direction: {side_flag} • Balance: ${balance:,.2f} • "
        f"Leverage: {int(leverage):,}× • Ref: {ref_price:,.2f} • Lot: {lot_size:.2f} • "
        f"Contract: {contract_sz:,.0f} • 1pt={point_value:.4f}"
    )