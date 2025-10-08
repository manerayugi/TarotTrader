# merlin_gtt.py
import math
import pandas as pd
import streamlit as st

# ===== สมมติฐานค่าพื้นฐาน (แก้ได้) =====
DEFAULT_PRICE_POINT = 0.01   # 1 point = 0.01 หน่วยราคา (เช่น XAU)
DEFAULT_VPP_PER_LOT = 1.0    # $/point/lot = 1 (ให้สอดคล้องกับหน้า MM ของคุณ)

def _hr(width: int = 360):
    st.markdown(
        f"""
        <div style='text-align:center; margin:14px 0;'>
          <hr style='width: {width}px; border: 1px solid #666; margin: 8px auto;'/>
        </div>
        """,
        unsafe_allow_html=True
    )

def _hrr():
    st.markdown(
        "<div style='text-align:center; margin:10px 0;'>"
        "<hr style='width:360px; border:1px solid #555; margin:8px auto;'/>"
        "</div>",
        unsafe_allow_html=True
    )

def _center_latex(expr: str):
    st.markdown("<div style='text-align:center;'>", unsafe_allow_html=True)
    st.latex(expr)
    st.markdown("</div>", unsafe_allow_html=True)

def _info_box(html: str):
    st.markdown(
        f"""
        <div style="border:1px solid #666; padding:12px 14px;
                    border-radius:10px; background:#202020; color:#e5e7eb;">
          {html}
        </div>
        """,
        unsafe_allow_html=True
    )

def _max_orders_by_remaining(balance: float, lot: float, R: float, S: float, vpp: float) -> int:
    """
    จำกัดด้วย 'เงินทุน' ภายใต้เงื่อนไข:
      - เติมไม้ห่างกันเท่ากัน S points
      - หลังลงไม้สุดท้ายแล้ว หากราคาไปต่อ 'อีก R points' จึงจะแตก
      - แตก = ขาดทุนรวมเท่ากับ balance (ไม่จำลอง Margin Level/Stopout เพิ่มเติม)

    Loss รวม ณ จุดแตก:
        L(N) = lot * vpp * [ N*R + S * N*(N-1)/2 ]  <= balance

    แปลงเป็นควอดราติก: (lot*vpp)*(S/2) * N^2 + (lot*vpp)*(R - S/2) * N - balance <= 0
    หา N สูงสุด (ปัดลง)
    """
    if balance <= 0 or lot <= 0 or vpp <= 0 or R <= 0 or S <= 0:
        return 0

    a = (lot * vpp) * (S / 2.0)
    b = (lot * vpp) * (R - S / 2.0)
    c = -balance

    disc = b*b - 4*a*c
    if disc < 0:
        return 0
    sqrt_disc = math.sqrt(disc)

    # ใช้รากบวกของสมการ aN^2 + bN + c = 0
    n_pos = (-b + sqrt_disc) / (2*a) if a > 0 else 0
    return max(0, math.floor(n_pos))

def _calc_entries(current_price: float, N: int, step_points: float, price_point: float, side: str) -> list[float]:
    """
    ราคาเข้า N ไม้ แบ่งเท่า ๆ กันทีละ step จากราคาเริ่มต้น (LONG = ลดลง, SHORT = เพิ่มขึ้น)
    """
    if N <= 0:
        return []
    step_price = step_points * price_point
    sgn = -1.0 if side.upper() == "LONG" else 1.0
    return [round(current_price + sgn * i * step_price, 2) for i in range(N)]

