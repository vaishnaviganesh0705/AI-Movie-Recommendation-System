from app.graph.state import AgentGraphState
from app.graph.nodes.intent_router import deterministic_intent_classifier, intent_router_node


def test_deterministic_intent_timeline():
    q = "What happens at 01:27:37 in Interstellar?"
    assert deterministic_intent_classifier(q) == "TIMELINE_QA"

    q2 = "What dialogue occurs 5 minutes before 00:45:00?"
    assert deterministic_intent_classifier(q2) == "TIMELINE_QA"


def test_deterministic_intent_metadata():
    assert deterministic_intent_classifier("Who directed Interstellar?") == "MOVIE_METADATA"
    assert deterministic_intent_classifier("What is the runtime of Interstellar?") == "MOVIE_METADATA"
    assert deterministic_intent_classifier("Who acted in Interstellar?") == "MOVIE_METADATA"
    assert deterministic_intent_classifier("When was Interstellar released?") == "MOVIE_METADATA"


def test_deterministic_intent_recommendation():
    assert deterministic_intent_classifier("Recommend sci-fi movies similar to Interstellar") == "RECOMMENDATION"
    assert deterministic_intent_classifier("Suggest movies like Inception") == "RECOMMENDATION"
    assert deterministic_intent_classifier("Find me top rated thriller movies") == "RECOMMENDATION"


def test_deterministic_intent_subtitle_qa():
    assert deterministic_intent_classifier("What did Cooper say to Murph about Murphy's law?") == "SUBTITLE_QA"
    assert deterministic_intent_classifier("What is TARS's honesty setting?") == "SUBTITLE_QA"
    assert deterministic_intent_classifier("Why did Dr. Mann betray the crew?") == "SUBTITLE_QA"


def test_deterministic_intent_unsupported():
    assert deterministic_intent_classifier("Write python code to invert a binary tree") == "UNSUPPORTED"
    assert deterministic_intent_classifier("What is the capital of France?") == "UNSUPPORTED"


def test_intent_router_node_execution():
    state = AgentGraphState(query="Who directed Interstellar?")
    out = intent_router_node(state)
    assert out.intent == "MOVIE_METADATA"
    assert out.intent_confidence >= 0.8
