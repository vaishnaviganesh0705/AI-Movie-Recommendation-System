from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ConversationState(BaseModel):
    content_type: str = "movie"  # "movie" or "tv"
    language: Optional[str] = None  # e.g. "ta", "te", "en", "hi"
    language_name: Optional[str] = None  # e.g. "Tamil", "Telugu"
    genres: List[str] = Field(default_factory=list)  # e.g. ["comedy", "action"]
    genre_ids: List[int] = Field(default_factory=list)  # e.g. [35, 28]
    min_runtime: Optional[int] = None  # in minutes
    max_runtime: Optional[int] = None  # in minutes
    min_rating: Optional[float] = None  # e.g. 8.0
    year: Optional[int] = None  # specific release year e.g. 2024
    year_gte: Optional[int] = None  # release year >= e.g. 2020
    sort_by: str = "popularity.desc"  # "popularity.desc", "vote_average.desc", "primary_release_date.desc"
    
    # State continuity across turns (e.g. for "Who acted in it?", "Add the second movie")
    last_search_query: Optional[str] = None
    last_movie_id: Optional[int] = None
    last_movie_title: Optional[str] = None
    last_results: List[Dict[str, Any]] = Field(default_factory=list)

    # Subtitle RAG continuity across turns
    last_subtitle_chunk_index: Optional[int] = None
    last_subtitle_seconds: Optional[float] = None
    last_subtitle_start_time: Optional[str] = None
    last_subtitle_end_time: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()

    def reset_filters(self):
        self.language = None
        self.language_name = None
        self.genres = []
        self.genre_ids = []
        self.min_runtime = None
        self.max_runtime = None
        self.min_rating = None
        self.year = None
        self.year_gte = None
        self.sort_by = "popularity.desc"


def merge_state(current_state: Optional[ConversationState], incoming_dict: Optional[Dict[str, Any]]) -> ConversationState:
    if not incoming_dict:
        return current_state or ConversationState()
    
    base = (current_state or ConversationState()).to_dict()
    for k, v in incoming_dict.items():
        if v is not None and k in base:
            base[k] = v
    return ConversationState(**base)
