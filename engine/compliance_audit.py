import logging
from typing import List, Generator, Any
from config import env
from datatypes import ComplianceReport, SidebarConfig
from streamlit.runtime.uploaded_file_manager import UploadedFile
from .schema_builder import build_extraction_model, build_field_matches_model
from .vision import call_vision_api
from .scoring import calculate_score
from .image_tools import preprocess_image_for_ai

logger = logging.getLogger("ComplianceEngine")


def run_batch_compliance_audit(
    uploaded_labels: List[UploadedFile],
    form_data: List[dict],
    sidebar_config: SidebarConfig,
) -> Generator[ComplianceReport, Any, None]:
    for application in form_data:
        target_filenames = application.get("associated_files", [])
        matched_files = [f for f in uploaded_labels if f.name in target_filenames]
        report = run_compliance_audit(
            matched_files,
            application,
            sidebar_config,
        )
        yield report


def run_compliance_audit(
    uploaded_labels: List[UploadedFile],
    form_data: dict,
    sidebar_config: SidebarConfig,
) -> ComplianceReport:
    """
    Orchestrates the full compliance audit pipeline.
    Each step is handled by a dedicated module; this function just wires them together.
    """
    beverage_category = form_data.get("rules_category", "Distilled Spirits")
    logger.info(
        f"Audit starting. Category: '{beverage_category}' | Deep Dive: {sidebar_config.deep_dive}"
    )

    # 1. Filter rules for this beverage category
    active_checks = [
        c
        for c in env.configured_compliance_checks()
        if "ALL" in c.get("applicable_categories", ["ALL"])
        or beverage_category in c.get("applicable_categories", [])
    ]
    logger.info(f"Active rules: {len(active_checks)} for '{beverage_category}'")

    # 2. Build dynamic Pydantic schemas for this request
    extraction_model = build_extraction_model(active_checks)
    field_matches_model = build_field_matches_model(active_checks)

    # prepare images for processing
    images_b64 = []
    images_b64.extend(
        [
            preprocess_image_for_ai(
                uploaded_file,
                sidebar_config.preprocess_size,
                sidebar_config.preprocess_contrast,
            )
            for uploaded_file in uploaded_labels
        ]
    )

    # 3. Call the Vision API
    ai_result = call_vision_api(
        images_b64, form_data, active_checks, sidebar_config.deep_dive, extraction_model
    )

    # 4. Score results deterministically
    score, fields_state = calculate_score(
        ai_result, active_checks, sidebar_config.deep_dive
    )

    # 5. Assemble and return the final report
    return ComplianceReport(
        is_legible=ai_result.is_legible,
        legibility_remarks=ai_result.legibility_remarks,
        confidence_score=score,
        matched_fields=field_matches_model(**fields_state),
        application=form_data,
    )
