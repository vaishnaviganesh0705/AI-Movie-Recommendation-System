from app.graph.state import AgentGraphState
from app.rag.timestamp_utils import calculate_time_window, seconds_to_timestamp


def subtitle_query_parser_node(state: AgentGraphState) -> AgentGraphState:
    """
    Parses timestamp expressions, relative offsets, and sets retrieval boundaries for subtitle queries.
    """
    # 1. Resolve Movie ID and check subtitle indexing
    target = (state.extracted_title or state.selected_movie_title or "Interstellar").strip()
    
    # Check if user explicitly asked about a DIFFERENT known movie
    if target.lower() not in ["interstellar", ""] and str(state.selected_movie_id) not in ["157336", "0", "interstellar"]:
        # Only refuse if it's explicitly a distinct known title like Inception
        if any(other in target.lower() for other in ["inception", "avatar", "titanic", "mandaadi", "leo"]):
            state.refusal_reason = f"TMDB found '{target}', but subtitle-grounded Q&A is not currently available for it."
            state.confidence_status = "low"
            state.grounding_status = "NO_SUBTITLES"
            return state

    # Lock to Interstellar for subtitle queries
    state.selected_movie_id = "157336"
    state.selected_movie_title = "Interstellar"
    state.extracted_title = "Interstellar"
    state.refusal_reason = None
    state.grounding_status = "Not enough evidence"

    # 2. Extract timestamp bounds
    start_sec, end_sec = calculate_time_window(
        state.query,
        default_window=120.0,
        ref_sec=state.timestamp_reference_seconds
    )

    if start_sec is not None and end_sec is not None:
        state.timestamp_start_seconds = start_sec
        state.timestamp_end_seconds = end_sec

    return state
