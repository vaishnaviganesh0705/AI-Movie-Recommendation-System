import json
from typing import Dict, Any, List, Optional
from app.graph.state import AgentGraphState
from app.services.entity_resolver import resolve_tmdb_entity
from app.services.tmdb_service import (
    get_movie_similar,
    get_movie_recommendations,
    get_tv_similar,
    get_tv_recommendations,
    LANGUAGE_CODES
)


def format_disambiguation_text(title: str, candidates: List[Dict[str, Any]]) -> str:
    """Formats disambiguation list matching Section 5 requirements."""
    lines = [f"I found multiple TMDB results for \"{title}\":\n"]
    for idx, c in enumerate(candidates[:5], 1):
        m_type = "Movie" if c.get("media_type") == "movie" else "TV Series"
        yr = c.get("year", "N/A")
        lang = c.get("language", "EN")
        t_name = c.get("title") or "Unknown"
        lines.append(f"{idx}. **{t_name}** ({yr}) — {m_type} — {lang}")
    lines.append("\nPlease choose the title you mean.")
    return "\n".join(lines)


def title_search_agent_node(state: AgentGraphState) -> AgentGraphState:
    """
    Universal TMDB search and information agent.
    Dynamically searches, ranks, and resolves any movie or TV title present on TMDB.
    Never uses hardcoded titles or stale selected movie fallbacks.
    """
    state.agent = "title_search_agent"

    # Strict Context Isolation:
    # Use selected movie ONLY if use_selected_movie is True. Otherwise, use extracted title or raw query.
    if state.use_selected_movie and state.selected_movie_id:
        target_id = str(state.selected_movie_id)
        from app.services.tmdb_service import get_movie_details, get_movie_credits, get_tv_details, get_tv_credits
        m_details = get_movie_details(target_id)
        if m_details and "id" in m_details:
            resolution = {
                "status": "verified",
                "media_type": "movie",
                "tmdb_id": target_id,
                "title": m_details.get("title") or state.selected_movie_title or "Selected Movie",
                "details": m_details,
                "credits": get_movie_credits(target_id),
                "resolution_confidence": 1.0,
                "candidates": [m_details],
                "ranking_breakdown": [{"id": target_id, "title": m_details.get("title"), "score": 1.0}]
            }
        else:
            t_details = get_tv_details(target_id)
            resolution = {
                "status": "verified" if t_details else "not_found",
                "media_type": "tv",
                "tmdb_id": target_id,
                "title": t_details.get("name") if t_details else (state.selected_movie_title or "Selected Title"),
                "details": t_details or {},
                "credits": get_tv_credits(target_id) if t_details else {},
                "resolution_confidence": 1.0 if t_details else 0.0,
                "candidates": [t_details] if t_details else [],
                "ranking_breakdown": [{"id": target_id, "title": t_details.get("name") if t_details else "", "score": 1.0}]
            }
    else:
        target_title = state.extracted_title if state.extracted_title else state.query
        resolution = resolve_tmdb_entity(
            query_title=target_title,
            media_type_hint=state.media_type_hint if state.media_type_hint != "unknown" else None,
            language_hint=state.language_hint,
            year_hint=state.year_hint
        )

    state.resolved_entity = resolution
    status = resolution.get("status")

    # Build Section 15 Debug Trace
    endpoint_called = f"/search/{state.media_type_hint if state.media_type_hint in ['movie', 'tv'] else 'multi'}"
    trace_obj = {
        "trace_id": state.trace_id,
        "query": state.query,
        "raw_query": state.query,
        "detected_intent": state.intent,
        "intent": state.intent,
        "extracted_entity": state.extracted_title,
        "extracted_title": state.extracted_title,
        "media_type_filter": state.media_type_hint or "unknown",
        "media_type": state.media_type_hint or "unknown",
        "language_filter": state.language_hint,
        "language_hint": state.language_hint,
        "use_selected_movie": state.use_selected_movie,
        "tmdb_endpoint_called": endpoint_called,
        "tmdb_endpoint": endpoint_called,
        "tmdb_query": target_title if 'target_title' in locals() else (state.selected_movie_title or state.query),
        "raw_result_count": len(resolution.get("candidates", [])),
        "result_count": len(resolution.get("candidates", [])),
        "resolved_tmdb_id": str(resolution.get("tmdb_id") or "none"),
        "ranking_breakdown": resolution.get("ranking_breakdown", []),
        "selected_candidate": {
            "id": resolution.get("tmdb_id"),
            "title": resolution.get("title"),
            "media_type": resolution.get("media_type")
        } if resolution.get("tmdb_id") else None,
        "resolution_status": status,
        "hallucination_check_status": "TMDB_VERIFIED" if status == "verified" else ("NO_RESULT" if status == "not_found" else "AMBIGUOUS"),
        "grounding_status": "TMDB_VERIFIED" if status == "verified" else ("NO_RESULT" if status == "not_found" else "AMBIGUOUS")
    }
    state.debug_trace = trace_obj
    print("[DEBUG_TRACE]", json.dumps(trace_obj))

    # Case 1: No Result
    if status == "not_found":
        state.final_answer = f"I could not find a matching movie or TV show in TMDB for \"{target_title}\"."
        state.confidence_status = "low"
        state.grounding_status = "NO_RESULT"
        return state

    # Case 2: Ambiguous Results
    if status == "ambiguous":
        state.disambiguation_options = resolution.get("candidates", [])
        state.final_answer = format_disambiguation_text(target_title, state.disambiguation_options)
        state.confidence_status = "medium"
        state.grounding_status = "TMDB_VERIFIED"

        # Provide cards for ambiguous results so the user can see them
        cards = []
        for c in resolution.get("candidates", [])[:4]:
            cards.append({
                "id": c.get("tmdb_id"),
                "title": c.get("title"),
                "media_type": c.get("media_type", "movie"),
                "release_date": c.get("year", ""),
                "overview": c.get("overview", "")
            })
        state.recommendation_candidates = cards
        return state

    # Case 3: Verified Single Title Match
    details = resolution.get("details", {})
    tmdb_id = resolution.get("tmdb_id")
    media_type = resolution.get("media_type", "movie")
    title = resolution.get("title")
    orig_title = resolution.get("original_title") or title
    rel_date = resolution.get("release_date", "")
    year_str = rel_date[:4] if rel_date and len(rel_date) >= 4 else "N/A"
    orig_lang = resolution.get("original_language", "en")
    
    # Reverse lookup language code to readable name
    lang_name = next((k.capitalize() for k, v in LANGUAGE_CODES.items() if v == orig_lang.lower()), orig_lang.upper())

    # Update state context to the newly resolved title
    state.selected_movie_id = str(tmdb_id)
    state.selected_movie_title = title
    state.grounding_status = "TMDB_VERIFIED"
    state.confidence_status = "high"

    # Extract verified TMDB details
    rating = details.get("vote_average", "N/A")
    if isinstance(rating, (int, float)):
        rating = f"{rating:.1f}"
    vote_count = details.get("vote_count", 0)
    overview = details.get("overview") or "No overview available."
    genres_list = [g.get("name") for g in details.get("genres", [])] if details.get("genres") else []
    genres_str = ", ".join(genres_list) if genres_list else "TMDB does not provide genre information for this title."

    # Credits
    credits_data = details.get("credits", {})
    crew = credits_data.get("crew", [])
    cast = credits_data.get("cast", [])[:8]
    
    directors = [c.get("name") for c in crew if c.get("job") == "Director"]
    creators = [cr.get("name") for cr in details.get("created_by", [])]
    lead_person = ", ".join(directors or creators) if (directors or creators) else "TMDB does not provide that information for this title."
    person_label = "Creator(s)" if media_type == "tv" else "Director"

    cast_names = ", ".join([f"{c.get('name')} (as {c.get('character')})" for c in cast if c.get("name")]) if cast else "TMDB does not provide cast information for this title."

    # Subtitle availability check (Section 10)
    q_lower = state.query.lower()
    if any(k in q_lower for k in ["subtitle", "dialogue", "what did", "spoken", "quote", "scene"]):
        # Only Interstellar currently has indexed subtitles
        if str(tmdb_id) != "157336" and "interstellar" not in title.lower():
            state.final_answer = (
                f"**{title} ({year_str})** was successfully found on TMDB.\n\n"
                f"However, subtitle-grounded Q&A is not currently available for it.\n\n"
                f"• **{person_label}:** {lead_person}\n"
                f"• **Language:** {lang_name}\n"
                f"• **TMDB Rating:** {rating}/10\n"
                f"• **Overview:** {overview}"
            )
            state.recommendation_candidates = [{
                "id": tmdb_id,
                "title": title,
                "media_type": media_type,
                "poster_path": details.get("poster_path"),
                "backdrop_path": details.get("backdrop_path"),
                "vote_average": details.get("vote_average", 0.0),
                "release_date": rel_date,
                "overview": overview
            }]
            return state

    # Similar Titles Intent
    if state.intent == "SIMILAR_TITLES":
        if media_type == "movie":
            similar_items = get_movie_similar(tmdb_id) or get_movie_recommendations(tmdb_id)
        else:
            similar_items = get_tv_similar(tmdb_id) or get_tv_recommendations(tmdb_id)

        if not similar_items:
            state.final_answer = f"Found **{title}**, but TMDB returned no similar titles for it."
            return state

        sim_cards = []
        sim_text_lines = [f"Titles similar to **{title}** ({year_str}):\n"]
        for s in similar_items[:8]:
            s_title = s.get("title") or s.get("name")
            s_date = s.get("release_date") or s.get("first_air_date") or ""
            s_yr = s_date[:4] if s_date else ""
            s_vote = f"{s.get('vote_average', 0.0):.1f}"
            sim_text_lines.append(f"• **{s_title}** ({s_yr}) — Rating: {s_vote}/10")
            sim_cards.append({
                "id": s.get("id"),
                "title": s_title,
                "media_type": media_type,
                "poster_path": s.get("poster_path"),
                "backdrop_path": s.get("backdrop_path"),
                "vote_average": s.get("vote_average", 0.0),
                "release_date": s_date,
                "overview": s.get("overview", "")
            })

        state.final_answer = "\n".join(sim_text_lines)
        state.recommendation_candidates = sim_cards
        return state

    # Watchlist Action Intent
    if state.intent == "WATCHLIST_ACTION":
        state.action = {
            "type": "watchlist_add",
            "tmdb_id": tmdb_id,
            "media_type": media_type,
            "title": title
        }
        state.final_answer = f"I've identified **{title} ({year_str})** (TMDB ID: `{tmdb_id}`). You can add it to your watchlist."
        state.recommendation_candidates = [{
            "id": tmdb_id,
            "title": title,
            "media_type": media_type,
            "poster_path": details.get("poster_path"),
            "backdrop_path": details.get("backdrop_path"),
            "vote_average": details.get("vote_average", 0.0),
            "release_date": rel_date,
            "overview": overview
        }]
        return state

    # Default Title & Information Presentation
    info_lines = [
        f"### **{title}** ({year_str}) — {media_type.capitalize()}\n",
        f"• **{person_label}:** {lead_person}",
        f"• **Main Cast:** {cast_names}",
        f"• **Original Language:** {lang_name} (`{orig_lang}`)",
        f"• **Genres:** {genres_str}",
        f"• **TMDB Rating:** {rating}/10 ({vote_count:,} votes)",
    ]
    if media_type == "movie":
        rt = details.get("runtime")
        rt_str = f"{rt} mins" if rt else "TMDB does not provide runtime for this title."
        info_lines.append(f"• **Runtime:** {rt_str}")
    else:
        seasons = details.get("number_of_seasons")
        episodes = details.get("number_of_episodes")
        s_str = f"{seasons} seasons, {episodes} episodes" if seasons else "TMDB does not provide episode information."
        info_lines.append(f"• **Format:** {s_str}")

    info_lines.append(f"\n**Overview:**\n{overview}")
    state.final_answer = "\n".join(info_lines)

    # Attach verified card so frontend renders movie card
    card = {
        "id": tmdb_id,
        "title": title,
        "media_type": media_type,
        "poster_path": details.get("poster_path"),
        "backdrop_path": details.get("backdrop_path"),
        "vote_average": details.get("vote_average", 0.0),
        "release_date": rel_date,
        "overview": overview
    }
    state.recommendation_candidates = [card]
    return state
