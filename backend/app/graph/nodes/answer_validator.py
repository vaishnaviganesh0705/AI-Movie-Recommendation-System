import re
from typing import List, Dict, Any
from app.graph.state import AgentGraphState


def answer_validator_node(state: AgentGraphState) -> AgentGraphState:
    """
    Validates generated answer against retrieved evidence and grounding constraints:
    1. Checks for empty answer.
    2. Validates that cited timestamps exist in retrieved chunks.
    3. Detects visual hallucination attempts (e.g. colors, appearance).
    4. Triggers controlled single retry or safe refusal if invalid.
    """
    # Only validate subtitle answers or metadata
    if state.intent not in ["SUBTITLE_QA", "TIMELINE_QA"]:
        state.validation_passed = True
        return state

    answer = state.draft_answer or ""

    # Check 1: Empty answer
    if not answer.strip():
        state.validation_passed = False
        state.final_answer = (
            "Answer:\n"
            "I could not find enough relevant subtitle evidence to answer your question.\n\n"
            "Evidence:\n"
            "- None available\n\n"
            "Grounding status:\n"
            "Not enough evidence"
        )
        return state

    # Check 2: Check for visual hallucination in answer
    # If the user asked for visual info (e.g. shirt color, car color) but the model invented a color
    visual_q_match = re.search(r"what\s+color\b|what\s+was\s+\w+\s+wearing|\bwearing\b|clothing|shoes|sneakers|jacket\s+color|shirt\s+color|paint", state.query.lower())
    if visual_q_match:
        if "not available in the subtitles" not in answer.lower() and "cannot be determined" not in answer.lower() and "not enough evidence" not in answer.lower():
            # Force grounded refusal
            state.validation_passed = True
            state.final_answer = (
                "Answer:\n"
                "This information is not available in the subtitles.\n\n"
                "Evidence:\n"
                "- Subtitles contain spoken dialogue only.\n\n"
                "Grounding status:\n"
                "Not enough evidence\n\n"
                "Limitations:\n"
                "The available source is subtitle text, so visual details such as clothing colors or physical appearances are not recorded."
            )
            state.grounding_status = "Not enough evidence"
            state.limitations = "The available source is subtitle text, so visual details such as clothing colors or physical appearances are not recorded."
            return state
        else:
            state.validation_passed = True
            state.final_answer = answer
            return state

    # Check 3: Check timestamp references
    # Extract timestamps cited in answer
    cited_timestamps = re.findall(r'[0-9]{1,2}:[0-9]{2}:[0-9]{2}', answer)
    evidence_timestamps = []
    for ev in state.retrieved_evidence:
        st = ev.get("start_timestamp", "")
        et = ev.get("end_timestamp", "")
        if st:
            evidence_timestamps.append(st[:8])
        if et:
            evidence_timestamps.append(et[:8])

    # If the model claims strong evidence but cited zero timestamps from evidence
    if "strong evidence" in answer.lower() and cited_timestamps:
        matching = any(ts in evidence_timestamps for ts in cited_timestamps)
        if not matching and len(evidence_timestamps) > 0 and state.retry_count < state.max_retries:
            state.retry_count += 1
            state.validation_passed = False
            # Return for single retry or sanitize
            return state

    # Check 4: Normal completion
    state.validation_passed = True
    state.final_answer = answer
    return state
