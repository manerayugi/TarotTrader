import os
import base64
import pandas as pd
import streamlit as st

# ============= CSS เฉพาะตอนหน้า Login =============
LOGIN_CSS = """
<style>
/* ให้คอนเทนต์ใต้ Header สูงพอและจัดกึ่งกลางแนวตั้งเฉพาะหน้า login */
[data-testid="stAppViewContainer"] > .main > div.block-container {
  min-height: calc(100svh - 64px);
  display: flex;
  align-items: center;
  padding-top: 0 !important;
  padding-bottom: 0 !important;
}

/* โลโก้วงกลม */
.login-logo {
  width: 120px;
  height: 120px;
  border-radius: 50%;
  object-fit: cover;
  border: 2px solid #2f3651;
  display: block;
  margin: 0 auto 8px auto;
}

/* ชื่อเพจใต้โลโก้ */
.login-subtitle {
  text-align: center;
  font-size: 1.3rem;
  font-weight: 600;
  margin: 6px 0 18px 0;
}

/* จัดปุ่ม submit ของ st.form ให้อยู่กึ่งกลาง */
div[data-testid="stFormSubmitButton"]{
  display: flex !important;
  justify-content: center !important;
}
div[data-testid="stFormSubmitButton"] button{
  width: auto !important;
}
</style>
"""

def inject_login_css():
    st.markdown(LOGIN_CSS, unsafe_allow_html=True)

