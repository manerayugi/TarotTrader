# merlin_gtt_pro.py
from __future__ import annotations

import streamlit as st
from func import hr, header
from gtt_pro_gfc import render_gfc_tab
from gtt_pro_grd import render_grd_tab


def render_gtt_pro_tab(default_mode: str = "GRD"):
    header("🧮 GTT PRO — Grid Risk Designer", "CSV mode + Manual Mean/SD presets")
    st.caption("รวมโหมด: ① GFC: จากไฟล์ CSV ② GRD: ป้อน Mean/SD เอง + Risk presets")
    hr()

    # โหมดตั้งต้น = GRD
    idx = 1 if str(default_mode).upper() == "GFC" else 0
    mode = st.radio("เลือกโหมด", options=["GRD (Manual)", "GFC (From CSV)"], index=idx, horizontal=True, key="gttpro_mode_switch")

    st.markdown("---")
    if mode.startswith("GRD"):
        render_grd_tab()
    else:
        render_gfc_tab()