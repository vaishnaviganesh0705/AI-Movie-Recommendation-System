import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.dependencies import get_optional_current_user
from app.models import User
from app.graph.workflow import movie_assistant_graph
from app.graph.state import AgentGraphState

logger = logging.getLogger("ai_chat")
router = APIRouter(prefix="/api/ai", tags=["AI Multi-Agent Chat"])


class AIChatRequest(BaseModel):
    query: str = Field(..., description="User question or statement")
    movie_id: Optional[str] = Field(None, description="Target movie ID or slug")
    movie_title: Optional[str] = Field(None, description="Target movie title")
    reference_timestamp: Optional[str] = Field(None, description="Optional reference timestamp HH:MM:SS")
    session_id: Optional[str] = Field("default_session", description="Session ID for multi-turn conversations")


class EvidenceItem(BaseModel):
    text: str
    start_timestamp: Optional[str] = None
    end_timestamp: Optional[str] = None
    start_seconds: Optional[float] = None
    end_seconds: Optional[float] = None
    movie_title: Optional[str] = None
    retrieval_strategy: Optional[str] = None


class AIChatResponse(BaseModel):
    answer: str
    intent: str
    agent: str
    movie_id: Optional[str] = None
    evidence: List[Dict[str, Any]] = Field(default_factory=list)
    grounding_status: str
    sources: List[str] = Field(default_factory=list)
    trace_id: str
    confidence_status: Optional[str] = "high"
    limitations: Optional[str] = None
    recommendations: Optional[List[Dict[str, Any]]] = None
    metadata: Optional[Dict[str, Any]] = None


@router.post("/chat", response_model=AIChatResponse)
def ai_chat_endpoint(
    req: AIChatRequest,
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """
    Main LangGraph AI Multi-Agent Chat endpoint.
    Performs deterministic intent routing, subtitle RAG, TMDB metadata retrieval,
    recommendations, and anti-hallucination validation.
    """
    if not req.query or not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    try:
        # Prepare initial graph state
        initial_input = {
            "query": req.query.strip(),
            "selected_movie_id": req.movie_id,
            "selected_movie_title": req.movie_title,
            "session_id": req.session_id or "default_session",
            "user_id": str(current_user.id) if current_user else None
        }

        # Execute compiled LangGraph workflow
        result: Dict[str, Any] = movie_assistant_graph.invoke(initial_input)

        # Build clean evidence objects
        evidence_list = []
        for e in result.get("retrieved_evidence", []):
            evidence_list.append({
                "text": e.get("text", ""),
                "start_timestamp": e.get("start_timestamp"),
                "end_timestamp": e.get("end_timestamp"),
                "start_seconds": e.get("start_seconds"),
                "end_seconds": e.get("end_seconds"),
                "movie_title": e.get("movie_title"),
                "retrieval_strategy": e.get("retrieval_strategy")
            })

        sources_list = result.get("citations", [])
        if not sources_list and evidence_list:
            sources_list = [
                f"{e.get('movie_title', 'Interstellar')} [{e.get('start_timestamp')} --> {e.get('end_timestamp')}]"
                for e in evidence_list[:3]
            ]

        return AIChatResponse(
            answer=result.get("final_answer") or result.get("draft_answer") or "I could not generate an answer.",
            intent=result.get("intent", "GENERAL_MOVIE_QUERY"),
            agent=result.get("agent", "StreamHub Agent"),
            movie_id=result.get("selected_movie_id", req.movie_id),
            evidence=evidence_list,
            grounding_status=result.get("grounding_status", "Not enough evidence"),
            sources=sources_list,
            trace_id=result.get("trace_id", "trace_000"),
            confidence_status=result.get("confidence_status", "medium"),
            limitations=result.get("limitations"),
            recommendations=result.get("recommendation_candidates"),
            metadata=result.get("metadata_fields")
        )

    except Exception as e:
        logger.exception(f"Error in ai_chat_endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))
