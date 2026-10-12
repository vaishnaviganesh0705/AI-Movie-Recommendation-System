from typing import Optional, List, Dict, Any
from app.services import tmdb_service
from app.agents.state import ConversationState


def format_movie_summary(movie: Dict[str, Any]) -> Dict[str, Any]:
    genres = movie.get("genres", [])
    genre_names = [g if isinstance(g, str) else g.get("name") for g in genres] if genres else []
    
    return {
        "id": movie.get("id"),
        "title": movie.get("title") or movie.get("original_title") or "Untitled",
        "original_title": movie.get("original_title"),
        "poster_path": movie.get("poster_path"),
        "backdrop_path": movie.get("backdrop_path"),
        "overview": movie.get("overview") or "",
        "release_date": movie.get("release_date") or "",
        "runtime": movie.get("runtime"),
        "rating": round(movie.get("vote_average", 0), 1) if movie.get("vote_average") else None,
        "vote_average": movie.get("vote_average"),
        "vote_count": movie.get("vote_count"),
        "original_language": movie.get("original_language"),
        "genres": [g for g in genre_names if g]
    }


def format_tv_summary(tv: Dict[str, Any]) -> Dict[str, Any]:
    genres = tv.get("genres", [])
    genre_names = [g if isinstance(g, str) else g.get("name") for g in genres] if genres else []

    return {
        "id": tv.get("id"),
        "title": tv.get("name") or tv.get("original_name") or "Untitled",
        "original_title": tv.get("original_name"),
        "poster_path": tv.get("poster_path"),
        "backdrop_path": tv.get("backdrop_path"),
        "overview": tv.get("overview") or "",
        "release_date": tv.get("first_air_date") or "",
        "rating": round(tv.get("vote_average", 0), 1) if tv.get("vote_average") else None,
        "vote_average": tv.get("vote_average"),
        "original_language": tv.get("original_language"),
        "genres": [g for g in genre_names if g]
    }


# =========================================================
# TOOL IMPLEMENTATIONS
# =========================================================

def tool_search_movies(query: str, year: Optional[int] = None, limit: int = 10) -> List[Dict[str, Any]]:
    results = tmdb_service.search_movies(query=query, year=year)
    return [format_movie_summary(m) for m in results[:limit]]


def tool_movie_details(movie_id: Optional[int] = None, title: Optional[str] = None) -> Optional[Dict[str, Any]]:
    if not movie_id and title:
        candidates = tmdb_service.search_movies(query=title)
        if not candidates:
            return None
        movie_id = candidates[0].get("id")

    if not movie_id:
        return None

    data = tmdb_service.get_movie_details(movie_id)
    if not data or data.get("status_code") == 34:  # TMDB not found
        return None

    cast = data.get("credits", {}).get("cast", [])[:8]
    crew = data.get("credits", {}).get("crew", [])
    director = next((c.get("name") for c in crew if c.get("job") == "Director"), None)
    
    formatted = format_movie_summary(data)
    formatted["director"] = director
    formatted["cast"] = [c.get("name") for c in cast if c.get("name")]
    formatted["cast_details"] = cast
    return formatted


def tool_movie_credits(movie_id: Optional[int] = None, title: Optional[str] = None) -> Optional[Dict[str, Any]]:
    if not movie_id and title:
        candidates = tmdb_service.search_movies(query=title)
        if not candidates:
            return None
        movie_id = candidates[0].get("id")
        title = candidates[0].get("title")

    if not movie_id:
        return None

    credits = tmdb_service.get_movie_credits(movie_id)
    cast = credits.get("cast", [])[:10]
    crew = credits.get("crew", [])
    director = next((c.get("name") for c in crew if c.get("job") == "Director"), None)

    return {
        "movie_id": movie_id,
        "title": title,
        "director": director,
        "cast": [c.get("name") for c in cast if c.get("name")],
        "cast_full": cast
    }


