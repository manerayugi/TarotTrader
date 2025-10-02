import os, base64, mimetypes
import streamlit as st

def center_image_safe(path: str, caption: str = None, width: int = 480):
    """แสดงรูปแบบกึ่งกลาง + แคปชันกึ่งกลาง (เรนเดอร์ครั้งเดียว)"""
    def _data_uri(p: str):
        mime, _ = mimetypes.guess_type(p)
        if mime is None:
            ext = os.path.splitext(p)[1].lower()
            mime = {
                ".jpg": "image/jpeg", 
                ".jpeg": "image/jpeg",
                ".png": "image/png", 
                ".gif": "image/gif", 
                ".webp": "image/webp",
            }.get(ext, "image/jpeg")
        with open(p, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        return f"data:{mime};base64,{b64}"

    # สร้าง HTML เดียวที่มีทั้งรูปและแคปชันภายใน <figure>
    if path and os.path.exists(path):
        src = _data_uri(path)
        img_html = f"<img src='{src}' width='{width}' style='display:block;margin:0 auto;border-radius:8px;'/>"
    else:
        h = int(width * 0.62)
        img_html = (
            f"<div style='display:inline-flex;width:{width}px;height:{h}px;"
            "align-items:center;justify-content:center;background:#1f2937;"
            "border:1px dashed #4b5563;border-radius:10px;color:#9ca3af;"
            "font-size:0.9rem;text-align:center;padding:10px;'>"
            f"📷 ไม่พบรูปภาพ</div>"
            # f"📷 ไม่พบรูปภาพ<br><small>{path}</small></div>"
        )

    caption_html = (
        f"<figcaption style='font-size:0.9rem;color:#9ca3af;margin-top:6px;'>{caption}</figcaption>"
        if caption else ""
    )

    st.markdown(
        "<div style='display:flex;justify-content:center;margin:16px 0;'>"
        f"<figure style='margin:0;text-align:center'>{img_html}{caption_html}</figure>"
        "</div>",
        unsafe_allow_html=True,
    )