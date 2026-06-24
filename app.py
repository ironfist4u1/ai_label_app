import streamlit as st
import base64
import logging
import json
import os
from engine import run_compliance_audit, CONFIG_CHECKS
from utils import preprocess_image_for_ai

logger = logging.getLogger("StreamlitUI")

# Load the dynamic UI schema from environment
try:
    APP_SCHEMA = json.loads(os.getenv("APPLICATION_SCHEMA", "[]"))
except Exception as e:
    logger.error(f"Failed to load APPLICATION_SCHEMA: {e}")
    APP_SCHEMA = []

st.set_page_config(page_title="Dynamic TTB Verification Portal", layout="wide")

st.title("Alcohol Label Compliance Verifier")
st.markdown("Automated extensible verification framework for TTB COLA label validation.")

with st.sidebar:
    st.header("Audit Configuration")
    deep_dive = st.checkbox("Enable Deep Dive Mode", value=False)
    
    st.divider()
    st.subheader("Active Registry Checks")
    for check in CONFIG_CHECKS:
        badge = "🔬 Deep Dive" if check["deep_dive_only"] else "⚡ Core"
        st.caption(f"**{check['label']}** ({badge})\nPenalty: -{check['deduction']} pts")

st.header("1. Application Metadata & Target Visuals")
col1, col2 = st.columns(2)

# -------------------------------------------------------------
# DYNAMIC METADATA INPUT PORTION
# -------------------------------------------------------------
with col1:
    st.subheader("Application Data")
    
    # Toggle for Manual vs Upload
    manual_entry = st.checkbox("Manually enter application details", value=True, help="Uncheck to upload a JSON application file.")
    
    form_payload = {}
    
    if manual_entry:
        # Dynamically draw text inputs based on the .env schema
        for field in APP_SCHEMA:
            form_payload[field["id"]] = st.text_input(
                label=field["label"], 
                placeholder=field.get("placeholder", "")
            )
    else:
        # Provide a file uploader for the application data
        app_file = st.file_uploader("Upload Application File (.json)", type=["json"])
        if app_file is not None:
            try:
                form_payload = json.load(app_file)
                st.success("Application data successfully extracted.")
                with st.expander("View Extracted Data"):
                    st.json(form_payload)
            except Exception as e:
                st.error("Failed to parse JSON application file.")
                logger.error(f"JSON Parsing error: {e}")

# -------------------------------------------------------------
# LABEL ARTIFACT UPLOAD PORTION
# -------------------------------------------------------------
with col2:
    st.subheader("Label Artifact")
    uploaded_labels = st.file_uploader("Upload Label Images", type=["jpg", "png", "jpeg"], accept_multiple_files=True)

# -------------------------------------------------------------
# EXECUTION TRIGGER
# -------------------------------------------------------------
if st.button("Run Verification Audit", type="primary"):
    # Check if we have both data and images
    has_data = any(form_payload.values()) if manual_entry else bool(form_payload)
    
    if not has_data or not uploaded_labels:
        logger.warning("Audit attempted without required form data or image artifacts.")
        st.error("Please provide validation metadata (either typed or uploaded) and submit at least one label image.")
    else:
        logger.info(f"Audit Initiated. Batch size: {len(uploaded_labels)} file(s). Deep Dive: {deep_dive}")
        st.divider()
        st.header("2. System Compliance Report Output")
        
        label_lookup = {c["id"]: c["label"] for c in CONFIG_CHECKS}
        
        for uploaded_file in uploaded_labels:
            logger.info(f"Processing frontend artifact: {uploaded_file.name}")
            st.subheader(f"Results for: {uploaded_file.name}")
            
            with st.spinner(f"Running automated evaluations on {uploaded_file.name}..."):
                img_b64 = preprocess_image_for_ai(uploaded_file)

                try:
                    # The engine dynamically compares whatever is in form_payload against the .env checks!
                    report = run_compliance_audit(img_b64, form_payload, deep_dive=deep_dive)
                    
                    if not report.is_legible:
                        st.error(f"🛑 **Image Rejected:** {report.legibility_remarks}")
                    else:
                        score = report.confidence_score
                        metric_color = "green" if score >= 85 else "orange" if score >= 50 else "red"
                        st.markdown(f"**Confidence Score:** :{metric_color}[**{score} / 100**]")
                        
                        st.subheader("Field Audit Breakdown & Rationale")
                        
                        f_state = report.matched_fields
                        for field_id in f_state.model_fields.keys():
                            evaluation_data = getattr(f_state, field_id)
                            display_label = label_lookup.get(field_id, field_id.title())
                            
                            if evaluation_data.matched:
                                with st.expander(f"✅ {display_label}"):
                                    st.markdown(f"**Status:** Passed")
                                    st.info(evaluation_data.explanation)
                            else:
                                with st.expander(f"❌ {display_label}", expanded=True):
                                    st.markdown(f"**Status:** Failed / Discrepancy Found")
                                    st.warning(evaluation_data.explanation)
                                    
                    logger.info(f"Frontend successfully rendered results for {uploaded_file.name}")
                        
                except Exception as e:
                    logger.error(f"Frontend caught engine fault on {uploaded_file.name}: {str(e)}", exc_info=True)
                    st.error(f"Engine Fault encountered on {uploaded_file.name}: {str(e)}")
            st.divider()
