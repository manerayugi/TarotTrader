# merlin_tab_jarvis.py
import streamlit as st

def render_jarvis_tab():
    st.subheader("🤖 จาวิส — Admin Chat Console")
    st.caption("เชื่อมต่อ LLM ภายนอก (เช่น OpenAI) — จะเพิ่มรายละเอียด/การยิง API ภายหลัง")

    # เก็บ state แชท
    if "merlin_jarvis_msgs" not in st.session_state:
        st.session_state.merlin_jarvis_msgs = []  # list[{"role":"user|assistant","content":"..."}]

    # พื้นที่ตั้งค่าเบื้องต้น (placeholder)
    with st.expander("ตั้งค่าแชท (ชั่วคราว)"):
        st.text_input("API Base URL", key="merlin_api_base", placeholder="https://api.openai.com/v1")
        st.text_input("API Key (จะเก็บใน session เท่านั้น)", key="merlin_api_key", type="password")
        st.selectbox("Model", ["gpt-4o-mini", "gpt-4o", "gpt-4.1", "gpt-3.5-turbo"], index=0, key="merlin_model")
        st.caption("**หมายเหตุ**: ตอนนี้ยังไม่ยิง API จริง แค่หน้า UI เตรียมไว้")

    # แสดงประวัติแชท
    st.markdown("---")
    for m in st.session_state.merlin_jarvis_msgs:
        if m["role"] == "user":
            st.markdown(f"**คุณ:** {m['content']}")
        else:
            st.markdown(f"**จาวิส:** {m['content']}")

    st.markdown("---")
    # ช่องพิมพ์
    with st.form("jarvis_form", clear_on_submit=True):
        prompt = st.text_area("พิมพ์ข้อความถึงจาวิส", height=100, key="jarvis_prompt")
        sent = st.form_submit_button("ส่ง")
    if sent and prompt.strip():
        # บันทึกข้อความผู้ใช้
        st.session_state.merlin_jarvis_msgs.append({"role": "user", "content": prompt.strip()})
        # ตอบแบบ mock ไว้ก่อน (ยังไม่เรียก API จริง)
        reply = "🛠️ (ยังไม่ได้เชื่อม API) — จะตอบจริงเมื่อเปิดใช้การยิง API"
        st.session_state.merlin_jarvis_msgs.append({"role": "assistant", "content": reply})
        st.rerun()

    # ปุ่มล้างประวัติ
    cols = st.columns(2)
    with cols[0]:
        if st.button("🧹 ล้างประวัติแชท"):
            st.session_state.merlin_jarvis_msgs = []
            st.experimental_rerun() if hasattr(st, "experimental_rerun") else st.rerun()