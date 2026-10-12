from app.rag.retriever import SubtitleRetriever


def get_retriever():
    return SubtitleRetriever(default_top_k=3)


def test_retriever_semantic_interstellar():
    retriever = get_retriever()
    chunks = retriever.retrieve("What did Brand say about love?", movie_id="157336", top_k=2)
    assert len(chunks) > 0
    assert any("love" in c["text"].lower() for c in chunks)
    assert chunks[0]["start_timestamp"] is not None
    assert chunks[0]["end_timestamp"] is not None


def test_retriever_movie_alias():
    retriever = get_retriever()
    chunks = retriever.retrieve("What did Brand say about love?", movie_id="interstellar", top_k=2)
    assert len(chunks) > 0
    assert any("love" in c["text"].lower() for c in chunks)


def test_retriever_time_window_chronological():
    retriever = get_retriever()
    # Edmunds / Mann conversation at around 01:27:00 (5220s)
    chunks = retriever.retrieve(
        query="What is discussed around 01:27:00?",
        movie_id="157336",
        timestamp_start_seconds=5200.0,
        timestamp_end_seconds=5300.0,
        top_k=4
    )
    assert len(chunks) > 0
    # Verify chronological ordering
    for i in range(len(chunks) - 1):
        assert chunks[i]["start_seconds"] <= chunks[i + 1]["start_seconds"]


def test_retriever_movie_isolation():
    retriever = get_retriever()
    # Non-existent movie must NOT leak Interstellar chunks
    chunks = retriever.retrieve("love transcending space", movie_id="non_existent_movie_99999", top_k=5)
    assert len(chunks) == 0
