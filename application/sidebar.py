import streamlit as st
from config import env
from datatypes import SidebarConfig


def render_sidebar() -> SidebarConfig:
    """
    Renders the audit configuration sidebar.
    Returns deep_dive (bool): whether Deep Dive Mode is enabled.
    """
    with st.sidebar:
        st.header("Audit Configuration")
        deep_dive = st.checkbox("Enable Deep Dive Mode", value=False)
        batch_mode = st.checkbox("Enable Batch Upload Mode", value=False)
        preprocess_contrast = st.number_input(
            label="Boost Contrast",
            value=1.25,
            help="Change photo contrast by raising or lowering this. (0 is dark, 2 is brighter.)",
            min_value=0.00,
            max_value=10.0
        )
        preprocess_size = st.number_input(
            label="Boost Contrast",
            value=1500,
            help="Change photo size by raising or lowering this.",
            min_value=100,
            max_value=2500
        )
        st.divider()
        st.subheader("Active Registry Checks")
        for check in env.configured_compliance_checks():
            badge = "🔬 Deep Dive" if check.get("deep_dive_only") else "⚡ Core"
            st.caption(f"**{check['label']}** ({badge})\nPenalty: -{check['deduction']} pts")
    return SidebarConfig(
        deep_dive=deep_dive,
        batch_mode=batch_mode,
        preprocess_contrast=preprocess_contrast,
        preprocess_size=preprocess_size,
    )
