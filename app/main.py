import os
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import the compiled LangGraph application
from app.agent_graph import agent_app
from langchain_core.messages import HumanMessage

# --- Data Models ---
class AuditRequest(BaseModel):
    query: str = Field(..., description="The injury or liability situation to audit")
    thread_id: str = Field(default="default-thread", description="Thread ID for conversation memory")

class AuditResponse(BaseModel):
    report: str
    metadata: dict

# --- Lifecycle & App Definition ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle manager."""
    print("=" * 80)
    print("Initializing Anatomy-of-Liability Auditor...")
    print("=" * 80)
    
    required = ["GROQ_API_KEY", "COURTLISTENER_API_KEY"]
    missing = [v for v in required if not os.environ.get(v)]
    
    if missing:
        print(f"⚠️  CRITICAL WARNING: Missing API Keys: {missing}")
        print("The system will not function correctly without these keys.")
    else:
        print("✓ All required API keys detected")
    
    print("✓ Agent graph compiled")
    
    # Initialize MCP client on startup
    from app.agent_graph import get_mcp_client
    try:
        await get_mcp_client()
        print("✓ MCP servers initialized")
    except Exception as e:
        print(f"⚠️  MCP server initialization warning: {e}")
    
    print("=" * 80)
    yield
    
    # Cleanup on shutdown
    print("\nShutting down Auditor...")
    from app.agent_graph import mcp_client
    if mcp_client:
        try:
            # Close MCP client connections if needed
            pass
        except:
            pass

app = FastAPI(
    title="The Anatomy-of-Liability Auditor",
    description="Agentic AI system for legal-medical liability analysis using LangGraph, Groq, and MCP",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Root endpoint with system information."""
    return {
        "system": "Anatomy-of-Liability Auditor",
        "version": "1.0.0",
        "status": "operational",
        "engine": "Groq LPU",
        "architecture": "LangGraph + MCP",
        "endpoints": {
            "health": "/health",
            "audit": "/audit (POST)"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "operational", 
        "engine": "Groq LPU",
        "groq_configured": bool(os.environ.get("GROQ_API_KEY")),
        "courtlistener_configured": bool(os.environ.get("COURTLISTENER_API_KEY"))
    }

@app.post("/audit", response_model=AuditResponse)
async def generate_audit(request: AuditRequest):
    """
    Main endpoint. Triggers the LangGraph workflow to audit the user's query.
    
    Args:
        request: AuditRequest containing the query and optional thread_id
        
    Returns:
        AuditResponse with the full report and metadata
    """
    try:
        print(f"\n{'='*80}")
        print(f"New Audit Request: {request.query[:100]}...")
        print(f"{'='*80}\n")
        
        # Construct the initial state for the graph
        initial_state = {
            "messages": [HumanMessage(content=request.query)],
            "anatomical_context": "",
            "legal_context": "",
            "query_plan": ""
        }
        
        # Configure thread for potential persistence
        config = {"configurable": {"thread_id": request.thread_id}}
        
        # Execute the graph asynchronously
        result = await agent_app.ainvoke(initial_state, config=config)
        
        # Extract the final report from the last AI message
        final_message = result["messages"][-1]
        report_content = final_message.content
        
        # Count cases found
        cases_count = result.get("legal_context", "").count("CASE:")
        
        print(f"\n{'='*80}")
        print(f"✓ Audit Complete - {cases_count} cases analyzed")
        print(f"{'='*80}\n")
        
        return AuditResponse(
            report=report_content,
            metadata={
                "anatomical_context_used": bool(result.get("anatomical_context")),
                "legal_query_used": result.get("query_plan", ""),
                "cases_found_count": cases_count,
                "thread_id": request.thread_id
            }
        )
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"\n❌ ERROR:\n{error_trace}")
        raise HTTPException(
            status_code=500, 
            detail=f"Audit Process Failed: {str(e)}"
        )

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        log_level="info"
    )