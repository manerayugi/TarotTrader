import streamlit as st
import os

def center_image_safe(path: str, caption: str = None, width: int = 480):
    """แสดงรูปภาพกึ่งกลางแบบปลอดภัย:
       - ถ้าไฟล์มี: โชว์รูป
       - ถ้าไฟล์หาย: โชว์กล่อง placeholder แต่ 'ไม่ throw error'
       และจะ 'ยังแสดงเนื้อหาด้านล่างต่อ' แน่นอน
    """
    st.markdown("<div style='text-align:center; margin:16px 0;'>", unsafe_allow_html=True)

    if path and os.path.exists(path):
        st.image(path, width=width)
    else:
        # กล่องเทาเป็น placeholder (กว้างเท่ารูป) เพื่อไม่ให้เลย์เอาท์เพี้ยน
        h = int(width * 0.62)
        st.markdown(
            f"""
            <div style="
                display:inline-flex; width:{width}px; height:{h}px;
                align-items:center; justify-content:center;
                background:#1f2937; border:1px dashed #4b5563; border-radius:10px;
                color:#9ca3af; font-size:0.9rem; text-align:center; padding:10px;">
                📷 ไม่พบรูปภาพ<br><small>{path}</small>
            </div>
            """,
            unsafe_allow_html=True
        )

    if caption:
        st.markdown(
            f"<div style='font-size:0.9rem; color:#9ca3af; margin-top:6px;'>{caption}</div>",
            unsafe_allow_html=True
        )
    st.markdown("</div>", unsafe_allow_html=True)