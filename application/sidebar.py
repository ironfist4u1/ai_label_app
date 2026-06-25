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
        st.divider()
        st.subheader("Active Registry Checks")
        for check in env.configured_compliance_checks():
            badge = "🔬 Deep Dive" if check.get("deep_dive_only") else "⚡ Core"
            st.caption(f"**{check['label']}** ({badge})\nPenalty: -{check['deduction']} pts")
    return SidebarConfig(deep_dive=deep_dive)