def tool_similar_movies(movie_id: Optional[int] = None, title: Optional[str] = None, limit: int = 10) -> Dict[str, Any]:
    if not movie_id and title:
        candidates = tmdb_service.search_movies(query=title)
        if not candidates:
            return {"title": title, "results": []}
        movie_id = candidates[0].get("id")
        title = candidates[0].get("title")

    if not movie_id:
        return {"title": title, "results": []}

    similar = tmdb_service.get_similar_movies(movie_id)
    if not similar:
        similar = tmdb_service.get_movie_recommendations(movie_id)

    return {
        "movie_id": movie_id,
        "title": title,
        "results": [format_movie_summary(m) for m in similar[:limit]]
    }


def tool_trending_movies(limit: int = 10) -> List[Dict[str, Any]]:
    results = tmdb_service.get_trending_movies(time_window="week")
    return [format_movie_summary(m) for m in results[:limit]]


def tool_top_rated_movies(limit: int = 10) -> List[Dict[str, Any]]:
    results = tmdb_service.get_top_rated_movies(page=1)
    return [format_movie_summary(m) for m in results[:limit]]


def tool_discover_and_filter_movies(state: ConversationState, limit: int = 10) -> List[Dict[str, Any]]:
    genre_str = ",".join(str(gid) for gid in state.genre_ids) if state.genre_ids else None
    
    release_date_gte = f"{state.year_gte}-01-01" if state.year_gte else None
    
    candidates = tmdb_service.discover_movies(
        language=state.language,
        with_genres=genre_str,
        sort_by=state.sort_by or "popularity.desc",
        year=state.year,
        primary_release_date_gte=release_date_gte,
        vote_average_gte=state.min_rating,
        page=1
    )

    # If runtime constraint is active, invoke verified runtime filtering
    if state.min_runtime is not None or state.max_runtime is not None:
        filtered = tmdb_service.filter_movies_by_runtime(
            candidates=candidates,
            min_runtime=state.min_runtime,
            max_runtime=state.max_runtime,
            limit=limit
        )
        return [format_movie_summary(m) for m in filtered]

    # No runtime filter: return formatted candidates directly
    return [format_movie_summary(m) for m in candidates[:limit]]


def tool_search_tv(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    results = tmdb_service.search_tv(query=query)
    return [format_tv_summary(s) for s in results[:limit]]


def tool_tv_details(tv_id: Optional[int] = None, title: Optional[str] = None) -> Optional[Dict[str, Any]]:
    if not tv_id and title:
        candidates = tmdb_service.search_tv(query=title)
        if not candidates:
            return None
        tv_id = candidates[0].get("id")

    if not tv_id:
        return None

    data = tmdb_service.get_tv_details(tv_id)
    if not data or data.get("status_code") == 34:
        return None

    formatted = format_tv_summary(data)
    cast = data.get("credits", {}).get("cast", [])[:8]
    formatted["cast"] = [c.get("name") for c in cast if c.get("name")]
    formatted["number_of_seasons"] = data.get("number_of_seasons")
    formatted["number_of_episodes"] = data.get("number_of_episodes")
    return formatted


def tool_similar_tv(tv_id: Optional[int] = None, title: Optional[str] = None, limit: int = 10) -> Dict[str, Any]:
    if not tv_id and title:
        candidates = tmdb_service.search_tv(query=title)
        if not candidates:
            return {"title": title, "results": []}
        tv_id = candidates[0].get("id")
        title = candidates[0].get("name")

    if not tv_id:
        return {"title": title, "results": []}

    similar = tmdb_service.get_similar_tv(tv_id)
    return {
        "tv_id": tv_id,
        "title": title,
        "results": [format_tv_summary(s) for s in similar[:limit]]
    }


def tool_discover_tv(state: ConversationState, limit: int = 10) -> List[Dict[str, Any]]:
    genre_str = ",".join(str(gid) for gid in state.genre_ids) if state.genre_ids else None
    results = tmdb_service.discover_tv(
        language=state.language,
        with_genres=genre_str,
        sort_by=state.sort_by or "popularity.desc",
        page=1
    )
    return [format_tv_summary(s) for s in results[:limit]]
