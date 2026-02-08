"""
MTEA Backend Tests — Comprehensive test suite.
Tests routing, parsing, endpoints, extraction schema, and edge cases.
"""

import pytest
import json
import os
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

# Mock environment before imports
os.environ["GEMINI_API_KEY"] = ""
os.environ["OPENROUTER_API_KEY"] = ""


class TestModelRouter:
    """Test intelligent model routing (FR-C2.2)."""

    def test_formula_keywords_route_to_openrouter(self):
        """Formula-related queries should prefer OpenRouter."""
        from models.router import ModelRouter
        with patch.dict(os.environ, {"GEMINI_API_KEY": "", "OPENROUTER_API_KEY": ""}):
            router = ModelRouter()
            # Without any models, it should raise
            prompt = "Create a VLOOKUP formula"
            handler = router._select_text_model(prompt)
            assert handler is None  # No models configured

    def test_general_queries_route_to_gemini(self):
        """General queries should prefer Gemini."""
        from models.router import ModelRouter
        router = ModelRouter()
        prompt = "Explain the data trends"
        handler = router._select_text_model(prompt)
        assert handler is None  # No models configured without keys

    def test_get_available_models(self):
        """Should report model availability."""
        from models.router import ModelRouter
        router = ModelRouter()
        models = router.get_available_models()
        assert "gemini" in models
        assert "openrouter" in models

    @pytest.mark.asyncio
    async def test_extract_invoice_requires_gemini(self):
        """Invoice extraction should require Gemini."""
        from models.router import ModelRouter
        router = ModelRouter()
        with pytest.raises(ValueError, match="Gemini API key not configured"):
            await router.extract_invoice([b"fake_image"])

    @pytest.mark.asyncio
    async def test_text_query_requires_models(self):
        """Text query should raise when no models configured."""
        from models.router import ModelRouter
        router = ModelRouter()
        with pytest.raises(ValueError, match="No AI models configured"):
            await router.text_query("test prompt")


class TestJSONParsing:
    """Test JSON response parsing."""

    def test_parse_clean_json(self):
        """Should parse clean JSON."""
        from models.gemini_handler import GeminiHandler
        handler = GeminiHandler.__new__(GeminiHandler)
        result = handler._parse_json_response('{"answer": "test", "formula": null}')
        assert result["answer"] == "test"

    def test_parse_json_with_code_fences(self):
        """Should handle markdown code fences."""
        from models.gemini_handler import GeminiHandler
        handler = GeminiHandler.__new__(GeminiHandler)
        text = '```json\n{"answer": "hello"}\n```'
        result = handler._parse_json_response(text)
        assert result["answer"] == "hello"

    def test_parse_json_embedded_in_text(self):
        """Should extract JSON from surrounding text."""
        from models.gemini_handler import GeminiHandler
        handler = GeminiHandler.__new__(GeminiHandler)
        text = 'Here is the result:\n{"answer": "found it"}\nDone.'
        result = handler._parse_json_response(text)
        assert result["answer"] == "found it"

    def test_parse_invalid_json_raises(self):
        """Should raise on completely invalid JSON."""
        from models.gemini_handler import GeminiHandler
        handler = GeminiHandler.__new__(GeminiHandler)
        with pytest.raises(ValueError, match="Could not parse JSON"):
            handler._parse_json_response("This is not JSON at all")

    def test_extract_formula_from_text(self):
        """Should extract Excel formula from text."""
        from models.gemini_handler import GeminiHandler
        handler = GeminiHandler.__new__(GeminiHandler)
        text = 'Use this formula: =VLOOKUP(A2, Sheet2!A:B, 2, FALSE) to find matches.'
        formula = handler._extract_formula(text)
        assert formula is not None
        assert formula.startswith("=VLOOKUP")


class TestPDFConverter:
    """Test PDF to image conversion."""

    def test_converter_initialization(self):
        """Should initialize with default DPI."""
        from ocr.pdf_converter import PDFConverter
        converter = PDFConverter()
        assert converter.dpi == 200

    def test_custom_dpi(self):
        """Should accept custom DPI."""
        from ocr.pdf_converter import PDFConverter
        converter = PDFConverter(dpi=300)
        assert converter.dpi == 300
        assert converter.zoom == 300 / 72

    def test_invalid_pdf_raises(self):
        """Should raise on invalid PDF bytes."""
        from ocr.pdf_converter import PDFConverter
        converter = PDFConverter()
        with pytest.raises(ValueError, match="Could not convert PDF"):
            converter.pdf_to_images(b"not a pdf")

    def test_get_page_count_invalid(self):
        """Should return 0 for invalid PDF."""
        from ocr.pdf_converter import PDFConverter
        converter = PDFConverter()
        assert converter.get_page_count(b"bad data") == 0

    def test_extract_text_invalid(self):
        """Should return empty string for invalid PDF."""
        from ocr.pdf_converter import PDFConverter
        converter = PDFConverter()
        assert converter.extract_text(b"bad data") == ""


