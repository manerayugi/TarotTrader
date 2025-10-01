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
    
def art_trend_following():
    st.write(
        """
        Trend Following คือแนวทางเทรดที่เดินตามทิศทางหลักของราคา...
        """
    )

def art_support_resistance():
    st.write(
        """
        แนวรับ-แนวต้านเป็นโซนราคาที่ผู้เล่นจำนวนมากให้ความสนใจ...
        """
    )

ARTICLES = [
    {
        "title": "พื้นฐาน Trend Following ที่เข้าใจง่าย",
        "desc": "จับทิศทางหลักของราคาและปล่อยให้กำไรวิ่ง",
        "render": art_trend_following,
    },
    {
        "title": "อ่านแนวรับ-แนวต้านแบบเนียน ๆ",
        "desc": "ดูจุดกลับตัวและบริเวณที่น่าเข้าทำ",
        "render": art_support_resistance,
    },
]