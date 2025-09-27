import os
import base64
import streamlit as st

def render_home_page():
    """แสดงหน้า Home Page หลัก"""
    # ---------- CSS ----------
    st.markdown("""
    <style>
    .home-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
        padding-top: 40px;
    }

    /* โลโก้: จัดกลางแน่นอน */
    .home-logo {
        width: 120px;
        height: 120px;
        border-radius: 50%;
        object-fit: cover;
        border: 2px solid #2f3651;
        margin-bottom: 8px;
        display: block;
        margin-left: auto;
        margin-right: auto;
    }

    .home-title {
        font-size: 1.6rem;
        font-weight: 700;
        margin-bottom: 4px;
        text-align: center;
    }
    .home-sub {
        font-size: 1.1rem;
        font-weight: 700;
        color: #bbb;
        text-align: center;
        line-height: 1.6;
    }

    .qr-row {
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 48px;
        margin-top: 32px;
        flex-wrap: wrap;
    }
    .qr-item {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
    }
    .qr-img {
        width: 100px;
        height: 100px;
        border-radius: 12px;
        object-fit: cover;
        margin-bottom: 8px;
        border: 1px solid #333;
        display: block;
    }
    .qr-name {
        text-align: center;
        margin-bottom: 6px;
        font-weight: 500;
    }
    </style>
    """, unsafe_allow_html=True)

    # ---------- Content ----------
    st.markdown("<div class='home-container'>", unsafe_allow_html=True)

    # โลโก้ (จัดกลางแน่นอน)
    logo_path = "assets/logo.png"
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as f:
            _b64 = base64.b64encode(f.read()).decode("utf-8")
        st.markdown(f"<img src='data:image/png;base64,{_b64}' class='home-logo' />", unsafe_allow_html=True)

    # ชื่อเพจ + คำโปรย
    st.markdown("<div class='home-title'>🔮 Tarot Trader 💹</div>", unsafe_allow_html=True)
    st.markdown("<div class='home-title'>หมอดูพาเทรด</div>", unsafe_allow_html=True)
    st.markdown("<div class='home-sub'>จับไพ่ จับเทรนด์ พาเทรด พัฒนาความคิด สร้างวินัยสู่อิสรภาพทางการเงิน</div>", unsafe_allow_html=True)

    # ---------- QR + ปุ่ม ----------
    qr_data = [
        {"name": "TikTok", "img": "assets/qr_tiktok.png", "url": "https://www.tiktok.com/@tarottrader162"},
        {"name": "Facebook", "img": "assets/qr_facebook.png", "url": "https://www.facebook.com/TarotTrader162"},
        {"name": "LINE", "img": "assets/qr_line.png", "url": "https://lin.ee/Fwd8Qqen"},
    ]
    
    st.markdown("<div class='qr-row'>", unsafe_allow_html=True)
    cols = st.columns(len(qr_data))
    for i, q in enumerate(qr_data):
        with cols[i]:
            if os.path.exists(q["img"]):
                # st.image(q["img"], width=300)
                with open(q["img"], "rb") as f:
                    b64 = base64.b64encode(f.read()).decode()
                st.markdown(
                    f"""
                    <div style='text-align:center'>
                        <img src='data:image/png;base64,{b64}' width='300' style='border-radius:12px; border:1px solid #333;' />
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            st.markdown("<div style='margin-top:10px;'>", unsafe_allow_html=True)
            st.link_button(f"ไปที่ {q['name']}", q["url"], use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)