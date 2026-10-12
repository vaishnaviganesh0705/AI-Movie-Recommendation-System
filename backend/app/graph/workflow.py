from typing import Literal
from langgraph.graph import StateGraph, START, END

from app.graph.state import AgentGraphState
from app.graph.nodes.input_validation import input_validation_node
from app.graph.nodes.intent_router import intent_router_node
from app.graph.nodes.title_search_agent import title_search_agent_node
from app.graph.nodes.subtitle_query_parser import subtitle_query_parser_node
from app.graph.nodes.timeline_retriever import timeline_retriever_node
from app.graph.nodes.subtitle_answer_agent import subtitle_answer_agent_node
from app.graph.nodes.recommendation_agent import recommendation_agent_node
from app.graph.nodes.metadata_agent import metadata_agent_node
from app.graph.nodes.discovery_agent import discovery_agent_node
from app.graph.nodes.fallback_agent import fallback_agent_node
from app.graph.nodes.answer_validator import answer_validator_node
from app.graph.nodes.response_formatter import response_formatter_node
from app.graph.nodes.music_agent import music_agent_node


def route_by_intent(state: AgentGraphState) -> Literal[
    "title_search_agent",
    "metadata_agent",
    "discovery_agent",
    "recommendation_agent",
    "music_agent",
    "subtitle_query_parser",
    "fallback_agent"
]:
    """Conditional router function for intent-based branching."""
    intent = state.intent
    if intent in [
        "MUSIC_SEARCH",
        "MUSIC_RECOMMENDATION",
        "MOVIE_MUSIC",
        "COMBINED_MOVIE_MUSIC"
    ]:
        return "music_agent"
    elif intent in [
        "TITLE_SEARCH",
        "MOVIE_SEARCH",
        "TV_SEARCH",
        "MULTI_SEARCH",
        "SIMILAR_TITLES",
        "WATCHLIST_ACTION"
    ]:
        return "title_search_agent"
    elif intent == "FILTERED_DISCOVERY":
        return "discovery_agent"
    elif intent in ["MOVIE_METADATA", "TV_METADATA", "CREDITS_QUERY"]:
        return "metadata_agent"
    elif intent == "RECOMMENDATION":
        return "recommendation_agent"
    elif intent in ["SUBTITLE_QA", "TIMELINE_QA"]:
        return "subtitle_query_parser"
    elif intent == "UNSUPPORTED":
        return "fallback_agent"
    else:
        if state.extracted_title:
            return "title_search_agent"
        return "fallback_agent"


def route_after_validation(state: AgentGraphState) -> Literal[
    "response_formatter",
    "subtitle_answer_agent",
    "fallback_agent"
]:
    """Routes based on validation pass or single retry."""
    if state.validation_passed:
        return "response_formatter"
    if state.retry_count < state.max_retries and state.intent in ["SUBTITLE_QA", "TIMELINE_QA"]:
        return "subtitle_answer_agent"
    return "fallback_agent"


def create_movie_assistant_graph():
    """
    Constructs and compiles the explicit LangGraph StateGraph.
    """
    workflow = StateGraph(AgentGraphState)

    # Add Nodes
    workflow.add_node("input_validation", input_validation_node)
    workflow.add_node("intent_router", intent_router_node)
    workflow.add_node("title_search_agent", title_search_agent_node)
    workflow.add_node("metadata_agent", metadata_agent_node)
    workflow.add_node("discovery_agent", discovery_agent_node)
    workflow.add_node("recommendation_agent", recommendation_agent_node)
    workflow.add_node("music_agent", music_agent_node)
    workflow.add_node("subtitle_query_parser", subtitle_query_parser_node)
    workflow.add_node("timeline_retriever", timeline_retriever_node)
    workflow.add_node("subtitle_answer_agent", subtitle_answer_agent_node)
    workflow.add_node("fallback_agent", fallback_agent_node)
    workflow.add_node("answer_validator", answer_validator_node)
    workflow.add_node("response_formatter", response_formatter_node)

    # Define Transitions
    workflow.add_edge(START, "input_validation")
    workflow.add_edge("input_validation", "intent_router")

    workflow.add_conditional_edges(
        "intent_router",
        route_by_intent,
        {
            "title_search_agent": "title_search_agent",
            "metadata_agent": "metadata_agent",
            "discovery_agent": "discovery_agent",
            "recommendation_agent": "recommendation_agent",
            "music_agent": "music_agent",
            "subtitle_query_parser": "subtitle_query_parser",
            "fallback_agent": "fallback_agent"
        }
    )

    # Subtitle Branch Pipeline
    workflow.add_edge("subtitle_query_parser", "timeline_retriever")
    workflow.add_edge("timeline_retriever", "subtitle_answer_agent")

    # Convergence to Answer Validator
    workflow.add_edge("subtitle_answer_agent", "answer_validator")
    workflow.add_edge("title_search_agent", "answer_validator")
    workflow.add_edge("metadata_agent", "answer_validator")
    workflow.add_edge("discovery_agent", "answer_validator")
    workflow.add_edge("recommendation_agent", "answer_validator")
    workflow.add_edge("music_agent", "answer_validator")
    workflow.add_edge("fallback_agent", "answer_validator")

    # Post-validation routing
    workflow.add_conditional_edges(
        "answer_validator",
        route_after_validation,
        {
            "response_formatter": "response_formatter",
            "subtitle_answer_agent": "subtitle_answer_agent",
            "fallback_agent": "fallback_agent"
        }
    )

    workflow.add_edge("response_formatter", END)

    return workflow.compile()


# Pre-compiled application graph singleton
movie_assistant_graph = create_movie_assistant_graph()
