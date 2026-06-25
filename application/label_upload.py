from typing import List
import streamlit as st


def render_upload() -> List:
    """
    Renders the label image upload section.
    Returns a list of uploaded file objects.
    """
    st.subheader("Label Artifacts")
    return st.file_uploader(
        "Upload Label Images",
        type=["jpg", "png", "jpeg"],
        accept_multiple_files=True,
    )
