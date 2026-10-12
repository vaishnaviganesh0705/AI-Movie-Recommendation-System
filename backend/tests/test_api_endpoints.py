from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_api_ai_chat_validation_error():
    res = client.post("/api/ai/chat", json={"query": ""})
    assert res.status_code == 400


def test_api_ai_chat_subtitle_qa():
    payload = {
        "query": "What is Murphy's Law according to Cooper in Interstellar?",
        "movie_id": "157336",
        "movie_title": "Interstellar"
    }
    res = client.post("/api/ai/chat", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "answer" in data
    assert data["intent"] in ["SUBTITLE_QA", "TIMELINE_QA"]
    assert "agent" in data
    assert "evidence" in data
    assert data["grounding_status"] in ["Strong evidence", "Limited evidence"]
    assert "trace_id" in data
    assert len(data["evidence"]) > 0


def test_api_ai_chat_metadata():
    payload = {
        "query": "Who directed Interstellar and what is its runtime?",
        "movie_id": "157336"
    }
    res = client.post("/api/ai/chat", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["intent"] == "MOVIE_METADATA"
    assert "Christopher Nolan" in data["answer"]
    assert "169" in data["answer"]


def test_api_ai_chat_recommendations():
    payload = {
        "query": "Recommend sci-fi movies similar to Interstellar",
        "movie_id": "157336"
    }
    res = client.post("/api/ai/chat", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["intent"] == "RECOMMENDATION"
    assert data["recommendations"] is not None
    assert len(data["recommendations"]) > 0


def test_legacy_chat_endpoint_compatibility():
    payload = {
        "prompt": "Recommend sci-fi movies similar to Interstellar"
    }
    res = client.post("/chat", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "response" in data
    assert "agent" in data
    assert "type" in data
    assert data["type"] == "movie_results"
    assert len(data.get("results", [])) > 0


def test_subtitles_qa_endpoint():
    payload = {
        "question": "What did Amelia Brand say about love?",
        "movie_title": "Interstellar",
        "movie_id": 157336
    }
    res = client.post("/subtitles/qa", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "answer" in data
    assert "sources" in data
    assert len(data["sources"]) > 0
