from fastapi import APIRouter, HTTPException
import requests
import time
from typing import Optional
import urllib3

from app.config import TMDB_ACCESS_TOKEN
from rapidfuzz import process, fuzz

# Suppress InsecureRequestWarning when using verify=False for local SSL compatibility
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

router = APIRouter(
    prefix="/tmdb",
    tags=["TMDB"]
)

PRIMARY_TMDB_URL = "https://api.tmdb.org/3"
FALLBACK_TMDB_URL = "https://api.themoviedb.org/3"


# =========================================================
# COMMON TMDB REQUEST WITH RESILIENCE
# =========================================================

def tmdb_get(endpoint: str, params: dict = None):
    if params is None:
        params = {}

    headers = {
        "Authorization": f"Bearer {TMDB_ACCESS_TOKEN}",
        "accept": "application/json"
    }

    base_urls = [PRIMARY_TMDB_URL, FALLBACK_TMDB_URL]
    last_exception = None

    for base_url in base_urls:
        url = f"{base_url}{endpoint}"
        print("=" * 50)
        print("TMDB URL:", url)
        print("TOKEN FOUND:", bool(TMDB_ACCESS_TOKEN))

        for attempt in range(2):
            try:
                response = requests.get(
                    url,
                    headers=headers,
                    params=params,
                    timeout=10,
                    verify=False
                )

                print("STATUS:", response.status_code)

                if response.status_code == 401:
                    print("TMDB AUTHENTICATION FAILED (401)")
                    raise HTTPException(
                        status_code=401,
                        detail="TMDB authentication failed. Check TMDB_ACCESS_TOKEN."
                    )

                content_type = response.headers.get("Content-Type", "")
                if response.status_code == 403:
                    print("TMDB ACCESS BLOCKED (403)")
                    # Check if blocked by network firewall proxy
                    if "text/html" in content_type:
                        raise HTTPException(
                            status_code=503,
                            detail="TMDB upstream request is blocked by the local network firewall (HTTP 403: Restricted site). Please connect to an unrestricted network or whitelist api.themoviedb.org."
                        )
                    raise HTTPException(
                        status_code=403,
                        detail="TMDB returned 403 Forbidden."
                    )

                if response.status_code == 200 and "application/json" in content_type:
                    return response.json()

                response.raise_for_status()
                return response.json()

            except HTTPException:
                raise

            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                print(f"TMDB connection attempt {attempt + 1} to {base_url} failed: {type(e).__name__}")
                last_exception = e
                time.sleep(0.5)
                continue

            except requests.exceptions.HTTPError as e:
                print("TMDB HTTP ERROR:", response.status_code)
                raise HTTPException(
                    status_code=502,
                    detail=f"TMDB upstream service returned HTTP error: {response.status_code}"
                )

            except Exception as e:
                last_exception = e
                break

    # If all base URLs failed
    raise HTTPException(
        status_code=503,
        detail=f"TMDB service unavailable: external request blocked or unreachable ({str(last_exception)})"
    )


# =========================================================
# SEARCH MOVIES
# =========================================================

@router.get("/movies/search")
def search_movies(
    query: str,
    page: int = 1,
    language: str = "en-US"
):
    data = tmdb_get(
        "/search/movie",
        {
            "query": query,
            "page": page,
            "include_adult": "false",
            "language": language
        }
    )

    return {
        "page": data.get("page", 1),
        "total_pages": data.get("total_pages", 0),
        "total_results": data.get("total_results", 0),
        "results": data.get("results", [])
    }


# =========================================================
# MULTI SEARCH (MOVIES + TV)
# =========================================================

@router.get("/multi/search")
def multi_search(
    query: str,
    page: int = 1,
    language: str = "en-US"
):
    data = tmdb_get(
        "/search/multi",
        {
            "query": query,
            "page": page,
            "include_adult": "false",
            "language": language
        }
    )

    return {
        "page": data.get("page", 1),
        "total_pages": data.get("total_pages", 0),
        "total_results": data.get("total_results", 0),
        "results": data.get("results", [])
    }


