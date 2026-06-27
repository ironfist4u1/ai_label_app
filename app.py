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
        if "settings_overrides" not in st.session_state:
            st.session_state.settings_overrides = {}

        if "active_checks_list" not in st.session_state:
            st.session_state.active_checks_list = env.configured_compliance_checks()
        if "active_schema_list" not in st.session_state:
            st.session_state.active_schema_list = env.configured_application_schema()

        # Apply any active session overrides to the config singleton on every render
        # cycle so the engine always reads the correct values.
        for key, value in st.session_state.settings_overrides.items():
            env.override(key, value)

    def render_settings(self):
        """
        Frontend override panel for AI connection settings.
        Values entered here take precedence over .env for the current session.
        Placeholders show the active .env default so users know what they're overriding.
        """
        overrides = st.session_state.settings_overrides

        c1, c2, c3 = st.columns(3)
        with c1:
            url_val = st.text_input(
                "AI Base URL",
                value=overrides.get("AI_BASE_URL", ""),
                placeholder=env.get("AI_BASE_URL", "Not set in .env"),
                help="Overrides AI_BASE_URL from .env for this session.",
            )
        with c2:
            token_val = st.text_input(
                "AI Access Token",
                value=overrides.get("AI_API_KEY", ""),
                type="password",
                placeholder="●●●●●●●● (from .env)"
                if env.get("AI_API_KEY")
                else "Not set in .env",
                help="Overrides AI_API_KEY. Stored in session only — never written to disk.",
            )
        with c3:
            model_val = st.text_input(
                "Model Name",
                value=overrides.get("AI_MODEL_NAME", ""),
                placeholder=env.get("AI_MODEL_NAME", "Not set in .env"),
                help="Overrides AI_MODEL_NAME from .env for this session.",
            )

        with st.expander("Verification Check Configurations"):
            checks_layout = [0.2, 1, 2, 1]
            c0, c1, c2, c3 = st.columns(checks_layout)
            c0.markdown("##")
            c1.markdown("**Check Label**")
            c2.markdown("**Verification Prompt**")
            c3.markdown("**Category**")

            compliance_checks = {}
            for i, check in enumerate(st.session_state.active_checks_list):
                col0, col1, col2, col3 = st.columns(checks_layout)
                label = check.get("label")
                desc = check.get("description")
                categories = check.get("applicable_categories")

                with col0:
                    if st.button("🗑️", key=f"del_check_{i}"):
                        st.session_state.active_checks_list.pop(i)
                        st.rerun()

                with col1:
                    st.write(label)
                with col2:
                    compliance_checks[label] = st.text_input(
                        label=label, value=desc, label_visibility="collapsed"
                    )
                with col3:
                    st.write(",".join(categories))

            st.divider()
            st.markdown("### Add New Verification Check")
            col1, col2, col3 = st.columns([1, 2, 1])
            new_lbl = col1.text_input("New Label", key="new_check_label")
            new_desc = col2.text_input("New Desc", key="new_check_desc")
            new_cat = col3.text_input("Category (e.g. WINE)", key="new_check_cat")

            if st.button("Add Check"):
                if new_lbl not in [
                    check.get("label") for check in st.session_state.active_checks_list
                ]:
                    st.session_state.active_checks_list.append(
                        {
                            "id": new_lbl.lower().replace(" ", "_"),
                            "label": new_lbl,
                            "description": new_desc,
                            "applicable_categories": [new_cat] if new_cat else ["ALL"],
                            "deduction": 10,  # Default
                        }
                    )
                    st.rerun()

        with st.expander("Application Schema Configurations"):
            application_schema_label_key = st.text_input(
                label="Application Label File",
                value=overrides.get("LABEL_FILE_KEY", ""),
                placeholder=env.get("LABEL_FILE_KEY", "Not set in .env"),
                help="Override the label file input key on the application schema.",
            )
            checks_layout = [0.2, 1, 2, 1]
            c0, c1, c2, c3 = st.columns(checks_layout)
            c0.markdown("##")
            c1.markdown("**Id**")
            c2.markdown("**Label**")
            c3.markdown("**Placeholder**")

            application_schema = {}
            for i, check in enumerate(st.session_state.active_schema_list):
                col0, col1, col2, col3 = st.columns(checks_layout)
                id = check.get("id")
                label = check.get("label")
                placeholder = check.get("placeholder")

                with col0:
                    if st.button("🗑️", key=f"del_schema_{i}"):
                        st.session_state.active_schema_list.pop(i)
                        st.rerun()

                with col1:
                    st.write(id)
                with col2:
                    application_schema[id] = st.text_input(
                        label=label, value=label, label_visibility="collapsed"
                    )
                with col3:
                    st.write(placeholder)
            st.divider()
            st.markdown("### Add New Schema Field")
            col1, col2, col3 = st.columns([1, 2, 1])
            new_id = col1.text_input("ID", key="new_schema_id")
            new_label = col2.text_input("Label", key="new_schema_label")
            new_placeholder = col3.text_input(
                "Placeholder", key="new_schema_placeholder"
            )

            if st.button("Add Field"):
                if new_id not in [
                    schema.get("id") for schema in st.session_state.active_schema_list
                ]:
                    st.session_state.active_schema_list.append(
                        {
                            "id": new_id,
                            "label": new_label,
                            "placeholder": new_placeholder,
                        }
                    )
                    st.rerun()

        col_apply, col_reset, col_status = st.columns([1, 1, 4])
        with col_apply:
            if st.button("💾 Apply", use_container_width=True):
                configured_checks = st.session_state.active_checks_list
                for index, check in enumerate(configured_checks):
                    if check.get("label") in compliance_checks:
                        check["description"] = compliance_checks[check.get("label")]
                        configured_checks[index] = check

                configured_schema = st.session_state.active_schema_list
                for index, check in enumerate(configured_schema):
                    if check.get("id") in compliance_checks:
                        check["label"] = compliance_checks[check.get("id")]
                        configured_schema[index] = check

                for key, val in [
                    ("AI_BASE_URL", url_val),
                    ("AI_API_KEY", token_val),
                    ("AI_MODEL_NAME", model_val),
                    ("LABEL_FILE_KEY", application_schema_label_key),
                    ("VERIFICATION_CHECKS", configured_checks),
                    ("APPLICATION_SCHEMA", configured_schema),
                ]:
                    if val:
                        st.session_state.settings_overrides[key] = val
                    else:
                        st.session_state.settings_overrides.pop(key, None)
                st.rerun()
        with col_reset:
            if st.button("↩ Reset to .env", use_container_width=True):
                st.session_state.settings_overrides.clear()
                env.clear_overrides()
                st.rerun()
        with col_status:
            active = list(overrides.keys())
            if active:
                st.info(f"Session overrides active: {', '.join(active)}", icon="⚙️")
            else:
                st.caption("Using .env defaults for all settings.")

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
                        target_filenames = app_data.get(env.get("LABEL_FILE_KEY"), [])
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
            target_filenames = single_payload.get(env.get("LABEL_FILE_KEY"), [])
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
                st.markdown(env.get("INSTRUCTIONS"))
            with st.expander("📖 Label Requirements", expanded=False):
                markdown_str = "### **Label Checks and Their Prompt**\n\n"
                for check in st.session_state.active_checks_list:
                    desc = check.get("description")
                    label = check.get("label")
                    categories = check.get("applicable_categories")
                    markdown_str += (
                        f"- **Categories({','.join(categories)}) - {label}**: {desc}\n"
                    )
                st.markdown(markdown_str)
            with st.expander("⚙️ Engine Settings", expanded=False):
                self.render_settings()

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
