# merlin_gtt.py
from __future__ import annotations

import math
from typing import List, Dict, Literal, Tuple

import pandas as pd
import streamlit as st
import altair as alt

from func import _hr, _hrr, center_latex, info_box, grid_entries

# ===== ค่าพื้นฐาน (ปรับได้) =================================
DEFAULT_PRICE_POINT   = 0.01   # 1 point = 0.01 (เช่น XAU)
DEFAULT_VPP_PER_LOT   = 1.0    # $/point/lot = 1
DEFAULT_CONTRACT_SIZE = 100.0  # contract size เริ่มต้น

GridSide = Literal["LONG", "SHORT"]

# ===== Logic เฉพาะของ GTT ===================================
def _max_orders_by_risk_after_grid(
    balance: float,
    lot: float,
    buffer_pts: float,
    step_pts: float,
    vpp: float,
) -> int:
    """
    เติมครบ N ไม้แล้วยังต้องทนได้อีก buffer_pts จุด:
      L(N) = lot * vpp * [ N*buffer_pts + step_pts * N(N-1)/2 ] <= balance
    หา N สูงสุดแบบควอดราติก (ปัดลง)
    """
    if min(balance, lot, buffer_pts, step_pts, vpp) <= 0:
        return 0
    A = (lot * vpp) * (step_pts / 2.0)
    B = (lot * vpp) * (buffer_pts - step_pts / 2.0)
    C = -balance
    disc = B * B - 4 * A * C
    if disc < 0:
        return 0
    n_pos = (-B + math.sqrt(disc)) / (2 * A)  # A>0 → ขอบบน
    return max(0, math.floor(n_pos)) if n_pos > 0 else 0


def _points_between(a_price: float, b_price: float, price_point: float) -> float:
    """ระยะเป็น 'points' ระหว่างราคา a → b (มีเครื่องหมาย)"""
    return (b_price - a_price) / float(price_point)


def _pnl_usd_for_position(entry_price: float, cur_price: float, lot: float, vpp: float, price_point: float, side: GridSide) -> float:
    """คำนวณ Floating P/L ของ 1 ไม้ ณ ราคาปัจจุบัน"""
    pts = _points_between(entry_price, cur_price, price_point)
    sgn = 1.0 if side == "LONG" else -1.0  # LONG: ราคาลง → แพ้ (pts<0), SHORT ตรงข้าม
    return lot * vpp * pts * sgn


def _margin_for_position(entry_price: float, lot: float, contract_size: float, leverage: float) -> float:
    """Margin ของ 1 ไม้ ≈ (entry * lot * contract) / leverage"""
    if leverage <= 0:
        return 0.0
    cost = entry_price * lot * contract_size
    return cost / float(leverage)


