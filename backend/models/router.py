"""
ModelRouter — Intelligent routing between Gemini Vision and OpenRouter.
FR-C2.2: invoice extraction → Gemini Vision, text tasks → auto-select.
"""

import os
import json
import logging
import re
from typing import Optional

logger = logging.getLogger("mtea.router")


class ModelRouter:
    """Routes requests to the appropriate AI model."""

    def __init__(self):
        self.gemini_key = os.getenv("GEMINI_API_KEY", "")
        self.openrouter_key = os.getenv("OPENROUTER_API_KEY", "")

        if self.gemini_key:
            from models.gemini_handler import GeminiHandler
            self.gemini = GeminiHandler(self.gemini_key)
            logger.info("✅ Gemini configured")
        else:
            self.gemini = None
            logger.warning("⚠️ GEMINI_API_KEY not set — vision extraction unavailable")

        if self.openrouter_key:
            from models.openrouter_handler import OpenRouterHandler
            self.openrouter = OpenRouterHandler(self.openrouter_key)
            logger.info("✅ OpenRouter configured")
        else:
            self.openrouter = None
            logger.info("ℹ️ OPENROUTER_API_KEY not set — text fallback unavailable")

    def get_available_models(self) -> dict:
        return {
            "gemini": self.gemini is not None,
            "openrouter": self.openrouter is not None,
        }

    async def extract_invoice(self, images: list[bytes], model_preference: str = "gemini") -> dict:
        """
        FR-B2: Extract invoice data from images using Gemini Vision.
        Falls back to OpenRouter if Gemini unavailable (text-only, lower quality).
        """
        # Invoice extraction requires vision — Gemini is primary
        if self.gemini:
            return await self.gemini.extract_invoice(images)

        raise ValueError(
            "Gemini API key not configured. Invoice extraction requires vision capabilities. "
            "Set GEMINI_API_KEY in your environment variables."
        )

    async def text_query(self, prompt: str, context: str = "", model_preference: str = "auto") -> dict:
        """
        FR-C1, FR-C2: Route text queries to the best available model.
        """
        # Explicit model selection
        if model_preference == "gemini" and self.gemini:
            return await self.gemini.text_query(prompt, context)
        if model_preference == "openrouter" and self.openrouter:
            return await self.openrouter.text_query(prompt, context)

        # Auto-routing
        handler = self._select_text_model(prompt)
        if handler is None:
            raise ValueError("No AI models configured. Set GEMINI_API_KEY or OPENROUTER_API_KEY.")
        return await handler.text_query(prompt, context)

    def _select_text_model(self, prompt: str):
        """
        FR-C2.2: Routing rules for text tasks.
        Formula/technical → try OpenRouter (free), else Gemini.
        General → try Gemini, else OpenRouter.
        """
        prompt_lower = prompt.lower()
        formula_keywords = {"formula", "function", "vlookup", "index", "match", "sumif",
                           "countif", "if(", "calculate", "equation", "macro", "vba"}

        is_formula = any(kw in prompt_lower for kw in formula_keywords)

        if is_formula:
            return self.openrouter or self.gemini
        return self.gemini or self.openrouter
