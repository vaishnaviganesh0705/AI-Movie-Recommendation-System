import uuid
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class AgentGraphState(BaseModel):
    """
    Strongly typed state for the LangGraph explicit multi-agent movie assistant workflow.
    """
    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    session_id: str = "default_session"
    user_id: Optional[str] = None
    query: str = ""
    conversation_history: List[Dict[str, Any]] = Field(default_factory=list)

    # Movie Context
    selected_movie_id: Optional[str] = None
    selected_movie_title: Optional[str] = None
    use_selected_movie: bool = False

    # Universal Search & Entity Extraction
    extracted_title: Optional[str] = None
    media_type_hint: Optional[str] = None  # movie, tv, unknown
    language_hint: Optional[str] = None
    year_hint: Optional[int] = None
    genre_hint: Optional[str] = None
    min_runtime_minutes: Optional[int] = None
    max_runtime_minutes: Optional[int] = None
    similar_to_title: Optional[str] = None
    similar_to_tmdb_id: Optional[str] = None
    target_person_id: Optional[str] = None
    target_person_name: Optional[str] = None
    requires_tmdb_search: bool = True
    resolved_entity: Optional[Dict[str, Any]] = None
    disambiguation_options: List[Dict[str, Any]] = Field(default_factory=list)
    debug_trace: Dict[str, Any] = Field(default_factory=dict)

    # Intent Classification
    intent: Optional[str] = None  # RECOMMENDATION, MOVIE_METADATA, SUBTITLE_QA, TIMELINE_QA, GENERAL_MOVIE_QUERY, UNSUPPORTED
    intent_confidence: float = 1.0

    # Timestamp & Interval Tracking
    timestamp_start_seconds: Optional[float] = None
    timestamp_end_seconds: Optional[float] = None
    timestamp_reference_seconds: Optional[float] = None

    # Evidence & Candidates
    retrieved_documents: List[Dict[str, Any]] = Field(default_factory=list)
    retrieved_evidence: List[Dict[str, Any]] = Field(default_factory=list)
    recommendation_candidates: List[Dict[str, Any]] = Field(default_factory=list)
    song_candidates: List[Dict[str, Any]] = Field(default_factory=list)
    music_context: Optional[str] = None

    # Generated Output
    draft_answer: Optional[str] = None
    final_answer: Optional[str] = None
    agent: str = "StreamHub Agent"
    confidence_status: str = "medium"  # high, medium, low
    grounding_status: Optional[str] = "Not enough evidence"  # Strong evidence, Limited evidence, Not enough evidence
    citations: List[str] = Field(default_factory=list)
    limitations: Optional[str] = None
    refusal_reason: Optional[str] = None
    error: Optional[str] = None

    # Validation & Execution Flow
    validation_passed: bool = True
    retry_count: int = 0
    max_retries: int = 1
    action: Optional[Dict[str, Any]] = None
    metadata_fields: Dict[str, Any] = Field(default_factory=dict)
