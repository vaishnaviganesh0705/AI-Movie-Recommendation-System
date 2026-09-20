import os
import re
import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import httpx

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.subscription import SubscriptionPlan, UserSubscription
from app.models.activity import Watchlist, WatchHistory
from app.models.notification import Notification
from app.models.music import Song, Artist, Album
from app.routers.tmdb import tmdb_get
from pydantic import BaseModel

router = APIRouter(prefix="/chat", tags=["Chatbot"])


# =========================================================
# SCHEMAS
# =========================================================

class MessageItem(BaseModel):
    sender: Optional[str] = None
    text: Optional[str] = None
    role: Optional[str] = None
    content: Optional[str] = None

    def get_text(self) -> str:
        return self.text or self.content or ""

    def get_sender(self) -> str:
        return self.sender or self.role or "user"


class ChatRequest(BaseModel):
    prompt: str
    history: Optional[List[MessageItem]] = None


class MovieItem(BaseModel):
    id: int
    title: str
    poster_path: Optional[str] = None
    backdrop_path: Optional[str] = None
    vote_average: Optional[float] = None
    release_date: Optional[str] = None
    runtime: Optional[int] = None
    overview: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    agent: str
    movies: Optional[List[Dict[str, Any]]] = None
    action: Optional[Dict[str, Any]] = None


# =========================================================
# HELPER: GENRE & LANGUAGE MAPS
# =========================================================

GENRE_MAP = {
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
    "sci-fi": 878,
    "science fiction": 878,
    "thriller": 53,
    "war": 10752,
    "western": 37
}

LANG_MAP = {
    "tamil": "ta",
    "telugu": "te",
    "hindi": "hi",
    "malayalam": "ml",
    "kannada": "kn",
    "korean": "ko",
    "japanese": "ja",
    "english": "en",
    "spanish": "es",
    "french": "fr",
    "german": "de",
    "chinese": "zh"
}


# =========================================================
# CONTEXT AGENT: EXTRACT AND ACCUMULATE CONTEXT
# =========================================================

def extract_context_filters(prompt: str, history: Optional[List[MessageItem]] = None) -> Dict[str, Any]:
    combined_texts = []
    if history:
        # Inspect up to last 4 messages for active context
        for h in history[-4:]:
            combined_texts.append(h.get_text().lower())
    combined_texts.append(prompt.lower())

    full_conversation = " ".join(combined_texts)
    current_prompt = prompt.lower()

    filters: Dict[str, Any] = {
        "language": None,
        "genre": None,
        "min_runtime": None,
        "max_runtime": None,
        "min_year": None,
        "min_rating": None,
        "search_term": None
    }

    # Language detection (search in current, fallback to history)
    for lang_name, code in LANG_MAP.items():
        if lang_name in full_conversation:
            filters["language"] = code
            break

    # Genre detection
    for genre_name, genre_id in GENRE_MAP.items():
        if genre_name in full_conversation:
            filters["genre"] = genre_id
            break

    # Runtime detection
    # "under 1 hour" / "less than 60 minutes"
    if re.search(r'(under|less than|within)\s*(1\s*hour|60\s*(mins|minutes))', full_conversation):
        filters["max_runtime"] = 60
    # "under 90 minutes" / "less than 90"
    elif re.search(r'(under|less than|within)\s*90\s*(mins|minutes)?', full_conversation):
        filters["max_runtime"] = 90
    # "under 2 hours" / "less than 120"
    elif re.search(r'(under|less than|within)\s*(2\s*hours|120\s*(mins|minutes))', full_conversation):
        filters["max_runtime"] = 120
    # "around 2 hours"
    elif re.search(r'(around|about)\s*2\s*hours', full_conversation):
        filters["min_runtime"] = 105
        filters["max_runtime"] = 135
    # "between 1 and 2 hours"
    elif re.search(r'between\s*1\s*(and|to)\s*2\s*hours', full_conversation):
        filters["min_runtime"] = 60
        filters["max_runtime"] = 120

    # Year detection (e.g. "after 2020", "released in 2023")
    year_match = re.search(r'(after|from|since)\s*(20\d\d)', full_conversation)
    if year_match:
        filters["min_year"] = int(year_match.group(2))

    # Rating detection (e.g. "top rated", "highly rated", "rating above 8")
    if "top rated" in full_conversation or "highly rated" in full_conversation:
        filters["min_rating"] = 7.5

    return filters


