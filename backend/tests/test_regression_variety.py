from app.graph.workflow import movie_assistant_graph


def test_ten_diverse_questions_non_repetitive():
    """
    Verifies that the agent does NOT return canned or repetitive answers
    across 10 diverse questions covering quotes, plot, science, metadata,
    recommendations, visual negatives, and unsupported requests.
    """
    questions = [
        "What is Murphy's Law according to Cooper?",
        "What did Brand say about love transcending dimensions?",
        "What is TARS's honesty setting?",
        "What poem does Professor Brand recite before the launch?",
        "How long did Romilly wait on the Endurance?",
        "Who directed Interstellar?",
        "What is the runtime of Interstellar?",
        "Recommend sci-fi movies similar to Interstellar",
        "What color shirt was Cooper wearing while driving the truck?",
        "Write python code to invert a binary tree"
    ]

    answers = []
    intents = []
    agents = []

    for q in questions:
        state_out = movie_assistant_graph.invoke({
            "query": q,
            "selected_movie_id": "157336",
            "selected_movie_title": "Interstellar"
        })
        ans = state_out.get("final_answer", "").strip()
        intent = state_out.get("intent")
        agent = state_out.get("agent")

        assert len(ans) > 10, f"Answer too short for query: {q}"
        answers.append(ans)
        intents.append(intent)
        agents.append(agent)

    # 1. Assert all 10 answers are distinct (no repetitive / canned responses)
    unique_answers = set(answers)
    assert len(unique_answers) == len(questions), (
        f"Detected repetitive answers! Found {len(unique_answers)} unique answers out of {len(questions)} queries."
    )

    # 2. Assert multi-agent routing occurred
    unique_intents = set(intents)
    assert len(unique_intents) >= 4, f"Expected at least 4 distinct intents, got: {unique_intents}"

    unique_agents = set(agents)
    assert len(unique_agents) >= 3, f"Expected at least 3 distinct agents, got: {unique_agents}"
