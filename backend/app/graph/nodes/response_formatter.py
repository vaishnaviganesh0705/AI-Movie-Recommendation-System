from typing import Dict, Any
from app.graph.state import AgentGraphState


def response_formatter_node(state: AgentGraphState) -> AgentGraphState:
    """
    Normalizes and finalizes state output before returning to API controllers.
    Ensures both new API contract and frontend ChatModal backwards-compatibility.
    """
    if not state.final_answer:
        state.final_answer = state.draft_answer or "No response generated."

    # Normalize citations / sources
    if not state.citations and state.retrieved_evidence:
        state.citations = [
            f"subtitle:{state.selected_movie_id}:{ev.get('start_timestamp')}-{ev.get('end_timestamp')}"
            for ev in state.retrieved_evidence
        ]

    return state