def render_gtt_tab():
    # ===== Header (subheader + caption บรรทัดเดียว) =====
    st.markdown("""
    <div style='display:flex; align-items:baseline; gap:10px;'>
      <h3 style='margin:0;'>🜏 GTT — Gemini Tenebris Theoria</h3>
      <span style='color:#aaa; font-size:0.9rem;'>Grid Trading Technique</span>
    </div>
    """, unsafe_allow_html=True)
    st.caption("Balance in Shadows. Profit in Silence.")
    st.caption("คำนวณจำนวนไม้สูงสุดที่เปิดได้ โดยยังเหลือ ‘ระยะที่ทนได้หลังไม้สุดท้าย’ อีก R points")

    _hr()
    _hrr()
    _center_latex(r"1~\text{point} = 0.01~\text{price unit}\quad,\quad \$\!/\text{point}/\text{lot} = 1")
    _hrr()

    # ===== Inputs =====
    c1, c2, c3 = st.columns([1,1,1])
    with c1:
        balance   = st.number_input("ทุน ($)", min_value=0.0, value=10000.0, step=100.0)
        leverage  = st.number_input("Leverage (ยังไม่ใช้ในสูตรนี้)", min_value=1, value=1000, step=50, format="%d")
    with c2:
        current   = st.number_input("ราคาปัจจุบัน", min_value=0.0, value=4000.0, step=0.1)
        step_pts  = st.number_input("ระยะห่าง/ไม้ (points)", min_value=1, value=1000, step=100)
    with c3:
        remain_pts = st.number_input("ระยะที่ยังทนได้หลังไม้สุดท้าย (points)", min_value=1, value=50000, step=1000,
                                     help="เช่น 50,000 points หมายถึงหลังลงไม้สุดท้ายแล้ว ยังให้ราคาวิ่งต่อได้อีก 50,000 points ก่อนพอร์ตแตก")
        lot_size  = st.number_input("Lot size (ต่อไม้)", min_value=0.0, value=0.01, step=0.01)

    side = st.radio("ทิศทางกริด", options=["LONG", "SHORT"], horizontal=True, index=0)

    # (ออปชัน) ปรับค่าหน่วย point / $/pt/lot
    with st.expander("ตัวเลือกขั้นสูง (หน่วย point และ $/pt/lot)"):
        price_point = st.number_input("1 point = กี่หน่วยราคา", min_value=0.0001, value=DEFAULT_PRICE_POINT, step=0.0001, format="%.4f")
        vpp         = st.number_input("มูลค่าการเคลื่อนที่ ($/point/lot)", min_value=0.0001, value=DEFAULT_VPP_PER_LOT, step=0.1)

    _hrr()
    # ===== สูตร (LaTeX ไม่มีสี + เส้นคั่นบน/ล่าง) =====
    _center_latex(r"""
        \text{ขาดทุนรวม ณ จุดแตก (เติมไม้ห่างกัน }S\text{ points)}:\quad
        L(N)=\text{lot}\cdot\frac{\$}{\text{pt}\cdot\text{lot}}\cdot\Big(NR+S\frac{N(N-1)}{2}\Big)
    """)
    _center_latex(r"""
        \text{เงื่อนไขพอร์ตไม่แตก}:\quad L(N)\le B
        \quad\Rightarrow\quad \text{แก้ควอดราติกหา }N_{\max}\ \text{แล้วปัดลง}
    """)
    _hrr()

    # ===== Compute =====
    if step_pts <= 0 or remain_pts <= 0 or lot_size <= 0 or price_point <= 0 or vpp <= 0:
        st.error("กรุณาตรวจสอบอินพุตหลัก ๆ (step, remain, lot, หน่วย point, $/pt/lot) ต้องมากกว่า 0")
        return

    # จำนวนไม้สูงสุดจากเงื่อนไข 'เหลือ R points หลังไม้สุดท้าย'
    N_max = _max_orders_by_remaining(
        balance=float(balance),
        lot=float(lot_size),
        R=float(remain_pts),
        S=float(step_pts),
        vpp=float(vpp),
    )

    # ราคารายไม้ (แก้ชื่อคีย์เวิร์ดเป็น current_price)
    entries = _calc_entries(current_price=float(current),
                            N=N_max,
                            step_points=float(step_pts),
                            price_point=float(price_point),
                            side=side)

    # ===== Output =====
    st.markdown(
        f"""
        <div style="
            border: 2px solid #22c55e22;
            background: rgba(34,197,94,0.07);
            padding: 16px 18px;
            border-radius: 14px;
            margin: 10px 0 14px 0;">
          <div style="font-size: 1.1rem; font-weight: 800; color: #86efac;">
            จำนวนไม้สูงสุดที่ออกได้
          </div>
          <div style="font-size: 2.6rem; font-weight: 900; margin-top: 4px; line-height: 1;">
            {N_max:,} <span style="font-size: 1.6rem; font-weight: 700;">ไม้</span>
          </div>
          <div style="margin-top: 6px; color:#a3a3a3;">
            หลังไม้สุดท้ายยังทนได้อีก <b>{int(remain_pts):,}</b> points
          </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    if entries:
        st.markdown("**ราคาที่ออกไม้ (เรียงตามการเติมไม้):**")
        # st.code(", ".join(f"{p:,.2f}" for p in entries), language="text")

    # ===== ตารางประกอบ (เลือกดู) =====
    with st.expander("ดูรายละเอียด/คำอธิบาย"):
        _info_box(
            "หลักคิด: เติมไม้ห่างกันทีละ S points จากราคาปัจจุบัน "
            "จนกระทั่งถ้าราคาเดินหน้าต่อจาก “ไม้สุดท้าย” อีก R points จึงจะถึงจุดที่ Equity = 0 (แตก). "
            "สมมติ Margin Call/Stopout ไม่มาก่อน และ $/point/lot คงที่ตามที่กำหนด"
        )
        if N_max > 0:
            df = pd.DataFrame({
                "ลำดับไม้": list(range(1, N_max+1)),
                "ราคาเข้า": entries
            })
            st.dataframe(
                df.style.format({"ราคาเข้า": "{:,.2f}"}).set_properties(**{"text-align":"center"}),
                use_container_width=True,
                height=min(420, (len(df) + 2) * 33)
            )