# =========================================================
# DISCOVER MOVIES
# =========================================================

@router.get("/movies/discover")
def discover_movies(
    page: int = 1,
    language: str = "en-US",
    with_original_language: Optional[str] = None,
    with_genres: Optional[str] = None,
    sort_by: str = "popularity.desc",
    year: Optional[int] = None
):
    params = {
        "page": page,
        "language": language,
        "sort_by": sort_by,
        "include_adult": "false",
        "include_video": "false"
    }

    if with_original_language:
        params["with_original_language"] = with_original_language

    if with_genres:
        params["with_genres"] = with_genres

    if year:
        params["primary_release_year"] = year

    data = tmdb_get(
        "/discover/movie",
        params
    )

    return {
        "page": data.get("page", 1),
        "total_pages": data.get("total_pages", 0),
        "total_results": data.get("total_results", 0),
        "results": data.get("results", [])
    }


# =========================================================
# POPULAR MOVIES
# =========================================================

@router.get("/movies/popular")
def popular_movies(page: int = 1):
    data = tmdb_get(
        "/movie/popular",
        {
            "language": "en-US",
            "page": page
        }
    )

    return {
        "page": data.get("page", 1),
        "total_pages": data.get("total_pages", 0),
        "total_results": data.get("total_results", 0),
        "results": data.get("results", [])
    }


# =========================================================
# TOP RATED MOVIES
# =========================================================

@router.get("/movies/top-rated")
def top_rated_movies(page: int = 1):
    data = tmdb_get(
        "/movie/top_rated",
        {
            "language": "en-US",
            "page": page
        }
    )

    return {
        "page": data.get("page", 1),
        "total_pages": data.get("total_pages", 0),
        "total_results": data.get("total_results", 0),
        "results": data.get("results", [])
    }


# =========================================================
# NOW PLAYING MOVIES
# =========================================================

@router.get("/movies/now-playing")
def now_playing_movies(page: int = 1):
    data = tmdb_get(
        "/movie/now_playing",
        {
            "language": "en-US",
            "page": page
        }
    )

    return {
        "page": data.get("page", 1),
        "total_pages": data.get("total_pages", 0),
        "total_results": data.get("total_results", 0),
        "results": data.get("results", [])
    }


# =========================================================
# UPCOMING MOVIES
# =========================================================

@router.get("/movies/upcoming")
def upcoming_movies(page: int = 1):
    data = tmdb_get(
        "/movie/upcoming",
        {
            "language": "en-US",
            "page": page
        }
    )

    return {
        "page": data.get("page", 1),
        "total_pages": data.get("total_pages", 0),
        "total_results": data.get("total_results", 0),
        "results": data.get("results", [])
    }


# =========================================================
# TRENDING MOVIES
# =========================================================

@router.get("/movies/trending")
def trending_movies():
    data = tmdb_get(
        "/trending/movie/week"
    )

    return {
        "results": data.get("results", [])
    }


# =========================================================
# LANGUAGES
# =========================================================

@router.get("/languages")
def get_languages():
    return [
        {"code": "en", "name": "English"},
        {"code": "ta", "name": "Tamil"},
        {"code": "te", "name": "Telugu"},
        {"code": "ml", "name": "Malayalam"},
        {"code": "kn", "name": "Kannada"},
        {"code": "hi", "name": "Hindi"},
        {"code": "bn", "name": "Bengali"},
        {"code": "mr", "name": "Marathi"},
        {"code": "pa", "name": "Punjabi"},
        {"code": "ko", "name": "Korean"},
        {"code": "ja", "name": "Japanese"},
        {"code": "zh", "name": "Chinese"},
        {"code": "fr", "name": "French"},
        {"code": "es", "name": "Spanish"},
        {"code": "de", "name": "German"}
    ]


# =========================================================
# GENRES (MOVIES)
# =========================================================

@router.get("/genres")
def get_genres():
    data = tmdb_get(
        "/genre/movie/list",
        {
            "language": "en-US"
        }
    )

    return data.get("genres", [])


