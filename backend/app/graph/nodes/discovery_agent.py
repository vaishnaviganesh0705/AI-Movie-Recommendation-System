"""
Deterministic TMDB Filtered Discovery Agent.
Handles runtime-filtered discovery, language filtering, genre filtering,
and similar-title discovery with strict local post-verification.
Never invents titles, runtimes, or languages.
"""
import json
import logging
from typing import Dict, Any, List, Optional

from app.graph.state import AgentGraphState
from app.services.runtime_parser import (
    satisfies_runtime_filter,
    TMDB_MOVIE_GENRES,
    TMDB_TV_GENRES
)
from app.services.tmdb_service import (
    discover_movies,
    discover_tv,
    discover_similar_with_filters,
    get_movie_details,
    get_tv_details,
    LANGUAGE_CODES
)
from app.services.entity_resolver import resolve_tmdb_entity

logger = logging.getLogger("discovery_agent")


def discovery_agent_node(state: AgentGraphState) -> AgentGraphState:
    """
    Deterministic Filtered Discovery Node.
    Executes TMDB discover / similar with verified runtime and language checks.
    """
    state.agent = "discovery_agent"

    min_r = state.min_runtime_minutes
    max_r = state.max_runtime_minutes
    lang_hint = state.language_hint
    lang_code = LANGUAGE_CODES.get(lang_hint.lower()) if lang_hint else None
    media_type = state.media_type_hint or "movie"
    if media_type == "unknown":
        media_type = "movie"
    
    genre_hint = state.genre_hint
    similar_to_title = state.similar_to_title
    year_hint = state.year_hint

    # Resolve genre ID if present
    genre_id = None
    if genre_hint:
        genre_id = TMDB_MOVIE_GENRES.get(genre_hint.lower()) if media_type == "movie" else TMDB_TV_GENRES.get(genre_hint.lower())

    candidates: List[Dict[str, Any]] = []
    endpoint_called = "/discover/movie" if media_type == "movie" else "/discover/tv"

    # Step 1: Similar to title with filters (e.g. "Movies like Interstellar under 2 hours")
    if similar_to_title:
        resolved_sim = resolve_tmdb_entity(similar_to_title, media_type_hint=media_type)
        if resolved_sim.get("status") == "verified" and resolved_sim.get("tmdb_id"):
            sim_id = int(resolved_sim["tmdb_id"])
            endpoint_called = f"/{media_type}/{sim_id}/similar"
            candidates = discover_similar_with_filters(
                tmdb_id=sim_id,
                filters={"language": lang_code},
                media_type=media_type
            )
        else:
            state.final_answer = f"I could not resolve the referenced title \"{similar_to_title}\" on TMDB to find similar titles."
            state.confidence_status = "low"
            state.grounding_status = "NO_RESULT"
            return state

    # Step 2: Direct filtered discovery (e.g. "1 hr Tamil movies to watch", "Tamil movies under 2 hours")
    if not candidates and not similar_to_title:
        api_filters: Dict[str, Any] = {
            "sort_by": "popularity.desc",
            "page": 1
        }
        if lang_code:
            api_filters["with_original_language"] = lang_code
        if min_r is not None:
            api_filters["with_runtime.gte"] = min_r
        if max_r is not None:
            api_filters["with_runtime.lte"] = max_r
        if genre_id:
            api_filters["with_genres"] = genre_id
        if year_hint:
            api_filters["primary_release_year"] = year_hint

        if media_type == "tv":
            candidates = discover_tv(filters=api_filters)
        else:
            candidates = discover_movies(filters=api_filters)

    # Step 3: Fetch full details & apply local verification (Runtime + Language)
    verified_results: List[Dict[str, Any]] = []
    ranking_breakdown: List[Dict[str, Any]] = []

    for c in candidates[:25]:
        cid = c.get("id")
        if not cid:
            continue

        details: Dict[str, Any] = {}
        try:
            if media_type == "tv":
                details = get_tv_details(cid)
            else:
                details = get_movie_details(cid)
        except Exception:
            details = c

        if not details or not details.get("id"):
            continue

        # Extract verified runtime
        runtime_val: Optional[int] = None
        if media_type == "tv":
            ep_runtimes = details.get("episode_run_time") or []
            if ep_runtimes and isinstance(ep_runtimes, list):
                runtime_val = ep_runtimes[0]
            elif details.get("runtime"):
                runtime_val = details.get("runtime")
        else:
            runtime_val = details.get("runtime")

        # Local Runtime Verification (Section 8)
        # Missing runtime is rejected when strict runtime filter was requested
        if min_r is not None or max_r is not None:
            if not satisfies_runtime_filter(runtime_val, min_runtime=min_r, max_runtime=max_r):
                continue

        # Local Language Verification (Section 7)
        cand_lang = details.get("original_language", "").lower()
        if lang_code and cand_lang != lang_code.lower():
            continue

        # Verified candidate record
        title_str = details.get("title") or details.get("name") or c.get("title") or c.get("name")
        p_path = details.get("poster_path") or c.get("poster_path")
        poster_url = f"https://image.tmdb.org/t/p/w500{p_path}" if p_path else None
        genres_list = [g.get("name") for g in details.get("genres", []) if isinstance(g, dict)]

        res_item = {
            "media_type": media_type,
            "tmdb_id": details.get("id"),
            "id": details.get("id"),
            "title": title_str,
            "runtime_minutes": runtime_val,
            "runtime": f"{runtime_val} min" if runtime_val else "N/A",
            "original_language": cand_lang,
            "release_date": details.get("release_date") or details.get("first_air_date") or "",
            "genres": genres_list,
            "vote_average": details.get("vote_average", 0.0),
            "vote_count": details.get("vote_count", 0),
            "popularity": details.get("popularity", 0.0),
            "overview": details.get("overview", ""),
            "poster_path": poster_url,
            "poster": poster_url,
            "source": "tmdb"
        }
        verified_results.append(res_item)
        ranking_breakdown.append({
            "id": res_item["tmdb_id"],
            "title": res_item["title"],
            "runtime": runtime_val,
            "lang": cand_lang,
            "pop": res_item["popularity"],
            "votes": res_item["vote_count"]
        })

    # Sort verified results by popularity and vote count
    verified_results.sort(key=lambda x: (x.get("vote_count", 0), x.get("popularity", 0.0)), reverse=True)

    # Step 4: Build Response & Formatting
    cards_to_show = verified_results[:10]
    state.recommendation_candidates = cards_to_show

    # Build Section 15 Debug Trace
    trace_obj = {
        "trace_id": state.trace_id,
        "query": state.query,
        "raw_query": state.query,
        "detected_intent": "FILTERED_DISCOVERY",
        "intent": "FILTERED_DISCOVERY",
        "extracted_entity": similar_to_title or "none",
        "media_type_filter": media_type,
        "media_type": media_type,
        "language_filter": lang_hint,
        "language_hint": lang_hint,
        "min_runtime_minutes": min_r,
        "max_runtime_minutes": max_r,
        "use_selected_movie": state.use_selected_movie,
        "tmdb_endpoint_called": endpoint_called,
        "tmdb_endpoint": endpoint_called,
        "raw_result_count": len(candidates),
        "result_count": len(verified_results),
        "ranking_breakdown": ranking_breakdown[:5],
        "selected_candidate": {
            "id": cards_to_show[0]["tmdb_id"],
            "title": cards_to_show[0]["title"],
            "runtime": cards_to_show[0]["runtime_minutes"],
            "lang": cards_to_show[0]["original_language"]
        } if cards_to_show else None,
        "resolution_status": "verified" if cards_to_show else "not_found",
        "hallucination_check_status": "TMDB_VERIFIED" if cards_to_show else "NO_RESULT",
        "grounding_status": "TMDB_VERIFIED" if cards_to_show else "NO_RESULT"
    }
    state.debug_trace = trace_obj
    print("[DEBUG_TRACE]", json.dumps(trace_obj))

    # Case A: Zero verified results
    if not cards_to_show:
        time_desc = ""
        if min_r and max_r:
            time_desc = f"between {min_r} and {max_r} minutes"
        elif max_r:
            time_desc = f"under {max_r} minutes"
        elif min_r:
            time_desc = f"over {min_r} minutes"

        lang_label = f"{lang_hint.capitalize()} " if lang_hint else ""
        state.final_answer = f"I could not find any verified {lang_label}{media_type}s with runtimes {time_desc} on TMDB."
        state.confidence_status = "low"
        state.grounding_status = "NO_RESULT"
        return state

    # Case B: Success with verified results
    time_label = ""
    if min_r and max_r:
        time_label = f"between {min_r} and {max_r} minutes"
    elif max_r:
        time_label = f"of {max_r} minutes or less"
    elif min_r:
        time_label = f"of {min_r} minutes or more"

    lang_phrase = f"{lang_hint.capitalize()} " if lang_hint else ""
    m_type_label = "movies" if media_type == "movie" else "TV shows"
    intro = f"Here are verified {lang_phrase}{m_type_label} with runtimes {time_label} from TMDB (showing top {len(cards_to_show)}):\n\n"

    lines = [intro]
    for idx, item in enumerate(cards_to_show, 1):
        yr = item.get("release_date", "")[:4] or "N/A"
        rt = item.get("runtime_minutes")
        rt_str = f"{rt} min" if rt else "N/A"
        lang_str = item.get("original_language", "").upper()
        rating_str = f"Rating: {item.get('vote_average')}/10" if item.get("vote_average") else ""
        lines.append(f"{idx}. **{item.get('title')}** ({yr}) — **{rt_str}** — {lang_str} ({rating_str})")
        if item.get("overview"):
            ov = item.get("overview", "")
            lines.append(f"   _{ov[:120]}..._\n" if len(ov) > 120 else f"   _{ov}_\n")

    if media_type == "tv":
        lines.append("\n*Note: For TV series, runtime refers to the episode runtime (or average episode duration), not the total duration of the entire series.*")

    state.final_answer = "\n".join(lines)
    state.confidence_status = "high"
    state.grounding_status = "TMDB_VERIFIED"
    return state
