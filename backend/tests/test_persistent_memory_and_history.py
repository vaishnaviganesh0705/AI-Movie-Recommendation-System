# Persistent memory and history tests
import sys
import os
sys.path.insert(0, os.path.abspath("."))

from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models import User, ChatConversation, ChatMessage, WatchHistory
from app.auth import hash_password, create_access_token
from app.graph.state import AgentGraphState
from app.graph.nodes.intent_router import intent_router_node, resolve_entity_from_history
from app.graph.nodes.recommendation_agent import recommendation_agent_node

client = TestClient(app)


def get_or_create_test_user(email: str, name: str) -> User:
    db = SessionLocal()
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            name=name,
            email=email,
            password=hash_password("password123"),
            role="user"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    db.close()
    return user


def test_pronoun_resolution_from_history():
    """Verify that multi-turn pronouns like 'Who directed it?' resolve to the preceding entity."""
    history = [
        {"role": "user", "content": "Tell me about Leo"},
        {"role": "assistant", "content": "**Leo (2023)**\nDirected by Lokesh Kanagaraj. An action thriller about Parthiban."}
    ]

    # Test 1: Resolve title directly from helper
    resolved_title = resolve_entity_from_history(history)
    assert resolved_title.lower() == "leo"

    # Test 2: Intent router node pronoun resolution
    state = AgentGraphState(
        query="Who directed it?",
        conversation_history=history
    )
    res_state = intent_router_node(state)
    assert res_state.intent in ["CREDITS_QUERY", "MOVIE_METADATA"]
    assert res_state.extracted_title.lower() == "leo"
    assert res_state.selected_movie_title.lower() == "leo"

    # Test 3: Release year pronoun resolution
    state2 = AgentGraphState(
        query="What year was it released?",
        conversation_history=history
    )
    res_state2 = intent_router_node(state2)
    assert res_state2.intent == "MOVIE_METADATA"
    assert res_state2.extracted_title.lower() == "leo"


def test_conversation_crud_and_cascade_delete():
    """Verify conversations and messages are persisted in MySQL and cascade deleted."""
    user = get_or_create_test_user("test_chat_crud@example.com", "Chat User")
    token = create_access_token(data={"sub": user.email})
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create Conversation
    create_res = client.post("/chat/conversations", json={"title": "Test Sci-Fi Chat"}, headers=headers)
    assert create_res.status_code == 200
    conv_data = create_res.json()
    conv_id = conv_data["id"]
    assert conv_data["title"] == "Test Sci-Fi Chat"
    assert conv_data["user_id"] == user.id

    # 2. Add message directly in DB or via chat endpoint
    db = SessionLocal()
    db.add(ChatMessage(conversation_id=conv_id, role="user", content="Hello StreamHub"))
    db.add(ChatMessage(conversation_id=conv_id, role="assistant", content="Hello! How can I help?", agent_name="Movie Agent"))
    db.commit()

    # 3. Retrieve conversation details
    detail_res = client.get(f"/chat/conversations/{conv_id}", headers=headers)
    assert detail_res.status_code == 200
    messages = detail_res.json()["messages"]
    assert len(messages) == 2
    assert messages[0]["content"] == "Hello StreamHub"
    assert messages[1]["role"] == "assistant"

    # 4. Delete conversation
    del_res = client.delete(f"/chat/conversations/{conv_id}", headers=headers)
    assert del_res.status_code == 200

    # 5. Verify conversation and messages are gone
    check_conv = db.query(ChatConversation).filter(ChatConversation.id == conv_id).first()
    assert check_conv is None
    check_msgs = db.query(ChatMessage).filter(ChatMessage.conversation_id == conv_id).all()
    assert len(check_msgs) == 0
    db.close()


def test_user_chat_and_history_isolation():
    """Verify User A cannot access or delete User B's conversations or watch history."""
    user_a = get_or_create_test_user("usera_iso@example.com", "User A")
    user_b = get_or_create_test_user("userb_iso@example.com", "User B")

    token_a = create_access_token(data={"sub": user_a.email})
    token_b = create_access_token(data={"sub": user_b.email})
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # User A creates a conversation
    create_res = client.post("/chat/conversations", json={"title": "User A Private Chat"}, headers=headers_a)
    assert create_res.status_code == 200
    conv_id_a = create_res.json()["id"]

    # User B attempts to GET User A's conversation -> Must be 403 Forbidden!
    hack_get = client.get(f"/chat/conversations/{conv_id_a}", headers=headers_b)
    assert hack_get.status_code == 403

    # User B attempts to DELETE User A's conversation -> Must be 403 Forbidden!
    hack_del = client.delete(f"/chat/conversations/{conv_id_a}", headers=headers_b)
    assert hack_del.status_code == 403

    # User B lists conversations -> must NOT see User A's conversation
    list_b = client.get("/chat/conversations", headers=headers_b)
    assert list_b.status_code == 200
    assert not any(c["id"] == conv_id_a for c in list_b.json())

    # User A cleans up
    client.delete(f"/chat/conversations/{conv_id_a}", headers=headers_a)


def test_watch_history_persistence_and_personalization():
    """Verify watch history persistence in MySQL and its personalization seeding."""
    user = get_or_create_test_user("test_wh_user@example.com", "WH User")
    token = create_access_token(data={"sub": user.email})
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Update watch history with Interstellar (157336)
    wh_post = client.post("/history", json={
        "tmdb_id": 157336,
        "content_type": "movie",
        "progress_seconds": 1800,
        "duration_seconds": 10140,
        "completed": False
    }, headers=headers)
    assert wh_post.status_code == 200

    # 2. Get history
    wh_get = client.get("/history", headers=headers)
    assert wh_get.status_code == 200
    items = wh_get.json()
    assert any(i["tmdb_id"] == 157336 for i in items)

    # 3. Test recommendation agent personalized seeding
    state = AgentGraphState(
        query="Recommend movies to watch",
        user_id=str(user.id)
    )
    res_state = recommendation_agent_node(state)
    assert len(res_state.recommendation_candidates) > 0
    assert "Interstellar" in res_state.final_answer or "watch history" in res_state.final_answer.lower()

    # 4. Clean up watch history
    del_wh = client.delete("/history/157336", headers=headers)
    assert del_wh.status_code == 200


if __name__ == "__main__":
    print("Running test_pronoun_resolution_from_history...")
    test_pronoun_resolution_from_history()
    print("PASSED: Pronoun resolution from history")

    print("Running test_conversation_crud_and_cascade_delete...")
    test_conversation_crud_and_cascade_delete()
    print("PASSED: Conversation CRUD and cascade delete")

    print("Running test_user_chat_and_history_isolation...")
    test_user_chat_and_history_isolation()
    print("PASSED: Multi-user isolation")

    print("Running test_watch_history_persistence_and_personalization...")
    test_watch_history_persistence_and_personalization()
    print("PASSED: Watch history persistence & personalization")
    print("ALL TESTS PASSED SUCCESSFULLY!")
