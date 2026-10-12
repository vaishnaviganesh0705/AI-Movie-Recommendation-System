from app.graph.state import AgentGraphState


def fallback_agent_node(state: AgentGraphState) -> AgentGraphState:
    """
    Controlled safe fallback for unsupported, out-of-scope, or insufficient-evidence queries.
    Never hallucinates ungrounded facts.
    """
    state.agent = "fallback_agent"
    state.confidence_status = "low"

    if state.refusal_reason:
        state.final_answer = state.refusal_reason
        return state

    if state.intent == "UNSUPPORTED":
        state.final_answer = (
            "I can only answer questions related to movie discovery, TMDB metadata (directors, cast, ratings), "
            "and grounded movie subtitle timelines. I do not have grounded data to answer that general inquiry."
        )
    elif state.intent in ["SUBTITLE_QA", "TIMELINE_QA"]:
        state.final_answer = (
            "Answer:\n"
            "I could not find enough relevant subtitle evidence to answer your question.\n\n"
            "Evidence:\n"
            "- None available\n\n"
            "Grounding status:\n"
            "Not enough evidence\n\n"
            "Limitations:\n"
            "Subtitles contain spoken dialogue only and do not describe visual-only events or unstated actions."
        )
    else:
        state.final_answer = (
            "I'm sorry, I could not find enough grounded movie information to answer that question. "
            "Try asking for movie recommendations by genre, details about a specific director/actor, or spoken scenes in Interstellar."
        )

    return state
