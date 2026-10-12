import os
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.services.subtitle_service import SubtitleService
from app.tools.subtitle_rag_tools import answer_movie_subtitle_question

router = APIRouter(prefix="/subtitles", tags=["Movie Subtitles RAG"])


# =========================================================
# SCHEMAS
# =========================================================

class SubtitleSource(BaseModel):
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    start_seconds: Optional[float] = None
    end_seconds: Optional[float] = None
    chunk_index: Optional[int] = None
    text: Optional[str] = None


class SubtitleQARequest(BaseModel):
    question: str
    movie_title: Optional[str] = "Interstellar"
    movie_id: Optional[int] = 157336
    state: Optional[Dict[str, Any]] = None


class SubtitleQAResponse(BaseModel):
    answer: str
    movie_title: str
    sources: List[SubtitleSource]
    evidence_used: int = 0
    state: Optional[Dict[str, Any]] = None


# =========================================================
# ENDPOINTS
# =========================================================

@router.get("/status")
def get_subtitle_status():
    """Returns indexing status and available subtitle files."""
    return SubtitleService.get_status()


@router.post("/index")
def trigger_index_subtitles():
    """Triggers on-demand discovery and indexing of data/subtitles/."""
    results = SubtitleService.index_all_subtitles()
    return {
        "status": "completed",
        "results": results,
        "chromadb_status": SubtitleService.get_status()
    }


@router.post("/reindex/{movie_id}")
def reindex_movie_subtitles(movie_id: str):
    """Forces re-indexing of subtitles for a specific movie_id."""
    from app.rag.indexer import SubtitleIndexer
    files = SubtitleService.discover_subtitle_files()
    target_file = None
    for f in files:
        if str(f.get("movie_id")) == str(movie_id) or str(movie_id).lower() in f.get("movie_title", "").lower():
            target_file = f
            break
    if not target_file and (str(movie_id) in ["157336", "interstellar", "0"]):
        for f in files:
            if "interstellar" in f.get("filename", "").lower():
                target_file = f
                break
    if not target_file:
        raise HTTPException(status_code=404, detail=f"No subtitle file found for movie_id: {movie_id}")

    res = SubtitleIndexer.index_movie_file(
        file_path=target_file["filepath"],
        movie_id=str(movie_id),
        movie_title=target_file["movie_title"],
        force_reindex=True
    )
    return {
        "status": "reindexed",
        "movie_id": str(movie_id),
        "result": res
    }


@router.post("/qa", response_model=SubtitleQAResponse)
def ask_movie_subtitle(req: SubtitleQARequest):
    """
    Executes real Subtitle RAG for the specified movie:
    - Semantic vector similarity retrieval from ChromaDB
    - Temporal / timestamp search
    - Multi-turn continuity (before/after context)
    - Strictly grounded answer from Groq LLM with source timestamps
    """
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    m_title = req.movie_title or "Interstellar"
    res = answer_movie_subtitle_question(
        question=req.question,
        movie_title=m_title,
        state=req.state
    )

    return SubtitleQAResponse(
        answer=res["answer"],
        movie_title=res["movie_title"],
        sources=res["sources"],
        evidence_used=res.get("evidence_used", len(res["sources"])),
        state=res.get("state_update")
    )
