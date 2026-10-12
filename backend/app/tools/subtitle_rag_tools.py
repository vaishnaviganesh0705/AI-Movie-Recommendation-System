import os
import re
from typing import List, Dict, Any, Optional, Tuple
import httpx
from dotenv import load_dotenv
from groq import Groq

from app.services.subtitle_service import (
    get_subtitles_collection,
    parse_timestamp_to_seconds,
    format_seconds_to_timestamp,
    MOVIE_ID_MAPPINGS
)

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Resilient Groq client
_groq_client = None


def get_groq_client() -> Groq:
    global _groq_client
    if _groq_client is None:
        http_client = httpx.Client(verify=False, timeout=30.0)
        _groq_client = Groq(api_key=GROQ_API_KEY, http_client=http_client)
    return _groq_client


def parse_temporal_intent(query: str) -> Optional[Tuple[float, float]]:
    """
    Parses natural language expressions into (start_seconds, end_seconds).
    Examples:
    - 'around 30 minutes' -> (1680.0, 1920.0)
    - 'around 1 hour' / 'at 1 hour' -> (3420.0, 3780.0)
    - 'between 01:20:00 and 01:25:00' -> (4800.0, 5100.0)
    - 'at 01:20:00' -> (4700.0, 4900.0)
    - 'near the beginning' -> (60.0, 600.0)
    - 'near the end' -> (9000.0, 9850.0)
    """
    q = query.lower().strip()

    # 1. Beginning / End
    if any(k in q for k in ["near the beginning", "at the beginning", "in the beginning", "early in the movie", "start of the movie"]):
        return (60.0, 600.0)
    if any(k in q for k in ["near the end", "at the end", "towards the end", "ending of the movie", "final scene", "climax"]):
        return (9000.0, 9850.0)

    # 2. Time range e.g. "between 01:20:00 and 01:25:00"
    range_match = re.search(r'between\s+(\d{1,2}:\d{2}(?::\d{2})?)\s+and\s+(\d{1,2}:\d{2}(?::\d{2})?)', q)
    if range_match:
        t1 = parse_timestamp_to_seconds(range_match.group(1))
        t2 = parse_timestamp_to_seconds(range_match.group(2))
        return (min(t1, t2), max(t1, t2))

    # 3. Specific timestamp e.g. "at 01:20:00" or "around 01:20:00"
    exact_match = re.search(r'(?:at|around|about)\s+(\d{1,2}:\d{2}:\d{2})', q)
    if exact_match:
        sec = parse_timestamp_to_seconds(exact_match.group(1))
        return (max(0.0, sec - 120.0), sec + 120.0)

    # 4. Hours e.g. "around 1 hour", "at one hour", "around 2 hours"
    hours_match = re.search(r'(?:around|at|about|after)\s+(?:(\d+(?:\.\d+)?)|one|two|three)\s+hour', q)
    if hours_match:
        val_str = hours_match.group(1)
        if not val_str:
            if "one" in q:
                val = 1.0
            elif "two" in q:
                val = 2.0
            elif "three" in q:
                val = 3.0
            else:
                val = 1.0
        else:
            val = float(val_str)
        sec = val * 3600.0
        return (max(0.0, sec - 180.0), sec + 180.0)

    # 5. Minutes e.g. "around 30 minutes", "at 45 mins"
    mins_match = re.search(r'(?:around|at|about|after)\s+(\d+)\s*(?:minutes|mins|min)', q)
    if mins_match:
        val = float(mins_match.group(1))
        sec = val * 60.0
        return (max(0.0, sec - 120.0), sec + 120.0)

    return None


def detect_continuity_intent(query: str) -> Optional[str]:
    """
    Detects if the user is asking a chronological follow-up question.
    """
    q = query.lower().strip()
    if any(k in q for k in ["after that", "after this", "what happened next", "what did they say next", "what was said next", "shortly after", "immediately after"]):
        return "AFTER"
    if any(k in q for k in ["before that", "before this", "prior to that", "before they", "what happened before", "what did he say before"]):
        return "BEFORE"
    if any(k in q for k in ["who was talking", "tell me more about that", "what was that conversation about", "more about that"]):
        return "CURRENT"
    return None


