import streamlit as st
from datatypes import SidebarConfig


def render_sidebar() -> SidebarConfig:
    """
    Renders the audit configuration sidebar.
    Returns deep_dive (bool): whether Deep Dive Mode is enabled.
    """
    with st.sidebar:
        st.header("Audit Configuration")
        st.subheader("Data Ingestion")
        ingestion_format = st.selectbox(
            "Application Data Format",
            ["JSON Manifest", "PDF Forms", "XML Export", "JPEG Scans"],
        )

        st.divider()
        st.subheader("Execution Mode")
        deep_dive = st.checkbox("Enable Deep Dive Mode", value=True)
        batch_mode = st.checkbox("Enable Batch Upload Mode", value=False)
        image_processing = st.checkbox("Enable Image Processing", value=False)

        preprocess_contrast = st.number_input(
            label="Boost Contrast",
            value=1.25,
            help="Change photo contrast by raising or lowering this. (0 is dark, 2 is brighter.)",
            min_value=0.00,
            max_value=10.0,
            disabled=not image_processing,
        )
        preprocess_size = st.number_input(
            label="Enlarge photo",
            value=2500,
            help="Change photo size by raising or lowering this.",
            min_value=100,
            max_value=3500,
            disabled=not image_processing,
        )

        st.divider()
        st.subheader("Active Registry Checks")
        for check in st.session_state.active_checks_list:
            badge = "🔬 Deep Dive" if check.get("deep_dive_only") else "⚡ Core"
            st.caption(
                f"**{check['label']}** ({badge})\nPenalty: -{check['deduction']} pts"
            )
    return SidebarConfig(
        deep_dive=deep_dive,
        batch_mode=batch_mode,
        image_processing=image_processing,
        ingestion_format=ingestion_format,
        preprocess_contrast=preprocess_contrast,
        preprocess_size=preprocess_size,
    )
