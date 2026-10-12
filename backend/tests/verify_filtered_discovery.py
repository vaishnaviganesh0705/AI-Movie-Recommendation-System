"""
Comprehensive verification test suite for Filtered Discovery and Runtime Parsing.
Validates:
1. Deterministic runtime expression parsing and boundary assertions.
2. Routing priority between TITLE_SEARCH, METADATA, and FILTERED_DISCOVERY.
3. Live TMDB filtered discovery for runtime and regional languages.
4. Title-plus-filter discovery (e.g. Movies like Interstellar under 2 hours).
5. TV episode-runtime filtered discovery.
6. Context isolation (selected Interstellar does not leak into 1 hr Tamil movies).
7. Full regression suite from verify_universal_search.py (Mandaadi, Avatar, Leo, etc.).
"""
import sys
import os
import json

# Ensure app is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app
from app.services.runtime_parser import (
    parse_runtime_expression,
    satisfies_runtime_filter
)
from app.graph.nodes.intent_router import classify_deterministic_intent
from app.graph.workflow import movie_assistant_graph

client = TestClient(app)


def test_runtime_parser_units():
    print("\n--- 1. RUNTIME PARSER UNIT TESTS ---")

    cases = [
        ("1 hr", (None, 60)),
        ("1 hour", (None, 60)),
        ("90 minutes", (None, 90)),
        ("under 2 hours", (None, 120)),
        ("over 2 hours", (120, None)),
        ("between 90 and 120 minutes", (90, 120)),
        ("1 hr 30 min", (None, 90)),
        ("around 90 minutes", (75, 105))
    ]

    for expr, expected in cases:
        min_r, max_r, _ = parse_runtime_expression(expr)
        assert (min_r, max_r) == expected, f"Failed for '{expr}': expected {expected}, got {(min_r, max_r)}"
        print(f"  [PASS] '{expr}' -> min={min_r}, max={max_r}")

    # Boundary verification checks
    assert satisfies_runtime_filter(60, max_runtime=60) is True, "60 min must be accepted for max 60"
    assert satisfies_runtime_filter(61, max_runtime=60) is False, "61 min must be rejected for max 60"
    assert satisfies_runtime_filter(None, max_runtime=60) is False, "None must be rejected"
    assert satisfies_runtime_filter(89, min_runtime=90, max_runtime=120) is False, "89 min must be rejected for 90-120"
    assert satisfies_runtime_filter(90, min_runtime=90, max_runtime=120) is True, "90 min must be accepted for 90-120"
    assert satisfies_runtime_filter(120, min_runtime=90, max_runtime=120) is True, "120 min must be accepted for 90-120"
    assert satisfies_runtime_filter(121, min_runtime=90, max_runtime=120) is False, "121 min must be rejected for 90-120"
    print("  [PASS] Boundary checks verified (60 accepted, 61 rejected; 89 rejected, 90/120 accepted, 121 rejected).")


def test_routing_priority():
    print("\n--- 2. INTENT ROUTING PRIORITY TESTS ---")

    cases = [
        ("1 hr Tamil movies to watch", "FILTERED_DISCOVERY"),
        ("Tamil movies under 2 hours", "FILTERED_DISCOVERY"),
        ("Find Mandaadi", "TITLE_SEARCH"),
        ("Who directed Mandaadi?", "CREDITS_QUERY"),
        ("Movies like Interstellar under 2 hours", "FILTERED_DISCOVERY"),
        ("1 hour TV shows", "FILTERED_DISCOVERY"),
        ("What did Cooper say about ghosts?", "SUBTITLE_QA"),
        ("Add Avatar to my watchlist", "WATCHLIST_ACTION"),
    ]

    for q, expected_intent in cases:
        res = classify_deterministic_intent(q)
        actual_intent = res["intent"]
        assert actual_intent == expected_intent, f"Routing failed for '{q}': expected {expected_intent}, got {actual_intent}"
        print(f"  [PASS] '{q}' -> {actual_intent}")


