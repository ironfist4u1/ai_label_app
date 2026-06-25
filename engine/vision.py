import json
import logging
from typing import List, Dict, Any
from openai import OpenAI
from config import env

logger = logging.getLogger("APIClient")


def call_vision_api(
    images_b64: List[str],
    form_data: dict,
    active_checks: List[Dict[str, Any]],
    deep_dive: bool,
    extraction_model,
):
    """
    Builds the multimodal payload and calls the Vision API.
    Returns the parsed structured output using the provided Pydantic model.
    """
    client = OpenAI(base_url=env.config.AI_BASE_URL, api_key=env.config.AI_API_KEY)

    rules_summary = "\n".join(
        [
            f"- {c['id']}: {c['description']}"
            for c in active_checks
            if not c.get("deep_dive_only") or deep_dive
        ]
    )
    beverage_category = form_data.get("rules_category", "Distilled Spirits")
    mode_context = (
        f"Category: {beverage_category}\n"
        f"Execution Mode: {'Deep Dive' if deep_dive else 'Quick Mode'}\n\n"
        f"Rules to Apply:\n{rules_summary}"
    )

    user_content: List[Dict[str, Any]] = [
        {
            "type": "text",
            "text": f"Form Data: {json.dumps(form_data)}\n\n{mode_context}",
        },
    ]
    for img_b64 in images_b64:
        user_content.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"},
            }
        )

    tokens_key = "DEEP_DIVE_MAX_TOKENS" if deep_dive else "QUICK_MODE_MAX_TOKENS"
    logger.info(
        f"Calling Vision API. Images: {len(images_b64)}, Mode: {'Deep Dive' if deep_dive else 'Quick'}."
    )

    try:
        response = client.beta.chat.completions.parse(
            model=env.config.AI_MODEL_NAME,
            messages=[
                {"role": "system", "content": env.config.SYSTEM_PROMPT_CORE},
                {"role": "user", "content": user_content},
            ],
            response_format=extraction_model,
            max_tokens=int(getattr(env.config, tokens_key)),
            temperature=0.0,
        )
        result = response.choices[0].message.parsed
        logger.info(f"Vision API call succeeded. Legibility: {result.is_legible}")
        return result
    except Exception as e:
        logger.error("Vision API call failed.", exc_info=True)
        raise RuntimeError(f"Vision Inference Failed: {str(e)}") from e
