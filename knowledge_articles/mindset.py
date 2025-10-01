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

def art_trading_journal():
    st.write(
        """
        บันทึกการเทรด (Trading Journal) ช่วยให้เราเรียนรู้จากข้อผิดพลาด...
        """
    )

def art_loss_aversion():
    st.write(
        """
        Loss Aversion คืออคติที่กลัวการขาดทุนมากเกินไป...
        """
    )

ARTICLES = [
    {
        "title": "เริ่มต้นทำ Trading Journal แบบไม่ยุ่งยาก",
        "desc": "กรอบการจดเพื่อสะท้อนตนเองและพัฒนาระบบเทรด",
        "render": art_trading_journal,
    },
    {
        "title": "เข้าใจ Loss Aversion แล้วอยู่กับตลาดได้ยาวขึ้น",
        "desc": "เคล็ดลับฝึกสติ ลดอคติในการตัดสินใจ",
        "render": art_loss_aversion,
    },
]