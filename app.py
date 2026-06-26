import logging
import streamlit as st
from engine import (
    run_compliance_audit,
    run_batch_compliance_audit,
    rerun_failed_checks,
)
from application import (
    render_sidebar,
    render_form,
    render_upload,
    render_results,
    render_batch_form,
)
from datatypes import SidebarConfig
from config import env

logger = logging.getLogger("StreamlitUI")
st.set_page_config(page_title="Dynamic TTB Verification Portal", layout="wide")


class ComplianceApp:
    def __init__(self):
        if "audit_results" not in st.session_state:
            st.session_state.audit_results = []
        if "brand_name_target" not in st.session_state:
            st.session_state.brand_name_target = ""

    def process_audit(
        self, uploaded_labels, form_payload, sidebar_config: SidebarConfig
    ):
        """Handles the initial validation and engine execution."""
        has_data = (
            0 < len(form_payload)
            if isinstance(form_payload, list)
            else any(form_payload.values())
        )

        if not has_data or not uploaded_labels:
            logger.warning(
                "Audit attempted without required form data or image artifacts."
            )
            st.error(
                "Please provide validation metadata and submit at least one label image."
            )
            return

        brand_name = (
            form_payload.get("brand_name", "Brand Name Not Found")
            if not sidebar_config.batch_mode
            else "Batch"
        )

        st.session_state.brand_name_target = brand_name
        st.session_state.audit_results = []

        try:
            if not sidebar_config.batch_mode:
                report = run_compliance_audit(
                    uploaded_labels, form_payload, sidebar_config
                )
                st.session_state.audit_results.append(report)
            else:
                total = len(form_payload)
                progress_bar = st.progress(
                    0, text=f"Starting batch — 0 of {total} complete"
                )

                for i, report in enumerate(
                    run_batch_compliance_audit(
                        uploaded_labels, form_payload, sidebar_config
                    )
                ):
                    st.session_state.audit_results.append(report)
                    progress_bar.progress(
                        (i + 1) / total, text=f"Completed {i + 1} of {total}"
                    )
                progress_bar.empty()

        except Exception as e:
            logger.error(f"Engine fault on '{brand_name}': {str(e)}", exc_info=True)
            st.error(f"Engine Fault encountered on {brand_name}: {str(e)}")

    def execute_rerun(
        self,
        uploaded_labels,
        form_payload,
        sidebar_config,
        target_index=None,
        only_failed=False,
    ):
        """Controller to handle state updates for full reruns or targeted failure reruns."""
        if target_index is None:
            if only_failed:
                if sidebar_config.batch_mode:
                    for i, report in enumerate(st.session_state.audit_results):
                        app_data = form_payload[i]
                        target_filenames = app_data.get("label_files", [])
                        matched_files = [
                            f for f in uploaded_labels if f.name in target_filenames
                        ]
                        st.session_state.audit_results[i] = rerun_failed_checks(
                            matched_files, app_data, sidebar_config, report
                        )
                else:
                    st.session_state.audit_results[0] = rerun_failed_checks(
                        uploaded_labels,
                        form_payload,
                        sidebar_config,
                        st.session_state.audit_results[0],
                    )
            else:
                self.process_audit(uploaded_labels, form_payload, sidebar_config)
        else:
            single_payload = form_payload[target_index]
            target_filenames = single_payload.get("label_files", [])
            matched_files = [f for f in uploaded_labels if f.name in target_filenames]

            try:
                if only_failed:
                    st.session_state.audit_results[target_index] = rerun_failed_checks(
                        matched_files,
                        single_payload,
                        sidebar_config,
                        st.session_state.audit_results[target_index],
                    )
                else:
                    new_report = next(
                        run_batch_compliance_audit(
                            matched_files, [single_payload], sidebar_config
                        )
                    )
                    st.session_state.audit_results[target_index] = new_report
            except Exception as e:
                logger.error(f"Engine fault on targeted rerun: {str(e)}", exc_info=True)
                st.error(f"Engine Fault encountered: {str(e)}")

        st.rerun()

    def render_results_area(
        self, results_slot, uploaded_labels, form_payload, sidebar_config
    ):
        """Builds the results UI, including rerun controls."""
        with results_slot:
            if not st.session_state.audit_results:
                return

            st.divider()
            st.header("2. System Compliance Report Output")

            # --- GLOBAL BATCH CONTROLS ---
            if sidebar_config.batch_mode and len(st.session_state.audit_results) > 1:
                col1, col2 = st.columns(2)
                all_passed = all(
                    report.confidence_score == 100
                    for report in st.session_state.audit_results
                )
                with col1:
                    if st.button(
                        "🔄 Rerun Entire Batch",
                        type="secondary",
                        use_container_width=True,
                        disabled=all_passed,
                    ):
                        with st.spinner("Rerunning entire batch..."):
                            self.execute_rerun(
                                uploaded_labels, form_payload, sidebar_config
                            )
                with col2:
                    if st.button(
                        "🎯 Rerun All Failed Checks",
                        type="primary",
                        use_container_width=True,
                        disabled=all_passed,
                    ):
                        with st.spinner(
                            "Retesting failures across all applications..."
                        ):
                            self.execute_rerun(
                                uploaded_labels,
                                form_payload,
                                sidebar_config,
                                only_failed=True,
                            )

            st.subheader(f"Results for: {st.session_state.brand_name_target}")

            # --- INDIVIDUAL RENDER LOOP ---
            for i, report in enumerate(st.session_state.audit_results):
                if not sidebar_config.batch_mode:
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("🔄 Rerun Full Application"):
                            with st.spinner("Rerunning..."):
                                self.execute_rerun(
                                    uploaded_labels, form_payload, sidebar_config
                                )
                    with col2:
                        if st.button("🎯 Rerun Failed Checks", type="primary"):
                            with st.spinner("Retesting failures..."):
                                self.execute_rerun(
                                    uploaded_labels,
                                    form_payload,
                                    sidebar_config,
                                    only_failed=True,
                                )
                    render_results(report)
                else:
                    brand = report.application.get("brand_name", f"Application {i + 1}")
                    passed = report.confidence_score >= 85
                    with st.expander(
                        f"{'✅' if passed else '❌'} {brand}", expanded=not passed
                    ):
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button(
                                "🔄 Rerun Full App",
                                key=f"rerun_full_{i}",
                                disabled=report.confidence_score == 100,
                            ):
                                with st.spinner(f"Rerunning {brand}..."):
                                    self.execute_rerun(
                                        uploaded_labels,
                                        form_payload,
                                        sidebar_config,
                                        target_index=i,
                                    )
                        with col2:
                            if st.button(
                                "🎯 Rerun Failed Checks",
                                key=f"rerun_fail_{i}",
                                type="primary",
                                disabled=report.confidence_score == 100,
                            ):
                                with st.spinner(f"Retesting failures for {brand}..."):
                                    self.execute_rerun(
                                        uploaded_labels,
                                        form_payload,
                                        sidebar_config,
                                        target_index=i,
                                        only_failed=True,
                                    )

                        render_results(report)

    def render(self):
        header_slot = st.container()
        instructions_slot = st.container()
        input_slot = st.container()
        action_slot = st.container()
        results_slot = st.container()

        with header_slot:
            st.title("Alcohol Label Compliance Verifier")
            st.markdown(
                "Automated extensible verification framework for TTB COLA label validation."
            )

        with instructions_slot:
            with st.expander("📖 How to Use This Tool", expanded=True):
                st.markdown(env.config.INSTRUCTIONS)
            with st.expander("📖 Label Requirements", expanded=False):
                markdown_str = "### **Label Checks and Their Prompt**\n\n"
                for check in env.configured_compliance_checks():
                    desc = check.get("description")
                    label = check.get("label")
                    categories = check.get("applicable_categories")
                    markdown_str += (
                        f"- **Categories({','.join(categories)}) - {label}**: {desc}\n"
                    )
                st.markdown(markdown_str)

        with input_slot:
            sidebar_config: SidebarConfig = render_sidebar()
            st.header(
                f"1. Upload Application & Artifacts ({sidebar_config.ingestion_format})"
            )
            manual_entry = st.checkbox(
                "Manually enter application details", value=False
            )
            col1, col2 = st.columns(2)
            with col1:
                form_payload = (
                    render_batch_form(sidebar_config.ingestion_format, manual_entry)
                    if sidebar_config.batch_mode
                    else render_form(sidebar_config.ingestion_format, manual_entry)
                )
            with col2:
                uploaded_labels = render_upload()

        with action_slot:
            if st.button(
                "Run Verification Audit", type="primary", use_container_width=True
            ):
                with st.spinner("Processing documents through the AI engine..."):
                    self.process_audit(uploaded_labels, form_payload, sidebar_config)

        # Cleaner Render call
        self.render_results_area(
            results_slot, uploaded_labels, form_payload, sidebar_config
        )


if __name__ == "__main__":
    app = ComplianceApp()
    app.render()
