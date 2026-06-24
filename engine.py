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


try:
    CONFIG_CHECKS: List[Dict[str, Any]] = json.loads(os.getenv("VERIFICATION_CHECKS", "[]"))
    logger.info(f"Successfully loaded {len(CONFIG_CHECKS)} dynamic verification rules from environment.")
except Exception as e:
    logger.critical(f"Failed to parse VERIFICATION_CHECKS from environment. Check JSON formatting. Error: {e}")
    CONFIG_CHECKS = []


class EvaluationResult(BaseModel):
    matched: bool = Field(description="True if requirement satisfied, False otherwise.")
    explanation: str = Field(description="Detailed text explaining why it passed or failed based on visual evidence.")


class ComplianceReport(BaseModel):
    is_legible: bool
    legibility_remarks: str
    confidence_score: int
    matched_fields: Any  


def run_compliance_audit(images_b64: List[str], form_data: dict, deep_dive: bool = False) -> ComplianceReport:
    """Dynamically generates schemas based on beverage category and executes the audit."""
    beverage_category: str = form_data.get("rules_category", "Distilled Spirits")
    logger.info(f"Audit starting. Category: {beverage_category} | Deep Dive: {deep_dive}")
    
    # 1. Filter active rules based on the selected beverage category
    active_checks = []
    for check in CONFIG_CHECKS:
        cats = check.get("applicable_categories", ["ALL"])
        if "ALL" in cats or beverage_category in cats:
            active_checks.append(check)
            
    logger.info(f"Filtered to {len(active_checks)} active rules for {beverage_category}.")

    # 2. Build the Pydantic Schema dynamically for THIS specific request
    extraction_fields = {
        "is_legible": (bool, Field(description="False if image is illegible.")),
        "legibility_remarks": (str, Field(description="Reason if unreadable."))
    }
    
    for check in active_checks:
        field_key = f"{check['id']}_evaluation"
        extraction_fields[field_key] = (EvaluationResult, Field(description=check["description"]))

    AIModelExtraction = create_model("AIModelExtraction", **extraction_fields)
    FieldMatches = create_model("FieldMatches", **{c["id"]: (EvaluationResult, Field(...)) for c in active_checks})

    client = OpenAI(base_url=os.getenv("AI_BASE_URL"), api_key=os.getenv("AI_API_KEY"))
    
    rules_summary = "\n".join([f"- {c['id']}: {c['description']}" for c in active_checks if not c.get("deep_dive_only") or deep_dive])
    mode_context = f"Category: {beverage_category}\nExecution Mode: {'Deep Dive' if deep_dive else 'Quick Mode'}\n\nRules to Apply:\n{rules_summary}"
    
    user_content = [
        {"type": "text", "text": f"Form Data: {json.dumps(form_data)}\n\n{mode_context}"},
    ]
    for _, img_b64 in enumerate(images_b64):
        user_content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}
        })

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
        logger.error("Vision API failed.", exc_info=True)
        raise RuntimeError(f"Vision Inference Failed: {str(e)}")
    
    # 3. Deterministic Scoring
    score = 100
    fields_state = {}
    
    if not getattr(ai_result, "is_legible"):
        logger.warning(f"Image deemed illegible. Reason: {getattr(ai_result, 'legibility_remarks')}. Setting score to 0.")
        score = 0
        for check in active_checks:
            fields_state[check["id"]] = EvaluationResult(matched=False, explanation="Skipped: Image illegible.")
    else:
        for check in active_checks:
            rule_id = check["id"]
            evaluation: EvaluationResult = getattr(ai_result, f"{rule_id}_evaluation", EvaluationResult(matched=False, explanation="No data generated."))
            
            if not evaluation.matched:
                if not check.get("deep_dive_only") or deep_dive:
                    score -= check.get("deduction", 0)
                    logger.info(f"Deduction Applied: -{check['deduction']} pts for '{rule_id}'")
            
            fields_state[rule_id] = evaluation
            
        score = max(0, min(100, score))
        logger.info(f"Scoring complete. Final Confidence Score: {score}/100")
    
    typed_fields = FieldMatches(**fields_state)
    return ComplianceReport(
        is_legible=ai_result.is_legible,
        legibility_remarks=ai_result.legibility_remarks,
        confidence_score=score,
        matched_fields=typed_fields,
    )
