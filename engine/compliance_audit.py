import logging
from typing import List, Generator, Any
from config import env
from datatypes import ComplianceReport, SidebarConfig
from streamlit.runtime.uploaded_file_manager import UploadedFile
from .schema_builder import build_extraction_model, build_field_matches_model
from .vision import call_vision_api
from .scoring import calculate_score
from .image_tools import get_encoded_images

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
    active_checks = env.get_active_compliance_checks(beverage_category)
    logger.info(f"Active rules: {len(active_checks)} for '{beverage_category}'")

    # 2. Build dynamic Pydantic schemas for this request
    extraction_model = build_extraction_model(active_checks)
    field_matches_model = build_field_matches_model(active_checks)

    # prepare images for processing
    images_b64 = get_encoded_images(uploaded_labels, sidebar_config)

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


def rerun_failed_checks(
    uploaded_labels: List[UploadedFile],
    form_data: dict,
    sidebar_config: SidebarConfig,
    existing_report: ComplianceReport,
) -> ComplianceReport:
    """
    Scans an existing report for failed rules, isolates them, and executes a hyper-focused AI audit.
    Mutates the existing report with the new findings and recalculates the overall score.
    """
    beverage_category = form_data.get("rules_category", "Distilled Spirits")

    # 1. Fetch all active checks for scoring later
    all_active_checks = env.get_active_compliance_checks(beverage_category)

    # 2. Identify which checks failed in the current report
    failed_check_ids = [
        field_id
        for field_id in existing_report.matched_fields.model_fields.keys()
        if not getattr(existing_report.matched_fields, field_id).matched
    ]

    if not failed_check_ids:
        logger.info("No failed checks to rerun.")
        return existing_report

    # 3. Filter down to ONLY the rules that failed
    failed_checks = [c for c in all_active_checks if c["id"] in failed_check_ids]
    logger.info(f"Targeted rerun executing for {len(failed_checks)} failed checks.")

    # 4. Build a micro-schema strictly for these failures
    extraction_model = build_extraction_model(failed_checks)

    images_b64 = get_encoded_images(uploaded_labels, sidebar_config)

    # 5. Call Vision API (The AI is now 100% focused on fixing its mistakes)
    try:
        ai_result = call_vision_api(
            images_b64,
            form_data,
            failed_checks,
            sidebar_config.deep_dive,
            extraction_model,
        )
    except Exception as e:
        logger.error(f"Vision API failed on targeted rerun: {e}")
        raise

    # 6. Inject the new evaluations into the existing report state
    for check in failed_checks:
        new_eval = getattr(ai_result, f"{check['id']}_evaluation", None)
        if new_eval:
            setattr(existing_report.matched_fields, check["id"], new_eval)

    # 7. Manually recalculate the deterministic score based on the newly patched state
    new_score = 100
    for check in all_active_checks:
        eval_state = getattr(existing_report.matched_fields, check["id"])
        if not eval_state.matched:
            if not check.get("deep_dive_only") or sidebar_config.deep_dive:
                new_score -= check.get("deduction", 0)

    existing_report.confidence_score = max(0, min(100, new_score))

    return existing_report
