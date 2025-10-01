import streamlit as st

def center_image(path: str, caption: str = None, width: int = 480):
    """แสดงรูปภาพให้อยู่ตรงกลาง พร้อม caption (ถ้ามี)"""
    html = f"""
    <div style='text-align:center; margin:16px 0;'>
        <img src='{path}' width='{width}' style='border-radius:8px;'/>
        {f"<div style='font-size:0.9rem; color:#9ca3af; margin-top:4px;'>{caption}</div>" if caption else ""}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

# --------- ตัวอย่างบทความ (เพิ่มได้เรื่อย ๆ) ---------
def art_budget_basic():
    st.write(
        """
        การวางแผนงบประมาณเป็นรากฐานสำคัญของสุขภาพการเงินส่วนบุคคล...
        (ใส่เนื้อหาประมาณ 300–500 คำตามต้องการ)
        """
    )
    st.image("assets/finance_cover.jpg", width=300, caption="ภาพประกอบหมวดการเงินพื้นฐาน")

def art_emergency_fund():
    st.write(
        """
        กองทุนฉุกเฉินคือกันชนทางการเงินที่ช่วยให้คุณไม่ต้องไปพึ่งหนี้ระยะสั้น...
        """
    )

# --------- ดัชนีบทความในหมวดนี้ ---------
ARTICLES = [
    {
        "title": "เริ่มต้นวางแผนงบประมาณอย่างชาญฉลาด",
        "desc": "พื้นฐานการจัดสรรรายรับ-รายจ่ายให้เงินเหลือและงอกเงย",
        "render": art_budget_basic,
    },
    {
        "title": "กองทุนฉุกเฉิน: ทำไมต้องมี และควรมีกี่เดือน",
        "desc": "วิธีคำนวณขนาดกองทุนฉุกเฉินและแนวทางเก็บสะสม",
        "render": art_emergency_fund,
    },
]