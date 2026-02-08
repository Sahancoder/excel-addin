"""
McLarens Transformation Excel Assistant — Backend API
FastAPI service for Render deployment.
Handles invoice extraction (Gemini Vision), AI text helper, and health checks.
"""

import os
import io
import json
import time
import logging
import traceback
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from models.router import ModelRouter
from ocr.pdf_converter import PDFConverter

load_dotenv()

# ===== LOGGING =====
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("mtea")

# ===== RATE LIMITING =====
limiter = Limiter(key_func=get_remote_address)

# ===== LIFESPAN =====
router_instance: Optional[ModelRouter] = None
pdf_converter: Optional[PDFConverter] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global router_instance, pdf_converter
    logger.info("🚀 Starting McLarens Transformation Excel Assistant Backend")
    router_instance = ModelRouter()
    pdf_converter = PDFConverter()
    logger.info(f"  Models configured: {router_instance.get_available_models()}")
    yield
    logger.info("👋 Shutting down MTEA Backend")


# ===== APP =====
app = FastAPI(
    title="McLarens Transformation Excel Assistant API",
    version="1.0.0",
    lifespan=lifespan,
)
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded. Please try again later."})


# ===== CORS =====
# NFR-S3: Restrict to allowed origins
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "https://localhost:3000,null").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in ALLOWED_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== MODELS =====


class TextRequest(BaseModel):
    prompt: str
    model: str = "auto"
    context: Optional[dict] = None


class TextResponse(BaseModel):
    answer: str
    formula: Optional[str] = None
    model_used: str


class InvoiceResponse(BaseModel):
    header: dict
    items: list = []
    confidence: dict
    warnings: list
    raw_text: Optional[str] = None


# ===== ENDPOINTS =====

@app.get("/health")
async def health():
    """Health check endpoint."""
    models = router_instance.get_available_models() if router_instance else {}
    return {
        "status": "ok",
        "bot": "McLarens Transformation Excel Assistant",
        "version": "1.0.0",
        "models": models,
        "timestamp": time.time(),
    }


@app.post("/api/invoice/extract", response_model=InvoiceResponse)
@limiter.limit("30/minute")
async def extract_invoice(
    request: Request,
    file: UploadFile = File(...),
    model: str = Form("gemini"),
):
    """
    FR-B2: Extract invoice header and items from PDF/image using Gemini Vision.
    """
    logger.info(f"📄 Invoice extraction: {file.filename} (model={model})")

    # Validate file type (FR-B1.2)
    allowed_types = {
        "application/pdf", "image/png", "image/jpeg", "image/jpg", "image/tiff",
    }
    content_type = file.content_type or ""
    ext = (file.filename or "").rsplit(".", 1)[-1].lower()

    if content_type not in allowed_types and ext not in {"pdf", "png", "jpg", "jpeg", "tiff", "tif"}:
        raise HTTPException(400, detail="Unsupported file type. Upload PDF or image files.")

    # Validate file size
    max_size = int(os.getenv("MAX_FILE_SIZE_MB", "10")) * 1024 * 1024
    contents = await file.read()
    if len(contents) > max_size:
        raise HTTPException(400, detail=f"File too large. Maximum {max_size // (1024*1024)}MB.")

    try:
        # Convert PDF pages to images if needed
        images = []
        if ext == "pdf" or content_type == "application/pdf":
            images = pdf_converter.pdf_to_images(contents)
            if not images:
                raise ValueError("Could not extract images from PDF")
        else:
            images = [contents]

        # FR-B2.1-B2.4: Call Gemini Vision for extraction
        result = await router_instance.extract_invoice(images, model_preference=model)

        logger.info(f"✅ Extraction complete: confidence={result.get('confidence', {}).get('overall', 'N/A')}")
        return InvoiceResponse(**result)

    except Exception as e:
        logger.error(f"❌ Extraction failed: {e}\n{traceback.format_exc()}")
        raise HTTPException(500, detail=f"Extraction failed: {str(e)}")


@app.post("/api/ai/text", response_model=TextResponse)
@limiter.limit("60/minute")
async def ai_text_helper(request: Request, body: TextRequest):
    """
    FR-C1: AI text/formula helper.
    Sends prompt + context to AI model and returns answer + optional formula.
    """
    logger.info(f"🤖 AI text request: model={body.model}, prompt_len={len(body.prompt)}")

    if not body.prompt.strip():
        raise HTTPException(400, detail="Prompt cannot be empty.")

    try:
        # Build context string
        context_str = ""
        if body.context:
            context_str = f"\n\nSpreadsheet context:\n"
            context_str += f"Sheet: {body.context.get('sheetName', 'Unknown')}\n"
            headers = body.context.get("headers", [])
            if headers:
                context_str += f"Headers: {', '.join(str(h) for h in headers)}\n"
            sample = body.context.get("sampleData", [])
            if sample:
                context_str += f"Sample rows ({len(sample)}):\n"
                for row in sample[:5]:
                    context_str += f"  {row}\n"
            context_str += f"Total rows: {body.context.get('totalRows', '?')}\n"

        # Route to appropriate model
        result = await router_instance.text_query(
            prompt=body.prompt,
            context=context_str,
            model_preference=body.model,
        )

        return TextResponse(
            answer=result["answer"],
            formula=result.get("formula"),
            model_used=result["model_used"],
        )

    except Exception as e:
        logger.error(f"❌ AI text error: {e}\n{traceback.format_exc()}")
        raise HTTPException(500, detail=f"AI request failed: {str(e)}")


@app.get("/api/templates")
async def list_templates():
    """Return available template definitions."""
    return {
        "templates": [
            {"id": "invoices", "name": "Invoices", "description": "Standard invoice register table"},
            {"id": "invoice_items", "name": "Invoice Items", "description": "Line items linked to invoices"},
            {"id": "import_log", "name": "Import Log", "description": "Audit trail for all operations"},
        ]
    }


# ===== MAIN =====
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
