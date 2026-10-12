import time
import urllib.parse
from typing import Optional, List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.routers.tmdb import tmdb_get

# TMDB Genre dictionaries
MOVIE_GENRES = {
    "action": 28,
    "adventure": 12,
    "animation": 16,
    "comedy": 35,
    "crime": 80,
    "documentary": 99,
    "drama": 18,
    "family": 10751,
    "fantasy": 14,
    "history": 36,
    "horror": 27,
    "music": 10402,
    "mystery": 9648,
    "romance": 10749,
    "science fiction": 878,
    "sci-fi": 878,
    "scifi": 878,
    "tv movie": 10770,
    "thriller": 53,
    "war": 10752,
    "western": 37
}

TV_GENRES = {
    "action & adventure": 10759,
    "action": 10759,
    "adventure": 10759,
    "animation": 16,
    "comedy": 35,
    "crime": 80,
    "documentary": 99,
    "drama": 18,
    "family": 10751,
    "kids": 10762,
    "mystery": 9648,
    "news": 10763,
    "reality": 10764,
    "sci-fi & fantasy": 10765,
    "sci-fi": 10765,
    "scifi": 10765,
    "fantasy": 10765,
    "soap": 10766,
    "talk": 10767,
    "war & politics": 10768,
    "western": 37
}

LANGUAGE_CODES = {
    "tamil": "ta",
    "telugu": "te",
    "hindi": "hi",
    "malayalam": "ml",
    "kannada": "kn",
    "bengali": "bn",
    "marathi": "mr",
    "punjabi": "pa",
    "korean": "ko",
    "japanese": "ja",
    "chinese": "zh",
    "english": "en",
    "spanish": "es",
    "french": "fr",
    "german": "de",
    "italian": "it",
    "russian": "ru"
}


# =========================================================
# UNIVERSAL SEARCH & RETRIEVAL FUNCTIONS
# =========================================================

def search_movies(
    query: str,
    page: int = 1,
    language: Optional[str] = None,
    year: Optional[int] = None
) -> List[Dict[str, Any]]:
    """Searches TMDB for movies matching query, with optional language and year."""
    params: Dict[str, Any] = {"query": query, "page": page, "include_adult": "false"}
    if year:
        params["primary_release_year"] = year
    if language:
        params["language"] = language
    data = tmdb_get("/search/movie", params)
    results = data.get("results", [])
    for r in results:
        r["media_type"] = "movie"
    return results


def search_tv(
    query: str,
    page: int = 1,
    language: Optional[str] = None,
    year: Optional[int] = None
) -> List[Dict[str, Any]]:
    """Searches TMDB for TV shows matching query."""
    params: Dict[str, Any] = {"query": query, "page": page, "include_adult": "false"}
    if year:
        params["first_air_date_year"] = year
    if language:
        params["language"] = language
    data = tmdb_get("/search/tv", params)
    results = data.get("results", [])
    for r in results:
        r["media_type"] = "tv"
    return results


