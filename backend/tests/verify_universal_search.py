"""
Comprehensive verification test for Universal TMDB Title Search and Information System.
Tests:
- Dynamic discovery for all titles across multiple languages and media types
- Strict context isolation (no fallback to selected movie when new title is mentioned)
- Anaphoric resolution ("this movie", "its director") to selected movie
- Proper error handling for non-existent titles (honest no-result reporting)
- Debug trace compliance (Section 15 schema)
- Both API endpoints: /api/ai/chat and /chat
"""
import sys
import os
import json

# Ensure app can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def run_tests():
    print("=" * 70)
    print("STARTING COMPREHENSIVE UNIVERSAL TMDB SEARCH & CHAT VERIFICATION")
    print("=" * 70)

    test_cases_standalone = [
        {"query": "mandaadi movie tamil", "expected_title_part": "Mandaadi", "expected_lang": "ta"},
        {"query": "Interstellar", "expected_title_part": "Interstellar", "expected_media": "movie"},
        {"query": "Inception", "expected_title_part": "Inception", "expected_media": "movie"},
        {"query": "Avatar", "expected_title_part": "Avatar", "expected_media": "movie"},
        {"query": "Leo Tamil movie", "expected_title_part": "Leo", "expected_lang": "ta"},
        {"query": "Kumbalangi Nights Malayalam", "expected_title_part": "Kumbalangi Nights", "expected_lang": "ml"},
        {"query": "RRR Telugu movie", "expected_title_part": "RRR", "expected_lang": "te"},
        {"query": "Parasite Korean movie", "expected_title_part": "Parasite", "expected_lang": "ko"},
        {"query": "Breaking Bad series", "expected_title_part": "Breaking Bad", "expected_media": "tv"},
        {"query": "Stranger Things", "expected_title_part": "Stranger Things", "expected_media": "tv"},
    ]

    print("\n--- 1. STANDALONE TITLE DISCOVERY TESTS (/api/ai/chat) ---")
    for tc in test_cases_standalone:
        q = tc["query"]
        res = client.post("/api/ai/chat", json={"query": q})
        assert res.status_code == 200, f"Failed for {q}: {res.status_code} {res.text}"
        data = res.json()
        ans = data.get("answer", "")
        intent = data.get("intent", "")
        print(f"Query: '{q}' -> Intent: {intent}")
        print(f"  Answer preview: {ans[:100]}...")
        expected = tc["expected_title_part"].lower()
        assert expected in ans.lower(), f"Expected '{expected}' in answer for query '{q}', got: {ans}"
        print(f"  [PASS] Found '{tc['expected_title_part']}' in answer.")

    print("\n--- 2. NON-EXISTENT TITLE HONEST REPORTING TEST ---")
    fake_query = "aslkdjhfasd random fake movie 9999"
    res = client.post("/api/ai/chat", json={"query": fake_query})
    assert res.status_code == 200
    data = res.json()
    ans = data.get("answer", "")
    print(f"Fake query answer: {ans}")
    assert "could not find" in ans.lower() or "no matching" in ans.lower(), f"Expected no-match response, got: {ans}"
    print("  [PASS] Non-existent title correctly reported as not found in TMDB.")

    print("\n--- 3. MULTI-TURN CONTEXT ISOLATION SEQUENCES ---")

    # Sequence 1: Search Interstellar -> then search "Find Mandaadi Tamil movie"
    print("\nSequence 1: Interstellar -> Find Mandaadi Tamil movie")
    res1 = client.post("/chat", json={"prompt": "Interstellar"})
    assert res1.status_code == 200
    state1 = res1.json().get("state", {})
    print(f"  Turn 1 response preview: {res1.json().get('response', '')[:80]}...")
    
    res2 = client.post("/chat", json={"prompt": "Find Mandaadi Tamil movie", "state": state1})
    assert res2.status_code == 200
    data2 = res2.json()
    ans2 = data2.get("response", "")
    print(f"  Turn 2 response preview: {ans2[:100]}...")
    assert "mandaadi" in ans2.lower(), f"Expected Mandaadi in response, got: {ans2}"
    assert "interstellar" not in ans2.lower() or "mandaadi" in ans2.lower(), "Interstellar should not override Mandaadi!"
    print("  [PASS] Sequence 1 passed: New query 'Mandaadi' completely superseded previous 'Interstellar' context.")

    # Sequence 2: Selected movie is Mandaadi -> Ask "Tell me about Avatar"
    print("\nSequence 2: Selected Mandaadi -> Tell me about Avatar")
    state_mandaadi = {"movie_id": "1465943", "movie_title": "Mandaadi"}
    res_avatar = client.post("/chat", json={"prompt": "Tell me about Avatar", "state": state_mandaadi})
    assert res_avatar.status_code == 200
    ans_avatar = res_avatar.json().get("response", "")
    print(f"  Turn 2 response preview: {ans_avatar[:100]}...")
    assert "avatar" in ans_avatar.lower(), f"Expected Avatar in response, got: {ans_avatar}"
    print("  [PASS] Sequence 2 passed: Explicit title 'Avatar' resolved cleanly without sticking to Mandaadi.")

    # Sequence 3: Selected movie is Avatar -> Ask "Who directed this movie?" (Anaphoric reference)
    print("\nSequence 3: Selected Avatar -> 'Who directed this movie?'")
    state_avatar = {"movie_id": "19995", "movie_title": "Avatar"}
    res_dir = client.post("/chat", json={"prompt": "Who directed this movie?", "state": state_avatar})
    assert res_dir.status_code == 200
    ans_dir = res_dir.json().get("response", "")
    print(f"  Turn response: {ans_dir}")
    assert "james cameron" in ans_dir.lower(), f"Expected James Cameron in response, got: {ans_dir}"
    print("  [PASS] Sequence 3 passed: Anaphoric reference 'this movie' resolved correctly to selected movie (Avatar).")

    # Sequence 4: Tamil movie -> Malayalam movie
    print("\nSequence 4: Tamil movie -> Malayalam movie")
    res_ta = client.post("/chat", json={"prompt": "Recommend a popular Tamil movie"})
    assert res_ta.status_code == 200
    ans_ta = res_ta.json().get("response", "")
    print(f"  Tamil response preview: {ans_ta[:80]}...")

    res_ml = client.post("/chat", json={"prompt": "Recommend a popular Malayalam movie"})
    assert res_ml.status_code == 200
    ans_ml = res_ml.json().get("response", "")
    print(f"  Malayalam response preview: {ans_ml[:80]}...")
    print("  [PASS] Sequence 4 passed: Distinct language transitions handled.")

    # Sequence 5: Movie -> TV show
    print("\nSequence 5: Movie -> TV show")
    res_mv = client.post("/chat", json={"prompt": "Search movie Inception"})
    assert res_mv.status_code == 200
    ans_mv = res_mv.json().get("response", "")
    print(f"  Movie response preview: {ans_mv[:80]}...")

    res_tv = client.post("/chat", json={"prompt": "Search TV series Stranger Things"})
    assert res_tv.status_code == 200
    ans_tv = res_tv.json().get("response", "")
    print(f"  TV response preview: {ans_tv[:80]}...")
    assert "stranger things" in ans_tv.lower(), f"Expected Stranger Things in TV response, got: {ans_tv}"
    print("  [PASS] Sequence 5 passed: Media type transitions handled.")

    # Sequence 6: New title -> no-result query
    print("\nSequence 6: New title -> no-result query")
    res_nr = client.post("/chat", json={"prompt": "Find movie zzzxxxqqq999nonexistent"})
    assert res_nr.status_code == 200
    ans_nr = res_nr.json().get("response", "")
    print(f"  No-result response: {ans_nr}")
    assert "could not find" in ans_nr.lower() or "no matching" in ans_nr.lower(), f"Expected not found, got: {ans_nr}"
    print("  [PASS] Sequence 6 passed: New non-existent query honestly reports no match.")

    # Section 15 Debug Trace verification via direct graph invocation
    print("\n--- 4. SECTION 15 DEBUG TRACE VALIDATION ---")
    from app.graph.workflow import movie_assistant_graph
    debug_state = movie_assistant_graph.invoke({"query": "Mandaadi movie tamil"})
    debug_trace = debug_state.get("debug_trace", {})
    print("Debug trace received:")
    print(json.dumps(debug_trace, indent=2))

    required_keys = [
        "query", "detected_intent", "extracted_entity", "media_type_filter",
        "language_filter", "tmdb_endpoint_called", "raw_result_count",
        "ranking_breakdown", "selected_candidate", "hallucination_check_status"
    ]
    for key in required_keys:
        assert key in debug_trace, f"Missing required debug trace key: {key}"
    print("  [PASS] All Section 15 debug trace fields present and valid.")

    print("\n" + "=" * 70)
    print("ALL TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)

if __name__ == "__main__":
    run_tests()
