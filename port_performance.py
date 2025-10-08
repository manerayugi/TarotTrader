# port_performance.py
import streamlit as st
import pandas as pd

# ---------- Helpers ----------
def _hr(width: int = 360):
    st.markdown(
        f"""
        <div style='text-align:center; margin:14px 0;'>
          <hr style='width: {width}px; border: 1px solid #666; margin: 8px auto;'/>
        </div>
        """,
        unsafe_allow_html=True
    )

def _info_box(html_inner: str):
    st.markdown(
        f"""
        <div style="
            border:1px solid #666; padding:12px 14px; border-radius:10px;
            background:#202020; color:#e5e7eb; line-height:1.55;">
          {html_inner}
        </div>
        """,
        unsafe_allow_html=True
    )

def _parse_numbers_csv(raw: str) -> list[float]:
    vals: list[float] = []
    for tok in [t.strip() for t in (raw or "").split(",") if t.strip()]:
        try:
            vals.append(float(tok))
        except Exception:
            # ข้ามค่าที่พาร์สไม่ได้แทนที่จะล้ม
            pass
    return vals

# ---------- Main Tab Renderer ----------
def render_performance_tab():
    st.subheader("📈 Performance (เชนกำไร/ขาดทุน)")

    _hr()

    # สูตร (LaTeX) — ไม่มีการใส่สี
    st.markdown("<div style='text-align:center;'>", unsafe_allow_html=True)
    st.latex(r"""
        r_i = \frac{\Delta_i}{E_{i-1}} \times 100\% \quad,\quad
        E_i = E_{i-1} + \Delta_i \;,\; E_0 = B
    """)
    st.latex(r"""
        R_{\text{เทียบทุนตั้งต้น}}(\%) = \frac{\sum_{i=1}^{n} \Delta_i}{B} \times 100\%
    """)
    st.markdown("</div>", unsafe_allow_html=True)

    _hr()

    # ---------- Inputs ----------
    c1, c2 = st.columns([1.4, 1])
    with c1:
        raw = st.text_area(
            "ใส่ผลกำไร/ขาดทุน (ดอลลาร์): ใช้ , คั่นหลายค่า",
            value="1, -1, 20, -2",
            help="ตัวอย่าง: 1, -1, 20, -2  (ค่าบวก = กำไร, ค่าลบ = ขาดทุน)"
        )
    with c2:
        base = st.number_input("ทุนตั้งต้น ($)", min_value=0.0, value=100.0, step=10.0)

    vals = _parse_numbers_csv(raw)

    if not vals or base <= 0:
        st.info("กรอกกำไร/ขาดทุนอย่างน้อย 1 ค่า และกำหนดทุนตั้งต้น (> 0)")
        return

    # ---------- คำนวณแบบเชน ----------
    rows, equity, cum_profit = [], base, 0.0
    for i, delta in enumerate(vals, start=1):
        pct_on_equity = (delta / equity * 100.0) if equity != 0 else 0.0
        rows.append({
            "#": i,
            "Amount ($)": delta,
            "Equity ก่อนรายการ ($)": equity,
            "% ของทุนขณะนั้น": pct_on_equity,
        })
        equity += delta
        cum_profit += delta

    df = pd.DataFrame(rows)
    sty = (
        df.style
          .format({
              "Amount ($)": "{:,.2f}",
              "Equity ก่อนรายการ ($)": "{:,.2f}",
              "% ของทุนขณะนั้น": "{:.2f}%"
          })
          .set_table_styles([{'selector': 'th', 'props': [('text-align', 'center')]}])
          .set_properties(**{'text-align': 'center'})
    )
    st.dataframe(sty, use_container_width=True, height=min(420, (len(df)+2)*33))

    total_pct_of_base = (cum_profit / base) * 100.0
    _info_box(
        f"กำไรรวม = <b>${cum_profit:,.2f}</b> | เท่ากับ <b>{total_pct_of_base:.2f}%</b> ของทุนตั้งต้น ${base:,.2f}"
    )

    st.markdown("---")
    st.subheader("🎯 ต้องการกำไรจากทุนเป็นกี่ % ?")

    _hr()

    st.latex(r"""
        \text{Profit (USD)} = \frac{\text{Target \%}}{100} \times \text{Base Capital}
    """)

    _hr()

    c3, c4 = st.columns([1, 1])
    with c3:
        target_base = st.number_input("ใช้ทุนฐาน ($)", min_value=0.0, value=base, step=10.0)
    with c4:
        target_pct = st.number_input("ต้องการ (%) ของทุนฐาน", min_value=0.0, value=2.0, step=0.25)

    profit = (target_pct / 100.0) * target_base
    _info_box(
        f"💡 ต้องทำกำไร ≈ <b>${profit:,.2f}</b> เพื่อให้ได้ <b>{target_pct:.2f}%</b> ของทุน ${target_base:,.2f}"
    )