# =========================================================
# MOVIE DETAILS (WITH CREDITS, VIDEOS, SIMILAR, RECOMMENDATIONS)
# =========================================================

@router.get("/movies/{movie_id}")
def get_movie(movie_id: int):
    return tmdb_get(
        f"/movie/{movie_id}",
        {
            "language": "en-US",
            "append_to_response": "credits,videos,similar,recommendations"
        }
    )


# =========================================================
# TV SHOWS ENDPOINTS
# =========================================================

@router.get("/tv/popular")
def popular_tv(page: int = 1):
    data = tmdb_get(
        "/tv/popular",
        {
            "language": "en-US",
            "page": page
        }
    )
    return {
        "page": data.get("page", 1),
        "total_pages": data.get("total_pages", 0),
        "total_results": data.get("total_results", 0),
        "results": data.get("results", [])
    }


@router.get("/tv/top-rated")
def top_rated_tv(page: int = 1):
    data = tmdb_get(
        "/tv/top_rated",
        {
            "language": "en-US",
            "page": page
        }
    )
    return {
        "page": data.get("page", 1),
        "total_pages": data.get("total_pages", 0),
        "total_results": data.get("total_results", 0),
        "results": data.get("results", [])
    }


@router.get("/tv/trending")
def trending_tv():
    data = tmdb_get(
        "/trending/tv/week"
    )
    return {
        "results": data.get("results", [])
    }


@router.get("/tv/airing-today")
def airing_today_tv(page: int = 1):
    data = tmdb_get(
        "/tv/airing_today",
        {
            "language": "en-US",
            "page": page
        }
    )
    return {
        "page": data.get("page", 1),
        "total_pages": data.get("total_pages", 0),
        "total_results": data.get("total_results", 0),
        "results": data.get("results", [])
    }


@router.get("/tv/on-the-air")
def on_the_air_tv(page: int = 1):
    data = tmdb_get(
        "/tv/on_the_air",
        {
            "language": "en-US",
            "page": page
        }
    )
    return {
        "page": data.get("page", 1),
        "total_pages": data.get("total_pages", 0),
        "total_results": data.get("total_results", 0),
        "results": data.get("results", [])
    }


@router.get("/tv/genres")
def tv_genres():
    data = tmdb_get(
        "/genre/tv/list",
        {
            "language": "en-US"
        }
    )
    return data.get("genres", [])


@router.get("/tv/search")
def search_tv(
    query: str,
    page: int = 1,
    language: str = "en-US"
):
    data = tmdb_get(
        "/search/tv",
        {
            "query": query,
            "page": page,
            "include_adult": "false",
            "language": language
        }
    )
    return {
        "page": data.get("page", 1),
        "total_pages": data.get("total_pages", 0),
        "total_results": data.get("total_results", 0),
        "results": data.get("results", [])
    }


@router.get("/tv/discover")
def discover_tv(
    page: int = 1,
    language: str = "en-US",
    with_original_language: Optional[str] = None,
    with_genres: Optional[str] = None,
    sort_by: str = "popularity.desc",
    first_air_date_year: Optional[int] = None
):
    params = {
        "page": page,
        "language": language,
        "sort_by": sort_by,
        "include_adult": "false"
    }

    if with_original_language:
        params["with_original_language"] = with_original_language

    if with_genres:
        params["with_genres"] = with_genres

    if first_air_date_year:
        params["first_air_date_year"] = first_air_date_year

    data = tmdb_get(
        "/discover/tv",
        params
    )

    return {
        "page": data.get("page", 1),
        "total_pages": data.get("total_pages", 0),
        "total_results": data.get("total_results", 0),
        "results": data.get("results", [])
    }


@router.get("/tv/{tv_id}")
def get_tv(tv_id: int):
    return tmdb_get(
        f"/tv/{tv_id}",
        {
            "language": "en-US",
            "append_to_response": "credits,videos,similar,recommendations"
        }
    )