def retrieve_subtitle_chunks(
    query: str,
    movie_title: str = "Interstellar",
    state: Optional[Dict[str, Any]] = None,
    limit: int = 5
) -> List[Dict[str, Any]]:
    """
    Retrieves the most relevant subtitle chunks using vector similarity,
    temporal filtering, or chronological continuity.
    """
    collection = get_subtitles_collection()
    state = state or {}

    temporal_window = parse_temporal_intent(query)
    continuity = detect_continuity_intent(query)
    last_chunk_index = state.get("last_subtitle_chunk_index")

    # Case 1: Chronological follow-up ("What happened after that?")
    if continuity and last_chunk_index is not None:
        target_indices = []
        if continuity == "AFTER":
            target_indices = [last_chunk_index + 1, last_chunk_index + 2, last_chunk_index + 3]
        elif continuity == "BEFORE":
            target_indices = [max(0, last_chunk_index - 2), max(0, last_chunk_index - 1)]
        else:
            target_indices = [last_chunk_index, last_chunk_index + 1]

        slug = re.sub(r'[^a-zA-Z0-9_]', '_', movie_title.lower())
        target_ids = [f"{slug}_chunk_{idx:04d}" for idx in target_indices]

        try:
            res = collection.get(ids=target_ids)
            if res and res["ids"]:
                chunks = []
                for i, doc_id in enumerate(res["ids"]):
                    meta = res["metadatas"][i]
                    chunks.append({
                        "id": doc_id,
                        "text": res["documents"][i],
                        "movie_title": meta.get("movie_title"),
                        "start_time": meta.get("start_time"),
                        "end_time": meta.get("end_time"),
                        "start_seconds": meta.get("start_seconds"),
                        "end_seconds": meta.get("end_seconds"),
                        "chunk_index": meta.get("chunk_index")
                    })
                chunks.sort(key=lambda x: x["chunk_index"])
                if chunks:
                    return chunks
        except Exception:
            pass

    # Case 2: Specific time-window query ("around 1 hour", "between 01:20:00 and 01:25:00")
    if temporal_window:
        t_start, t_end = temporal_window
        # Fetch all chunks for movie and filter in python for precision
        movie_docs = collection.get(
            where={"movie_title": movie_title}
        )
        if movie_docs and movie_docs["ids"]:
            matched = []
            for i, doc_id in enumerate(movie_docs["ids"]):
                meta = movie_docs["metadatas"][i]
                c_start = meta.get("start_seconds", 0.0)
                c_end = meta.get("end_seconds", 0.0)
                # Check overlap with temporal window
                if not (c_end < t_start or c_start > t_end):
                    matched.append({
                        "id": doc_id,
                        "text": movie_docs["documents"][i],
                        "movie_title": meta.get("movie_title"),
                        "start_time": meta.get("start_time"),
                        "end_time": meta.get("end_time"),
                        "start_seconds": c_start,
                        "end_seconds": c_end,
                        "chunk_index": meta.get("chunk_index", 0)
                    })
            if matched:
                matched.sort(key=lambda x: x["start_seconds"])
                return matched[:limit]

    # Case 3: Semantic vector similarity search
    results = collection.query(
        query_texts=[query],
        n_results=limit,
        where={"movie_title": movie_title}
    )

    chunks = []
    if results and results["ids"] and results["ids"][0]:
        for i, doc_id in enumerate(results["ids"][0]):
            meta = results["metadatas"][0][i]
            chunks.append({
                "id": doc_id,
                "text": results["documents"][0][i],
                "movie_title": meta.get("movie_title"),
                "start_time": meta.get("start_time"),
                "end_time": meta.get("end_time"),
                "start_seconds": meta.get("start_seconds"),
                "end_seconds": meta.get("end_seconds"),
                "chunk_index": meta.get("chunk_index"),
                "distance": results["distances"][0][i] if "distances" in results and results["distances"] else None
            })

    return chunks


