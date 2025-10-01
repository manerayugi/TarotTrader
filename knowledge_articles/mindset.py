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

# ---------- บทความเดิม ----------
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

# ---------- บทความใหม่ ----------
def art_emotion_control():
    st.header("ควบคุมอารมณ์ในวันที่กราฟสวน")
    center_image_safe("assets/articles/emotion_control.jpg")

    st.markdown("""
วันที่กราฟสวนคือวันที่ระบบ **ทดสอบวินัย** ของเราอย่างแท้จริง ความโกรธ เสียดาย และกลัวพลาด  
ทำให้ตัดสินใจผิดซ้ำ ๆ เช่น เพิ่มไม้โดยไม่มีแผน หรือยกเลิก SL เพื่อ “เอาคืน”

### 🧭 Framework 3 ขั้น ช่วยคุมอารมณ์
**(1) Pause** – หยุดการคลิกทุกอย่าง 60–120 วินาที หายใจลึก 4–7–8 ครั้ง  
**(2) Review** – กลับไปที่แผน: Entry/SL/TP, Risk/ไม้, สัญญาณที่ใช้  
**(3) Decide** – เลือกหนึ่งเดียว: *ทำตามแผน* หรือ *ออกนอกตลาด* ห้ามแก้ไม้กลางทาง

### 🧰 เครื่องมือที่ช่วย
- ✅ **Check-list ก่อนเข้า**: เงื่อนไขครบ? RR คุ้ม? ความผันผวนวันนี้สูงผิดปกติไหม?  
- 🛑 **กำหนด Max loss per day**: ถึงจุดหยุด → ปิดจอ (รักษาเงินและสภาพจิตใจ)  
- 📏 **ใช้ขนาด Lot ตาม Risk%**: ให้ระบบช่วยลดแรงกระแทกทางอารมณ์

> การควบคุมอารมณ์ไม่ได้หมายถึง “ไม่รู้สึก”  
> แต่คือการยอมรับความรู้สึก และทำในสิ่งที่ถูกต้องต่อระบบของเราอย่างสม่ำเสมอ
    """)

def art_loss_aversion_deep():
    st.header("จิตวิทยาเทรด: ทำไมกำไรน้อยแต่ขาดทุนหนัก")
    center_image_safe("assets/articles/psych_loss.jpg", caption="Loss Aversion – กลัวขาดทุนมากกว่ารักกำไร")

    st.markdown("""
**Loss Aversion** คือธรรมชาติที่สมองให้ค่าน้ำหนักกับ “ความเจ็บปวดจากการขาดทุน” มากกว่า  
“ความสุขจากการได้กำไร” ส่งผลให้พฤติกรรมทั่วไปคือ *รีบตัดกำไร แต่ปล่อยขาดทุนยาว*  

เมื่อราคาเริ่มบวกเล็กน้อย เราอยากล็อกผลลัพธ์ทันทีเพื่อสบายใจ  
แต่พอขาดทุน เรามักจะหวังและรอให้กลับมาเท่าทุน จนกลายเป็นความเสียหายหนักและทำลายวินัย

---

### 🧠 ทำไมมันเกิดขึ้น?
- สมองเกลียดความไม่แน่นอน → เลือกปิดกำไรเล็ก ๆ เพื่อจบความเสี่ยงเร็ว  
- ความหวัง / อคติยืนยัน (Confirmation Bias) → มองเฉพาะข้อมูลที่ “อยากให้เป็น”  
- ไม่มี **แผนก่อนเข้า**: จุดเข้า–SL–TP และขนาด Lot ที่สัมพันธ์กับความเสี่ยง

---

### 🧭 วิธีแก้แบบใช้งานได้จริง
1. **ตั้ง SL/TP ก่อนเข้าเสมอ** และไม่เลื่อน SL ออกไป  
2. **Risk ต่อไม้คงที่ (% ของพอร์ต)** เพื่อให้ระบบทำงานแทนความรู้สึก  
3. **บันทึกการเทรด (Trading Journal)** เพื่อสะท้อนพฤติกรรมซ้ำ ๆ  
4. **วัดคุณภาพการตัดสินใจ** ไม่ใช่ผลกำไร เช่น R-multiple, Win/Loss Expectancy  

> 💡 **เคล็ดลับ:** ให้รางวัลตัวเองเมื่อ “ทำตามแผน” ไม่ใช่เมื่อ “ได้กำไร”  
> เพราะเป้าหมายคือความสม่ำเสมอในระยะยาว ไม่ใช่ชัยชนะครั้งเดียว
""")
    
# ---------- รวมบทความ ----------
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
    {
        "title": "ควบคุมอารมณ์ในวันที่กราฟสวน",
        "desc": "เรียนรู้เทคนิคการจัดการอารมณ์ เมื่อเจอสถานการณ์สวนทางกับแผนการเทรด เพื่อป้องกันการตัดสินใจผิดพลาด",
        "render": art_emotion_control,
    },
    {
        "title": "จิตวิทยาเทรด: ทำไมกำไรน้อยแต่ขาดทุนหนัก",
        "desc": "เข้าใจกลไกสมองและฝึกวินัยเพื่ออยู่รอดในตลาดระยะยาว",
        "render": art_loss_aversion_deep,
    },
]