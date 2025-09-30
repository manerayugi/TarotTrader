import streamlit as st
from knowledge_articles import financial, trading, mindset, risk_management
from streamlit.components.v1 import html as st_html
import streamlit.components.v1 as components
import re, hashlib

# ---------- CONFIG (ปรับเส้นทางรูปได้) ----------
COVERS = {
    "financial":       "assets/finance_cover.jpg",
    "trading":         "assets/trading_cover.jpg",
    "mindset":         "assets/mindset_cover.jpg",
    "risk_management": "assets/risk_cover.jpg",
}

# ---------- Helpers ----------
def _cover(path: str, width=220):
    # กัน error รูปหาย
    try:
        st.image(path, width=width)
    except Exception:
        st.warning(f"⚠️ ไม่พบรูปภาพ: {path}")

def _slugify(art: dict) -> str:
    """คืน slug จาก art['slug'] ถ้ามี; ไม่งั้นสร้างจาก title ให้สะอาด/ไม่ว่าง"""
    if isinstance(art, dict) and art.get("slug"):
        base = str(art["slug"])
    else:
        base = str(art.get("title", "article"))
    s = base.strip().lower()
    s = re.sub(r"\s+", "-", s)                 # เว้นวรรค -> -
    s = re.sub(r"[^a-z0-9\-]+", "", s)         # เก็บเฉพาะ a-z0-9-
    s = re.sub(r"-{2,}", "-", s)               # ยุบ --- เป็น -
    s = s.strip("-")                            # ตัด - หัวท้าย
    if not s:
        # กรณีว่างจริง ๆ สร้าง slug จาก hash สั้น ๆ เพื่อกันซ้ำ
        s = "article-" + hashlib.md5(base.encode("utf-8")).hexdigest()[:6]
    return s

def _scroll_to(anchor_id: str):
    components.html(
        f"""
        <script>
        const el = document.getElementById("{anchor_id}");
        if (el) {{
            el.scrollIntoView({{behavior: "smooth", block: "start"}});
        }}
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

def _render_article_list(articles, display_mode: str, cat_id: str):
    for art in articles:
        title = art["title"]
        slug = art.get("slug", title.replace(" ", "_").lower())
        key_suffix = f"{cat_id}_{slug}"

        if display_mode == "เปิดหน้าใหม่":
            if st.button(f"📝 {title}", use_container_width=True, key=f"open_{key_suffix}"):
                st.session_state["show_article"] = art
                st.session_state["sel_cat_id"] = cat_id
                st.session_state["sel_slug"] = slug
                st.rerun()
        else:
            if st.button(f"📝 {title}", use_container_width=True, key=f"append_{key_suffix}"):
                st.session_state["show_article"] = art
                st.session_state["sel_cat_id"] = cat_id
                st.session_state["sel_slug"] = slug
                st.rerun()

# ---------- MAIN ----------
def render_knowledge_index():
    # จุดอ้างอิงด้านบนสุดของหน้าไว้สำหรับปุ่ม "กลับไปด้านบน"
    st.markdown("<div id='top'></div>", unsafe_allow_html=True)

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
    for i, cat in enumerate(categories):
        cat_id = f"cat{i}"  # id ประจำหมวด
        st.subheader(f"{cat['icon']} {cat['title']}")
        col_img, col_desc = st.columns([1, 3])
        with col_img:
            _cover(cat["cover"])
        with col_desc:
            st.caption(cat["desc"])
        _render_article_list(cat["articles"], display_mode, cat_id)
        st.divider()

    # ---------- โซนบทความ (ต่อท้าย) ----------
    if display_mode == "ต่อท้ายสารบัญ" and st.session_state.get("show_article"):
        art = st.session_state["show_article"]
        cat_id = st.session_state.get("sel_cat_id", "cat0")
        slug = st.session_state.get("sel_slug", art["title"].replace(" ", "_").lower())
        anchor_id = f"article-{cat_id}-{slug}"

        # จุดยึดเพื่อเลื่อน
        st.markdown(f"<div id='{anchor_id}'></div>", unsafe_allow_html=True)

        st.markdown("---")
        st.subheader(art["title"])
        if "desc" in art and art["desc"]:
            st.caption(art["desc"])
        art["render"]()  # ฟังก์ชันวาดบทความของไฟล์นั้น

        # เรียกเลื่อนลงมาที่บทความ (หลังแสดงผลแล้ว)
        _scroll_to(anchor_id)

        # ปุ่มกลับบนสุด
        if st.button("🔝 กลับไปด้านบน", key=f"back_top_{anchor_id}"):
            _scroll_top()

    # # โหมด "เปิดหน้าใหม่" — ในแอปเดียวกันเรายังเรนเดอร์ด้านล่างเหมือนเดิม
    # # แต่ก็เลื่อนไปที่บทความทันทีเช่นกัน
    # if mode_state == "เปิดหน้าใหม่" and show_article:
    #     slug = _slugify(show_article)
    #     anchor_id = f"article-{slug}"

    #     st.markdown(f"<div id='{anchor_id}'></div>", unsafe_allow_html=True)
    #     st.markdown("---")
    #     st.subheader(show_article["title"])
    #     st.caption(show_article.get("desc", ""))
    #     if callable(show_article.get("render")):
    #         show_article["render"]()
    #     else:
    #         st.info("บทความนี้ยังไม่มีเนื้อหา")

    #     # ปุ่มกลับไปด้านบน
    #     if st.button("🔝 กลับไปด้านบน", key=f"back_top_new_{slug}"):
    #         _scroll_to("top")

    #     # เลื่อนไปยังบทความที่เพิ่งเปิด
    #     jump = st.session_state.get("__jump_to__")
    #     if jump == anchor_id:
    #         _scroll_to(anchor_id)
    #         st.session_state["__jump_to__"] = None