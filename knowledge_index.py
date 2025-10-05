# knowledge_index.py
import streamlit as st
from knowledge_articles import financial, trading, mindset, risk_management
from streamlit.components.v1 import html as st_html
import streamlit.components.v1 as components
import re, hashlib
from auth import require_login_or_public

# ---------- CONFIG ----------
COVERS = {
    "financial":       "assets/finance_cover.jpg",
    "trading":         "assets/trading_cover.jpg",
    "mindset":         "assets/mindset_cover.jpg",
    "risk_management": "assets/risk_cover.jpg",
}

# ---------- Helpers ----------
def _cover(path: str, width=220):
    try:
        st.image(path, width=width)
    except Exception:
        st.warning(f"⚠️ ไม่พบรูปภาพ: {path}")

def _slugify(art: dict) -> str:
    base = str(art.get("slug") or art.get("title") or "article")
    s = base.strip().lower()
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"[^a-z0-9\-]+", "", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    if not s:
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

def _render_article_buttons(articles, cat_id: str, cat_title: str, cat_icon: str):
    """แสดงปุ่มชื่อบทความเป็นกริด 3 คอลัมน์ + ใช้ไอคอนตามหมวด"""
    if not articles:
        st.info("ยังไม่มีบทความในหมวดนี้")
        return

    cols_per_row = 3
    for i in range(0, len(articles), cols_per_row):
        row_items = articles[i:i+cols_per_row]
        cols = st.columns(cols_per_row, gap="small")

        for j, art in enumerate(row_items):
            with cols[j]:
                title = art["title"]
                slug = art.get("slug") or _slugify(art)
                key_suffix = f"{cat_id}_{i+j}_{slug}"
                if st.button(f"{cat_icon} {title}", use_container_width=True, key=f"open_{key_suffix}"):
                    st.session_state["show_article"]   = art
                    st.session_state["sel_cat_id"]     = cat_id
                    st.session_state["sel_slug"]       = slug
                    st.session_state["sel_cat_title"]  = cat_title
                    st.session_state["sel_cat_icon"]   = cat_icon
                    st.session_state["__jump_to__"]    = f"article-{cat_id}-{slug}"
                    st.rerun()

# ---------- MAIN ----------
def render_knowledge_index():
    # 🔐 ตรวจสิทธิ์ก่อน
    if not require_login_or_public("knowledge"):
        return
    # จุดอ้างอิงด้านบนสุด
    st.markdown("<div id='top'></div>", unsafe_allow_html=True)

    # ---------- ถ้าเลือกบทความแล้ว: แสดงบทความเดี่ยว ----------
    show_article = st.session_state.get("show_article")
    if show_article:
        catid = st.session_state.get("sel_cat_id", "cat0")
        slug  = st.session_state.get("sel_slug", _slugify(show_article))
        cat_title = st.session_state.get("sel_cat_title", "คลังความรู้")
        cat_icon  = st.session_state.get("sel_cat_icon", "📚")
        anchor_id = f"article-{catid}-{slug}"

        st.markdown(f"<div id='{anchor_id}'></div>", unsafe_allow_html=True)

        # แถบบน: ปุ่มย้อนกลับ (เล็ก ๆ) + breadcrumb หมวด
        top_l, top_r = st.columns([1, 6])
        with top_l:
            if st.button("← กลับ", key=f"back_{anchor_id}", use_container_width=False):
                st.session_state.pop("show_article", None)
                st.session_state.pop("sel_cat_id", None)
                st.session_state.pop("sel_slug", None)
                st.session_state.pop("sel_cat_title", None)
                st.session_state.pop("sel_cat_icon", None)
                _scroll_top()
                st.rerun()
        with top_r:
            st.caption(f"จากหมวด: {cat_icon} **{cat_title}**")

        st.markdown("---")
        st.subheader(show_article["title"])
        if show_article.get("desc"):
            st.caption(show_article["desc"])
        if callable(show_article.get("render")):
            show_article["render"]()
        else:
            st.info("บทความนี้ยังไม่มีเนื้อหา")

        if st.session_state.get("__jump_to__") == anchor_id:
            _scroll_to(anchor_id)
            st.session_state["__jump_to__"] = None

        return  # จบโหมดบทความเดี่ยว

    # ---------- หน้า “รวมบทความ” (สาธารณะ) ----------
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

    for i, cat in enumerate(categories):
        cat_id = f"cat{i}"
        st.subheader(f"{cat['icon']} {cat['title']}")
        col_img, col_desc = st.columns([1, 3])
        with col_img:
            _cover(cat["cover"])
        with col_desc:
            st.caption(cat["desc"])
        _render_article_buttons(cat["articles"], cat_id, cat["title"], cat["icon"])
        st.divider()

    st.markdown(
        "<div style='text-align:center; color:#9aa0a6; font-size:.9rem; margin-top:12px;'>"
        "บทความยาว ~3–5 นาทีต่อชิ้น • เน้นนำไปใช้จริงในระบบ Tarot Trader ของคุณ</div>",
        unsafe_allow_html=True,
    )