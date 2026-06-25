import logging
from typing import List, Dict, Any, Tuple
from datatypes import EvaluationResult


logger = logging.getLogger(__name__)


def calculate_score(
    ai_result,
    active_checks: List[Dict[str, Any]],
    deep_dive: bool,
) -> Tuple[int, Dict[str, EvaluationResult]]:
    """
    Applies deterministic point deductions based on AI evaluation results.

    Returns:
        score:         Final 0–100 integer.
        fields_state:  Mapping of rule_id -> EvaluationResult for report assembly.
    """
    fields_state: Dict[str, EvaluationResult] = {}

    if not ai_result.is_legible:
        logger.warning(f"Image illegible: {ai_result.legibility_remarks}. Score set to 0.")
        for check in active_checks:
            fields_state[check["id"]] = EvaluationResult(
                matched=False, explanation="Skipped: image illegible."
            )
        return 0, fields_state

    score = 100
    for check in active_checks:
        rule_id = check["id"]
        evaluation: EvaluationResult = getattr(
            ai_result,
            f"{rule_id}_evaluation",
            EvaluationResult(matched=False, explanation="No evaluation data returned."),
        )
        if not evaluation.matched and (not check.get("deep_dive_only") or deep_dive):
            deduction = check.get("deduction", 0)
            score -= deduction
            logger.info(f"Deduction: -{deduction} pts for rule '{rule_id}'")
        fields_state[rule_id] = evaluation

    score = max(0, min(100, score))
    logger.info(f"Scoring complete. Final score: {score}/100")
    return score, fields_state
