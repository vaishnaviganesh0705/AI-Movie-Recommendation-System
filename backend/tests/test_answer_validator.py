from app.graph.state import AgentGraphState
from app.graph.nodes.answer_validator import answer_validator_node


def test_validator_intercepts_visual_query():
    state = AgentGraphState(
        query="What color shirt was Cooper wearing in the cornfield?",
        intent="SUBTITLE_QA",
        draft_answer="Cooper was wearing a brown jacket and blue shirt.",
        grounding_status="Strong evidence"
    )
    validated = answer_validator_node(state)
    assert validated.grounding_status == "Not enough evidence"
    assert "not available in the subtitles" in validated.final_answer.lower()
    assert "visual details" in validated.limitations.lower()


def test_validator_passes_grounded_answer():
    evidence = [{
        "start_timestamp": "00:05:56,147",
        "end_timestamp": "00:06:16,001",
        "text": "Murphy's Law doesn't mean that something bad will happen."
    }]
    answer_text = (
        "Answer:\nCooper explains that whatever can happen will happen.\n\n"
        "Evidence:\n- [00:05:56,147 --> 00:06:16,001] Murphy's Law doesn't mean that something bad will happen.\n\n"
        "Grounding status:\nStrong evidence\n\nLimitations:\nNone"
    )
    state = AgentGraphState(
        query="What is Murphy's Law according to Cooper?",
        intent="SUBTITLE_QA",
        draft_answer=answer_text,
        grounding_status="Strong evidence",
        retrieved_evidence=evidence
    )
    validated = answer_validator_node(state)
    assert validated.grounding_status == "Strong evidence"
    assert validated.validation_passed is True
    assert "00:05:56,147" in validated.final_answer