# =========================================================
# MOVIE AGENT WITH VERIFIED RUNTIME FILTERING
# =========================================================

def movie_agent_execute(filters: Dict[str, Any], query_text: str = "", limit: int = 5) -> (str, List[Dict[str, Any]]):
    params: Dict[str, Any] = {
        "page": 1,
        "sort_by": "popularity.desc",
        "include_adult": "false"
    }

    if filters.get("language"):
        params["with_original_language"] = filters["language"]

    if filters.get("genre"):
        params["with_genres"] = str(filters["genre"])

    if filters.get("min_year"):
        params["primary_release_date.gte"] = f"{filters['min_year']}-01-01"

    if filters.get("min_rating"):
        params["vote_average.gte"] = filters["min_rating"]
        params["vote_count.gte"] = 100
        params["sort_by"] = "vote_average.desc"

    # Preliminary discover runtime bounds
    if filters.get("max_runtime"):
        params["with_runtime.lte"] = filters["max_runtime"]
    if filters.get("min_runtime"):
        params["with_runtime.gte"] = filters["min_runtime"]

    data = tmdb_get("/discover/movie", params)
    candidates = data.get("results", [])

    verified_movies: List[Dict[str, Any]] = []

    # If runtime constraint is specified, strictly verify actual movie runtime via /movie/{id}
    req_max_rt = filters.get("max_runtime")
    req_min_rt = filters.get("min_runtime")

    for cand in candidates[:20]:
        mid = cand.get("id")
        if not mid:
            continue

        try:
            details = tmdb_get(f"/movie/{mid}")
            cand_runtime = details.get("runtime") or 0

            # Filter out movies where runtime is unknown (0) or outside verified bounds
            if req_max_rt and (cand_runtime <= 0 or cand_runtime > req_max_rt):
                continue
            if req_min_rt and cand_runtime < req_min_rt:
                continue

            verified_movies.append({
                "id": mid,
                "title": cand.get("title") or details.get("title"),
                "poster_path": cand.get("poster_path"),
                "backdrop_path": cand.get("backdrop_path"),
                "vote_average": cand.get("vote_average"),
                "release_date": cand.get("release_date"),
                "runtime": cand_runtime,
                "overview": cand.get("overview")
            })

            if len(verified_movies) >= limit:
                break
        except Exception:
            continue

    # Fallback if strict runtime filter had few results: return what we verified
    if not verified_movies and not req_max_rt:
        for cand in candidates[:limit]:
            verified_movies.append({
                "id": cand.get("id"),
                "title": cand.get("title"),
                "poster_path": cand.get("poster_path"),
                "backdrop_path": cand.get("backdrop_path"),
                "vote_average": cand.get("vote_average"),
                "release_date": cand.get("release_date"),
                "runtime": None,
                "overview": cand.get("overview")
            })

    # Construct descriptive response text
    desc_parts = []
    if filters.get("language"):
        # reverse lookup language name
        for k, v in LANG_MAP.items():
            if v == filters["language"]:
                desc_parts.append(k.capitalize())
                break
    if filters.get("genre"):
        for k, v in GENRE_MAP.items():
            if v == filters["genre"]:
                desc_parts.append(k.capitalize())
                break
    if req_max_rt:
        desc_parts.append(f"under {req_max_rt} minutes")
    elif req_min_rt and req_max_rt:
        desc_parts.append(f"between {req_min_rt} and {req_max_rt} minutes")
    if filters.get("min_year"):
        desc_parts.append(f"released after {filters['min_year']}")

    filter_summary = " ".join(desc_parts) if desc_parts else "popular"

    if not verified_movies:
        return f"Movie Agent: I couldn't find any {filter_summary} movies matching those strict criteria on TMDB. Try widening your criteria!", []

    message = f"Movie Agent: Here are top {len(verified_movies)} {filter_summary} movies verified from TMDB:\n\n"
    for m in verified_movies:
        rt_str = f" • {m['runtime']}m" if m.get('runtime') else ""
        yr_str = f" ({m['release_date'][:4]})" if m.get('release_date') else ""
        rating_str = f" • Rating: {m['vote_average']}/10" if m.get('vote_average') else ""
        message += f"• **{m['title']}**{yr_str}{rt_str}{rating_str}\n"

    return message, verified_movies