def _simulate_advanced_path(
    *,
    balance: float,
    leverage: float,
    current: float,
    step_pts: int,
    buffer_pts: int,
    lot_size: float,
    price_point: float,
    vpp: float,
    contract_size: float,
    side: GridSide,
    so_level_pct: float,
    step_granularity_pts: int,
) -> Tuple[pd.DataFrame, List[float], List[Dict]]:
    """
    จำลองราคาเดินทาง “ทางที่แย่ที่สุด” ทีละ step_granularity_pts (points)
    - เปิดไม้ใหม่เมื่อถึงระดับกริดถัดไป
    - คำนวณ Equity, Used Margin, Margin Level ทุกก้าว
    - ถ้า Margin Level <= SO → ตัดไม้ 'ที่ขาดทุนหนักสุดก่อน' ไปเรื่อย ๆ จนกว่าจะ > SO หรือไม่มีไม้เหลือ
    คืน:
      curve_df: DataFrame[price, equity, used_margin, margin_level, open_positions]
      entries_filled: รายการราคาเข้า (เปิดสำเร็จจริง ณ จุดสิ้นสุดการจำลอง)
      liquidations: log การตัดไม้แต่ละครั้ง
    """
    sgn_price = -1.0 if side == "LONG" else 1.0
    step_price = sgn_price * step_granularity_pts * price_point
    if step_price == 0:
        step_price = sgn_price * price_point

    # ราคาปลายทางอย่างน้อย buffer_pts points ไปทางเสียเปรียบ
    end_price = current + sgn_price * buffer_pts * price_point

    # ระดับ “ราคาเข้าไม้ใหม่” ตามกริด step_pts
    grid_prices = grid_entries(
        current_price=current,
        n_orders=10000,  # เพดานกว้าง ๆ เปิดเท่าที่ถึงจริง
        step_points=step_pts,
        price_point=price_point,
        side=side,
    )

    open_positions: List[float] = []    # entry ที่เปิดอยู่
    liquidations: List[Dict] = []       # log ตัดไม้
    curve_rows: List[Dict] = []

    price = current
    next_grid_idx = 0
    reached_tail = False

    while True:
        # เปิดไม้ใหม่ถ้าราคาแตะระดับกริดถัดไป
        while next_grid_idx < len(grid_prices):
            gp = grid_prices[next_grid_idx]
            if (side == "LONG" and price <= gp) or (side == "SHORT" and price >= gp):
                open_positions.append(gp)
                next_grid_idx += 1
            else:
                break

        # คำนวณตัวเลขหลัก
        used_margin = sum(_margin_for_position(ep, lot_size, contract_size, leverage) for ep in open_positions)
        floating_pl = sum(_pnl_usd_for_position(ep, price, lot_size, vpp, price_point, side) for ep in open_positions)
        equity = balance + floating_pl
        margin_level = (equity / used_margin * 100.0) if used_margin > 0 else float("inf")

        curve_rows.append({
            "price": price,
            "open_positions": len(open_positions),
            "equity": equity,
            "used_margin": used_margin,
            "margin_level": margin_level,
        })

        # เช็ค SO → ตัดไม้แบบ worst-loss-first
        if used_margin > 0 and margin_level <= so_level_pct and len(open_positions) > 0:
            while len(open_positions) > 0:
                # หาไม้ที่ขาดทุนมากสุด
                worst_idx = None
                worst_pl = 0.0
                for i, ep in enumerate(open_positions):
                    pl = _pnl_usd_for_position(ep, price, lot_size, vpp, price_point, side)
                    if (worst_idx is None) or (pl < worst_pl):
                        worst_idx = i
                        worst_pl = pl

                ep_cut = open_positions.pop(worst_idx)  # ตัดออก
                # อัปเดต
                used_margin = sum(_margin_for_position(ep, lot_size, contract_size, leverage) for ep in open_positions)
                floating_pl = sum(_pnl_usd_for_position(ep, price, lot_size, vpp, price_point, side) for ep in open_positions)
                equity = balance + floating_pl
                margin_level = (equity / used_margin * 100.0) if used_margin > 0 else float("inf")

                liquidations.append({
                    "price": price,
                    "cut_entry": ep_cut,
                    "equity_after": equity,
                    "used_margin_after": used_margin,
                    "margin_level_after(%)": margin_level
                })

                if used_margin <= 0 or margin_level > so_level_pct:
                    break

            curve_rows.append({
                "price": price,
                "open_positions": len(open_positions),
                "equity": equity,
                "used_margin": used_margin,
                "margin_level": margin_level,
            })

            if len(open_positions) == 0 or equity <= 0:
                reached_tail = True

        # จบเมื่อเดินทางถึงปลายทางขั้นต่ำ
        if (side == "LONG" and price <= end_price) or (side == "SHORT" and price >= end_price):
            reached_tail = True

        if reached_tail:
            break

        price = price + step_price

    curve_df = pd.DataFrame(curve_rows)
    # entries ที่เปิดสำเร็จจริง ณ จุดสิ้นสุด
    entries_filled = open_positions.copy()
    return curve_df, entries_filled, liquidations


