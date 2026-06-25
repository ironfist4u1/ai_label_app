import json
import logging
import streamlit as st
from typing import Dict, List, Any

from datatypes import SidebarConfig
from config import env

logger = logging.getLogger("UI.Form")


def render_form(sidebar_config: SidebarConfig) -> Dict | List[Dict]:
    """
    Renders the application data entry section (manual text input or JSON upload).
    Returns form_payload (dict): the collected application data.
    """
    st.subheader("Application Data")
    manual_entry = st.checkbox("Manually enter application details", value=True)

    if manual_entry and sidebar_config.batch_mode:
        form_payload: List[Dict] = []
        number_of_apps = st.number_input(label="Number of application(s)", min_value=1, max_value=10)
        for index in range(len(form_payload), number_of_apps):
            index_form = {}
            for field in env.configured_application_schema():
                index_form[field["id"]] = st.text_input(
                    label=f"App({index+1}): {field['label']}",
                    placeholder=field.get("placeholder", ""),
                )
            index_form["associated_files"] = st.text_input(
                label=f"App({index+1}): associated_files",
                placeholder="[label_file_name.png, label_file_name.png]",
            )
            if index > len(form_payload) - 1:
                form_payload.append(index_form)
            else:
                form_payload[index] = index_form
    elif manual_entry:
        form_payload: Dict[str, Any] = {}
        for field in env.configured_application_schema():
            form_payload[field["id"]] = st.text_input(
                label=field["label"],
                placeholder=field.get("placeholder", ""),
            )
    elif sidebar_config.batch_mode:
        form_payload: List[Dict] = []
        temp_fields = {field["id"]: "N/A" for field in env.configured_application_schema()}
        app_files = st.file_uploader("Upload Application File (.json)", type=["json"], accept_multiple_files=True)
        if app_files:
            for app_file in app_files:
                try:
                    loaded_payload = json.load(app_file)
                    if isinstance(loaded_payload, list):
                        loaded_payload = [
                            {**temp_fields, **single_app}
                            for single_app in loaded_payload
                        ]
                        form_payload.extend(loaded_payload)
                    else:
                        loaded_payload = {**temp_fields, **loaded_payload}
                        form_payload.append(loaded_payload)
                    st.success("Application data successfully extracted.")
                    with st.expander(f"View File {app_file.name} Extracted Data"):
                        st.json(loaded_payload)
                except Exception as e:
                    st.error("Failed to parse JSON application file.")
                    logger.error(f"JSON parsing error: {e}")
    else:
        form_payload: Dict = {}
        temp_fields = {field["id"]: "N/A" for field in env.configured_application_schema()}
        app_file = st.file_uploader("Upload Application File (.json)", type=["json"])
        if app_file is not None:
            try:
                form_payload = json.load(app_file)
                form_payload = {**temp_fields, **form_payload}
                st.success("Application data successfully extracted.")
                with st.expander("View Extracted Data"):
                    st.json(form_payload)
            except Exception as e:
                st.error("Failed to parse JSON application file.")
                logger.error(f"JSON parsing error: {e}")

    return form_payload
