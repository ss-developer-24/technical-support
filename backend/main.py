"""
Backend API for Technical Support Assistant with Google ADK Agents
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import logging
from typing import Optional

from agents.orchestrator import OrchestratorAgent
from agents.researcher import ResearcherAgent
from agents.reviewer import ReviewerAgent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Technical Support Backend",
    description="Backend API with Google ADK agents for technical support",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response Models
class QuestionRequest(BaseModel):
    question: str
    session_id: Optional[str] = None

class QuestionResponse(BaseModel):
    answer: str
    sources: Optional[list] = None
    session_id: Optional[str] = None

# Initialize agents (lazy initialization)
orchestrator_agent = None
researcher_agent = None
reviewer_agent = None

def initialize_agents():
    """Initialize all agents on first request"""
    global orchestrator_agent, researcher_agent, reviewer_agent
    
    if orchestrator_agent is None:
        logger.info("Initializing agents...")
        
        try:
            # Initialize Researcher with RAG and Tavily search
            researcher_agent = ResearcherAgent()
            
            # Initialize Reviewer
            reviewer_agent = ReviewerAgent()
            
            # Initialize Orchestrator with access to other agents
            orchestrator_agent = OrchestratorAgent(
                researcher=researcher_agent,
                reviewer=reviewer_agent
            )
            
            logger.info("All agents initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize agents: {str(e)}")
            raise

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "technical-support-backend",
        "agents": {
            "orchestrator": orchestrator_agent is not None,
            "researcher": researcher_agent is not None,
            "reviewer": reviewer_agent is not None
        }
    }

@app.post("/api/question", response_model=QuestionResponse)
async def answer_question(request: QuestionRequest):
    """
    Process a user question through the agent system
    """
    try:
        # Initialize agents if needed
        initialize_agents()
        
        logger.info(f"Processing question: {request.question[:100]}...")
        
        # Process through orchestrator
        result = await orchestrator_agent.process_query(
            question=request.question,
            session_id=request.session_id
        )
        
        return QuestionResponse(
            answer=result["answer"],
            sources=result.get("sources", []),
            session_id=result.get("session_id")
        )
        
    except Exception as e:
        logger.error(f"Error processing question: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/status")
async def get_status():
    """Get system status and configuration"""
    return {
        "agents": {
            "orchestrator": {
                "initialized": orchestrator_agent is not None,
                "model": os.getenv("ORCHESTRATOR_MODEL", "gemini-pro")
            },
            "researcher": {
                "initialized": researcher_agent is not None,
                "model": os.getenv("RESEARCHER_MODEL", "gemini-pro"),
                "rag_enabled": os.getenv("ENABLE_RAG", "true") == "true",
                "tavily_enabled": os.getenv("TAVILY_API_KEY") is not None
            },
            "reviewer": {
                "initialized": reviewer_agent is not None,
                "model": os.getenv("REVIEWER_MODEL", "gemini-pro")
            }
        },
        "config": {
            "gcp_project": os.getenv("GCP_PROJECT_ID"),
            "vertex_ai_location": os.getenv("VERTEX_AI_LOCATION", "us-central1"),
            "storage_bucket": os.getenv("GCS_BUCKET_NAME")
        }
    }

@app.post("/api/ingest")
async def ingest_documents():
    """
    Trigger document ingestion from GCS bucket to create embeddings
    """
    try:
        initialize_agents()
        
        if researcher_agent:
            result = await researcher_agent.ingest_documents()
            return {
                "status": "success",
                "documents_processed": result.get("count", 0),
                "message": "Documents ingested successfully"
            }
        else:
            raise HTTPException(status_code=503, detail="Researcher agent not available")
            
    except Exception as e:
        logger.error(f"Error ingesting documents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        log_level="info",
        reload=False
    )
