import logging
import streamlit as st
from config import env
from datatypes import ComplianceReport

logger = logging.getLogger("UI.Results")

# Built once at import time from the shared config.
_LABEL_LOOKUP: dict = {c["id"]: c["label"] for c in env.configured_compliance_checks()}


def render_results(report: ComplianceReport, unique_key: str) -> bool:
    """
    Renders the full compliance report output from an audit run.
    Returns True if the user clicked the 'Rerun Application' button.
    """
    if not report.is_legible:
        st.error(f"🛑 **Image Rejected:** {report.legibility_remarks}")
        # Allow them to rerun even if it failed legibility (in case it was an AI hallucination)
        return st.button("🔄 Rerun Application", key=f"rerun_illegible_{unique_key}")

    score = report.confidence_score
    color = "green" if score >= 85 else "orange" if score >= 50 else "red"

    # Use columns to align the score and the rerun button cleanly on the same row
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"**Confidence Score:** :{color}[**{score} / 100**]")
    with col2:
        rerun_clicked = st.button(
            "🔄 Rerun Application",
            key=f"rerun_btn_{unique_key}",
            use_container_width=True,
        )

    st.subheader("Field Audit Breakdown")
    for field_id in report.matched_fields.model_fields.keys():
        evaluation = getattr(report.matched_fields, field_id)
        label = _LABEL_LOOKUP.get(field_id, field_id.title())

        if evaluation.matched:
            with st.expander(f"✅ {label}"):
                st.markdown("**Status:** Passed")
                st.info(evaluation.explanation)
        else:
            with st.expander(f"❌ {label}", expanded=True):
                st.markdown("**Status:** Failed / Discrepancy Found")
                st.warning(evaluation.explanation)

    return rerun_clicked
