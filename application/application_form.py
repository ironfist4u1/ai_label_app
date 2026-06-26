import logging
import streamlit as st
from typing import Dict, List, Any
from .ingestion import parse_application_data
from config import env

logger = logging.getLogger("UI.Form")


def _get_configured_application_fields() -> Dict[str, str]:
    """Fallback 'N/A' values for any schema keys missing from an uploaded file."""
    return {field["id"]: "N/A" for field in env.configured_application_schema()}


def render_form(ingestion_format: str, manual_entry: bool) -> Dict[str, Any]:
    """
    Single-application entry UI.
    Routes file uploads through the universal ingestion adapter.
    """
    st.subheader("Application Data")
    form_payload: Dict[str, Any] = {}

    if manual_entry:
        for field in env.configured_application_schema():
            form_payload[field["id"]] = st.text_input(
                label=field["label"],
                placeholder=field.get("placeholder", ""),
            )
    else:
        file_types = {
            "JSON Manifest": ["json"],
            "PDF Forms": ["pdf"],
            "XML Export": ["xml"],
            "JPEG Scans": ["jpg", "jpeg", "png"],
        }
        accepted_types = file_types.get(ingestion_format, ["*"])

        app_file = st.file_uploader(f"Upload {ingestion_format}", type=accepted_types)

        if app_file:
            try:
                # Pipe the raw file through the new ingestion adapter
                parsed_data = parse_application_data(app_file, ingestion_format)

                if parsed_data:
                    defaults = _get_configured_application_fields()
                    # Single mode: extract the first item and merge fallbacks
                    usable_items = {
                        key: value
                        for key, value in parsed_data[0].items()
                        if key in defaults.keys()
                    }
                    form_payload = {**defaults, **usable_items}
                    st.success(f"Successfully extracted data from {app_file.name}.")
                    with st.expander("View Extracted Data"):
                        st.json(form_payload)
                else:
                    st.warning("No data extracted from file.")

            except Exception as e:
                st.error(f"Ingestion Error: {e}")
                logger.error(f"Ingestion error on single file: {e}")

    return form_payload


def render_batch_form(
    ingestion_format: str, manual_entry: bool
) -> List[Dict[str, Any]]:
    """
    Multi-application entry UI.
    Routes batch file uploads through the universal ingestion adapter.
    """
    st.subheader("Application Data")
    form_payload: List[Dict[str, Any]] = []

    if manual_entry:
        number_of_apps = st.number_input(
            label="Number of application(s)", min_value=1, max_value=10
        )
        for index in range(number_of_apps):
            entry: Dict[str, Any] = {}
            with st.expander(f"Application({index + 1})"):
                for field in env.configured_application_schema():
                    entry[field["id"]] = st.text_input(
                        label=f"App({index + 1}): {field['label']}",
                        placeholder=field.get("placeholder", ""),
                    )
                entry["label_files"] = st.text_input(
                    label=f"App({index + 1}): Label Files",
                    placeholder="[label_file_name.png, label_file_name.png]",
                )
                form_payload.append(entry)
    else:
        file_types = {
            "JSON Manifest": ["json"],
            "PDF Forms": ["pdf"],
            "XML Export": ["xml"],
            "JPEG Scans": ["jpg", "jpeg", "png"],
        }
        accepted_types = file_types.get(ingestion_format, ["*"])

        app_files = st.file_uploader(
            label=f"Upload Application File(s) ({ingestion_format})",
            type=accepted_types,
            accept_multiple_files=True,
        )

        for app_file in app_files or []:
            try:
                # Pipe the raw file through the adapter
                defaults = _get_configured_application_fields()
                parsed_data = parse_application_data(app_file, ingestion_format)

                # Adapter always returns a list. Loop through and merge fallbacks.
                filled_form = []
                for item in parsed_data:
                    usable_items = {
                        key: value
                        for key, value in item.items()
                        if key in defaults.keys()
                    }
                    filled_form.append({**defaults, **usable_items})

                # filled_form = [{**defaults, **item} for item in parsed_data]
                form_payload.extend(filled_form)

                st.success(
                    f"Extracted {len(parsed_data)} applications from {app_file.name}"
                )
                with st.expander(f"View {app_file.name}"):
                    st.json(filled_form)

            except Exception as e:
                st.error(f"Failed to parse {app_file.name}.")
                logger.error(f"Ingestion parsing error for {app_file.name}: {e}")

    return form_payload
