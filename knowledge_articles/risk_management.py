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

# ---------- บทความใหม่ ----------
def art_lot_management():
    st.header("เข้าไม้ยังไงไม่ล้างพอร์ต: พื้นฐานการจัดการ Lot")
    center_image_safe("assets/articles/lot_mgmt.jpg", caption="Lot Size ที่สัมพันธ์กับความเสี่ยง คือหัวใจของการอยู่รอด")

    st.markdown(r"""
หัวใจของการรอดในตลาดคือ **ขนาดไม้ (Position Sizing)** ที่สัมพันธ์กับ *ความเสี่ยง* ไม่ใช่ความรู้สึก  
สูตรพื้นฐานที่ใช้ได้จริงในแอปนี้คือ:
""")
    st.latex(r'''
    \text{Lot}=\frac{\text{Risk Amount}}{\text{Distance(points)}\times (\$/\text{point}/\text{lot})}
    ''')

    st.markdown("""
### แนวปฏิบัติแนะนำ
- กำหนด **Risk ต่อไม้** เป็น % คงที่ เช่น 0.5–2% ของพอร์ต  
- คำนวณ **ระยะ SL** ตามโครงสร้างราคา ไม่ใช่ตามจำนวนเงินที่อยากเสี่ยง  
- ตรวจสอบ **MaxLot** เทียบ Leverage/Contract ก่อนทุกครั้ง  
- อย่าเพิ่มไม้เพราะอยากเอาคืน หากจะเฉลี่ย ควรมีแผน Grid/Martingale ที่ชัดเจน  

เมื่อ *Risk* คงที่ และ *ระยะ SL* มีเหตุผล ขนาดไม้จะออกมาอย่างสมดุล ช่วยให้กราฟไปผิดทางก็เสียหายจำกัด  
และเมื่อไปถูกทาง กำไรจะเติบโตอย่างเป็นระบบ
""")
    
def art_risk_reward_ratio():
    st.header("Risk–Reward คืออะไร?")
    center_image_safe(
        "assets/riskmm_cover.jpeg",
        caption="เข้าใจอัตราส่วนความเสี่ยงต่อผลตอบแทน (Risk–Reward Ratio)",
        width=480
    )

    st.markdown("""
**Risk–Reward (RR)** คืออัตราส่วนระหว่าง *ความเสี่ยงที่ยอมเสีย (Risk)* ต่อ *ผลตอบแทนที่คาดหวัง (Reward)*  
เช่น RR = 1:2 หมายถึง “เสี่ยง 1 เพื่อหวังผลตอบแทน 2” การตั้ง RR ที่ดีช่วยให้ระบบเทรดมี **ความคาดหวังบวก (Positive Expectancy)** ได้จริง
""")

    st.markdown("### วิธีใช้อย่างได้ผล")
    st.write(
        "- ✅ **กำหนด Stop Loss (SL)** ก่อนทุกครั้ง เพื่อรู้ว่า ‘ยอมเสียได้เท่าไร’\n"
        "- 🎯 **ตั้ง Take Profit (TP)** ให้สัมพันธ์กับ SL เช่น RR ≥ 1:1.5 หรือ 1:2\n"
        "- 📏 **คำนวณขนาด Lot ตาม Risk% ต่อไม้** (เช่น 1%) เพื่อคุมความเสี่ยงรวมของพอร์ต"
    )

    st.markdown("### สรุปสั้น ๆ")
    st.write(
        "กำไรระยะยาวไม่ได้มาจาก Winrate เพียงอย่างเดียว แต่เกิดจากการผสมผสานของ **Risk–Reward Ratio ที่เหมาะสม + วินัยในการทำตามระบบ**"
    )
# ---------- ตัวอย่างบทความอื่น (ถ้ามี) ----------

# ---------- รวมบทความ ----------
ARTICLES = [
    {
        "title": "เข้าไม้ยังไงไม่ล้างพอร์ต: พื้นฐานการจัดการ Lot",
        "desc": "เข้าใจ Position Sizing เพื่ออยู่รอดในตลาดอย่างมืออาชีพ",
        "render": art_lot_management,
    },
        {
        "title": "Risk–Reward คืออะไร?",
        "desc": "เข้าใจอัตราส่วนความเสี่ยงต่อผลตอบแทน เพื่อสร้างระบบที่มีความคาดหวังบวก",
        "render": art_risk_reward_ratio,
    },
]