def test_live_tmdb_discovery():
    print("\n--- 3. LIVE TMDB FILTERED DISCOVERY TESTS ---")

    # Test A: "1 hr Tamil movies to watch"
    print("Testing: '1 hr Tamil movies to watch'")
    res_ta = client.post("/api/ai/chat", json={"query": "1 hr Tamil movies to watch"})
    assert res_ta.status_code == 200
    data_ta = res_ta.json()
    assert data_ta["intent"] == "FILTERED_DISCOVERY"
    recs_ta = data_ta.get("recommendations", [])
    print(f"  Got {len(recs_ta)} verified Tamil candidates under 60 min.")
    for m in recs_ta:
        assert m.get("original_language") == "ta", f"Expected Tamil ('ta'), got {m.get('original_language')}"
        rt = m.get("runtime_minutes")
        assert rt is not None and rt <= 60, f"Expected runtime <= 60, got {rt}"
        print(f"    - {m.get('title')} ({m.get('release_date', '')[:4]}): {rt} min, lang={m.get('original_language')}")
    print("  [PASS] 1 hr Tamil movies verified (all ta, all <= 60 min).")

    # Test B: "Movies like Interstellar under 2 hours"
    print("\nTesting: 'Movies like Interstellar under 2 hours'")
    res_sim = client.post("/api/ai/chat", json={"query": "Movies like Interstellar under 2 hours"})
    assert res_sim.status_code == 200
    data_sim = res_sim.json()
    assert data_sim["intent"] == "FILTERED_DISCOVERY"
    recs_sim = data_sim.get("recommendations", [])
    print(f"  Got {len(recs_sim)} verified similar candidates under 120 min.")
    for m in recs_sim:
        rt = m.get("runtime_minutes")
        assert rt is not None and rt <= 120, f"Expected runtime <= 120, got {rt}"
        print(f"    - {m.get('title')} ({m.get('release_date', '')[:4]}): {rt} min")
    print("  [PASS] Movies like Interstellar under 2 hours verified.")

    # Test C: "TV shows with episodes under 60 minutes"
    print("\nTesting: 'TV shows with episodes under 60 minutes'")
    res_tv = client.post("/api/ai/chat", json={"query": "TV shows with episodes under 60 minutes"})
    assert res_tv.status_code == 200
    data_tv = res_tv.json()
    assert data_tv["intent"] == "FILTERED_DISCOVERY"
    ans_tv = data_tv.get("answer", "")
    assert "episode runtime" in ans_tv.lower(), "Expected TV episode runtime explanation in response"
    print("  [PASS] TV episode runtime explanation verified.")

    # Test D: Context isolation - Selected Interstellar must NOT leak into "1 hr Tamil movies"
    print("\nTesting: Context isolation with selected Interstellar")
    state_interstellar = {"movie_id": "157336", "movie_title": "Interstellar"}
    res_iso = client.post("/chat", json={"prompt": "1 hr Tamil movies to watch", "state": state_interstellar})
    assert res_iso.status_code == 200
    ans_iso = res_iso.json().get("response", "")
    assert "interstellar" not in ans_iso.lower(), "Interstellar leaked into 1 hr Tamil movies!"
    print("  [PASS] Interstellar context cleanly discarded for new discovery query.")


def test_universal_search_regressions():
    print("\n--- 4. REGRESSION VERIFICATION ACROSS UNIVERSAL TITLES ---")
    standalone_titles = [
        ("mandaadi movie tamil", "Mandaadi"),
        ("Interstellar", "Interstellar"),
        ("Inception", "Inception"),
        ("Avatar", "Avatar"),
        ("Leo Tamil movie", "Leo"),
        ("Kumbalangi Nights Malayalam", "Kumbalangi Nights"),
        ("RRR Telugu movie", "RRR"),
        ("Parasite Korean movie", "Parasite"),
        ("Breaking Bad series", "Breaking Bad"),
        ("Stranger Things", "Stranger Things"),
    ]

    for q, exp in standalone_titles:
        res = client.post("/api/ai/chat", json={"query": q})
        assert res.status_code == 200
        ans = res.json().get("answer", "")
        assert exp.lower() in ans.lower(), f"Failed regression for '{q}': expected '{exp}' in answer"
        print(f"  [PASS] Regression: '{q}' resolved to '{exp}'")

    # Non-existent query test
    res_fake = client.post("/api/ai/chat", json={"query": "aslkdjhfasd random fake movie 9999"})
    assert res_fake.status_code == 200
    ans_fake = res_fake.json().get("answer", "")
    assert "could not find" in ans_fake.lower() or "no matching" in ans_fake.lower()
    print("  [PASS] Regression: Non-existent title honestly reported.")

    # Sequence: Avatar selected -> Who directed this movie?
    res_dir = client.post("/chat", json={"prompt": "Who directed this movie?", "state": {"movie_id": "19995", "movie_title": "Avatar"}})
    assert res_dir.status_code == 200
    assert "james cameron" in res_dir.json().get("response", "").lower()
    print("  [PASS] Regression: Anaphoric query resolved to James Cameron for Avatar.")


def run_all():
    print("=" * 70)
    print("RUNNING EXTENDED FILTERED DISCOVERY & RUNTIME VERIFICATION SUITE")
    print("=" * 70)
    test_runtime_parser_units()
    test_routing_priority()
    test_live_tmdb_discovery()
    test_universal_search_regressions()
    print("\n" + "=" * 70)
    print("ALL FILTERED DISCOVERY & UNIVERSAL SEARCH TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    run_all()
