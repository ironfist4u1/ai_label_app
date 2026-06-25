import logging
from typing import List
from config import env
from datatypes import ComplianceReport
from .schema_builder import build_extraction_model, build_field_matches_model
from .vision import call_vision_api
from .scoring import calculate_score
from .image_tools import preprocess_image_for_ai

logger = logging.getLogger("ComplianceEngine")


def run_compliance_audit(
    uploaded_labels: List[str],
    form_data: dict,
    deep_dive: bool = False,
) -> ComplianceReport:
    """
    Orchestrates the full compliance audit pipeline.
    Each step is handled by a dedicated module; this function just wires them together.
    """
    beverage_category = form_data.get("rules_category", "Distilled Spirits")
    logger.info(f"Audit starting. Category: '{beverage_category}' | Deep Dive: {deep_dive}")

    # 1. Filter rules for this beverage category
    active_checks = [
        c for c in env.configured_compliance_checks()
        if "ALL" in c.get("applicable_categories", ["ALL"])
        or beverage_category in c.get("applicable_categories", [])
    ]
    logger.info(f"Active rules: {len(active_checks)} for '{beverage_category}'")

    # 2. Build dynamic Pydantic schemas for this request
    extraction_model = build_extraction_model(active_checks)
    field_matches_model = build_field_matches_model(active_checks)

    # prepare images for processing
    images_b64 = [
        preprocess_image_for_ai(uploaded_file)
        for uploaded_file in uploaded_labels
    ]

    # 3. Call the Vision API
    ai_result = call_vision_api(images_b64, form_data, active_checks, deep_dive, extraction_model)

    # 4. Score results deterministically
    score, fields_state = calculate_score(ai_result, active_checks, deep_dive)

    # 5. Assemble and return the final report
    return ComplianceReport(
        is_legible=ai_result.is_legible,
        legibility_remarks=ai_result.legibility_remarks,
        confidence_score=score,
        matched_fields=field_matches_model(**fields_state),
    )