# =========================================================
# RECOMMENDATION AGENT
# =========================================================

def recommendation_agent_execute(query: str, db: Session, current_user: User) -> (str, List[Dict[str, Any]]):
    # Check for "similar to [Movie]"
    sim_match = re.search(r'(similar to|like|recommend.*like)\s+([a-zA-Z0-9\s]+)', query, re.IGNORECASE)
    if sim_match:
        target_name = sim_match.group(2).strip()
        search_res = tmdb_get("/search/movie", {"query": target_name, "include_adult": "false"})
        results = search_res.get("results", [])
        if results:
            base_movie = results[0]
            movie_id = base_movie["id"]
            title = base_movie.get("title")

            rec_data = tmdb_get(f"/movie/{movie_id}/recommendations")
            recs = rec_data.get("results", [])
            if not recs:
                rec_data = tmdb_get(f"/movie/{movie_id}/similar")
                recs = rec_data.get("results", [])

            movie_list = []
            for r in recs[:5]:
                movie_list.append({
                    "id": r["id"],
                    "title": r.get("title"),
                    "poster_path": r.get("poster_path"),
                    "backdrop_path": r.get("backdrop_path"),
                    "vote_average": r.get("vote_average"),
                    "release_date": r.get("release_date"),
                    "overview": r.get("overview")
                })

            resp = f"Recommendation Agent: Because you enjoyed **{title}**, here are top recommendations:\n\n"
            for m in movie_list:
                resp += f"• **{m['title']}** ({m.get('release_date', '')[:4]}) • Rating: {m.get('vote_average')}/10\n"
            return resp, movie_list

    # Personalized recommendations based on User History & Watchlist
    history_items = db.query(WatchHistory).filter(WatchHistory.user_id == current_user.id).order_by(WatchHistory.last_watched_at.desc()).limit(3).all()
    if history_items:
        last_item = history_items[0]
        rec_data = tmdb_get(f"/movie/{last_item.tmdb_id}/recommendations")
        recs = rec_data.get("results", [])
        if recs:
            movie_list = [
                {
                    "id": r["id"],
                    "title": r.get("title"),
                    "poster_path": r.get("poster_path"),
                    "backdrop_path": r.get("backdrop_path"),
                    "vote_average": r.get("vote_average"),
                    "release_date": r.get("release_date")
                }
                for r in recs[:5]
            ]
            resp = "Recommendation Agent: Based on your recent viewing history, here are curated picks for you:\n\n"
            for m in movie_list:
                resp += f"• **{m['title']}** (Rating: {m.get('vote_average')}/10)\n"
            return resp, movie_list

    # Fallback to general trending recommendations
    trend = tmdb_get("/trending/movie/week")
    movie_list = [
        {
            "id": r["id"],
            "title": r.get("title"),
            "poster_path": r.get("poster_path"),
            "backdrop_path": r.get("backdrop_path"),
            "vote_average": r.get("vote_average"),
            "release_date": r.get("release_date")
        }
        for r in trend.get("results", [])[:5]
    ]
    resp = "Recommendation Agent: Here are the top trending movies right now on StreamHub:\n\n"
    for m in movie_list:
        resp += f"• **{m['title']}** (Rating: {m.get('vote_average')}/10)\n"
    return resp, movie_list


# =========================================================
# CONTENT PLANNING AGENT
# =========================================================

