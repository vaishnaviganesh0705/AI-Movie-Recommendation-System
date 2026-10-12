from app.graph.state import AgentGraphState
from app.rag.retriever import SubtitleRetriever

retriever_instance = SubtitleRetriever(default_top_k=5)


def timeline_retriever_node(state: AgentGraphState) -> AgentGraphState:
    """
    Executes movie-isolated subtitle chunk retrieval based on semantic query or timestamp intervals.
    """
    movie_id = state.selected_movie_id or "interstellar"

    # Execute retrieval
    chunks = retriever_instance.retrieve(
        query=state.query,
        movie_id=movie_id,
        timestamp_start_seconds=state.timestamp_start_seconds,
        timestamp_end_seconds=state.timestamp_end_seconds,
        reference_seconds=state.timestamp_reference_seconds,
        top_k=7
    )

    state.retrieved_documents = chunks

    # Build formatted evidence items
    evidence = []
    citations = []
    for c in chunks:
        ev_item = {
            "start_timestamp": c.get("start_timestamp"),
            "end_timestamp": c.get("end_timestamp"),
            "start_seconds": c.get("start_seconds"),
            "end_seconds": c.get("end_seconds"),
            "text": c.get("text"),
            "speakers": c.get("speakers"),
            "chunk_index": c.get("chunk_index")
        }
        evidence.append(ev_item)
        citations.append(f"[{c.get('start_timestamp')}–{c.get('end_timestamp')}]")

    state.retrieved_evidence = evidence
    state.citations = citations
    return state
