from typing import List, Dict, Any
from pydantic import Field, create_model
from datatypes import EvaluationResult
from config import env


def build_extraction_model(active_checks: List[Dict[str, Any]]):
    """
    Builds the Pydantic model used for structured AI output.
    Includes legibility fields + one EvaluationResult per active rule.
    """
    fields = {
        "is_legible": (
            bool,
            Field(
                description="False if the submitted image is illegible or too low quality to evaluate."
            ),
        ),
        "legibility_remarks": (
            str,
            Field(
                description="Explanation of why the image is unreadable, if applicable."
            ),
        ),
    }
    for check in active_checks:
        fields[f"{check['id']}_evaluation"] = (
            EvaluationResult,
            Field(description=check["description"]),
        )
    return create_model("AIModelExtraction", **fields)


def build_field_matches_model(active_checks: List[Dict[str, Any]]):
    """
    Builds the typed container holding one EvaluationResult per active rule ID.
    Used as the `matched_fields` value in the final ComplianceReport.
    """
    return create_model(
        "FieldMatches",
        **{c["id"]: (EvaluationResult, Field(...)) for c in active_checks},
    )


def build_application_fields():
    schema_fields = {}
    for field in env.configured_application_schema():
        # Every field is a string, with a default "N/A" if the AI can't read it
        schema_fields[field["id"]] = (
            str,
            Field(default="N/A", description=field["label"]),
        )

    PdfExtractionModel = create_model("PdfExtractionModel", **schema_fields)
    return PdfExtractionModel