def content_planning_agent_execute(prompt: str) -> (str, List[Dict[str, Any]]):
    # Determine days / count
    count = 3
    if "7-day" in prompt.lower() or "week" in prompt.lower():
        count = 7
    elif "weekend" in prompt.lower():
        count = 3

    # Discover popular movies with diverse genres
    data = tmdb_get("/discover/movie", {"sort_by": "vote_average.desc", "vote_count.gte": 500, "page": 1})
    candidates = data.get("results", [])

    planned_movies: List[Dict[str, Any]] = []
    for cand in candidates[:count * 2]:
        mid = cand["id"]
        try:
            det = tmdb_get(f"/movie/{mid}")
            rt = det.get("runtime") or 110
            planned_movies.append({
                "id": mid,
                "title": cand.get("title"),
                "poster_path": cand.get("poster_path"),
                "runtime": rt,
                "vote_average": cand.get("vote_average"),
                "release_date": cand.get("release_date"),
                "overview": cand.get("overview")
            })
            if len(planned_movies) >= count:
                break
        except Exception:
            continue

    day_names = ["Friday Evening", "Saturday Afternoon", "Saturday Prime Time", "Sunday Matinee", "Sunday Night Feature", "Monday Chill", "Tuesday Pick"]
    resp = "Content Planning Agent: Here is your personalized movie plan:\n\n"
    for idx, m in enumerate(planned_movies):
        slot = day_names[idx] if idx < len(day_names) else f"Session {idx + 1}"
        resp += f"• **{slot}**: **{m['title']}** ({m.get('runtime')} mins, Rating: {m.get('vote_average')}/10)\n"

    return resp, planned_movies


# =========================================================
# PAYMENT & SUBSCRIPTION AGENT
# =========================================================

def payment_agent_execute(prompt: str, db: Session, current_user: User) -> (str, Optional[Dict[str, Any]]):
    sub = db.query(UserSubscription).filter(
        UserSubscription.user_id == current_user.id,
        UserSubscription.status == "active"
    ).first()

    now = datetime.datetime.utcnow()

    # User asking about plans or pricing
    if any(k in prompt.lower() for k in ["plan", "price", "how much", "cost", "features", "upgrade"]):
        plans = db.query(SubscriptionPlan).all()
        resp = "Payment & Subscription Agent: Here are the official StreamHub membership plans:\n\n"
        for p in plans:
            resp += f"• **{p.name}** — **${float(p.price):.2f}/mo**\n  Features: {p.features}\n\n"
        resp += "To subscribe or upgrade, head over to the **Subscription** page in your profile!"
        return resp, {"action": "view_plans"}

    # User asking about current subscription status
    if any(k in prompt.lower() for k in ["my subscription", "status", "active", "expire", "billing"]):
        if not sub or (sub.expires_at and sub.expires_at < now):
            return "Payment & Subscription Agent: You currently do not have an active premium subscription (Free Tier). You can subscribe to Standard or Premium for 4K streaming and ad-free viewing!", {"action": "subscribe"}

        plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == sub.plan_id).first()
        plan_name = plan.name if plan else "Premium"
        exp_date = sub.expires_at.strftime("%B %d, %Y") if sub.expires_at else "Unlimited"

        return f"Payment & Subscription Agent: You are on the **StreamHub {plan_name}** plan!\n• Status: Active\n• Next Billing / Expiration: {exp_date}\n• Auto-Renew: {'Enabled' if sub.auto_renew else 'Disabled'}", {"action": "status"}

    return "Payment & Subscription Agent: I can help you with plan pricing, subscription status, or payment questions. How can I assist?", None


# =========================================================
# WATCHLIST AGENT
# =========================================================

