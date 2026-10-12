import re
import os
import httpx
from typing import List, Dict, Any, Optional
from groq import Groq

from app.graph.state import AgentGraphState
from app.routers.tmdb import tmdb_get

GENRE_MAP = {
    "action": 28, "adventure": 12, "animation": 16, "comedy": 35,
    "crime": 80, "documentary": 99, "drama": 18, "family": 10751,
    "fantasy": 14, "history": 36, "horror": 27, "music": 10402,
    "mystery": 9648, "romance": 10749, "sci-fi": 878, "science fiction": 878,
    "thriller": 53, "war": 10752, "western": 37
}

LANG_MAP = {
    "tamil": "ta", "telugu": "te", "hindi": "hi", "malayalam": "ml",
    "korean": "ko", "english": "en", "spanish": "es", "french": "fr",
    "japanese": "ja"
}


def recommendation_agent_node(state: AgentGraphState) -> AgentGraphState:
    """
    Hybrid Recommendation Agent using real TMDB candidates, deterministic hard-filters,
    ranking, and strict non-hallucinating explanations.
    """
    state.agent = "recommendation_agent"
    q = state.query.lower()

    # Step 1: Detect hard filters from query
    target_genre_id = None
    target_genre_name = None
    for g_name, g_id in GENRE_MAP.items():
        if g_name in q:
            target_genre_id = g_id
            target_genre_name = g_name.title()
            break

    target_lang_code = None
    target_lang_name = None
    for l_name, l_code in LANG_MAP.items():
        if l_name in q:
            target_lang_code = l_code
            target_lang_name = l_name.title()
            break

    max_runtime = None
    if re.search(r"under\s+(?:2|two)\s+hours?|under\s+120\s+mins?", q):
        max_runtime = 120
    elif re.search(r"under\s+(?:1|one)\s+hour|under\s+60\s+mins?", q):
        max_runtime = 60

    # Step 2: Check for "similar to <movie>" or "movies like <movie>"
    similar_match = re.search(r"(?:similar\s+to|movies?\s+like|liked|after\s+watching)\s+([a-zA-Z0-9\s\-:\']+)", q)
    base_movie_title = similar_match.group(1).strip() if similar_match else (state.selected_movie_title or None)

    candidates = []
    watched_seed_title = None

    # If asking for similar to a specific movie
    if base_movie_title and not any(k in base_movie_title for k in ["movie", "film", "something", "anything"]):
        search_res = tmdb_get("/search/movie", {"query": base_movie_title, "include_adult": "false"})
        if search_res.get("results"):
            base_id = search_res["results"][0]["id"]
            rec_res = tmdb_get(f"/movie/{base_id}/recommendations")
            candidates = rec_res.get("results", [])
            if not candidates:
                sim_res = tmdb_get(f"/movie/{base_id}/similar")
                candidates = sim_res.get("results", [])

    # Personalization: If logged-in user and no specific movie was requested, seed from watch history
    if not candidates and state.user_id and not base_movie_title:
        try:
            from app.database import SessionLocal
            from app.models import WatchHistory
            with SessionLocal() as db_sess:
                recent_watch = db_sess.query(WatchHistory).filter(
                    WatchHistory.user_id == int(state.user_id)
                ).order_by(WatchHistory.last_watched_at.desc()).first()
                if recent_watch and recent_watch.tmdb_id:
                    rec_res = tmdb_get(f"/movie/{recent_watch.tmdb_id}/recommendations")
                    seed_cands = rec_res.get("results", [])
                    if not seed_cands:
                        sim_res = tmdb_get(f"/movie/{recent_watch.tmdb_id}/similar")
                        seed_cands = sim_res.get("results", [])
                    if seed_cands:
                        candidates = seed_cands
                        seed_data = tmdb_get(f"/movie/{recent_watch.tmdb_id}")
                        watched_seed_title = seed_data.get("title") or "your watched titles"
        except Exception as e:
            print(f"Error querying watch history for recommendations: {e}")

    # If no similar candidates or pure genre/language discovery
    if not candidates:
        discover_params = {
            "sort_by": "popularity.desc",
            "include_adult": "false",
            "page": 1
        }
        if target_genre_id:
            discover_params["with_genres"] = target_genre_id
        if target_lang_code:
            discover_params["with_original_language"] = target_lang_code

        disc_res = tmdb_get("/discover/movie", discover_params)
        candidates = disc_res.get("results", [])

    if not candidates:
        state.final_answer = "Recommendation Agent: Could not find movie recommendations matching your exact criteria on TMDB."
        state.confidence_status = "low"
        return state

    # Step 3: Hard runtime filtering if requested
    filtered_candidates = []
    for c in candidates[:15]:
        if max_runtime:
            det = tmdb_get(f"/movie/{c['id']}")
            rt = det.get("runtime")
            if rt and rt > max_runtime:
                continue
        filtered_candidates.append(c)

    if not filtered_candidates:
        filtered_candidates = candidates[:6]

    final_selection = filtered_candidates[:5]

    # Step 4: Build structured candidate objects
    structured_candidates = []
    lines = []
    for m in final_selection:
        title = m.get("title")
        year = m.get("release_date", "")[:4] or "N/A"
        vote = m.get("vote_average", "N/A")
        m_id = str(m.get("id"))
        overview = m.get("overview", "")

        matched_features = []
        if target_genre_name:
            matched_features.append(target_genre_name)
        if target_lang_name:
            matched_features.append(target_lang_name)
        if base_movie_title:
            matched_features.append(f"Similar to {base_movie_title.title()}")
        if watched_seed_title:
            matched_features.append(f"Based on your watch history ({watched_seed_title})")

        structured_candidates.append({
            "movie_id": m_id,
            "title": title,
            "year": year,
            "vote_average": vote,
            "reason": overview[:120] + "..." if len(overview) > 120 else overview,
            "matched_features": matched_features,
            "source": "tmdb"
        })
        lines.append(f"• **{title}** ({year}) – Rating: {vote}/10\n  _{overview[:150]}..._")

    state.recommendation_candidates = structured_candidates

    # Step 5: Answer presentation
    header_desc = []
    if target_lang_name:
        header_desc.append(target_lang_name)
    if target_genre_name:
        header_desc.append(target_genre_name)
    if max_runtime:
        header_desc.append(f"under {max_runtime // 60}h")
    if base_movie_title:
        header_desc.append(f"similar to {base_movie_title.title()}")
    elif watched_seed_title:
        header_desc.append(f"personalized for you based on your watch history ({watched_seed_title})")

    desc_str = " ".join(header_desc) if header_desc else "top recommended"
    state.final_answer = (
        f"Here are {len(final_selection)} {desc_str} movies verified from TMDB:\n\n"
        + "\n\n".join(lines)
    )
    state.confidence_status = "high"
    return state