def search_multi(
    query: str,
    page: int = 1,
    language: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Searches TMDB across movies and TV shows simultaneously."""
    params: Dict[str, Any] = {"query": query, "page": page, "include_adult": "false"}
    if language:
        params["language"] = language
    data = tmdb_get("/search/multi", params)
    results = data.get("results", [])
    # Filter out persons if returned in multi-search unless relevant
    return [r for r in results if r.get("media_type") in ["movie", "tv"]]


def get_movie_details(
    movie_id: int,
    append_to_response: str = "credits,videos,similar,recommendations,watch/providers"
) -> Dict[str, Any]:
    """Fetches full movie details from TMDB with credits and recommendations."""
    return tmdb_get(f"/movie/{movie_id}", {
        "language": "en-US",
        "append_to_response": append_to_response
    })


def get_movie_credits(movie_id: int) -> Dict[str, Any]:
    """Fetches full movie cast and crew."""
    return tmdb_get(f"/movie/{movie_id}/credits", {"language": "en-US"})


def get_movie_similar(movie_id: int, page: int = 1) -> List[Dict[str, Any]]:
    """Fetches similar movies."""
    data = tmdb_get(f"/movie/{movie_id}/similar", {"language": "en-US", "page": page})
    return data.get("results", [])


def get_movie_recommendations(movie_id: int, page: int = 1) -> List[Dict[str, Any]]:
    """Fetches recommended movies."""
    data = tmdb_get(f"/movie/{movie_id}/recommendations", {"language": "en-US", "page": page})
    return data.get("results", [])


def get_tv_details(
    tv_id: int,
    append_to_response: str = "credits,videos,similar,recommendations,watch/providers"
) -> Dict[str, Any]:
    """Fetches full TV show details from TMDB."""
    return tmdb_get(f"/tv/{tv_id}", {
        "language": "en-US",
        "append_to_response": append_to_response
    })


def get_tv_credits(tv_id: int) -> Dict[str, Any]:
    """Fetches TV show credits."""
    return tmdb_get(f"/tv/{tv_id}/credits", {"language": "en-US"})


def get_tv_similar(tv_id: int, page: int = 1) -> List[Dict[str, Any]]:
    """Fetches similar TV shows."""
    data = tmdb_get(f"/tv/{tv_id}/similar", {"language": "en-US", "page": page})
    return data.get("results", [])


def get_tv_recommendations(tv_id: int, page: int = 1) -> List[Dict[str, Any]]:
    """Fetches recommended TV shows."""
    data = tmdb_get(f"/tv/{tv_id}/recommendations", {"language": "en-US", "page": page})
    return data.get("results", [])


def get_watch_providers(
    tmdb_id: int,
    media_type: str = "movie",
    region: str = "IN"
) -> Dict[str, Any]:
    """Fetches streaming availability / watch providers."""
    ep = f"/{media_type}/{tmdb_id}/watch/providers"
    data = tmdb_get(ep)
    results = data.get("results", {})
    return results.get(region.upper()) or results.get("US") or {}


def discover_movies(
    language: Optional[str] = None,
    with_genres: Optional[str] = None,
    sort_by: str = "popularity.desc",
    year: Optional[int] = None,
    primary_release_date_gte: Optional[str] = None,
    primary_release_date_lte: Optional[str] = None,
    vote_average_gte: Optional[float] = None,
    vote_count_gte: Optional[int] = None,
    min_runtime: Optional[int] = None,
    max_runtime: Optional[int] = None,
    page: int = 1,
    filters: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Discovers movies according to filters.
    Supports either keyword arguments or a 'filters' dictionary.
    """
    if filters:
        language = filters.get("with_original_language") or filters.get("language") or language
        with_genres = filters.get("with_genres") or with_genres
        sort_by = filters.get("sort_by") or sort_by
        year = filters.get("primary_release_year") or filters.get("year") or year
        primary_release_date_gte = filters.get("primary_release_date.gte") or primary_release_date_gte
        primary_release_date_lte = filters.get("primary_release_date.lte") or primary_release_date_lte
        vote_average_gte = filters.get("vote_average.gte") or filters.get("vote_average_gte") or vote_average_gte
        vote_count_gte = filters.get("vote_count.gte") or filters.get("vote_count_gte") or vote_count_gte
        min_runtime = filters.get("with_runtime.gte") or filters.get("min_runtime") or min_runtime
        max_runtime = filters.get("with_runtime.lte") or filters.get("max_runtime") or max_runtime
        page = filters.get("page") or page

    params: Dict[str, Any] = {
        "page": page,
        "language": "en-US",
        "sort_by": sort_by,
        "include_adult": "false",
        "include_video": "false"
    }
    if language:
        params["with_original_language"] = language
    if with_genres:
        params["with_genres"] = str(with_genres)
    if year:
        params["primary_release_year"] = year
    if primary_release_date_gte:
        params["primary_release_date.gte"] = primary_release_date_gte
    if primary_release_date_lte:
        params["primary_release_date.lte"] = primary_release_date_lte
    if vote_average_gte:
        params["vote_average.gte"] = vote_average_gte
    if vote_count_gte:
        params["vote_count.gte"] = vote_count_gte
    elif vote_average_gte:
        params["vote_count.gte"] = 10
    if min_runtime:
        params["with_runtime.gte"] = min_runtime
    if max_runtime:
        params["with_runtime.lte"] = max_runtime

    data = tmdb_get("/discover/movie", params)
    return data.get("results", [])


def discover_tv(
    language: Optional[str] = None,
    with_genres: Optional[str] = None,
    sort_by: str = "popularity.desc",
    min_runtime: Optional[int] = None,
    max_runtime: Optional[int] = None,
    page: int = 1,
    filters: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Discovers TV shows according to filters.
    Supports either keyword arguments or a 'filters' dictionary.
    """
    if filters:
        language = filters.get("with_original_language") or filters.get("language") or language
        with_genres = filters.get("with_genres") or with_genres
        sort_by = filters.get("sort_by") or sort_by
        min_runtime = filters.get("with_runtime.gte") or filters.get("min_runtime") or min_runtime
        max_runtime = filters.get("with_runtime.lte") or filters.get("max_runtime") or max_runtime
        page = filters.get("page") or page

    params: Dict[str, Any] = {"page": page, "language": "en-US", "sort_by": sort_by}
    if language:
        params["with_original_language"] = language
    if with_genres:
        params["with_genres"] = str(with_genres)
    if min_runtime:
        params["with_runtime.gte"] = min_runtime
    if max_runtime:
        params["with_runtime.lte"] = max_runtime

    data = tmdb_get("/discover/tv", params)
    return data.get("results", [])


def discover_by_runtime(filters: Dict[str, Any], media_type: str = "movie") -> List[Dict[str, Any]]:
    """Dedicated discovery helper filtered by runtime."""
    if media_type == "tv":
        return discover_tv(filters=filters)
    return discover_movies(filters=filters)


def discover_by_language_and_runtime(filters: Dict[str, Any], media_type: str = "movie") -> List[Dict[str, Any]]:
    """Dedicated discovery helper filtered by both language and runtime."""
    if media_type == "tv":
        return discover_tv(filters=filters)
    return discover_movies(filters=filters)


def discover_similar_with_filters(
    tmdb_id: int,
    filters: Optional[Dict[str, Any]] = None,
    media_type: str = "movie"
) -> List[Dict[str, Any]]:
    """
    Discovers titles similar to a target title, fetching recommendations & similar candidates.
    """
    filters = filters or {}
    candidates: List[Dict[str, Any]] = []
    if media_type == "movie":
        recs = get_movie_recommendations(tmdb_id)
        sims = get_movie_similar(tmdb_id)
    else:
        recs = get_tv_recommendations(tmdb_id)
        sims = get_tv_similar(tmdb_id)

    seen = set()
    for item in recs + sims:
        cid = item.get("id")
        if cid and cid not in seen and cid != tmdb_id:
            seen.add(cid)
            candidates.append(item)
    return candidates


def get_popular_movies(page: int = 1) -> List[Dict[str, Any]]:
    data = tmdb_get("/movie/popular", {"language": "en-US", "page": page})
    return data.get("results", [])


def get_top_rated_movies(page: int = 1) -> List[Dict[str, Any]]:
    data = tmdb_get("/movie/top_rated", {"language": "en-US", "page": page})
    return data.get("results", [])


def get_trending_movies(time_window: str = "week") -> List[Dict[str, Any]]:
    data = tmdb_get(f"/trending/movie/{time_window}")
    return data.get("results", [])


def get_popular_tv(page: int = 1) -> List[Dict[str, Any]]:
    data = tmdb_get("/tv/popular", {"language": "en-US", "page": page})
    return data.get("results", [])


def get_top_rated_tv(page: int = 1) -> List[Dict[str, Any]]:
    data = tmdb_get("/tv/top_rated", {"language": "en-US", "page": page})
    return data.get("results", [])


def get_trending_tv(time_window: str = "week") -> List[Dict[str, Any]]:
    data = tmdb_get(f"/trending/tv/{time_window}")
    return data.get("results", [])


def filter_movies_by_runtime(
    candidates: List[Dict[str, Any]],
    min_runtime: Optional[int] = None,
    max_runtime: Optional[int] = None,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """Parallel runtime evaluation for candidate movies."""
    if not candidates:
        return []

    eval_candidates = candidates[:25]
    matched_movies = []

    def fetch_details(movie):
        m_id = movie.get("id")
        if not m_id:
            return None
        try:
            details = get_movie_details(m_id, append_to_response="")
            return {
                **movie,
                "runtime": details.get("runtime"),
                "genres": [g.get("name") for g in details.get("genres", [])] if details.get("genres") else movie.get("genres", []),
                "overview": details.get("overview") or movie.get("overview")
            }
        except Exception:
            return None

    with ThreadPoolExecutor(max_workers=8) as executor:
        future_to_movie = {executor.submit(fetch_details, m): m for m in eval_candidates}
        for future in as_completed(future_to_movie):
            result = future.result()
            if not result:
                continue

            runtime = result.get("runtime")
            if not runtime or runtime <= 0:
                continue

            if min_runtime is not None and runtime < min_runtime:
                continue
            if max_runtime is not None and runtime > max_runtime:
                continue

            matched_movies.append(result)

    id_order = {m.get("id"): idx for idx, m in enumerate(eval_candidates)}
    matched_movies.sort(key=lambda m: id_order.get(m.get("id"), 999))
    return matched_movies[:limit]
