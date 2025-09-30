import streamlit as st
from knowledge_articles import financial, trading, mindset, risk_management
from streamlit.components.v1 import html as st_html

# ---------- CONFIG (ปรับเส้นทางรูปได้) ----------
COVERS = {
    "financial":      "assets/finance_cover.jpg",
    "trading":        "assets/trading_cover.jpg",
    "mindset":        "assets/mindset_cover.jpg",
    "risk_management":"assets/risk_cover.jpg",
}

def _cover(path: str, width=220):
    # กัน error รูปหาย
    try:
        st.image(path, width=width)
    except Exception:
        st.warning(f"⚠️ ไม่พบรูปภาพ: {path}")

def _render_article_list(articles, display_mode: str):
    # ปุ่ม/ลิงก์ของบทความในหมวดนั้น
    for art in articles:
        title = art["title"]
        if display_mode == "เปิดหน้าใหม่":
            # โหมดนี้จะ “รันต่อท้าย” เหมือนกัน (เป็น single-file app)
            # แต่เราทำให้ไปโชว์ส่วนบทความด้านล่างทันที
            if st.button(f"📝 {title}", use_container_width=True, key=f"open_{title}"):
                st.session_state["show_article"] = art
                st.rerun()
        else:
            if st.button(f"📝 {title}", use_container_width=True, key=f"append_{title}"):
                st.session_state["show_article"] = art
                st.rerun()

def _scroll_to(target_id: str):
    # ใช้ JS ใน iframe เลื่อนหน้า main ผ่าน parent
    st_html(
        f"""
        <script>
        const el = parent.document.getElementById("{target_id}");
        if (el) {{ el.scrollIntoView({{behavior: "smooth", block: "start"}}); }}
        </script>
        """,
        height=0,
    )

def _scroll_top():
    st_html(
        """
        <script>
        parent.window.scrollTo({top: 0, behavior: "smooth"});
        </script>
        """,
        height=0,
    )
    
def render_knowledge_index():
    # จุดยึดสำหรับเลื่อนขึ้นบนสุด
    st.markdown("<div id='ki-top'></div>", unsafe_allow_html=True)
    # ---------- HERO / TAGLINE ----------
    st.header("📚 Trader’s Wisdom – คลังความรู้เทรดเดอร์")
    st.caption("รวบรวมบทความให้ความรู้เพื่อพัฒนาทักษะการเงิน การเทรด จิตวิทยา และการจัดการความเสี่ยง")
    st.markdown(
        """
        <div style="padding:10px 14px; border:1px solid #333; border-radius:10px; margin:10px 0; color:#9aa0a6;">
          <b>คำแนะนำ:</b> เริ่มจากพื้นฐานด้านการเงิน → ต่อด้วยเทคนิคการเทรด → เสริมด้วย Mindset → ปิดท้ายด้วย Risk & Money Management
        </div>
        """,
        unsafe_allow_html=True
    )
       # แบนเนอร์เล็ก (optional)
    st.markdown(
        """
        <div style="text-align:center; margin:10px 0 18px 0; opacity:.9;">
          <hr style="width: 340px; border: 1px solid #666; margin: 8px auto;"/>
          <div style="font-size:1.05rem;">อ่านวันละนิด เพิ่มทักษะวันละครึ่งก้าว 🧭</div>
          <hr style="width: 340px; border: 1px solid #666; margin: 8px auto;"/>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ---------- โหมดการแสดงผล ----------
    display_mode = st.radio(
        "เลือกรูปแบบการเปิดบทความ",
        options=["ต่อท้ายสารบัญ", "เปิดหน้าใหม่"],
        horizontal=True
    )

    st.divider()

    # ---------- หมวดต่าง ๆ ----------
    categories = [
        {
            "icon": "💰",
            "title": "Financial – การเงินพื้นฐาน",
            "desc": "สร้างรากฐานการเงินที่แข็งแรง ด้วยแนวคิดและทักษะที่นำไปใช้ได้จริงในชีวิตประจำวัน",
            "cover": COVERS["financial"],
            "articles": financial.ARTICLES
        },
        {
            "icon": "📈",
            "title": "เทคนิคหรือความรู้ด้านการเทรด",
            "desc": "แนวคิดและเทคนิคการเทรดที่ย่อยง่าย ปฏิบัติได้จริง ในสไตล์ Tarot Trader",
            "cover": COVERS["trading"],
            "articles": trading.ARTICLES
        },
        {
            "icon": "🧠",
            "title": "Mindset หรือจิตวิทยาการเทรด",
            "desc": "จัดการอารมณ์ โฟกัสและวินัย เพื่อให้การเทรดยั่งยืนมากขึ้น",
            "cover": COVERS["mindset"],
            "articles": mindset.ARTICLES
        },
        {
            "icon": "⚖️",
            "title": "Risk & Money Management",
            "desc": "แก่นสำคัญของการอยู่รอดในตลาด: บริหารความเสี่ยงและเงินทุนอย่างเป็นระบบ",
            "cover": COVERS["risk_management"],
            "articles": risk_management.ARTICLES
        },
    ]

    # แต่ละหมวด — แสดงรูป/คำโปรย + ปุ่มชื่อบทความ
    for cat in categories:
        st.subheader(f"{cat['icon']} {cat['title']}")
        col_img, col_desc = st.columns([1, 3])
        with col_img:  _cover(cat["cover"])
        with col_desc: st.caption(cat["desc"])
        _render_article_list(cat["articles"], display_mode)
        st.divider()

    # ---------- โซนบทความ (ต่อท้าย) ----------
    # ถ้าโหมด "ต่อท้ายสารบัญ" และมีบทความที่ถูกเลือก → แสดงด้านล่างสุด
    if display_mode == "ต่อท้ายสารบัญ" and st.session_state.get("show_article"):
        art = st.session_state["show_article"]
        st.markdown("---")
        st.subheader(art["title"])
        st.caption(art["desc"])
        art["render"]()  # call renderer function of that article

        # ปุ่มกลับไปบนสุด + reset state
        if st.button("🔝 กลับไปด้านบน"):
            st.session_state.pop("show_article", None)
            st.rerun()