from typing import Any, Dict
from pydantic import BaseModel, Field


class EvaluationResult(BaseModel):
    matched: bool = Field(description="True if requirement satisfied, False otherwise.")
    explanation: str = Field(description="Detailed text explaining why it passed or failed based on visual evidence.")


class ComplianceReport(BaseModel):
    is_legible: bool
    legibility_remarks: str
    confidence_score: int
    matched_fields: Any
    application: Dict