def answer_movie_subtitle_question(
    question: str,
    movie_title: str = "Interstellar",
    state: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Executes real Subtitle RAG:
    1. Retrieves relevant subtitle chunks for the movie.
    2. Builds strictly-grounded prompt with evidence and timestamps.
    3. Calls Groq LLM with strict zero-hallucination instructions.
    4. Returns answer with verified source citations.
    """
    chunks = retrieve_subtitle_chunks(question, movie_title=movie_title, state=state, limit=4)

    if not chunks:
        return {
            "answer": "This information is not available in the provided subtitles.",
            "movie_title": movie_title,
            "sources": [],
            "state_update": {}
        }

    # Format evidence blocks with timestamps
    evidence_blocks = []
    for c in chunks:
        evidence_blocks.append(
            f"[{c['start_time']} --> {c['end_time']}]: {c['text']}"
        )
    evidence_text = "\n\n".join(evidence_blocks)

    system_prompt = f"""You are the StreamHub Movie Subtitle RAG Agent for the movie "{movie_title}".
Answer the user's question using ONLY the retrieved subtitle evidence provided below.

GROUNDING RULES:
1. Base your answer STRICTLY and ONLY on the provided subtitle dialogue.
2. If the user asks about dialogue or events around a timestamp or scene (e.g. "around 1 hour", "at 30 minutes", "near the beginning", "near the end"), summarize the spoken conversations and events that take place in the retrieved timestamped dialogue entries.
3. Do NOT invent visual events or physical details not spoken in the dialogue.
4. There is no video feed. If the user asks about purely visual details (e.g. clothing color, actor appearance, unseen objects) that are NOT spoken in the dialogue, answer: "This information is not available in the provided subtitles."
5. If the retrieved subtitle evidence does NOT contain the answer, answer: "This information is not available in the provided subtitles."
6. Quote or cite the characters who spoke the lines.
"""

    user_prompt = f"""RETRIEVED SUBTITLE EVIDENCE:
{evidence_text}

USER QUESTION: {question}

Please provide a grounded answer based strictly on the dialogue above:"""

    answer = ""
    client = get_groq_client()

    # Primary model: qwen/qwen3.8-27b (fast, precise dialogue extraction)
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            model="qwen/qwen3.8-27b",
            temperature=0.1,
            max_tokens=350
        )
        answer = chat_completion.choices[0].message.content.strip()
    except Exception as e:
        pass

    # Fallback if primary returned empty or errored
    if not answer:
        try:
            chat_completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model="openai/gpt-oss-120b",
                temperature=0.1,
                max_tokens=350
            )
            answer = chat_completion.choices[0].message.content.strip()
        except Exception as e2:
            answer = f"This information is not available in the provided subtitles."

    # Build sources for response
    sources = []
    for c in chunks:
        sources.append({
            "start_time": c.get("start_time"),
            "end_time": c.get("end_time"),
            "start_seconds": c.get("start_seconds"),
            "end_seconds": c.get("end_seconds"),
            "chunk_index": c.get("chunk_index"),
            "text": c.get("text")
        })

    # Prepare conversational state update
    top_chunk = chunks[0] if chunks else {}
    state_update = {
        "last_movie_title": movie_title,
        "last_subtitle_chunk_index": top_chunk.get("chunk_index"),
        "last_subtitle_seconds": top_chunk.get("start_seconds"),
        "last_subtitle_start_time": top_chunk.get("start_time"),
        "last_subtitle_end_time": top_chunk.get("end_time")
    }

    return {
        "answer": answer,
        "movie_title": movie_title,
        "sources": sources,
        "evidence_used": len(chunks),
        "state_update": state_update
    }
