"""OCR Agent — extracts portfolio holdings from a brokerage screenshot."""
from __future__ import annotations

import asyncio
import io
import logging
import os
import sys
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class OCRAgent(BaseAgent):
    """
    Extracts stock holdings from an uploaded image using:
      1. Tesseract (primary, always available)
      2. Google Cloud Vision (optional, set GOOGLE_VISION_KEY env var)

    Inputs:
        image_bytes     (bytes) – raw image data
        prefer_vision   (bool)  – try Google Vision first if key is available

    Outputs:
        holdings    – list of {stock_name, ticker, quantity, buy_price}
        ocr_engine  – "tesseract" | "google_vision"
        raw_text    – raw OCR output (for debugging)
    """

    AGENT_ID = "ocr_agent"

    def __init__(self) -> None:
        super().__init__()
        self._vision_key: Optional[str] = os.getenv("GOOGLE_VISION_KEY")

    async def _execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        image_bytes: bytes = inputs["image_bytes"]
        prefer_vision: bool = inputs.get("prefer_vision", False)

        loop = asyncio.get_event_loop()

        # Try Google Vision first if requested and available
        if prefer_vision and self._vision_key:
            try:
                result = await loop.run_in_executor(
                    None, self._google_vision_ocr, image_bytes
                )
                if result["holdings"]:
                    return result
            except Exception as exc:
                self.logger.warning(f"Google Vision failed, falling back to Tesseract: {exc}")

        # Primary: Tesseract
        return await loop.run_in_executor(None, self._tesseract_ocr, image_bytes)

    # ------------------------------------------------------------------
    # Tesseract OCR
    # ------------------------------------------------------------------

    def _tesseract_ocr(self, image_bytes: bytes) -> Dict[str, Any]:
        from portfolio_ocr import extract_portfolio_from_screenshot, extract_text_from_image

        raw_text = extract_text_from_image(image_bytes)
        holdings = extract_portfolio_from_screenshot(image_bytes)

        return {
            "holdings": holdings,
            "ocr_engine": "tesseract",
            "raw_text": raw_text[:2000],  # truncate for response size
        }

    # ------------------------------------------------------------------
    # Google Cloud Vision OCR
    # ------------------------------------------------------------------

    def _google_vision_ocr(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Uses Google Cloud Vision REST API (no extra SDK needed).
        Requires GOOGLE_VISION_KEY env var (API key, not service account).
        """
        import base64
        import json
        import re
        import requests

        encoded = base64.b64encode(image_bytes).decode("utf-8")
        url = f"https://vision.googleapis.com/v1/images:annotate?key={self._vision_key}"
        payload = {
            "requests": [{
                "image": {"content": encoded},
                "features": [{"type": "DOCUMENT_TEXT_DETECTION"}],
            }]
        }
        resp = requests.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        body = resp.json()

        full_text: str = (
            body.get("responses", [{}])[0]
            .get("fullTextAnnotation", {})
            .get("text", "")
        )

        if not full_text.strip():
            return {"holdings": [], "ocr_engine": "google_vision", "raw_text": ""}

        # Reuse the same text parser from portfolio_ocr
        from portfolio_ocr import parse_holdings_from_text
        holdings = parse_holdings_from_text(full_text)

        return {
            "holdings": holdings,
            "ocr_engine": "google_vision",
            "raw_text": full_text[:2000],
        }
