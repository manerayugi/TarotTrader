# port_advanced.py
import streamlit as st
import pandas as pd

SYMBOL_PRESETS = {
    "XAUUSD": {"contract_size": 100, "price_per_point": 1.0, "leverage": 2000, "currency": "USD"},
    "BTCUSD": {"contract_size": 1,   "price_per_point": 1.0, "leverage": 100,  "currency": "USD"},
}

def render_advanced_tab():
    st.subheader("📐 Elite Portfolio – คำนวณกำไร/ขาดทุน และ Margin")

    # ---------- Current Info Inputs ----------
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col1:
        current_price = st.number_input("ราคาปัจจุบัน", value=3700.00, step=0.01)
    with col2:
        balance = st.number_input("Balance", value=10400.00)
    with col3:
        credit = st.number_input("Credit", value=0.00)
    with col4:
        equity = st.number_input("Equity", value=10490.00)
    with col5:
        leverage = st.number_input("Leverage", value=2000)
    with col6:
        remain_pct = st.number_input("Remain %", value=0.0)

    st.divider()

    # ---------- Summary (ตัวอย่าง) ----------
    colA, colB, colC, colD, colE, colF, colG = st.columns(7)
    with colA: st.metric("รวมกำไร", "90.00")
    with colB: st.metric("Lot", "0.02")
    with colC: st.metric("Used Margin", "3.66")
    with colD: st.metric("Free Margin", "10,486.35")
    with colE: st.metric("% Margin", "287004.10%")
    with colF: st.metric("Swap", "-0.24")
    with colG: st.metric("Spread", "43")

    st.markdown("---")

    # ---------- Order Table ----------
    st.subheader("🧾 รายการออเดอร์")
    symbol = st.selectbox("เลือก Symbol", options=list(SYMBOL_PRESETS.keys()), index=0)
    preset = SYMBOL_PRESETS[symbol]
    contract_size = preset["contract_size"]
    pp_point = preset["price_per_point"]

    num_orders = st.number_input("จำนวนออเดอร์ที่ต้องการใส่", min_value=1, max_value=50, value=3, step=1)

    df_orders = pd.DataFrame({
        "Order": [f"#{i+1}" for i in range(num_orders)],
        "Type": ["BUY"] * num_orders,
        "Entry Price": [3700.0] * num_orders,
        "Lot": [0.01] * num_orders
    })

    edited_df = st.data_editor(df_orders, num_rows="dynamic", use_container_width=True)

    st.divider()

    # ---------- Calculation ----------
    st.subheader("📈 ผลการคำนวณ (ตามราคาปัจจุบัน)")

    total_pl = 0.0
    total_margin = 0.0
    result_rows = []

    for _, row in edited_df.iterrows():
        entry = float(row["Entry Price"])
        lot = float(row["Lot"])
        order_type = row["Type"]
        diff = (current_price - entry) if order_type == "BUY" else (entry - current_price)
        pl = diff * lot * pp_point * contract_size
        margin = (entry * lot * contract_size) / max(1, float(leverage))
        total_pl += pl
        total_margin += margin
        result_rows.append({
            "Order": row["Order"],
            "Type": order_type,
            "Entry": entry,
            "Lot": lot,
            "Diff": diff,
            "P/L ($)": pl,
            "Margin": margin
        })

    df_result = pd.DataFrame(result_rows)
    st.dataframe(
        df_result.style.format({
            "Entry": "{:,.2f}",
            "Lot": "{:.2f}",
            "Diff": "{:,.2f}",
            "P/L ($)": "{:,.2f}",
            "Margin": "{:,.2f}"
        }).set_properties(**{"text-align":"center"}),
        use_container_width=True
    )

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("💰 รวมกำไร/ขาดทุน", f"{total_pl:,.2f}")
    with col2:
        st.metric("🧱 รวม Margin", f"{total_margin:,.2f}")