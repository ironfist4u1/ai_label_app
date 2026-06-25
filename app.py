import logging
import streamlit as st
from engine import run_compliance_audit, run_batch_compliance_audit
from application import render_sidebar, render_form, render_upload, render_results, render_batch_results
from datatypes import SidebarConfig

logger = logging.getLogger("StreamlitUI")

st.set_page_config(page_title="Dynamic TTB Verification Portal", layout="wide")
st.title("Alcohol Label Compliance Verifier")
st.markdown("Automated extensible verification framework for TTB COLA label validation.")

sidebar_config: SidebarConfig = render_sidebar()

st.header("1. Application Metadata & Artifacts")
col1, col2 = st.columns(2)

with col1:
    form_payload = render_form(sidebar_config)

with col2:
    uploaded_labels = render_upload()

if st.button("Run Verification Audit", type="primary"):
    has_data = 0 < len(form_payload) if isinstance(form_payload, list) else any(form_payload.values())
    if not has_data or not uploaded_labels:
        logger.warning("Audit attempted without required form data or image artifacts.")
        st.error("Please provide validation metadata (either typed or uploaded) and submit at least one label image.")
    else:
        brand_name = form_payload.get("brand_name", "Brand Name Not Found") if sidebar_config.batch_mode is False else "Batch"
        logger.info(f"Audit initiated. Images: {len(uploaded_labels)} | Deep Dive: {sidebar_config.deep_dive}")
        st.divider()
        st.header("2. System Compliance Report Output")
        st.subheader(f"Results for: {brand_name}")
        with st.spinner(f"Running automated evaluations on {brand_name}..."):
            try:
                if not sidebar_config.batch_mode:
                    report = run_compliance_audit(uploaded_labels, form_payload, sidebar_config)
                    render_results(report)
                else:
                    reports = run_batch_compliance_audit(uploaded_labels, form_payload, sidebar_config)
                    render_batch_results(reports)
                logger.info(f"Results successfully rendered for '{brand_name}'")
            except Exception as e:
                logger.error(f"Engine fault on '{brand_name}': {str(e)}", exc_info=True)
                st.error(f"Engine Fault encountered on {brand_name}: {str(e)}")
        st.divider()