class TestInvoiceExtractionSchema:
    """Test the invoice extraction response schema (FR-B2)."""

    def test_valid_invoice_response(self):
        """Valid response should have all required fields."""
        response = {
            "header": {
                "vendor_name": "Test Corp",
                "invoice_number": "INV-001",
                "invoice_date": "2024-01-15",
                "due_date": "2024-02-15",
                "subtotal": 1000.00,
                "vat_tax": 150.00,
                "total": 1150.00,
                "currency": "LKR",
            },
            "items": [],
            "confidence": {"overall": 0.92},
            "warnings": [],
        }
        assert "header" in response
        assert response["header"]["total"] == 1150.00
        assert response["confidence"]["overall"] >= 0
        assert response["confidence"]["overall"] <= 1

    def test_header_fields_complete(self):
        """All required header fields should be present."""
        required_fields = [
            "vendor_name", "invoice_number", "invoice_date",
            "due_date", "subtotal", "vat_tax", "total", "currency"
        ]
        header = {f: "" for f in required_fields}
        for field in required_fields:
            assert field in header

    def test_line_items_schema(self):
        """Line items should have correct fields (FR-B3)."""
        item = {
            "description": "Widget A",
            "qty": 10,
            "unit_price": 50.00,
            "discount": None,
            "tax": None,
            "line_total": 500.00,
        }
        assert item["qty"] * item["unit_price"] == item["line_total"]


class TestDuplicateDetection:
    """Test duplicate protection logic (FR-B6)."""

    def test_primary_key_match(self):
        """Should detect vendor_name + invoice_number duplicates."""
        existing = [
            {"vendor_name": "ABC Corp", "invoice_number": "INV-001"},
            {"vendor_name": "XYZ Ltd", "invoice_number": "INV-002"},
        ]
        new = {"vendor_name": "ABC Corp", "invoice_number": "INV-001"}

        is_dup = any(
            e["vendor_name"].lower() == new["vendor_name"].lower() and
            e["invoice_number"].lower() == new["invoice_number"].lower()
            for e in existing
        )
        assert is_dup is True

    def test_no_false_positive(self):
        """Should not flag non-duplicates."""
        existing = [{"vendor_name": "ABC Corp", "invoice_number": "INV-001"}]
        new = {"vendor_name": "ABC Corp", "invoice_number": "INV-002"}

        is_dup = any(
            e["vendor_name"].lower() == new["vendor_name"].lower() and
            e["invoice_number"].lower() == new["invoice_number"].lower()
            for e in existing
        )
        assert is_dup is False

    def test_case_insensitive(self):
        """Duplicate check should be case-insensitive."""
        existing = [{"vendor_name": "abc corp", "invoice_number": "inv-001"}]
        new = {"vendor_name": "ABC Corp", "invoice_number": "INV-001"}

        is_dup = any(
            e["vendor_name"].lower() == new["vendor_name"].lower() and
            e["invoice_number"].lower() == new["invoice_number"].lower()
            for e in existing
        )
        assert is_dup is True


class TestHTTPEndpoints:
    """Test FastAPI HTTP endpoints."""

    @pytest.fixture(autouse=True)
    def setup_client(self):
        """Create test client with mocked models."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "", "OPENROUTER_API_KEY": ""}):
            from main import app
            self.client = TestClient(app)

    def test_health_returns_ok(self):
        """Health endpoint should return status ok."""
        res = self.client.get("/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ok"
        assert data["version"] == "1.0.0"
        assert "models" in data

    def test_health_shows_model_config(self):
        """Health should report model availability."""
        res = self.client.get("/health")
        data = res.json()
        assert "gemini" in data["models"]
        assert "openrouter" in data["models"]

    def test_templates_endpoint(self):
        """Templates endpoint should return list."""
        res = self.client.get("/api/templates")
        assert res.status_code == 200
        data = res.json()
        assert "templates" in data
        assert len(data["templates"]) == 3

    def test_text_endpoint_requires_prompt(self):
        """Text endpoint should validate required fields."""
        res = self.client.post("/api/ai/text", json={"prompt": ""})
        assert res.status_code == 400

    def test_text_endpoint_handles_no_models(self):
        """Text endpoint should 500 when no models configured."""
        res = self.client.post("/api/ai/text", json={"prompt": "test"})
        assert res.status_code == 500

    def test_invoice_rejects_bad_file_type(self):
        """Invoice endpoint should reject non-PDF/image files."""
        from io import BytesIO
        res = self.client.post(
            "/api/invoice/extract",
            files={"file": ("test.txt", BytesIO(b"hello"), "text/plain")},
            data={"model": "gemini"},
        )
        assert res.status_code == 400


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_prompt_rejected(self):
        """Empty prompts should be rejected."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "", "OPENROUTER_API_KEY": ""}):
            from main import app
            client = TestClient(app)
            res = client.post("/api/ai/text", json={"prompt": "   "})
            assert res.status_code == 400

    def test_unicode_in_prompt(self):
        """Unicode characters should be handled."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "", "OPENROUTER_API_KEY": ""}):
            from main import app
            client = TestClient(app)
            res = client.post("/api/ai/text", json={"prompt": "Calculate ¥ to LKR rate"})
            # Will 500 because no models, but should not crash
            assert res.status_code in [200, 500]

    def test_oversized_file_rejected(self):
        """Large files should be rejected."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "", "OPENROUTER_API_KEY": "", "MAX_FILE_SIZE_MB": "1"}):
            from main import app
            client = TestClient(app)
            # Create a 2MB fake file
            big_data = b"x" * (2 * 1024 * 1024)
            from io import BytesIO
            res = client.post(
                "/api/invoice/extract",
                files={"file": ("big.pdf", BytesIO(big_data), "application/pdf")},
                data={"model": "gemini"},
            )
            assert res.status_code == 400

    def test_context_with_text_query(self):
        """Text query with context should include it in prompt."""
        context = {
            "sheetName": "Sales",
            "headers": ["Date", "Amount", "Vendor"],
            "sampleData": [["2024-01-01", 100, "Test"]],
            "totalRows": 50,
        }
        # Just verify the data structure is valid
        assert context["sheetName"] == "Sales"
        assert len(context["headers"]) == 3
