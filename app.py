import streamlit as st
import base64
import logging
from engine import run_compliance_audit, CONFIG_CHECKS

# -------------------------------------------------------------
# LOGGING CONFIGURATION
# -------------------------------------------------------------
logger = logging.getLogger("StreamlitUI")
# Using basicConfig here will attach to the existing root logger setup by engine.py

st.set_page_config(page_title="Dynamic TTB Verification Portal", layout="wide")

st.title("Alcohol Label Compliance Verifier")
st.markdown("Automated extensible verification framework with per-field explanation routing.")

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

with col1:
    st.subheader("Application Metadata")
    brand_name = st.text_input("Brand Name", placeholder="e.g., OLD TOM DISTILLERY")
    alcohol_content = st.text_input("Alcohol Content (ABV)", placeholder="e.g., 45% Alc./Vol.")
    class_type = st.text_input("Class / Type Designation", placeholder="e.g., Kentucky Straight Bourbon Whiskey")

with col2:
    st.subheader("Label Artifact")
    uploaded_files = st.file_uploader("Upload Label Images", type=["jpg", "png", "jpeg"], accept_multiple_files=True)

if st.button("Run Verification Audit", type="primary"):
    if not brand_name or not uploaded_files:
        logger.warning("Audit attempted without required form data or image artifacts.")
        st.error("Please provide validation metadata and submit target objects.")
    else:
        logger.info(f"Audit Initiated. Batch size: {len(uploaded_files)} file(s). Deep Dive: {deep_dive}")
        st.divider()
        st.header("2. System Compliance Report Output")
        
        form_payload = {
            "brand_name": brand_name,
            "alcohol_content": alcohol_content,
            "class_type": class_type
        }
        
        label_lookup = {c["id"]: c["label"] for c in CONFIG_CHECKS}
        
        for uploaded_file in uploaded_files:
            logger.info(f"Processing frontend artifact: {uploaded_file.name}")
            st.subheader(f"Results for: {uploaded_file.name}")
            
            with st.spinner(f"Running automated evaluations on {uploaded_file.name}..."):
                bytes_data = uploaded_file.read()
                img_b64 = base64.b64encode(bytes_data).decode("utf-8")
                
                try:
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