# ============= First-run: สร้างแอดมินครั้งแรก =============
def render_initial_admin_form():
    st.markdown("<div style='text-align:center'>", unsafe_allow_html=True)
    if os.path.exists("assets/logo.png"):
        st.image("assets/logo.png", width=120)
    st.header("🔐 สร้างผู้ใช้แอดมิน (ครั้งแรก)")
    st.markdown("</div>", unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        new_admin_user = st.text_input("Admin Username", key="init_admin_user")
        new_admin_pass = st.text_input("Admin Password", type="password", key="init_admin_pass")
    with c2:
        new_admin_pass2 = st.text_input("Confirm Password", type="password", key="init_admin_pass2")
        if st.button("สร้างแอดมิน"):
            import func
            if not new_admin_user or not new_admin_pass:
                st.error("กรอกให้ครบ")
            elif new_admin_pass != new_admin_pass2:
                st.error("รหัสผ่านไม่ตรงกัน")
            else:
                if func.create_user(new_admin_user, new_admin_pass, role="admin"):
                    st.success("สร้าง Admin สำเร็จ! โปรดล็อกอินด้านล่าง")
                else:
                    st.error("ชื่อผู้ใช้ซ้ำ")

# ============= Login Form (กลางจอ) =============
def render_login_form():
    left, center, right = st.columns([1, 2, 1])
    with center:
        # โลโก้
        logo_path = "assets/logo.png"
        if os.path.exists(logo_path):
            with open(logo_path, "rb") as f:
                _b64 = base64.b64encode(f.read()).decode("utf-8")
            st.markdown(f"<img src='data:image/png;base64,{_b64}' class='login-logo' />",
                        unsafe_allow_html=True)

        # ชื่อเพจ
        st.markdown("<div class='login-subtitle'>🔮 Tarot Trader 💹</div>", unsafe_allow_html=True)

        # ฟอร์มล็อกอิน
        with st.form("login_form", clear_on_submit=False):
            u = st.text_input("Username", key="login_user")
            p = st.text_input("Password", type="password", key="login_pass")
            login_clicked = st.form_submit_button("เข้าสู่ระบบ")

        if login_clicked:
            import func
            user = func.verify_login(u, p)
            if user:
                st.session_state.auth = user
                st.success(f"ยินดีต้อนรับ {user['username']} ({user['role']})")
                st.rerun()
            else:
                st.error("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")

# ============= Sidebar (Branding + เมนู + ผู้ใช้ + Logout) =============
def render_sidebar(auth: dict):
    # ---- Branding ----
    logo_path = "assets/logo.png"
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as f:
            _b64 = base64.b64encode(f.read()).decode("utf-8")
        st.markdown(
            f"""
            <div style="text-align:center; margin-bottom:10px;">
                <img src="data:image/png;base64,{_b64}"
                     style="width:100px; height:100px; border-radius:50%; object-fit:cover;
                            border:2px solid #2f3651; margin-bottom:8px;">
                <h3 style="margin:0; font-size:1.2rem;">🔮 Tarot Trader 💹</h3>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.markdown("<h3 style='text-align:center;'>🔮 Tarot Trader 💹</h3>", unsafe_allow_html=True)

    st.divider()

    # ---- Navigation ----
    if "page" not in st.session_state:
        st.session_state.page = "money"

    if st.button("📊 Port", use_container_width=True):
        st.session_state.page = "port"
    if st.button("💰 Money Management", use_container_width=True):
        st.session_state.page = "money"

    # admin only
    if auth.get("role") == "admin":
        if st.button("👤 Users", use_container_width=True):
            st.session_state.page = "users"

    st.divider()

    # ---- User info + Logout ----
    st.markdown(
        f"""
        <div style='text-align:center;'>
            <p style='margin:4px 0;'>ผู้ใช้: <b>{auth['username']}</b><br>({auth['role']})</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    if st.button("🚪 ออกจากระบบ", use_container_width=True, key="logout"):
        st.session_state.auth = None
        st.rerun()

# ============= Pages =============
def render_port_page():
    st.header("📊 พอร์ตลงทุน")
    st.info("หน้านี้จะเติมภายหลัง")

def render_users_admin_page():
    import func
    st.header("👤 จัดการผู้ใช้")

    c1, c2 = st.columns([1, 1])
    with c1:
        st.markdown("**สร้างผู้ใช้ใหม่**")
        nuser = st.text_input("Username ใหม่")
        npass = st.text_input("Password", type="password")
        nrole = st.selectbox("Role", ["user", "admin"])
        if st.button("สร้างผู้ใช้"):
            if not nuser or not npass:
                st.error("กรอกให้ครบ")
            else:
                if func.create_user(nuser, npass, role=nrole):
                    st.success("สร้างผู้ใช้สำเร็จ")
                else:
                    st.error("ชื่อผู้ใช้ซ้ำหรือผิดพลาด")

    with c2:
        st.markdown("**เปลี่ยนรหัสผ่าน**")
        ch_user = st.text_input("Username ที่จะเปลี่ยนรหัส")
        ch_pass = st.text_input("รหัสผ่านใหม่", type="password")
        if st.button("เปลี่ยนรหัสผ่าน"):
            if not ch_user or not ch_pass:
                st.error("กรอกให้ครบ")
            else:
                if func.change_password(ch_user, ch_pass):
                    st.success("เปลี่ยนรหัสผ่านสำเร็จ")
                else:
                    st.error("ไม่พบผู้ใช้")

    st.divider()
    st.markdown("**รายการผู้ใช้ทั้งหมด**")
    users = func.list_users()
    if users:
        dfu = pd.DataFrame(users, columns=["id", "username", "role", "created_at"])
        st.dataframe(dfu, use_container_width=True, height=min(400, (len(dfu)+2)*33))
    else:
        st.info("ยังไม่มีผู้ใช้")

    st.divider()
    st.markdown("**ลบผู้ใช้**")
    del_user = st.text_input("Username ที่จะลบ")
    if st.button("ลบผู้ใช้"):
        if del_user == st.session_state.auth["username"]:
            st.error("ห้ามลบบัญชีที่กำลังใช้งาน")
        else:
            if func.delete_user(del_user):
                st.success("ลบสำเร็จ")
            else:
                st.error("ไม่พบผู้ใช้หรือผิดพลาด")

# ============= Money Management =============
def render_mm_tabs():
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

def render_mm_position_sizing(func_module):
    st.subheader("🧮 การออก Lot (Position Sizing – Max & Optimal)")

    # เลือกสินค้า
    preset_names = list(func_module.SYMBOL_PRESETS.keys())
    left, right = st.columns([2, 1])
    with left:
        symbol_name = st.selectbox(
            "สินค้า",
            preset_names,
            index=preset_names.index("XAUUSD") if "XAUUSD" in preset_names else 0
        )
    spec = func_module.SYMBOL_PRESETS[symbol_name]

    with right:
        st.write("สเปกสัญญา")
        st.caption(
            f"- Contract size: {spec.contract_size}\n"
            f"- Min lot: {spec.min_lot} | Step: {spec.lot_step}\n"
            f"- 1 point = ราคาเปลี่ยน {spec.price_point}\n"
            f"- 1 pip = {spec.pip_points} points"
        )

    # ราคา
    st.markdown("#### ราคา")
    c1, c2, _ = st.columns([1, 1, 2])
    with c1:
        use_fetch = st.toggle("ดึงราคา realtime", value=False)
    with c2:
        default_price = 0.0
        if use_fetch:
            fetched = func_module.fetch_price_yf(symbol_name)  # พยายาม XAUT-USD ก่อน
            if fetched:
                default_price = fetched
                st.success(f"ราคาโดยประมาณ: {fetched:,.2f}")
            else:
                st.warning("ดึงราคาไม่สำเร็จ กรุณากรอกเอง")
        price = st.number_input("ราคา (USD)", value=float(default_price), step=0.1, min_value=0.0)

    st.divider()

    # Max Lot
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
        m1 = func_module.margin_per_1lot(price, float(leverage), spec) if (price > 0 and leverage > 0) else 0.0
        maxlot = func_module.max_lot(balance, float(price), float(leverage), spec, buffer_pct)
        st.success(f"MaxLot โดยประมาณ: **{maxlot:.2f} lot**")
        if m1 > 0:
            st.caption(f"(Margin/lot เชิงปฏิบัติ ≈ (Contract × Price) / Leverage = ${m1:,.2f}/lot)")

    st.divider()

    # Optimal Lot
    st.markdown("### 2) Optimal Lot จากระยะที่ทนได้")
    u1, u2, u3, u4 = st.columns([1, 1, 1, 1.6])
    with u1:
        unit = st.selectbox("หน่วยระยะ", ["points", "pips"], index=0)
    with u2:
        distance_input = st.number_input(f"ระยะ Stop ({unit})", value=10000, step=1, min_value=0, format="%d")
    with u3:
        mode_safe = st.toggle("โหมดปลอดภัย (Risk%)", value=True)
    with u4:
        risk_percent = st.number_input("Risk ต่อไม้ (%)", value=1.0, step=0.25, min_value=0.0, disabled=not mode_safe)

    distance_points = float(distance_input) * (spec.pip_points if unit == "pips" else 1.0)

    vpp = func_module.value_per_point_per_lot(spec)
    st.caption(f"คำนวณจากสูตร: lot = (ทุนที่มี) / (ระยะ {distance_points:.0f} points × ${vpp:.2f}/point/lot)")

    if st.button("คำนวณ OptimalLot"):
        if distance_points <= 0:
            st.error("กรุณากรอกระยะ Stop > 0")
        else:
            if mode_safe and risk_percent > 0:
                lots = func_module.optimal_lot_by_points_risk(balance, risk_percent, distance_points, spec)
                pnl_stop = -func_module.pnl_usd(lots, distance_points, spec)
                st.info(f"ทุนที่มี: ${balance:,.2f} | ระยะ {distance_points:.0f} points")
                st.success(f"OptimalLot (ปลอดภัย): **{lots:.2f} lot**")
                st.caption(f"ถ้าโดน Stop จะประมาณ: ${pnl_stop:,.2f}")
            else:
                lots = func_module.optimal_lot_by_points_allin(balance, distance_points, spec)
                pnl_stop = -func_module.pnl_usd(lots, distance_points, spec)
                st.info(f"ทุนที่มี: ${balance:,.2f} | ระยะ {distance_points:.0f} points")
                st.success(f"OptimalLot (All-in): **{lots:.2f} lot**")
                st.caption(f"ถ้าโดน Stop จะประมาณ: ${pnl_stop:,.2f}")

    st.divider()
    st.markdown("#### สรุปมูลค่าการเคลื่อนที่ (ต่อ 1 lot)")
    df = pd.DataFrame({
        "รายการ": ["$/point/lot", f"$/pip/lot (1 pip = {spec.pip_points} points)"],
        "Value ($)": [func_module.value_per_point_per_lot(spec), func_module.value_per_pip_per_lot(spec)]
    })
    st.dataframe(df, use_container_width=True)

def render_mm_sl_to_lot(func_module):
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

        risk_amount, loss_pct = func_module.loss_to_amount_and_pct(balance, loss_mode, loss_val)
        if loss_mode == "%":
            st.caption(f"Loss ที่ใช้คำนวณ ≈ **${risk_amount:,.2f}**")
        else:
            st.caption(f"Loss ที่ใช้คำนวณ ≈ **{loss_pct:.2f}%** ของทุน")

        leverage = st.number_input("Leverage", value=1000, step=50, min_value=1, format="%d")
        custom_points = st.number_input("Stop Loss (Point) - กำหนดเอง", value=1000, step=1, min_value=0, format="%d")

        st.caption("สูตร MaxLot = (ทุน × Leverage) / (Price × ContractSize)")
        st.caption("สูตร Lot (ต่อระยะที่กำหนด) = ทุนที่มี / จำนวนจุด")

    with right:
        max_lot_val = func_module.maxlot_theoretical(balance, float(leverage), float(price), func_module.XAUUSD_SPEC)

        std_points = [10, 50, 100, 200, 300, 500, 1000, 1500, 2000, 5000, 10000, 20000]
        if custom_points and custom_points not in std_points:
            std_points.append(int(custom_points))
        std_points = sorted(std_points)

        rows = []
        for pts, lots in func_module.lots_from_stops(risk_amount, std_points):
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