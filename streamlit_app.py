import streamlit as st
import pandas as pd
import func

# ========================= App Config =========================
st.set_page_config(page_title="🔮 Tarot Trader 💹", page_icon="🔮", layout="wide")

# ========================= Sidebar =========================
st.sidebar.title("🔮 Tarot Trader 💹")

if "page" not in st.session_state:
    st.session_state.page = "money"

if st.sidebar.button("📊 Port", use_container_width=True):
    st.session_state.page = "port"
if st.sidebar.button("💰 Money Management", use_container_width=True):
    st.session_state.page = "money"

page = st.session_state.page

# ========================= Main =========================
if page == "port":
    st.header("📊 พอร์ตลงทุน")
    st.info("หน้านี้จะเติมภายหลัง")
else:
    # ---------------- Money Management ----------------
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

        # 1) เลือกสินค้า (อิงสเปกจาก func.SYMBOL_PRESETS)
        preset_names = list(func.SYMBOL_PRESETS.keys())
        left, right = st.columns([2, 1])
        with left:
            symbol_name = st.selectbox(
                "สินค้า",
                preset_names,
                index=preset_names.index("XAUUSD") if "XAUUSD" in preset_names else 0
            )
        spec = func.SYMBOL_PRESETS[symbol_name]

        with right:
            st.write("สเปกสัญญา")
            st.caption(
                f"- Contract size: {spec.contract_size}\n"
                f"- Min lot: {spec.min_lot} | Step: {spec.lot_step}\n"
                f"- 1 point = ราคาเปลี่ยน {spec.price_point}\n"
                f"- 1 pip = {spec.pip_points} points"
            )

        # 2) ราคา (ใช้ตัวดึงราคาใน func ถ้าต้องการ)
        st.markdown("#### ราคา")
        c1, c2, _ = st.columns([1, 1, 2])
        with c1:
            use_fetch = st.toggle("ดึงราคา realtime", value=False)
        with c2:
            default_price = 0.0
            if use_fetch:
                fetched = func.fetch_price_yf(symbol_name)  # ภายในจะพยายาม XAUT-USD ก่อน (อัปเดตใน func.py)
                if fetched:
                    default_price = fetched
                    st.success(f"ราคาโดยประมาณ: {fetched:,.2f}")
                else:
                    st.warning("ดึงราคาไม่สำเร็จ กรุณากรอกเอง")
            price = st.number_input("ราคา (USD)", value=float(default_price), step=0.1, min_value=0.0)

        st.divider()

        # 3) Max Lot (คำนวณใน func)
        st.markdown("### 1) Max Lot จากทุน + Leverage")
        cA, cB, cC, cD = st.columns([1, 1, 1, 1.6])
        with cA:
            balance = st.number_input("ทุน ($)", value=1000.0, step=100.0, min_value=0.0)
        with cB:
            leverage = st.number_input("Leverage", value=1000, step=50, min_value=1, format="%d")
        with cC:
            buffer_pct_ui = st.number_input("กันไว้ (Free Margin %)", value=0.0, step=1.0, min_value=0.0, max_value=90.0)
            buffer_pct = buffer_pct_ui / 100.0
        with cD:
            st.caption("สูตร: Maxlot = (ทุน * Leverage) / (Price * ContractSize)")

        if st.button("คำนวณ MaxLot", type="primary"):
            # margin/lot (ปฏิบัติ) และ max_lot (เผื่อ buffer) — ใช้ฟังก์ชันใน func
            m1 = func.margin_per_1lot(price, float(leverage), spec) if (price > 0 and leverage > 0) else 0.0
            maxlot = func.max_lot(balance, float(price), float(leverage), spec, buffer_pct)
            st.success(f"MaxLot โดยประมาณ: **{maxlot:.2f} lot**")
            if m1 > 0:
                st.caption(f"(Margin/lot เชิงปฏิบัติ ≈ (Contract × Price) / Leverage = ${m1:,.2f}/lot)")

        st.divider()

        # 4) Optimal Lot (คำนวณใน func)
        st.markdown("### 2) Optimal Lot จากระยะที่ทนได้")
        u1, u2, u3, u4 = st.columns([1, 1, 1, 1.6])
        with u1:
            unit = st.selectbox("หน่วยระยะ", ["points", "pips"], index=0)
        with u2:
            distance_input = st.number_input(
                f"ระยะ Stop ({unit})",
                value=10000,
                step=1,
                min_value=0,
                format="%d"
            )
        with u3:
            mode_safe = st.toggle("โหมดปลอดภัย (Risk%)", value=True)
        with u4:
            risk_percent = st.number_input("Risk ต่อไม้ (%)", value=1.0, step=0.25, min_value=0.0, disabled=not mode_safe)

        # แปลง stop → points
        distance_points = float(distance_input) * (spec.pip_points if unit == "pips" else 1.0)

        # คำอธิบาย
        vpp = func.value_per_point_per_lot(spec)   # $/point/lot
        st.caption(f"คำนวณจากสูตร: lot = (ทุนที่มี) / (ระยะ {distance_points:.0f} points × ${vpp:.2f}/point/lot)")

        if st.button("คำนวณ OptimalLot"):
            if distance_points <= 0:
                st.error("กรุณากรอกระยะ Stop > 0")
            else:
                if mode_safe and risk_percent > 0:
                    lots = func.optimal_lot_by_points_risk(balance, risk_percent, distance_points, spec)
                    pnl_stop = -func.pnl_usd(lots, distance_points, spec)
                    st.info(f"ทุนที่มี: ${balance:,.2f} | ระยะ {distance_points:.0f} points")
                    st.success(f"OptimalLot (ปลอดภัย): **{lots:.2f} lot**")
                    st.caption(f"ถ้าโดน Stop จะประมาณ: ${pnl_stop:,.2f}")
                else:
                    lots = func.optimal_lot_by_points_allin(balance, distance_points, spec)
                    pnl_stop = -func.pnl_usd(lots, distance_points, spec)
                    st.info(f"ทุนที่มี: ${balance:,.2f} | ระยะ {distance_points:.0f} points")
                    st.success(f"OptimalLot (All-in): **{lots:.2f} lot**")
                    st.caption(f"ถ้าโดน Stop จะประมาณ: ${pnl_stop:,.2f}")

        st.divider()
        st.markdown("#### สรุปมูลค่าการเคลื่อนที่ (ต่อ 1 lot)")
        df = pd.DataFrame({
            "รายการ": ["$/point/lot", f"$/pip/lot (1 pip = {spec.pip_points} points)"],
            "Value ($)": [func.value_per_point_per_lot(spec), func.value_per_pip_per_lot(spec)]
        })
        st.dataframe(df, use_container_width=True)

    # ---------------- Tab 2: ระยะ SL → Lot ----------------
    elif st.session_state.mm_tab == "sl":
        st.subheader("📏 ระยะ SL → คำนวณ Lot")

        # Layout: ซ้าย (กรอกข้อมูล) | ขวา (ตารางผลลัพธ์)
        left, right = st.columns([1, 1.2])

        with left:
            # ราคาปัจจุบัน (กรอกเอง) — การดึงจริงไปทำใน func.fetch_* ตามที่กำหนด
            price = st.number_input("ราคาปัจจุบัน (USD)", value=0.0, step=0.1, min_value=0.0)

            # ทุน (default = 1000)
            balance = st.number_input("ทุน ($)", value=1000.0, step=100.0, min_value=0.0)

            # เลือกโหมด Loss: % หรือ $
            loss_mode = st.selectbox("กรอก Loss เป็น", ["%", "$"], index=0)
            if loss_mode == "%":
                loss_val = st.number_input("Loss (%)", value=10.0, step=0.5, min_value=0.0)
            else:
                loss_val = st.number_input("Loss ($)", value=100.0, step=10.0, min_value=0.0)

            # แปลงค่า Loss และแสดงผล (คำนวณใน func)
            risk_amount, loss_pct = func.loss_to_amount_and_pct(balance, loss_mode, loss_val)
            if loss_mode == "%":
                st.caption(f"Loss ที่ใช้คำนวณ ≈ **${risk_amount:,.2f}**")
            else:
                st.caption(f"Loss ที่ใช้คำนวณ ≈ **{loss_pct:.2f}%** ของทุน")

            # Leverage (ใช้คำนวณ MaxLot) — default = 1000, จำนวนเต็ม
            leverage = st.number_input("Leverage", value=1000, step=50, min_value=1, format="%d")

            # ระยะ Stop (กำหนดเอง) — ไม่มีทศนิยม, default = 1000
            custom_points = st.number_input("Stop Loss (Point) - กำหนดเอง", value=1000, step=1, min_value=0, format="%d")

            # สูตรอธิบาย
            st.caption("สูตร MaxLot = (ทุน × Leverage) / (Price × ContractSize)")
            st.caption("สูตร Lot (ต่อระยะที่กำหนด) = ทุนที่มี / จำนวนจุด")

        with right:
            # MaxLot เชิงทฤษฎี (คำนวณใน func) — ใช้ XAUUSD spec
            max_lot_val = func.maxlot_theoretical(balance, float(leverage), float(price), func.XAUUSD_SPEC)

            # ระยะมาตรฐาน
            std_points = [10, 50, 100, 200, 300, 500, 1000, 1500, 2000, 5000, 10000, 20000]
            if custom_points and custom_points not in std_points:
                std_points.append(int(custom_points))
            std_points = sorted(std_points)

            # ตาราง: lot = ทุนที่มี / จำนวนจุด (ใช้ helper ใน func)
            rows = []
            for pts, lots in func.lots_from_stops(risk_amount, std_points):
                exceeds = lots > max_lot_val if max_lot_val > 0 else False
                rows.append({"Stop Loss (Point)": pts, "Lot (คำนวณ)": lots, "เกิน MaxLot?": "⚠️ ใช่" if exceeds else ""})
            df = pd.DataFrame(rows)

            # สไตล์: จัดกลาง + ไฮไลต์ธีมม่วงอ่อน + แสดงตารางเต็ม
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

            # ผลลัพธ์จากระยะกำหนดเอง (โชว์ใต้ตาราง)
            if custom_points > 0:
                custom_lot = risk_amount / float(custom_points)
                exceeds_custom = custom_lot > max_lot_val if max_lot_val > 0 else False

                st.subheader("ผลลัพธ์จากระยะที่กำหนดเอง")
                st.write(f"Stop Loss (Point): **{custom_points:,}** → Lot ที่ควรออก ≈ **{custom_lot:.2f} lot**")
                if exceeds_custom:
                    st.warning("ค่าที่คำนวณเกิน MaxLot ที่เปิดได้ในตอนนี้")

    else:
        st.info("เลือกหน้าฟังก์ชันอื่น ๆ ได้ในอนาคต (ยังไม่เปิดใช้งาน)")
