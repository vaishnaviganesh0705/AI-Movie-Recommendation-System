import re
import json
from typing import Optional, Dict, Any
from app.graph.state import AgentGraphState
from app.services.entity_resolver import resolve_tmdb_entity
from app.services.tmdb_service import get_movie_details, get_movie_credits, get_tv_details, get_tv_credits


def metadata_agent_node(state: AgentGraphState) -> AgentGraphState:
    """
    Deterministic TMDB metadata lookup agent.
    Never relies on hardcoded movie titles or memorized LLM answers.
    Answers strictly using verified TMDB details and credits.
    """
    state.agent = "metadata_agent"

    # Context Isolation:
    # Use selected movie ONLY if use_selected_movie is True.
    # Otherwise, prioritize the newly extracted title or raw query.
    if state.use_selected_movie and state.selected_movie_id:
        target_id = str(state.selected_movie_id)
        m_details = get_movie_details(target_id)
        if m_details and "id" in m_details:
            m_credits = get_movie_credits(target_id)
            resolution = {
                "status": "verified",
                "media_type": "movie",
                "tmdb_id": target_id,
                "title": m_details.get("title") or state.selected_movie_title or "Selected Movie",
                "details": m_details,
                "credits": m_credits,
                "resolution_confidence": 1.0,
                "candidates": [m_details],
                "ranking_breakdown": [{"id": target_id, "title": m_details.get("title"), "score": 1.0}]
            }
        else:
            t_details = get_tv_details(target_id)
            t_credits = get_tv_credits(target_id) if t_details else {}
            resolution = {
                "status": "verified" if t_details else "not_found",
                "media_type": "tv",
                "tmdb_id": target_id,
                "title": t_details.get("name") if t_details else (state.selected_movie_title or "Selected Title"),
                "details": t_details or {},
                "credits": t_credits or {},
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

    # Section 15 Debug Trace
    endpoint_called = f"/movie/{resolution.get('tmdb_id')}" if resolution.get("media_type") == "movie" else f"/tv/{resolution.get('tmdb_id')}"
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

    if status == "not_found":
        state.final_answer = f"Movie Metadata Agent: Could not find any title named \"{target_title}\" on TMDB."
        state.confidence_status = "low"
        state.grounding_status = "NO_RESULT"
        return state

    if status == "ambiguous":
        # Ask user to disambiguate
        lines = [f"I found multiple matches for \"{target_title}\":\n"]
        for idx, c in enumerate(resolution.get("candidates", [])[:4], 1):
            m_t = "Movie" if c.get("media_type") == "movie" else "TV Series"
            lines.append(f"{idx}. **{c.get('title')}** ({c.get('year', 'N/A')}) — {m_t}")
        lines.append("\nPlease clarify which title you mean.")
        state.final_answer = "\n".join(lines)
        state.confidence_status = "medium"
        state.grounding_status = "TMDB_VERIFIED"
        return state

    # Single verified title
    tmdb_id = resolution["tmdb_id"]
    media_type = resolution.get("media_type", "movie")
    title = resolution["title"]
    orig_title = resolution.get("original_title") or title
    rel_date = resolution.get("release_date", "")
    year_str = rel_date[:4] if rel_date and len(rel_date) >= 4 else "N/A"
    
    # Update state context
    state.selected_movie_id = str(tmdb_id)
    state.selected_movie_title = title
    state.grounding_status = "TMDB_VERIFIED"
    state.confidence_status = "high"

    # Fetch verified details & credits
    if media_type == "movie":
        details = get_movie_details(tmdb_id)
        credits_data = get_movie_credits(tmdb_id)
        crew = credits_data.get("crew", [])
        cast = credits_data.get("cast", [])[:10]
        directors = [c.get("name") for c in crew if c.get("job") == "Director"]
        lead_person = ", ".join(directors) if directors else None
        person_label = "Director"
        runtime_val = details.get("runtime")
        runtime_str = f"{runtime_val} minutes" if (runtime_val and runtime_val > 0) else None
    else:
        details = get_tv_details(tmdb_id)
        credits_data = get_tv_credits(tmdb_id)
        crew = credits_data.get("crew", [])
        cast = credits_data.get("cast", [])[:10]
        creators = [c.get("name") for c in details.get("created_by", [])]
        lead_person = ", ".join(creators) if creators else None
        person_label = "Creator(s)"
        seasons = details.get("number_of_seasons")
        episodes = details.get("number_of_episodes")
        runtime_str = f"{seasons} seasons, {episodes} episodes" if seasons else None

    cast_names = ", ".join([f"{c.get('name')} (as {c.get('character')})" for c in cast if c.get("name")]) if cast else None
    genres_list = [g.get("name") for g in details.get("genres", [])] if details.get("genres") else []
    genres_str = ", ".join(genres_list) if genres_list else None
    
    rating_val = details.get("vote_average")
    rating_str = f"{rating_val:.1f}/10" if (rating_val is not None) else None
    overview = details.get("overview")

    # Store structured metadata fields
    state.metadata_fields = {
        "title": title,
        "year": year_str,
        "director": lead_person or "TMDB does not provide that information for this title.",
        "cast": cast_names or "TMDB does not provide that information for this title.",
        "runtime": runtime_str or "TMDB does not provide that information for this title.",
        "genres": genres_str or "TMDB does not provide that information for this title.",
        "rating": rating_str or "TMDB does not provide that information for this title.",
        "overview": overview or "TMDB does not provide an overview for this title."
    }

    # Answer formatting matching question focus
    q_lower = state.query.lower()
    targeted_answers = []

    if any(k in q_lower for k in ["director", "who directed", "creator", "who created"]):
        val = lead_person or "TMDB does not provide that information for this title."
        targeted_answers.append(f"• **{person_label}:** {val}")

    if any(k in q_lower for k in ["runtime", "how long", "duration", "seasons", "episodes"]):
        val = runtime_str or "TMDB does not provide runtime/episode information for this title."
        label = "Format" if media_type == "tv" else "Runtime"
        targeted_answers.append(f"• **{label}:** {val}")

    if any(k in q_lower for k in ["cast", "actor", "who acted", "stars"]):
        val = cast_names or "TMDB does not provide cast information for this title."
        targeted_answers.append(f"• **Main Cast:** {val}")

    if any(k in q_lower for k in ["genre"]):
        val = genres_str or "TMDB does not provide genre information for this title."
        targeted_answers.append(f"• **Genres:** {val}")

    if any(k in q_lower for k in ["release", "year", "when was"]):
        val = year_str if year_str != "N/A" else "TMDB does not provide release date information for this title."
        targeted_answers.append(f"• **Release Year:** {val}")

    if any(k in q_lower for k in ["rating", "vote"]):
        val = rating_str or "TMDB does not provide rating information for this title."
        targeted_answers.append(f"• **TMDB Rating:** {val}")

    if targeted_answers:
        state.final_answer = f"**{title}** ({year_str}):\n" + "\n".join(targeted_answers)
    else:
        # Full concise metadata summary
        lead_display = lead_person or "TMDB does not provide that information for this title."
        cast_display = cast_names or "TMDB does not provide cast information for this title."
        rt_display = runtime_str or "TMDB does not provide that information for this title."
        g_display = genres_str or "TMDB does not provide that information for this title."
        r_display = rating_str or "TMDB does not provide that information for this title."
        ov_display = overview or "TMDB does not provide an overview for this title."

        state.final_answer = (
            f"**{title} ({year_str})** — {media_type.capitalize()}\n\n"
            f"• **{person_label}:** {lead_display}\n"
            f"• **Main Cast:** {cast_display}\n"
            f"• **Genres:** {g_display}\n"
            f"• **Runtime/Format:** {rt_display}\n"
            f"• **TMDB Rating:** {r_display}\n\n"
            f"**Overview:**\n{ov_display}"
        )

    # Attach card for frontend
    state.recommendation_candidates = [{
        "id": tmdb_id,
        "title": title,
        "media_type": media_type,
        "poster_path": details.get("poster_path"),
        "backdrop_path": details.get("backdrop_path"),
        "vote_average": details.get("vote_average", 0.0),
        "release_date": rel_date,
        "overview": overview or ""
    }]

    return state
