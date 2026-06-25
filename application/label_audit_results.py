import logging
import streamlit as st
from config import env
from datatypes import ComplianceReport
from typing import List

logger = logging.getLogger("UI.Results")

# Built once at import time from the shared config.
_LABEL_LOOKUP: dict = {
    c["id"]: c["label"]
    for c in env.configured_compliance_checks()
}


def render_batch_results(reports: List[ComplianceReport]):
    for report in reports:
        pass_fail = "**Status:** Passed" if report.confidence_score >= 85 else "**Status:** Failed"
        with st.expander(f"View {pass_fail} Results for: {report.application.get("brand_name")}"):
            render_results(report)


def render_results(report: ComplianceReport) -> None:
    """Renders the full compliance report output from an audit run."""
    if not report.is_legible:
        st.error(f"🛑 **Image Rejected:** {report.legibility_remarks}")
        return

    score = report.confidence_score
    color = "green" if score >= 85 else "orange" if score >= 50 else "red"
    st.markdown(f"**Confidence Score:** :{color}[**{score} / 100**]")

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