def watchlist_agent_execute(prompt: str, db: Session, current_user: User) -> (str, List[Dict[str, Any]]):
    # 1. "Add [movie] to my watchlist"
    add_match = re.search(r'add\s+([a-zA-Z0-9\s]+)\s+to\s+(my\s+)?watchlist', prompt, re.IGNORECASE)
    if add_match:
        m_name = add_match.group(1).strip()
        search_res = tmdb_get("/search/movie", {"query": m_name, "include_adult": "false"})
        results = search_res.get("results", [])
        if results:
            found = results[0]
            existing = db.query(Watchlist).filter(
                Watchlist.user_id == current_user.id,
                Watchlist.tmdb_id == found["id"]
            ).first()

            if not existing:
                new_item = Watchlist(user_id=current_user.id, tmdb_id=found["id"], content_type="movie")
                db.add(new_item)
                db.commit()
                return f"Watchlist Agent: Successfully added **{found['title']}** to your watchlist!", [found]
            else:
                return f"Watchlist Agent: **{found['title']}** is already in your watchlist!", [found]

    # 2. "Show my watchlist" / "What is in my watchlist"
    items = db.query(Watchlist).filter(Watchlist.user_id == current_user.id).all()
    if not items:
        return "Watchlist Agent: Your watchlist is currently empty. You can add any movie or TV show by clicking the + Watchlist button!", []

    movies_list = []
    resp = f"Watchlist Agent: You have {len(items)} items saved in your watchlist:\n\n"
    for it in items[:6]:
        try:
            det = tmdb_get(f"/movie/{it.tmdb_id}")
            movies_list.append({
                "id": it.tmdb_id,
                "title": det.get("title", "Movie"),
                "poster_path": det.get("poster_path"),
                "release_date": det.get("release_date"),
                "vote_average": det.get("vote_average")
            })
            resp += f"• **{det.get('title')}** ({det.get('release_date', '')[:4]})\n"
        except Exception:
            continue

    return resp, movies_list


# =========================================================
# MUSIC AGENT
# =========================================================

def music_agent_execute(prompt: str, db: Session) -> str:
    # Search for artist name in query
    artists = db.query(Artist).all()
    for a in artists:
        if a.name.lower() in prompt.lower():
            songs = db.query(Song).filter(Song.artist_id == a.id).limit(5).all()
            resp = f"Music Agent: Here are top tracks by **{a.name}** available on StreamHub Music:\n\n"
            for s in songs:
                resp += f"• **{s.title}** ({s.genre}) • {s.duration_seconds // 60}m {s.duration_seconds % 60}s\n"
            resp += "\nYou can listen to these tracks directly in the **Music** tab!"
            return resp

    # Search for genre
    genres = ["soundtrack", "rock", "pop", "classical", "electronic", "synthwave", "dance"]
    for g in genres:
        if g in prompt.lower():
            songs = db.query(Song).filter(Song.genre.ilike(f"%{g}%")).limit(5).all()
            if songs:
                resp = f"Music Agent: Here are top {g.capitalize()} tracks for you:\n\n"
                for s in songs:
                    resp += f"• **{s.title}** by {s.artist.name if s.artist else 'Artist'}\n"
                return resp

    # General music library overview
    songs_count = db.query(Song).count()
    artists_count = db.query(Artist).count()
    return f"Music Agent: StreamHub Music features {songs_count} tracks across {artists_count} featured artists including Hans Zimmer, A. R. Rahman, Anirudh Ravichander, Coldplay, and The Weeknd. Visit the Music tab to start listening!"


# =========================================================
# PROFILE & SETTINGS AGENT
# =========================================================

def profile_agent_execute(prompt: str, db: Session, current_user: User) -> str:
    # Check language change request
    for lang_name, code in LANG_MAP.items():
        if f"change" in prompt.lower() and lang_name in prompt.lower():
            current_user.preferred_language = lang_name.capitalize()
            db.commit()
            return f"Profile Agent: I've updated your preferred streaming language to **{lang_name.capitalize()}**!"

    return f"Profile Agent: Here is your account overview:\n• Name: {current_user.name}\n• Email: {current_user.email}\n• Preferred Language: {current_user.preferred_language or 'English'}\n• Role: {current_user.role}\n\nYou can edit your profile details and avatar in the **Profile** page!"


# =========================================================
# NOTIFICATION AGENT
# =========================================================

def notification_agent_execute(db: Session, current_user: User) -> str:
    notifs = db.query(Notification).filter(Notification.user_id == current_user.id).order_by(Notification.created_at.desc()).limit(5).all()
    if not notifs:
        return "Notification Agent: You have no new notifications at this time."

    resp = f"Notification Agent: You have {len(notifs)} recent notifications:\n\n"
    for n in notifs:
        unread_mark = "[NEW] " if not n.is_read else ""
        resp += f"{unread_mark}**{n.title}**: {n.message}\n"
    return resp


# =========================================================
# SUPERVISOR / ORCHESTRATOR ROUTING
# =========================================================

