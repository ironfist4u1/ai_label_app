import logging
import streamlit as st
from datatypes import ComplianceReport
from functools import lru_cache

logger = logging.getLogger("UI.Results")


@lru_cache(1)
def get_default_labels() -> dict:
    return {c["id"]: c["label"] for c in st.session_state.active_checks_list}


def render_results(report: ComplianceReport) -> None:
    """Purely renders the compliance report output without managing state or actions."""
    _LABEL_LOOKUP: dict = get_default_labels()
    if not report.is_legible:
        st.error(f"**Image Rejected:** {report.legibility_remarks}")
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
