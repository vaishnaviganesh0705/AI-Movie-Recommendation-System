import re
from app.graph.state import AgentGraphState

# Maximum safe query character length
MAX_QUERY_CHARS = 1000

INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior)\s+instructions",
    r"you\s+are\s+now\s+a",
    r"system\s*prompt",
    r"disregard\s+(the\s+)?(rules|above)",
    r"reveal\s+(the\s+)?(secret|token|api\s*key)",
    r"as\s+an\s+unfiltered\s+ai"
]


def input_validation_node(state: AgentGraphState) -> AgentGraphState:
    """
    Validates and sanitizes user input before graph execution.
    - Trims excess whitespace and enforces character bounds.
    - Flags potential prompt injections.
    - Sets safe defaults for movie contexts.
    """
    raw_query = (state.query or "").strip()

    if not raw_query:
        state.error = "Empty query provided."
        state.intent = "UNSUPPORTED"
        state.refusal_reason = "Please ask a question about movies, recommendations, or subtitles."
        return state

    # Length guard
    if len(raw_query) > MAX_QUERY_CHARS:
        raw_query = raw_query[:MAX_QUERY_CHARS]
    state.query = raw_query

    # Injection mitigation
    for pat in INJECTION_PATTERNS:
        if re.search(pat, raw_query, flags=re.IGNORECASE):
            state.intent = "UNSUPPORTED"
            state.refusal_reason = "I cannot process instructions attempting to override system behavior."
            return state

    # If selected_movie_title is passed or inferable
    if not state.selected_movie_title and state.selected_movie_id:
        if str(state.selected_movie_id).lower() in ["interstellar", "157336"]:
            state.selected_movie_title = "Interstellar"
            state.selected_movie_id = "interstellar"

    return state