# ===== Main Tab ==============================================
def render_gtt_tab(default_mode: str = "Normal") -> None:
    # Header
    st.markdown(
        """
        <div style='display:flex;align-items:baseline;gap:10px;'>
          <h3 style='margin:0;'>🜏 GTT — Gemini Tenebris Theoria</h3>
          <span style='color:#aaa;font-size:0.9rem;'>Grid Trading Technique</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption("Balance in Shadows. Profit in Silence.")
    st.caption("คำนวณจำนวนไม้สูงสุดที่เปิดได้ เมื่อ ‘เติมครบ N ไม้แล้วยังต้องทนได้อีก B จุด’ หรือจำลอง SO แบบ Advance")

    # --- โหมด (ค่าเริ่มต้นมาจากเมอร์ลิน: A=Normal, B=Advanced)
    mode_idx = 0 if str(default_mode).lower() != "advanced" else 1
    mode = st.radio("โหมดการคำนวณ", options=["Normal", "Advanced"], index=mode_idx, horizontal=True)

    _hr(); _hrr()
    center_latex(r"1~\text{point} = 0.01~\text{price unit},\qquad \$\!/\text{point}/\text{lot} = 1")
    _hrr()

    # --- Inputs (ใช้ร่วม)
    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        balance  = st.number_input("ทุน ($)", min_value=0.0, value=10000.0, step=100.0)
        leverage = st.number_input("Leverage", min_value=1, value=1000, step=50, format="%d")
    with c2:
        current  = st.number_input("ราคาปัจจุบัน", min_value=0.0, value=4000.0, step=0.1)
        step_pts = st.number_input("ระยะห่าง/ไม้ (points)", min_value=1, value=1000, step=100)
    with c3:
        buffer_pts = st.number_input(
            "บัฟเฟอร์หลังเติมครบ (points)",
            min_value=1,
            value=50000,
            step=1000,
            help="Normal: เติมครบ N แล้วยังต้องทนได้อีกเท่านี้ • Advanced: ใช้เป็นระยะจำลองขั้นต่ำ",
        )
        lot_size = st.number_input("Lot size (ต่อไม้)", min_value=0.0, value=0.01, step=0.01)

    side: GridSide = st.radio("ทิศทางกริด", options=["LONG", "SHORT"], horizontal=True, index=0)  # type: ignore

    # ---- Option (ตามที่ขอ) ----
    with st.expander("Option"):
        price_point   = st.number_input("1 point = กี่หน่วยราคา", min_value=0.0001, value=float(DEFAULT_PRICE_POINT), step=0.0001, format="%.4f")
        vpp           = st.number_input("มูลค่าการเคลื่อนที่ ($/point/lot)", min_value=0.0001, value=float(DEFAULT_VPP_PER_LOT), step=0.1)
        contract_size = st.number_input("Contract size", min_value=0.0001, value=float(DEFAULT_CONTRACT_SIZE), step=1.0)

        if mode == "Advanced":
            so_pct    = st.number_input("Stop-out level (%)", min_value=0.0, max_value=100.0, value=30.0, step=1.0)
            step_gran = st.number_input("ความละเอียดการจำลอง (points/ก้าว)", min_value=1, value=100, step=10,
                                        help="ยิ่งเล็กยิ่งละเอียด (ซอยจุดถี่ขึ้น) แต่จะใช้เวลาคำนวณมากขึ้น")

    _hrr()

    # ===================== Normal =====================
    if mode == "Normal":
        center_latex(r"L(N) = \text{lot}\cdot(\$/\text{pt}/\text{lot})\cdot\Big(NB + S\frac{N(N-1)}{2}\Big)\;\le\;\text{balance}")
        center_latex(r"N_{\max} = \left\lfloor \text{root of the inequality above} \right\rfloor")
        _hrr()

        if min(step_pts, buffer_pts, lot_size, price_point, vpp, contract_size) <= 0:
            st.error("กรุณาตรวจสอบอินพุตหลัก ๆ (step, buffer, lot, หน่วย point, $/pt/lot, contract) ต้องมากกว่า 0")
            return

        n_max = _max_orders_by_risk_after_grid(
            balance=float(balance),
            lot=float(lot_size),
            buffer_pts=float(buffer_pts),
            step_pts=float(step_pts),
            vpp=float(vpp),
        )
        entries = grid_entries(
            current_price=float(current),
            n_orders=int(n_max),
            step_points=float(step_pts),
            price_point=float(price_point),
            side=side,
        )

        st.markdown(
            f"""
            <div style='font-size:1.25rem;font-weight:700;'>
              จำนวนไม้สูงสุดที่ออกได้ ≈ <span style='font-size:1.6rem;'>{n_max:,} ไม้</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("#### รายละเอียดต้นทุนและมาร์จิ้นต่อไม้")
        if n_max <= 0 or not entries:
            st.info("ยังไม่มีไม้ที่จะเปิดได้จากเงื่อนไขปัจจุบัน")
            return

        rows: List[Dict] = []
        cum_cost = 0.0
        cum_margin = 0.0
        for i, price in enumerate(entries, start=1):
            cost_i   = float(price) * float(lot_size) * float(contract_size)
            margin_i = (cost_i / float(leverage)) if leverage > 0 else 0.0
            cum_cost += cost_i
            cum_margin += margin_i
            rows.append({
                "ลำดับไม้": i,
                "ราคาเข้า": price,
                "ต้นทุน/ไม้ ($)": cost_i,
                "มาร์จิ้น/ไม้ ($)": margin_i,
                "ต้นทุนรวม ($)": cum_cost,
                "มาร์จิ้นรวม ($)": cum_margin,
            })

        df = pd.DataFrame(rows)
        st.dataframe(
            df.style.format({
                "ราคาเข้า": "{:,.2f}",
                "ต้นทุน/ไม้ ($)": "{:,.2f}",
                "มาร์จิ้น/ไม้ ($)": "{:,.2f}",
                "ต้นทุนรวม ($)": "{:,.2f}",
                "มาร์จิ้นรวม ($)": "{:,.2f}",
            }).set_properties(**{"text-align":"center"}),
            use_container_width=True,
            height=min(480, (len(df)+2)*33)
        )
        return  # ===== END Normal =====

    # ===================== Advanced =====================
    center_latex(r"\textbf{Advanced SO Model: } \text{จำลอง Margin Level \& การตัดไม้แบบ Worst-Loss-First}")
    _hrr()

    # ตรวจอินพุตหลัก + ตัวเลือกจำลอง
    if min(step_pts, buffer_pts, lot_size, price_point, vpp, contract_size) <= 0:
        st.error("กรุณาตรวจสอบอินพุตหลัก ๆ (step, buffer, lot, หน่วย point, $/pt/lot, contract) ต้องมากกว่า 0")
        return

    so_pct    = locals().get("so_pct", 30.0)
    step_gran = locals().get("step_gran", 100)  # ค่าเริ่มต้นใหม่ = 100

    curve_df, entries_filled, liq_logs = _simulate_advanced_path(
        balance=float(balance),
        leverage=float(leverage),
        current=float(current),
        step_pts=int(step_pts),
        buffer_pts=int(buffer_pts),
        lot_size=float(lot_size),
        price_point=float(price_point),
        vpp=float(vpp),
        contract_size=float(contract_size),
        side=side,
        so_level_pct=float(so_pct),
        step_granularity_pts=int(step_gran),
    )

    # สรุปจำนวนไม้ที่เปิดสำเร็จ ณ จุดสิ้นสุดการจำลอง
    n_filled = int(curve_df["open_positions"].iloc[-1]) if not curve_df.empty else 0
    st.markdown(
        f"""
        <div style='font-size:1.1rem;font-weight:700;'>
          เปิดสำเร็จได้ทั้งหมด ≈ <span style='font-size:1.35rem;'>{n_filled:,} ไม้</span> 
          (จำลองขั้นต่ำ {int(buffer_pts):,} points ไปทางเสียเปรียบ • SO {so_pct:.0f}%)
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ตารางราคาเข้า + ต้นทุน/มาร์จิ้น (ของไม้ที่เปิดสำเร็จจริง)
    st.markdown("#### รายละเอียดไม้ที่เปิดสำเร็จ (ตามการจำลอง)")
    if n_filled <= 0:
        st.info("ไม่สามารถเปิดไม้ได้ภายใต้เงื่อนไข SO/ทุน ที่กำหนด")
    else:
        rows2: List[Dict] = []
        cum_cost = 0.0
        cum_margin = 0.0
        for i, price in enumerate(entries_filled[:n_filled], start=1):
            cost_i   = float(price) * float(lot_size) * float(contract_size)
            margin_i = (cost_i / float(leverage)) if leverage > 0 else 0.0
            cum_cost += cost_i
            cum_margin += margin_i
            rows2.append({
                "ลำดับไม้": i,
                "ราคาเข้า": price,
                "ต้นทุน/ไม้ ($)": cost_i,
                "มาร์จิ้น/ไม้ ($)": margin_i,
                "ต้นทุนรวม ($)": cum_cost,
                "มาร์จิ้นรวม ($)": cum_margin,
            })
        df2 = pd.DataFrame(rows2)
        st.dataframe(
            df2.style.format({
                "ราคาเข้า": "{:,.2f}",
                "ต้นทุน/ไม้ ($)": "{:,.2f}",
                "มาร์จิ้น/ไม้ ($)": "{:,.2f}",
                "ต้นทุนรวม ($)": "{:,.2f}",
                "มาร์จิ้นรวม ($)": "{:,.2f}",
            }).set_properties(**{"text-align":"center"}),
            use_container_width=True,
            height=min(480, (len(df2)+2)*33)
        )

    # === กราฟ: 3 อัน (Equity, Used Margin, Margin Level) — กราฟละ 1 แถว เรียงราคาสูง→ต่ำ ===
    if not curve_df.empty:
        st.markdown("#### Equity / Used Margin / Margin Level (ตามการจำลอง)")

        # เรียงราคาให้มาก→น้อยเพื่อให้ “ราคาสูงอยู่ซ้าย”
        cdf = curve_df.sort_values("price", ascending=False).copy()
        cdf["Equity"] = cdf["equity"]
        cdf["UsedMargin"] = cdf["used_margin"]
        cdf["MarginLevel(%)"] = cdf["margin_level"]

        # Equity
        chart_eq = (
            alt.Chart(cdf)
            .mark_line()
            .encode(
                x=alt.X("price:Q", sort="descending", title="Price (สูง→ต่ำ)"),
                y=alt.Y("Equity:Q", title="Equity ($)")
            )
            .properties(height=240, width="container")
        )
        st.altair_chart(chart_eq, use_container_width=True)

        # Used Margin
        chart_um = (
            alt.Chart(cdf)
            .mark_line()
            .encode(
                x=alt.X("price:Q", sort="descending", title="Price (สูง→ต่ำ)"),
                y=alt.Y("UsedMargin:Q", title="Used Margin ($)")
            )
            .properties(height=240, width="container")
        )
        st.altair_chart(chart_um, use_container_width=True)

        # Margin Level
        chart_ml = (
            alt.Chart(cdf)
            .mark_line()
            .encode(
                x=alt.X("price:Q", sort="descending", title="Price (สูง→ต่ำ)"),
                y=alt.Y("MarginLevel(%):Q", title="Margin Level (%)")
            )
            .properties(height=240, width="container")
        )
        st.altair_chart(chart_ml, use_container_width=True)

    # Log การตัดไม้ (ถ้ามี)
    if liq_logs:
        st.markdown("#### รายการตัดไม้เมื่อถึง Stop-out")
        dfL = pd.DataFrame(liq_logs)
        st.dataframe(
            dfL.style.format({
                "price": "{:,.2f}",
                "cut_entry": "{:,.2f}",
                "equity_after": "{:,.2f}",
                "used_margin_after": "{:,.2f}",
                "margin_level_after(%)": "{:,.2f}",
            }).set_properties(**{"text-align":"center"}),
            use_container_width=True,
            height=min(420, (len(dfL)+2)*33)
        )