import logging
import streamlit as st
from engine import run_compliance_audit, run_batch_compliance_audit
from application import (
    render_sidebar,
    render_form,
    render_upload,
    render_results,
    render_batch_form,
)
from datatypes import SidebarConfig


logger = logging.getLogger("StreamlitUI")
st.set_page_config(page_title="Dynamic TTB Verification Portal", layout="wide")


class ComplianceApp:
    def __init__(self):
        """Initialize session state to preserve data across UI reruns."""
        if "audit_results" not in st.session_state:
            # We will store a list of report objects here
            st.session_state.audit_results = []
        if "brand_name_target" not in st.session_state:
            st.session_state.brand_name_target = ""

    def process_audit(self, uploaded_labels, form_payload, sidebar_config):
        """Handles validation and engine execution, storing results in state."""
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
        logger.info(
            f"Audit initiated. Images: {len(uploaded_labels)} | Deep Dive: {sidebar_config.deep_dive}"
        )

        # Clear previous results before starting a new run
        st.session_state.audit_results = []

        try:
            if not sidebar_config.batch_mode:
                report = run_compliance_audit(
                    uploaded_labels, form_payload, sidebar_config
                )
                st.session_state.audit_results.append(report)
            else:
                # Evaluate the batch generator and store all reports in state
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

            logger.info(f"Results successfully stored for '{brand_name}'")

        except Exception as e:
            logger.error(f"Engine fault on '{brand_name}': {str(e)}", exc_info=True)
            st.error(f"Engine Fault encountered on {brand_name}: {str(e)}")

    def render(self):
        """Paints the UI using containers to break the top-to-bottom rigidness."""

        # 1. Define UI Slots in exact vertical order
        header_slot = st.container()
        instructions_slot = st.container()
        input_slot = st.container()
        action_slot = st.container()
        results_slot = st.container()

        # 2. Paint Header
        with header_slot:
            st.title("Alcohol Label Compliance Verifier")
            st.markdown(
                "Automated extensible verification framework for TTB COLA label validation."
            )

        # 3. Paint Instructions (New Section)
        with instructions_slot:
            with st.expander("📖 How to Use This Tool", expanded=True):
                st.markdown("""
                ### **Single Application Mode**
                1. **Provide Metadata:** Enter the application details manually on the left, or upload a single `.json` application file.
                2. **Upload Labels:** Drag and drop the front and/or back label images into the upload bin on the right.

                ### **Batch Processing Mode**
                1. **Enable Batch:** Toggle the "Batch Mode" checkbox in the left sidebar.
                2. **Provide Manifest:** Upload a `.json` manifest file containing an array of applications (or enter them manually).
                3. **Upload All Labels:** Drag and drop **all** label images referenced in your manifest into the upload bin on the right. The system will automatically map the correct images to the correct application.

                ### **Execution**
                Click **Run Verification Audit** below the inputs. The AI engine will process your documents and render a detailed compliance breakdown at the bottom of the page.
                """)

        # 4. Paint Inputs
        with input_slot:
            sidebar_config: SidebarConfig = render_sidebar()
            st.header("1. Application Metadata & Artifacts")
            manual_entry = st.checkbox(
                "Manually enter application details", value=False
            )
            col1, col2 = st.columns(2)

            with col1:
                if sidebar_config.batch_mode:
                    form_payload = render_batch_form(manual_entry)
                else:
                    form_payload = render_form(manual_entry)
            with col2:
                uploaded_labels = render_upload()

        # 5. Paint Action Button (Directly below the inputs)
        with action_slot:
            # Add some padding
            st.write("")
            if st.button(
                "🚀 Run Verification Audit", type="primary", use_container_width=True
            ):
                with st.spinner("Processing documents through the AI engine..."):
                    self.process_audit(uploaded_labels, form_payload, sidebar_config)

        # 6. Paint Results
        with results_slot:
            if st.session_state.audit_results:
                st.divider()
                st.header("2. System Compliance Report Output")

                # --- NEW: Batch Level Rerun Button ---
                if (
                    sidebar_config.batch_mode
                    and len(st.session_state.audit_results) > 1
                ):
                    if st.button("🔄 Rerun Entire Batch", type="secondary"):
                        with st.spinner("Rerunning entire batch..."):
                            self.process_audit(
                                uploaded_labels, form_payload, sidebar_config
                            )
                            st.rerun()  # Force a UI refresh to show new data

                st.subheader(f"Results for: {st.session_state.brand_name_target}")

                for i, report in enumerate(st.session_state.audit_results):
                    if not sidebar_config.batch_mode:
                        # Pass a unique key for the single item
                        if render_results(report, unique_key="single_run"):
                            with st.spinner("Rerunning application..."):
                                self.process_audit(
                                    uploaded_labels, form_payload, sidebar_config
                                )
                                st.rerun()
                    else:
                        brand = report.application.get(
                            "brand_name", f"Application {i + 1}"
                        )
                        passed = report.confidence_score >= 85
                        with st.expander(
                            f"{'✅' if passed else '❌'} {brand}", expanded=not passed
                        ):
                            # Listen for the individual rerun click inside the batch
                            if render_results(report, unique_key=f"batch_item_{i}"):
                                with st.spinner(f"Rerunning {brand}..."):
                                    # Extract just this one payload from the batch array
                                    single_payload = form_payload[i]

                                    # Execute just this one item
                                    new_report = next(
                                        run_batch_compliance_audit(
                                            uploaded_labels,
                                            [single_payload],
                                            sidebar_config,
                                        )
                                    )

                                    # Replace the old report with the new one in state
                                    st.session_state.audit_results[i] = new_report
                                    st.rerun()


# Instantiate and run the app
if __name__ == "__main__":
    app = ComplianceApp()
    app.render()
