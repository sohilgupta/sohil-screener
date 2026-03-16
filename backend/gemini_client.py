import os
import json
import re
import logging
from typing import Dict, Any, Optional

import google.generativeai as genai

logger = logging.getLogger(__name__)

# Models to try in order of preference
GEMINI_MODELS = [
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-1.5-pro-latest",
    "gemini-1.5-flash-latest",
]


def _configure():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set")
    genai.configure(api_key=api_key)


def get_gemini_analysis(prompt: str) -> str:
    """Send a prompt to Gemini and return the raw text response."""
    _configure()

    generation_config = genai.types.GenerationConfig(
        temperature=0.15,
        max_output_tokens=8192,
    )

    last_error = None
    for model_name in GEMINI_MODELS:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt, generation_config=generation_config)
            logger.info(f"Gemini analysis complete using model: {model_name}")
            return response.text
        except Exception as exc:
            logger.warning(f"Model {model_name} failed: {exc}")
            last_error = exc

    raise RuntimeError(f"All Gemini models failed. Last error: {last_error}")


def parse_valuation_response(response_text: str, current_price: float) -> Dict[str, Any]:
    """
    Extract structured valuation data from the LLM response.
    Looks for a ```json ... ``` block appended by the prompt template.
    """
    result: Dict[str, Any] = {
        "analysis_text": response_text,
        "bull_case": {
            "target_price": None,
            "probability": 0.25,
            "growth_rate": None,
            "key_assumptions": [],
        },
        "base_case": {
            "target_price": None,
            "probability": 0.50,
            "growth_rate": None,
            "key_assumptions": [],
        },
        "bear_case": {
            "target_price": None,
            "probability": 0.25,
            "growth_rate": None,
            "key_assumptions": [],
        },
        "probability_weighted_value": None,
        "upside_percentage": None,
        "recommendation": "Hold",
        "confidence_level": "Medium",
        "price_target": None,
        "executive_summary": "",
        "key_risks": [],
        "valuation_methods": [],
    }

    # Extract JSON block
    json_match = re.search(r"```json\s*([\s\S]*?)\s*```", response_text, re.IGNORECASE)
    if json_match:
        try:
            data = json.loads(json_match.group(1))
            for key in [
                "bull_case", "base_case", "bear_case",
                "probability_weighted_value", "upside_percentage",
                "recommendation", "confidence_level", "price_target",
                "executive_summary", "key_risks", "valuation_methods",
            ]:
                if key in data:
                    result[key] = data[key]
        except json.JSONDecodeError as exc:
            logger.warning(f"JSON parse error in LLM response: {exc}")

    # Compute PWV if missing but scenario targets are available
    if result["probability_weighted_value"] is None:
        bull_t = result["bull_case"].get("target_price")
        base_t = result["base_case"].get("target_price")
        bear_t = result["bear_case"].get("target_price")
        p_bull = result["bull_case"].get("probability", 0.25)
        p_base = result["base_case"].get("probability", 0.50)
        p_bear = result["bear_case"].get("probability", 0.25)
        if all(x is not None for x in [bull_t, base_t, bear_t]):
            result["probability_weighted_value"] = (
                p_bull * bull_t + p_base * base_t + p_bear * bear_t
            )

    # Compute upside % if missing
    pwv = result["probability_weighted_value"]
    if result["upside_percentage"] is None and pwv and current_price and current_price > 0:
        result["upside_percentage"] = round(
            (pwv - current_price) / current_price * 100, 2
        )

    # Use PWV as price target fallback
    if result["price_target"] is None:
        result["price_target"] = pwv

    # Strip JSON block from narrative text
    clean = re.sub(r"```json\s*[\s\S]*?\s*```", "", response_text, flags=re.IGNORECASE).strip()
    result["analysis_text"] = clean

    return result
