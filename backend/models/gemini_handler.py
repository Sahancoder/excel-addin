"""
GeminiHandler — Google Gemini Vision + Text API wrapper.
Handles invoice extraction (FR-B2) and text/formula queries (FR-C1).
"""

import json
import logging
import re
from typing import Optional

import google.generativeai as genai
from PIL import Image
import io

logger = logging.getLogger("mtea.gemini")

# Invoice extraction prompt (FR-B2.1 - B2.4)
INVOICE_EXTRACTION_PROMPT = """You are an expert invoice data extractor. Analyze this invoice image and extract all data.

Return ONLY valid JSON with this exact structure (no markdown, no explanation):
{
  "header": {
    "vendor_name": "string",
    "invoice_number": "string",
    "invoice_date": "YYYY-MM-DD or as shown",
    "due_date": "YYYY-MM-DD or null",
    "subtotal": number_or_null,
    "vat_tax": number_or_null,
    "total": number,
    "currency": "3-letter code like LKR, USD, EUR"
  },
  "items": [
    {
      "description": "string",
      "qty": number,
      "unit_price": number,
      "discount": number_or_null,
      "tax": number_or_null,
      "line_total": number
    }
  ],
  "confidence": {
    "overall": 0.0_to_1.0,
    "vendor_name": 0.0_to_1.0,
    "invoice_number": 0.0_to_1.0,
    "invoice_date": 0.0_to_1.0,
    "due_date": 0.0_to_1.0,
    "subtotal": 0.0_to_1.0,
    "vat_tax": 0.0_to_1.0,
    "total": 0.0_to_1.0,
    "currency": 0.0_to_1.0
  },
  "warnings": ["list of any issues found"]
}

Rules:
- Extract ALL visible fields. Set confidence to 0 for fields not found.
- If a field is unclear or partially obscured, set lower confidence and add a warning.
- For multi-page invoices, combine data from all pages.
- Currency: detect from symbols ($ → USD, £ → GBP, € → EUR, Rs/LKR → LKR) or text.
- Numbers: remove thousand separators, use decimal point.
- Return ONLY the JSON object, nothing else."""

TEXT_SYSTEM_PROMPT = """You are an expert Excel assistant. Help with formulas, data analysis, and spreadsheet tasks.

When providing a formula:
1. Give a clear explanation
2. Include the formula separately

Respond in this JSON format:
{
  "answer": "Your explanation here",
  "formula": "=YOUR_FORMULA_HERE or null if not applicable"
}

Return ONLY valid JSON, no markdown."""


class GeminiHandler:
    """Google Gemini API wrapper for vision and text tasks."""

    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.vision_model = genai.GenerativeModel("gemini-1.5-pro")
        self.text_model = genai.GenerativeModel("gemini-1.5-flash")
        self.configured = True

    async def extract_invoice(self, images: list[bytes]) -> dict:
        """
        FR-B2: Extract invoice data from images using Gemini Vision.
        NFR-R1: Retry on invalid JSON.
        """
        # Convert bytes to PIL Images
        pil_images = []
        for img_bytes in images:
            try:
                img = Image.open(io.BytesIO(img_bytes))
                pil_images.append(img)
            except Exception as e:
                logger.warning(f"Could not open image: {e}")

        if not pil_images:
            raise ValueError("No valid images to process")

        # Build content for Gemini
        content = [INVOICE_EXTRACTION_PROMPT] + pil_images

        # Attempt extraction with retry (NFR-R1)
        last_error = None
        for attempt in range(3):
            try:
                response = self.vision_model.generate_content(
                    content,
                    generation_config=genai.GenerationConfig(
                        temperature=0.1,
                        max_output_tokens=4096,
                    ),
                )

                raw_text = response.text.strip()
                result = self._parse_json_response(raw_text)

                # Validate required fields
                if "header" not in result:
                    result["header"] = {}
                if "confidence" not in result:
                    result["confidence"] = {"overall": 0.5}
                if "warnings" not in result:
                    result["warnings"] = []
                if "items" not in result:
                    result["items"] = []

                # Ensure overall confidence
                if "overall" not in result["confidence"]:
                    field_confs = [v for k, v in result["confidence"].items() if isinstance(v, (int, float))]
                    result["confidence"]["overall"] = sum(field_confs) / len(field_confs) if field_confs else 0.5

                logger.info(f"✅ Gemini extraction success (attempt {attempt + 1})")
                return result

            except Exception as e:
                last_error = e
                logger.warning(f"⚠️ Gemini attempt {attempt + 1} failed: {e}")

        raise ValueError(f"Gemini extraction failed after 3 attempts: {last_error}")

    async def text_query(self, prompt: str, context: str = "") -> dict:
        """FR-C1: Text/formula query using Gemini."""
        full_prompt = TEXT_SYSTEM_PROMPT + "\n\nUser request: " + prompt
        if context:
            full_prompt += "\n" + context

        response = self.text_model.generate_content(
            full_prompt,
            generation_config=genai.GenerationConfig(
                temperature=0.3,
                max_output_tokens=2048,
            ),
        )

        raw = response.text.strip()
        try:
            result = self._parse_json_response(raw)
            return {
                "answer": result.get("answer", raw),
                "formula": result.get("formula"),
                "model_used": "gemini",
            }
        except Exception:
            # If not JSON, return raw text
            return {
                "answer": raw,
                "formula": self._extract_formula(raw),
                "model_used": "gemini",
            }

    def _parse_json_response(self, text: str) -> dict:
        """Parse JSON from response, handling markdown code blocks."""
        # Remove markdown code fences
        cleaned = re.sub(r"```json\s*", "", text)
        cleaned = re.sub(r"```\s*", "", cleaned)
        cleaned = cleaned.strip()

        # Try direct parse
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # Try to find JSON object in text
        match = re.search(r"\{[\s\S]*\}", cleaned)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

        raise ValueError(f"Could not parse JSON from response: {text[:200]}")

    def _extract_formula(self, text: str) -> str | None:
        """Try to extract Excel formula from text."""
        match = re.search(r"(=[A-Z]+\([^)]*\)[\w\(\),\"!:\$\*]*)", text)
        if match:
            return match.group(1)
        return None