@router.post("", response_model=ChatResponse)
async def chat_with_agent(
    req: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    prompt_lower = req.prompt.lower().strip()

    # Accumulate conversational context across turns
    context_filters = extract_context_filters(req.prompt, req.history)

    # 1. Routing: Watchlist Agent
    if any(k in prompt_lower for k in ["watchlist", "save to watch", "saved movies"]):
        text, movies = watchlist_agent_execute(req.prompt, db, current_user)
        return ChatResponse(response=text, agent="Watchlist Agent", movies=movies)

    # 2. Routing: Content Planning Agent (plan movies, weekend marathon, etc.)
    if any(k in prompt_lower for k in ["plan movies", "movie plan", "weekend", "schedule", "7-day", "what should i watch", "marathon", "watch tonight"]):
        text, movies = content_planning_agent_execute(req.prompt)
        return ChatResponse(response=text, agent="Content Planning Agent", movies=movies)

    # 3. Routing: Payment & Subscription Agent
    if any(k in prompt_lower for k in ["subscription", "subscribe", "payment", "pricing", "how much", "membership", "upgrade", "billing", "plans", "cost of"]):
        text, action = payment_agent_execute(req.prompt, db, current_user)
        return ChatResponse(response=text, agent="Payment & Subscription Agent", action=action)

    # 4. Routing: Music Agent
    if any(k in prompt_lower for k in ["music", "song", "album", "artist", "track", "listen", "playlist", "rahman", "zimmer", "anirudh", "coldplay"]):
        text = music_agent_execute(req.prompt, db)
        return ChatResponse(response=text, agent="Music Agent")

    # 5. Routing: Profile Agent
    if any(k in prompt_lower for k in ["my profile", "account", "settings", "my email", "change language", "preferred language", "avatar"]):
        text = profile_agent_execute(req.prompt, db, current_user)
        return ChatResponse(response=text, agent="Profile Agent")

    # 6. Routing: Notification Agent
    if any(k in prompt_lower for k in ["notification", "alert", "unread", "messages"]):
        text = notification_agent_execute(db, current_user)
        return ChatResponse(response=text, agent="Notification Agent")

    # 7. Routing: Movie Agent with verified runtime / context filters (Language, Genre, Runtime)
    if (
        context_filters.get("max_runtime")
        or context_filters.get("genre")
        or context_filters.get("language")
        or context_filters.get("min_rating")
        or any(k in prompt_lower for k in ["movie", "film", "cinema", "show me", "give me", "find", "top 10", "comedy", "action", "tamil", "hindi"])
    ):
        text, movies = movie_agent_execute(context_filters, req.prompt)
        return ChatResponse(response=text, agent="Movie Agent", movies=movies)

    # 8. Routing: Recommendation Agent
    if any(k in prompt_lower for k in ["similar", "recommend", "based on my", "like interstellar"]):
        text, movies = recommendation_agent_execute(req.prompt, db, current_user)
        return ChatResponse(response=text, agent="Recommendation Agent", movies=movies)

    # 9. Fallback to Groq LLM (with custom httpx client to bypass Windows SSL issues)
    try:
        api_key = os.environ.get("GROQ_API_KEY")
        if api_key and api_key != "your_groq_api_key_here":
            from langchain_groq import ChatGroq
            http_client = httpx.Client(verify=False)
            llm = ChatGroq(
                api_key=api_key,
                model_name="openai/gpt-oss-20b",
                temperature=0.3,
                http_client=http_client
            )
            ai_msg = llm.invoke(
                f"You are the StreamHub OTT AI Assistant. Assist the user briefly with their OTT/streaming request: {req.prompt}"
            )
            return ChatResponse(response=ai_msg.content, agent="StreamHub Supervisor")
    except Exception as e:
        print(f"Groq LLM call error: {e}")

    # General Supervisor default response
    return ChatResponse(
        response="StreamHub Supervisor AI: I can help you find movies by runtime (e.g. 'under 1 hour'), discover Tamil/Hindi films, manage your watchlist, explore the music catalog, or check your subscription plans. What would you like to explore?",
        agent="StreamHub Supervisor"
    )
