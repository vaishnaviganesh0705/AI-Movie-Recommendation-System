import os
import sys
import json
import time

# Ensure backend directory is in python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from app.graph.workflow import movie_assistant_graph

QUERIES_TO_VERIFY = [
    "Who is Cooper?",
    "Who is Murph?",
    "What did Cooper say about ghosts?",
    "What did Murph say to Cooper?",
    "What happened before Cooper left?",
    "What was said around 00:37:15?",
    "What happened five minutes before 00:42:15?",
    "What happened between 00:37:15 and 00:42:15?",
    "What happened after 00:42:15?",
    "Who was mentioned around 01:10:00?",
    "Summarize the dialogue between 00:37:15 and 00:42:15."
]

def main():
    print("=" * 70)
    print("STREAMHUB SUBTITLE RAG VERIFICATION SUITE")
    print(f"Testing {len(QUERIES_TO_VERIFY)} Required Subtitle Questions")
    print("=" * 70 + "\n")

    results = []

    for idx, query in enumerate(QUERIES_TO_VERIFY, 1):
        print(f"[{idx:02d}/{len(QUERIES_TO_VERIFY)}] Testing: '{query}'")
        t0 = time.time()
        try:
            state_out = movie_assistant_graph.invoke({
                "query": query,
                "selected_movie_id": "157336",
                "selected_movie_title": "Interstellar",
                "session_id": f"verify_{idx}"
            })
            duration_ms = round((time.time() - t0) * 1000, 1)

            intent = state_out.get("intent")
            grounding = state_out.get("grounding_status")
            evidence = state_out.get("retrieved_evidence", [])
            answer = state_out.get("final_answer", "")

            # Check evidence and answer quality
            has_evidence = len(evidence) > 0
            is_refusal_fallback = "I could not find enough relevant subtitle evidence" in answer and grounding == "Not enough evidence"

            print(f"     -> Intent: {intent}")
            print(f"     -> Evidence chunks: {len(evidence)}")
            print(f"     -> Grounding status: {grounding}")
            print(f"     -> Answer snippet:\n{answer[:250]}...\n")

            results.append({
                "query": query,
                "intent": intent,
                "grounding_status": grounding,
                "evidence_count": len(evidence),
                "answer": answer,
                "latency_ms": duration_ms,
                "success": has_evidence and not is_refusal_fallback
            })

        except Exception as e:
            print(f"     -> ERROR: {e}\n")
            results.append({
                "query": query,
                "error": str(e),
                "success": False
            })

    passed_count = sum(1 for r in results if r.get("success"))
    print("=" * 70)
    print(f"VERIFICATION SUMMARY: {passed_count}/{len(QUERIES_TO_VERIFY)} Passed")
    print("=" * 70)

    out_file = os.path.join(current_dir, "verify_user_subtitle_results.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Results written to: {out_file}")

if __name__ == "__main__":
    main()
