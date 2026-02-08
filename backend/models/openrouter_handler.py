"""
OpenRouterHandler — Free text model fallback via OpenRouter API.
FR-C2.1: Optional text model for formula help / text summarization.
"""

import json
import logging
import re

import httpx

logger = logging.getLogger("mtea.openrouter")

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


class OpenRouterHandler:
    """OpenRouter API wrapper for free text models."""

    API_URL = "https://openrouter.ai/api/v1/chat/completions"
    # Free model — adjust if needed
    DEFAULT_MODEL = "meta-llama/llama-3.1-8b-instruct:free"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.configured = True

    async def text_query(self, prompt: str, context: str = "") -> dict:
        """FR-C1: Text/formula query via OpenRouter."""
        user_content = prompt
        if context:
            user_content += "\n" + context

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self.API_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://mclarens-excel-assistant.vercel.app",
                    "X-Title": "McLarens Transformation Excel Assistant",
                },
                json={
                    "model": self.DEFAULT_MODEL,
                    "messages": [
                        {"role": "system", "content": TEXT_SYSTEM_PROMPT},
                        {"role": "user", "content": user_content},
                    ],
                    "temperature": 0.3,
                    "max_tokens": 2048,
                },
            )
            response.raise_for_status()
            data = response.json()

        raw = data["choices"][0]["message"]["content"].strip()

        try:
            result = self._parse_json_response(raw)
            return {
                "answer": result.get("answer", raw),
                "formula": result.get("formula"),
                "model_used": "openrouter",
            }
        except Exception:
            return {
                "answer": raw,
                "formula": self._extract_formula(raw),
                "model_used": "openrouter",
            }

    def _parse_json_response(self, text: str) -> dict:
        cleaned = re.sub(r"```json\s*", "", text)
        cleaned = re.sub(r"```\s*", "", cleaned).strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass
        match = re.search(r"\{[\s\S]*\}", cleaned)
        if match:
            return json.loads(match.group())
        raise ValueError("Could not parse JSON")

    def _extract_formula(self, text: str) -> str | None:
        match = re.search(r"(=[A-Z]+\([^)]*\)[\w\(\),\"!:\$\*]*)", text)
        return match.group(1) if match else None
