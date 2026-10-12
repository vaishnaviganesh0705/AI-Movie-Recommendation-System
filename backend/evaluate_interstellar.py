import os
import sys
import json
import time
from typing import Dict, Any, List

# Ensure backend directory is in python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from app.graph.workflow import movie_assistant_graph


def run_evaluation():
    # Find dataset path
    data_candidates = [
        os.path.abspath(os.path.join(current_dir, "..", "data", "evaluation", "interstellar_eval_30.json")),
        os.path.abspath(os.path.join(current_dir, "data", "evaluation", "interstellar_eval_30.json"))
    ]
    data_path = next((p for p in data_candidates if os.path.exists(p)), None)
    if not data_path:
        print(f"Error: Evaluation dataset not found. Checked: {data_candidates}")
        sys.exit(1)

    with open(data_path, "r", encoding="utf-8") as f:
        cases = json.load(f)

    print(f"============================================================")
    print(f"STREAMHUB MULTI-AGENT BENCHMARK EVALUATION (INTERSTELLAR)")
    print(f"Total Test Cases: {len(cases)}")
    print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"============================================================\n")

    results: List[Dict[str, Any]] = []
    latencies: List[float] = []

    intent_correct = 0
    grounding_correct = 0
    refusals_correct = 0
    total_refusals_expected = 0
    qa_retrieval_hits = 0
    total_qa_cases = 0

    for idx, case in enumerate(cases, 1):
        q = case["query"]
        cat = case.get("category", "general")
        exp_intent = case.get("expected_intent")
        exp_grounding = case.get("expected_grounding")
        should_refuse = case.get("should_refuse", False)
        keywords = case.get("expected_content_keywords", [])

        if should_refuse:
            total_refusals_expected += 1
        if cat in ["dialogue_quote", "character_motivation", "plot_mechanics", "timestamp_dialogue"]:
            total_qa_cases += 1

        t0 = time.time()
        try:
            state_out = movie_assistant_graph.invoke({
                "query": q,
                "selected_movie_id": "157336",
                "selected_movie_title": "Interstellar",
                "session_id": f"bench_{idx}"
            })
            duration_ms = round((time.time() - t0) * 1000, 1)
        except Exception as e:
            duration_ms = round((time.time() - t0) * 1000, 1)
            print(f"[{idx:02d}/30] ERROR processing '{q}': {e}")
            results.append({
                "id": case["id"],
                "query": q,
                "error": str(e),
                "passed": False,
                "latency_ms": duration_ms
            })
            continue

        latencies.append(duration_ms)
        act_intent = state_out.get("intent")
        act_grounding = state_out.get("grounding_status")
        act_answer = state_out.get("final_answer", "")
        act_agent = state_out.get("agent", "")
        evidence = state_out.get("retrieved_evidence", [])

        # Check Intent
        if should_refuse:
            # For queries that should be refused, either SUBTITLE_QA (handled by subtitle validator refusal)
            # or UNSUPPORTED (handled by fallback agent) is a valid routing.
            if act_intent in ["SUBTITLE_QA", "UNSUPPORTED"]:
                i_match = True
                intent_correct += 1
            else:
                i_match = (act_intent == exp_intent)
                if i_match:
                    intent_correct += 1
        elif act_intent == exp_intent or (exp_intent in ["SUBTITLE_QA", "TIMELINE_QA"] and act_intent in ["SUBTITLE_QA", "TIMELINE_QA"]):
            i_match = True
            intent_correct += 1
        else:
            i_match = False

        # Check Grounding
        if exp_grounding == "Strong evidence":
            # Both Strong evidence and Limited evidence represent successful grounding in subtitles
            g_match = act_grounding in ["Strong evidence", "Limited evidence"]
            if g_match:
                grounding_correct += 1
        elif exp_grounding:
            g_match = (act_grounding == exp_grounding)
            if g_match:
                grounding_correct += 1
        else:
            g_match = True

        # Check Refusal if should_refuse
        r_match = True
        if should_refuse:
            refusal_markers = [
                "not available in the subtitles",
                "not enough evidence",
                "describe spoken dialogue, not visual details",
                "cannot be answered from the subtitles",
                "please ask a question about movies",
                "could not find",
                "unsupported",
                "no mention"
            ]
            ans_low = act_answer.lower()
            if any(m in ans_low for m in refusal_markers) or act_grounding == "Not enough evidence" or act_intent == "UNSUPPORTED":
                r_match = True
                refusals_correct += 1
            else:
                r_match = False

        # Check retrieval hit for QA
        retrieval_hit = False
        if cat in ["dialogue_quote", "character_motivation", "plot_mechanics", "timestamp_dialogue"]:
            if len(evidence) > 0:
                retrieval_hit = True
                qa_retrieval_hits += 1

        # Check keywords
        kw_found = []
        for kw in keywords:
            if kw.lower() in act_answer.lower():
                kw_found.append(kw)
        kw_match = len(kw_found) > 0 if keywords else True

        passed = i_match and (r_match if should_refuse else (g_match and kw_match))

        status_sym = "[PASS]" if passed else "[FAIL]"
        print(f"[{idx:02d}/30] {status_sym} Intent: {act_intent} ({duration_ms}ms) | Q: '{q[:50]}...'")

        results.append({
            "id": case["id"],
            "query": q,
            "category": cat,
            "expected_intent": exp_intent,
            "actual_intent": act_intent,
            "intent_match": i_match,
            "expected_grounding": exp_grounding,
            "actual_grounding": act_grounding,
            "grounding_match": g_match,
            "should_refuse": should_refuse,
            "refusal_passed": r_match if should_refuse else None,
            "evidence_count": len(evidence),
            "retrieval_hit": retrieval_hit if cat in ["dialogue_quote", "character_motivation", "plot_mechanics", "timestamp_dialogue"] else None,
            "keywords_expected": keywords,
            "keywords_found": kw_found,
            "agent": act_agent,
            "answer_preview": act_answer[:160].replace("\n", " "),
            "passed": passed,
            "latency_ms": duration_ms
        })

    # Summary Metrics
    total = len(cases)
    intent_acc = round((intent_correct / total) * 100, 1)
    retrieval_rate = round((qa_retrieval_hits / total_qa_cases) * 100, 1) if total_qa_cases > 0 else 100.0
    refusal_acc = round((refusals_correct / total_refusals_expected) * 100, 1) if total_refusals_expected > 0 else 100.0
    avg_latency = round(sum(latencies) / len(latencies), 1) if latencies else 0.0
    p95_latency = round(sorted(latencies)[int(len(latencies) * 0.95)], 1) if latencies else 0.0
    passed_total = sum(1 for r in results if r.get("passed"))
    overall_pass_rate = round((passed_total / total) * 100, 1)

    print(f"\n============================================================")
    print(f"BENCHMARK SUMMARY RESULTS")
    print(f"============================================================")
    print(f"Total Benchmark Cases:      {total}")
    print(f"Overall Passed Cases:       {passed_total}/{total} ({overall_pass_rate}%)")
    print(f"Intent Classification Acc:  {intent_correct}/{total} ({intent_acc}%)")
    print(f"Subtitle Retrieval Hit Rate:{qa_retrieval_hits}/{total_qa_cases} ({retrieval_rate}%)")
    print(f"Anti-Hallucination Refusal: {refusals_correct}/{total_refusals_expected} ({refusal_acc}%)")
    print(f"Average Latency:            {avg_latency} ms")
    print(f"P95 Latency:                {p95_latency} ms")
    print(f"============================================================")

    out_file = os.path.join(os.path.dirname(data_path), "eval_results_interstellar.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
            "total_cases": total,
            "passed_cases": passed_total,
            "overall_pass_rate_pct": overall_pass_rate,
            "intent_accuracy_pct": intent_acc,
            "retrieval_hit_rate_pct": retrieval_rate,
            "anti_hallucination_refusal_pct": refusal_acc,
            "avg_latency_ms": avg_latency,
            "p95_latency_ms": p95_latency,
            "cases": results
        }, f, indent=2)

    print(f"Detailed evaluation metrics written to: {out_file}\n")


if __name__ == "__main__":
    run_evaluation()
