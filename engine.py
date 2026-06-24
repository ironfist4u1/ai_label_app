import os
import json
import logging
from typing import List, Dict, Any
from pydantic import BaseModel, Field, create_model
from openai import OpenAI
from dotenv import load_dotenv

# -------------------------------------------------------------
# LOGGING CONFIGURATION
# -------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("ComplianceEngine")

load_dotenv()

# Parse Rule Definitions from Environment Context
try:
    CONFIG_CHECKS: List[Dict[str, Any]] = json.loads(os.getenv("VERIFICATION_CHECKS", "[]"))
    logger.info(f"Successfully loaded {len(CONFIG_CHECKS)} dynamic verification rules from environment.")
except Exception as e:
    logger.critical(f"Failed to parse VERIFICATION_CHECKS from environment. Check JSON formatting. Error: {e}")
    CONFIG_CHECKS = []


# Schema Definitions
class EvaluationResult(BaseModel):
    matched: bool = Field(description="True if this specific requirement is fully satisfied, False otherwise.")
    explanation: str = Field(description="Detailed text explaining exactly why it passed or failed, referencing visual evidence.")


# Dynamically Generate the AI Extraction Schema Class
extraction_fields = {
    "is_legible": (bool, Field(description="False if the image is too blurry, dark, cropped, or angled to read.")),
    "legibility_remarks": (str, Field(description="Detailed reason if the photo is unreadable."))
}


for check in CONFIG_CHECKS:
    field_key = f"{check['id']}_evaluation"
    extraction_fields[field_key] = (EvaluationResult, Field(description=check["description"]))


AIModelExtraction = create_model("AIModelExtraction", **extraction_fields)


# Dynamically Generate the Typed UI Field Model Class
frontend_fields = {check["id"]: (EvaluationResult, Field(...)) for check in CONFIG_CHECKS}
FieldMatches = create_model("FieldMatches", **frontend_fields)


class ComplianceReport(BaseModel):
    is_legible: bool
    legibility_remarks: str
    confidence_score: int
    matched_fields: Any


def run_compliance_audit(image_b64: str, form_data: dict, deep_dive: bool = False) -> ComplianceReport:
    """Evaluates rules dynamically, executes deterministic math, and maps structured AI reasoning."""
    logger.info(f"Starting compliance audit. Mode: {'Deep Dive' if deep_dive else 'Quick Mode'}. Target Metadata: {form_data.get('brand_name')}")
    
    try:
        client = OpenAI(
            base_url=os.getenv("AI_BASE_URL"),
            api_key=os.getenv("AI_API_KEY")
        )
    except Exception as e:
        logger.error(f"Failed to initialize AI Client: {e}")
        raise RuntimeError(f"Engine Initialization Error: {e}")
    
    active_rules_summary = "\n".join([
        f"- {c['id']}: {c['description']} (Active: {'Always' if not c['deep_dive_only'] else 'Deep Dive Only'})"
        for c in CONFIG_CHECKS if not c["deep_dive_only"] or deep_dive
    ])
    
    mode_context = f"Execution Mode: {'Deep Dive' if deep_dive else 'Quick Mode'}\n\nRules to Apply:\n{active_rules_summary}"
    
    user_content = [
        {"type": "text", "text": f"Application Form Data: {json.dumps(form_data)}\n\n{mode_context}"},
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}}
    ]
    
    # AI Execution Phase
    logger.info("Transmitting payload to Vision API...")
    try:
        response = client.beta.chat.completions.parse(
            model=os.getenv("AI_MODEL_NAME", "default-model"),
            messages=[
                {"role": "system", "content": os.getenv("SYSTEM_PROMPT_CORE")},
                {"role": "user", "content": user_content}
            ],
            response_format=AIModelExtraction,
            max_tokens=int(os.getenv("DEEP_DIVE_MAX_TOKENS") if deep_dive else os.getenv("QUICK_MODE_MAX_TOKENS")),
            temperature=0.0
        )
        ai_result = response.choices[0].message.parsed
        logger.info(f"API successful. Image Legibility: {getattr(ai_result, 'is_legible')}")
        
    except Exception as e:
        logger.error("Vision API evaluation failed.", exc_info=True)
        raise RuntimeError(f"Vision Inference Failed: {str(e)}")
    
    # Deterministic Scoring Engine Phase
    score = 100
    fields_state = {}
    
    if not getattr(ai_result, "is_legible"):
        logger.warning(f"Image deemed illegible. Reason: {getattr(ai_result, 'legibility_remarks')}. Setting score to 0.")
        score = 0
        for check in CONFIG_CHECKS:
            fields_state[check["id"]] = EvaluationResult(matched=False, explanation="Analysis skipped: Image is illegible.")
    else:
        for check in CONFIG_CHECKS:
            rule_id = check["id"]
            extraction_key = f"{rule_id}_evaluation"
            
            evaluation: EvaluationResult = getattr(ai_result, extraction_key, EvaluationResult(matched=False, explanation="No data generated."))
            
            if not evaluation.matched:
                if not check["deep_dive_only"] or deep_dive:
                    score -= check["deduction"]
                    logger.info(f"Deduction Applied: -{check['deduction']} pts for '{rule_id}'")
            
            fields_state[rule_id] = evaluation
            
        score = max(0, min(100, score))
        logger.info(f"Scoring complete. Final Confidence Score: {score}/100")
    
    typed_fields = FieldMatches(**fields_state)
    
    return ComplianceReport(
        is_legible=getattr(ai_result, "is_legible"),
        legibility_remarks=getattr(ai_result, "legibility_remarks"),
        confidence_score=score,
        matched_fields=typed_fields
    )
