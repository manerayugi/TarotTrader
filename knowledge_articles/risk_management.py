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

def art_position_sizing_intro():
    st.write(
        """
        Position Sizing คือวิธีตัดสินใจว่าจะเปิดสถานะขนาดเท่าไหร่ต่อดีล...
        """
    )

def art_risk_reward():
    st.write(
        """
        Risk/Reward Ratio คืออัตราส่วนความเสี่ยงต่อผลตอบแทนที่คาดหวัง...
        """
    )

ARTICLES = [
    {
        "title": "ทำความรู้จัก Position Sizing",
        "desc": "วิธีคิดขนาดสัญญาให้สอดคล้องกับความเสี่ยง",
        "render": art_position_sizing_intro,
    },
    {
        "title": "ออกแบบ Risk/Reward ให้เหมาะกับสไตล์คุณ",
        "desc": "เพิ่มโอกาสรอดด้วย RRR ที่มีวินัย",
        "render": art_risk_reward,
    },
]