from typing import Optional, Dict, Any, List, Union
from sqlalchemy.orm import Session
from app.models.activity import Watchlist
from app.services import tmdb_service
from app.tools.tmdb_tools import format_movie_summary


def tool_view_watchlist(user_id: int, db: Session) -> Dict[str, Any]:
    items = db.query(Watchlist).filter(Watchlist.user_id == user_id).all()
    if not items:
        return {
            "count": 0,
            "results": [],
            "message": "Your watchlist is currently empty."
        }

    results = []
    for item in items:
        try:
            if item.content_type == "tv":
                data = tmdb_service.get_tv_details(item.tmdb_id, append_to_response="")
                title = data.get("name") or data.get("original_name") or f"TV #{item.tmdb_id}"
            else:
                data = tmdb_service.get_movie_details(item.tmdb_id, append_to_response="")
                title = data.get("title") or data.get("original_title") or f"Movie #{item.tmdb_id}"

            results.append({
                "id": item.tmdb_id,
                "title": title,
                "poster_path": data.get("poster_path"),
                "release_date": (data.get("release_date") or data.get("first_air_date") or "")[:4],
                "rating": round(data.get("vote_average", 0), 1) if data.get("vote_average") else None,
                "content_type": item.content_type
            })
        except Exception:
            results.append({
                "id": item.tmdb_id,
                "title": f"Title #{item.tmdb_id}",
                "content_type": item.content_type
            })

    return {
        "count": len(results),
        "results": results,
        "message": f"You have {len(results)} title(s) in your watchlist."
    }


def tool_add_to_watchlist(user_id: int, movie_ref: Union[str, int], db: Session) -> Dict[str, Any]:
    tmdb_id = None
    title = None

    if isinstance(movie_ref, int) or (isinstance(movie_ref, str) and movie_ref.isdigit()):
        tmdb_id = int(movie_ref)
        try:
            data = tmdb_service.get_movie_details(tmdb_id, append_to_response="")
            title = data.get("title") or f"Movie #{tmdb_id}"
        except Exception:
            title = f"Movie #{tmdb_id}"
    else:
        # Search by title
        matches = tmdb_service.search_movies(query=str(movie_ref))
        if not matches:
            return {
                "success": False,
                "message": f"Could not find any movie named '{movie_ref}' on TMDB to add."
            }
        tmdb_id = matches[0].get("id")
        title = matches[0].get("title")

    # Check existing
    existing = db.query(Watchlist).filter(
        Watchlist.user_id == user_id,
        Watchlist.tmdb_id == tmdb_id
    ).first()

    if existing:
        return {
            "success": True,
            "already_present": True,
            "tmdb_id": tmdb_id,
            "title": title,
            "message": f"'{title}' is already in your watchlist."
        }

    # Add to DB
    entry = Watchlist(user_id=user_id, tmdb_id=tmdb_id, content_type="movie")
    db.add(entry)
    db.commit()

    return {
        "success": True,
        "already_present": False,
        "tmdb_id": tmdb_id,
        "title": title,
        "message": f"Successfully added '{title}' to your watchlist!"
    }


def tool_remove_from_watchlist(user_id: int, movie_ref: Union[str, int], db: Session) -> Dict[str, Any]:
    tmdb_id = None
    title = None

    if isinstance(movie_ref, int) or (isinstance(movie_ref, str) and movie_ref.isdigit()):
        tmdb_id = int(movie_ref)
        try:
            data = tmdb_service.get_movie_details(tmdb_id, append_to_response="")
            title = data.get("title") or f"Movie #{tmdb_id}"
        except Exception:
            title = f"Movie #{tmdb_id}"
    else:
        # Check current watchlist items to find matching title
        user_items = db.query(Watchlist).filter(Watchlist.user_id == user_id).all()
        ref_lower = str(movie_ref).lower()
        for item in user_items:
            try:
                data = tmdb_service.get_movie_details(item.tmdb_id, append_to_response="")
                m_title = data.get("title", "")
                if ref_lower in m_title.lower() or m_title.lower() in ref_lower:
                    tmdb_id = item.tmdb_id
                    title = m_title
                    break
            except Exception:
                continue

        if not tmdb_id:
            # Fallback search TMDB to get ID
            matches = tmdb_service.search_movies(query=str(movie_ref))
            if matches:
                tmdb_id = matches[0].get("id")
                title = matches[0].get("title")

    if not tmdb_id:
        return {
            "success": False,
            "message": f"Could not find '{movie_ref}' to remove from your watchlist."
        }

    entry = db.query(Watchlist).filter(
        Watchlist.user_id == user_id,
        Watchlist.tmdb_id == tmdb_id
    ).first()

    if not entry:
        return {
            "success": False,
            "message": f"'{title or movie_ref}' was not found in your watchlist."
        }

    db.delete(entry)
    db.commit()

    return {
        "success": True,
        "tmdb_id": tmdb_id,
        "title": title or str(movie_ref),
        "message": f"Successfully removed '{title or movie_ref}' from your watchlist."
    }
