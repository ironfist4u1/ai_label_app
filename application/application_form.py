import json
import logging
import streamlit as st
from typing import Dict, List, Any

from config import env

logger = logging.getLogger("UI.Form")


def _temp_fields() -> Dict[str, str]:
    """Fallback 'N/A' values for any schema keys missing from an uploaded JSON."""
    return {field["id"]: "N/A" for field in env.configured_application_schema()}


def render_form(manual_entry) -> Dict[str, Any]:
    """
    Single-application entry.
    Handles the manual / JSON-upload toggle internally.
    Returns a flat dict of field values.
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
        app_file = st.file_uploader("Upload Application File (.json)", type=["json"])
        if app_file is not None:
            try:
                form_payload = {**_temp_fields(), **json.load(app_file)}
                st.success("Application data successfully extracted.")
                with st.expander("View Extracted Data"):
                    st.json(form_payload)
            except Exception as e:
                st.error("Failed to parse JSON application file.")
                logger.error(f"JSON parsing error: {e}")

    return form_payload


def render_batch_form(manual_entry) -> List[Dict[str, Any]]:
    """
    Multi-application entry.
    Handles the manual / JSON-upload toggle internally.
    Returns a list of dicts, one per application.
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
                entry["associated_files"] = st.text_input(
                    label=f"App({index + 1}): Associated Files",
                    placeholder="[label_file_name.png, label_file_name.png]",
                )
                form_payload.append(entry)
    else:
        defaults = _temp_fields()
        app_files = st.file_uploader(
            "Upload Application File(s) (.json)",
            type=["json"],
            accept_multiple_files=True,
        )
        for app_file in app_files or []:
            try:
                loaded = json.load(app_file)
                if isinstance(loaded, list):
                    form_payload.extend({**defaults, **item} for item in loaded)
                else:
                    form_payload.append({**defaults, **loaded})
                st.success(f"Extracted: {app_file.name}")
                with st.expander(f"View {app_file.name}"):
                    st.json(loaded)
            except Exception as e:
                st.error(f"Failed to parse {app_file.name}.")
                logger.error(f"JSON parsing error for {app_file.name}: {e}")

    return form_payload
