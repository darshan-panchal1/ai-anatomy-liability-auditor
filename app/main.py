"""
Anatomy-of-Liability Auditor — FastAPI Application
"""

import os
import uuid
import logging
import time
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage

load_dotenv()

# ---------------------------------------------------------------------------
# Logging — structured, coloured output
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("auditor.main")

# ---------------------------------------------------------------------------
# Import agent after env is loaded
# ---------------------------------------------------------------------------

from app.agent_graph import agent_app  # noqa: E402  (env must be loaded first)

# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

class AuditRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="Medical/legal scenario to audit",
        example=(
            "A patient suffered a femoral nerve injury during a total hip "
            "replacement. The surgeon did not obtain informed consent for this "
            "known risk. Assess malpractice liability."
        ),
    )
    thread_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Conversation thread ID for tracing",
    )


class AuditResponse(BaseModel):
    request_id:   str
    report:       str
    metadata:     dict
    duration_ms:  int


class HealthResponse(BaseModel):
    status:                  str
    version:                 str
    groq_configured:         bool
    courtlistener_configured: bool


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 70)
    logger.info("  Anatomy-of-Liability Auditor  v1.0.0")
    logger.info("=" * 70)

    required = ["GROQ_API_KEY", "COURTLISTENER_API_KEY"]
    missing  = [k for k in required if not os.environ.get(k)]

    if missing:
        logger.warning("Missing API keys: %s — some features will be limited.", missing)
    else:
        logger.info("All API keys detected.")

    from app.agent_graph import get_mcp_client
    try:
        await get_mcp_client()
        logger.info("MCP servers initialised.")
    except Exception as exc:
        logger.warning("MCP init warning (non-fatal): %s", exc)

    logger.info("Server ready — http://0.0.0.0:8000")
    logger.info("=" * 70)

    yield

    logger.info("Shutting down Anatomy-of-Liability Auditor.")


# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Anatomy-of-Liability Auditor",
    description=(
        "Agentic AI system combining Wikidata anatomical ontologies with "
        "CourtListener case law to produce structured medical liability assessments."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request timing middleware
# ---------------------------------------------------------------------------

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start = time.monotonic()
    response = await call_next(request)
    elapsed_ms = int((time.monotonic() - start) * 1000)
    response.headers["X-Process-Time-Ms"] = str(elapsed_ms)
    return response


# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception on %s: %s", request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Check server logs for details."},
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/", tags=["Meta"])
async def root():
    return {
        "system":       "Anatomy-of-Liability Auditor",
        "version":      "1.0.0",
        "architecture": "LangGraph + Groq + MCP (Wikidata + CourtListener)",
        "docs":         "/docs",
    }


@app.get("/health", response_model=HealthResponse, tags=["Meta"])
async def health_check():
    return HealthResponse(
        status="operational",
        version="1.0.0",
        groq_configured=bool(os.environ.get("GROQ_API_KEY")),
        courtlistener_configured=bool(os.environ.get("COURTLISTENER_API_KEY")),
    )


@app.post("/audit", response_model=AuditResponse, tags=["Analysis"])
async def generate_audit(request: AuditRequest):
    """
    Run a full liability analysis through the 4-node agent pipeline:

    1. **Anatomy Node** — extracts & resolves anatomical entities via Wikidata SPARQL  
    2. **Strategy Node** — formulates Boolean legal search queries  
    3. **Legal Node** — retrieves case-law precedents from CourtListener  
    4. **Auditor Node** — synthesises a structured liability report  
    """
    request_id = str(uuid.uuid4())
    start      = time.monotonic()

    logger.info(
        "[%s] Audit request: %.100s...",
        request_id,
        request.query,
    )

    try:
        initial_state = {
            "messages":           [HumanMessage(content=request.query)],
            "anatomical_context": "",
            "legal_context":      "",
            "query_plan":         "",
        }

        config = {"configurable": {"thread_id": request.thread_id}}
        result = await agent_app.ainvoke(initial_state, config=config)

        final_message = result["messages"][-1]
        report_content = final_message.content

        legal_ctx    = result.get("legal_context", "")
        cases_count  = legal_ctx.count("CASE:")
        duration_ms  = int((time.monotonic() - start) * 1000)

        logger.info(
            "[%s] Audit complete in %dms — %d case(s) cited.",
            request_id, duration_ms, cases_count,
        )

        return AuditResponse(
            request_id=request_id,
            report=report_content,
            duration_ms=duration_ms,
            metadata={
                "thread_id":               request.thread_id,
                "anatomical_context_used": bool(result.get("anatomical_context")),
                "legal_query":             result.get("query_plan", ""),
                "cases_cited":             cases_count,
                "query_length_chars":      len(request.query),
            },
        )

    except Exception as exc:
        duration_ms = int((time.monotonic() - start) * 1000)
        logger.error(
            "[%s] Audit failed after %dms: %s",
            request_id, duration_ms, exc, exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error":      str(exc),
                "request_id": request_id,
                "hint":       "Verify API keys are set and MCP servers are reachable.",
            },
        )


# ---------------------------------------------------------------------------
# Entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
        access_log=True,
    )