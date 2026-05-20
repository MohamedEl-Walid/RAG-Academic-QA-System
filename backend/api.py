"""
FastAPI layer for the RAG-IS AI Education Platform.

Key improvements over v1:
- All endpoints properly typed with Pydantic response models
- CORS middleware enabled for Next.js frontend
- Centralized error handler returns structured JSON errors
- Request timing middleware adds X-Request-Time header
- /ask and /ask/stream both support full options
- In-memory LRU-style cache (bounded to 256 entries)
- /health exposes version + uptime
- Streaming generator is a proper async generator (no blocking time.sleep)
- All sync pipeline calls run in threadpool via asyncio.to_thread
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
import sys
import time
import uuid
from collections import OrderedDict
from contextlib import asynccontextmanager
from typing import Any

# Ensure project root is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field, field_validator

from pipeline import process_question
from quiz.generator import generate_quiz

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("api")

# ---------------------------------------------------------------------------
# App lifecycle
# ---------------------------------------------------------------------------

_start_time: float = 0.0


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _start_time
    _start_time = time.time()
    logger.info("RAG-IS API starting up")
    yield
    logger.info("RAG-IS API shutting down")


app = FastAPI(
    title="RAG-IS API",
    version="2.0.0",
    description="AI-powered educational RAG pipeline",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS — allow Next.js dev server and production domains
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        os.getenv("FRONTEND_ORIGIN", ""),
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Request timing middleware
# ---------------------------------------------------------------------------


@app.middleware("http")
async def add_timing_header(request: Request, call_next):
    t0 = time.perf_counter()
    response = await call_next(request)
    elapsed = round((time.perf_counter() - t0) * 1000, 1)
    response.headers["X-Request-Time-Ms"] = str(elapsed)
    logger.info(
        "%s %s  status=%d  time=%.1fms",
        request.method,
        request.url.path,
        response.status_code,
        elapsed,
    )
    return response


# ---------------------------------------------------------------------------
# Global exception handler — returns structured JSON instead of raw strings
# ---------------------------------------------------------------------------


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception on %s: %s", request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "internal_server_error",
            "message": str(exc),
            "path": request.url.path,
        },
    )


# ---------------------------------------------------------------------------
# Bounded in-memory LRU cache (max 256 entries)
# ---------------------------------------------------------------------------

_CACHE_MAX = 256
_cache: OrderedDict[str, dict] = OrderedDict()


def _cache_key(query: str, options: dict) -> str:
    raw = json.dumps({"query": query, "options": options}, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()


def _cache_get(key: str) -> dict | None:
    if key in _cache:
        _cache.move_to_end(key)
        return _cache[key]
    return None


def _cache_set(key: str, value: dict) -> None:
    if key in _cache:
        _cache.move_to_end(key)
    _cache[key] = value
    if len(_cache) > _CACHE_MAX:
        _cache.popitem(last=False)


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class AskOptions(BaseModel):
    quiz: bool = False
    concept_graph: bool = False
    diagram: bool = False
    code: bool = False
    study_plan: bool = False
    mode: str = Field("explain", pattern=r"^(explain|summarize|teach|revise)$")
    depth: str = Field("balanced", pattern=r"^(fast|balanced|deep)$")
    learning_level: str = Field("beginner", pattern=r"^(beginner|intermediate|expert)$")


class AskRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    user_id: str = Field("default", max_length=128)
    options: AskOptions | None = None

    @field_validator("query")
    @classmethod
    def query_not_blank(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("query must not be blank")
        return stripped

    @field_validator("user_id")
    @classmethod
    def sanitize_user_id(cls, v: str) -> str:
        # Only allow alphanumeric + hyphen/underscore to prevent path traversal
        import re as _re
        if not _re.match(r"^[a-zA-Z0-9_\-]+$", v):
            return "default"
        return v


class QuizRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=8000)
    level: str = Field("beginner", pattern=r"^(beginner|intermediate|expert)$")

    @field_validator("text")
    @classmethod
    def text_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("text must not be blank")
        return v.strip()


class ErrorResponse(BaseModel):
    error: str
    message: str
    request_id: str | None = None


class HealthResponse(BaseModel):
    status: str
    version: str
    uptime_seconds: float


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        version=app.version,
        uptime_seconds=round(time.time() - _start_time, 1),
    )


@app.post("/ask")
async def ask(req: AskRequest) -> dict:
    """
    Run the full RAG pipeline and return a structured response.
    Results are cached by (query, options) hash.
    The heavy sync pipeline runs in a threadpool to avoid blocking the event loop.
    """
    request_id = str(uuid.uuid4())
    logger.info("POST /ask  rid=%s  query=%r  user=%s", request_id, req.query, req.user_id)

    opts = req.options.model_dump() if req.options else {}
    key = _cache_key(req.query, opts)

    cached = _cache_get(key)
    if cached:
        logger.info("POST /ask  rid=%s  cache_hit", request_id)
        return cached

    try:
        result = await asyncio.to_thread(
            process_question,
            query=req.query,
            user_id=req.user_id,
            options=opts,
        )
    except Exception as exc:
        logger.error("POST /ask  rid=%s  pipeline_error: %s", request_id, exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "pipeline_error",
                "message": str(exc),
                "request_id": request_id,
            },
        )

    _cache_set(key, result)
    logger.info("POST /ask  rid=%s  done", request_id)
    return result


@app.post("/quiz")
async def quiz(req: QuizRequest) -> dict:
    """Generate a standalone quiz from the provided text."""
    logger.info("POST /quiz  text_len=%d  level=%s", len(req.text), req.level)
    try:
        result = await asyncio.to_thread(generate_quiz, req.text, level=req.level)
    except Exception as exc:
        logger.error("POST /quiz  failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"error": "quiz_error", "message": str(exc)},
        )
    logger.info("POST /quiz  done  questions=%d", len(result.get("questions", [])))
    return result


# ---------------------------------------------------------------------------
# Streaming endpoint
# ---------------------------------------------------------------------------


async def _stream_answer(query: str, user_id: str, options: dict):
    """
    Async streaming generator:
      1. Runs the pipeline in a threadpool (non-blocking).
      2. Streams the answer word-by-word for a smooth typing effect.
      3. Sends feature_results as a single JSON event after the text.
      4. Sends a final {done: true} marker.
    """
    request_id = str(uuid.uuid4())
    logger.info("STREAM  rid=%s  query=%r", request_id, query)

    try:
        result: dict = await asyncio.to_thread(
            process_question,
            query=query,
            user_id=user_id,
            options=options,
        )
    except Exception as exc:
        logger.error("STREAM  rid=%s  pipeline_error: %s", request_id, exc, exc_info=True)
        yield json.dumps({"error": str(exc), "request_id": request_id}) + "\n"
        return

    answer: str = result.get("answer", "")

    # Stream word-by-word for a natural typing effect
    words = answer.split(" ")
    chunk_size = 3  # words per emit
    for i in range(0, len(words), chunk_size):
        chunk = " ".join(words[i : i + chunk_size])
        if chunk:
            yield json.dumps({"chunk": chunk + " "}) + "\n"
            await asyncio.sleep(0.03)

    # Send structured features
    if result.get("feature_results"):
        yield json.dumps({"features": result["feature_results"]}) + "\n"

    # Send memory update
    if result.get("memory_update"):
        yield json.dumps({"memory_update": result["memory_update"]}) + "\n"

    # Send meta (execution timing etc.)
    if result.get("meta"):
        yield json.dumps({"meta": result["meta"]}) + "\n"

    yield json.dumps({"done": True}) + "\n"
    logger.info("STREAM  rid=%s  done", request_id)


@app.post("/ask/stream")
async def ask_stream(req: AskRequest) -> StreamingResponse:
    """Stream the pipeline response as NDJSON chunks."""
    logger.info(
        "POST /ask/stream  query=%r  user=%s", req.query, req.user_id
    )
    opts = req.options.model_dump() if req.options else {}
    return StreamingResponse(
        _stream_answer(req.query, req.user_id, opts),
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# Cache management
# ---------------------------------------------------------------------------


@app.delete("/cache")
async def clear_cache() -> dict:
    """Clear the in-memory result cache (useful during development)."""
    count = len(_cache)
    _cache.clear()
    logger.info("Cache cleared (%d entries removed)", count)
    return {"cleared": count}


@app.get("/cache/stats")
async def cache_stats() -> dict:
    return {"entries": len(_cache), "max": _CACHE_MAX}
