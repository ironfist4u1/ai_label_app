import json
import logging
import streamlit as st
from config import env

logger = logging.getLogger("UI.Form")


def render_form() -> dict:
    """
    Renders the application data entry section (manual text input or JSON upload).
    Returns form_payload (dict): the collected application data.
    """
    st.subheader("Application Data")
    form_payload: dict = {}
    manual_entry = st.checkbox("Manually enter application details", value=True)

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
                form_payload = json.load(app_file)
                st.success("Application data successfully extracted.")
                with st.expander("View Extracted Data"):
                    st.json(form_payload)
            except Exception as e:
                st.error("Failed to parse JSON application file.")
                logger.error(f"JSON parsing error: {e}")

    return form_payload
