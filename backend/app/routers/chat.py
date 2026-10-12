import os
import re
import uuid
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException
import httpx
from pydantic import BaseModel
from sqlalchemy.orm import Session
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool

from app.database import get_db
from app.dependencies import get_current_user, get_optional_current_user
from app.models import User, ChatConversation, ChatMessage
from app.schemas import (
    ChatMessageResponse,
    ChatConversationSummary,
    ChatConversationDetail,
    CreateConversationRequest,
    UpdateConversationRequest
)
from app.routers.tmdb import tmdb_get
from app.tools.subtitle_rag_tools import answer_movie_subtitle_question

router = APIRouter(prefix="/chat", tags=["Chatbot"])


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
    conversation_id: Optional[int] = None
    history: Optional[List[Any]] = None
    state: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    conversation_id: Optional[int] = None
    type: str = "text"
    agent: str = "StreamHub Agent"
    response: str
    query: Optional[str] = None
    state: Optional[Dict[str, Any]] = None
    results: Optional[List[Dict[str, Any]]] = None
    movies: Optional[List[Dict[str, Any]]] = None
    songs: Optional[List[Dict[str, Any]]] = None
    action: Optional[Dict[str, Any]] = None
    data: Optional[Dict[str, Any]] = None
    sources: Optional[List[Dict[str, Any]]] = None


def generate_conversation_title(prompt: str) -> str:
    cleaned = re.sub(r'["\'“‘”’\?\.\!]', '', prompt).strip()
    if not cleaned:
        return "New Chat"

    q_lower = cleaned.lower()

    # 1. "Who directed <Movie>?" or "Director of <Movie>" -> "<Movie> Movie Details"
    m_dir = re.search(r'^(?:who\s+directed|director\s+of)\s+(.+)$', q_lower)
    if m_dir:
        entity = m_dir.group(1).strip().title()
        return f"{entity} Movie Details"[:35]

    # 2. "Tell me about <Movie>" or "Details of <Movie>" -> "<Movie> Details"
    m_tell = re.search(r'^(?:tell\s+me\s+about|details\s+of|what\s+is\s+the\s+plot\s+of|what\s+is|show\s+info\s+for)\s+(.+)$', q_lower)
    if m_tell:
        entity = m_tell.group(1).strip().title()
        return f"{entity} Details"[:35]

    # 3. "Recommend <X> movies..." or "Suggest <X> movies..." -> "<X> Movie Recommendations"
    m_rec = re.search(r'^(?:recommend|suggest|show\s+me|find\s+me)\s+(.+?)(?:\s+movies|\s+films)?(?:\s+under\s+\d+\s*(?:hours|hrs|hr|m|minutes))?$', q_lower)
    if m_rec and any(w in q_lower for w in ['movie', 'film', 'recommend', 'suggest']):
        sub = m_rec.group(1).strip()
        sub = re.sub(r'^(?:me\s+|some\s+)', '', sub, flags=re.I).strip().title()
        if sub:
            return f"{sub} Movie Recommendations"[:35]
        return "Movie Recommendations"

    # 4. "Find <X> music" or "Cinematic music..." -> "<X> Music Search"
    m_music = re.search(r'^(?:find|search|play|get|show)\s+(.+?)(?:\s+music|\s+songs)?$', q_lower)
    if m_music and any(w in q_lower for w in ['music', 'song', 'soundtrack']):
        sub = m_music.group(1).strip()
        sub = re.sub(r'^(?:me\s+|some\s+)', '', sub, flags=re.I).strip().title()
        if sub:
            return f"{sub} Music Search"[:35]
        return "Music Search"

    # 5. Fallback clean title
    words = cleaned.split()
    title = " ".join(words[:5])
    if len(title) > 35:
        title = title[:32] + "..."
    return title.title()


logger = logging.getLogger("chat_router")


# ----------------------------------------------------
# CONVERSATION MANAGEMENT ENDPOINTS
# ----------------------------------------------------

@router.get("/conversations", response_model=List[ChatConversationSummary])
def get_user_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Fetches all chat conversations belonging to the authenticated user."""
    trace_id = str(uuid.uuid4())[:8]
    logger.info(f"[Trace:{trace_id}] Listing chat conversations for user_id:{current_user.id}")
    convs = db.query(ChatConversation).filter(
        ChatConversation.user_id == current_user.id
    ).order_by(ChatConversation.updated_at.desc()).all()

    result = []
    for c in convs:
        cnt = db.query(ChatMessage).filter(ChatMessage.conversation_id == c.id).count()
        result.append(ChatConversationSummary(
            id=c.id,
            user_id=c.user_id,
            title=c.title,
            created_at=c.created_at,
            updated_at=c.updated_at,
            message_count=cnt
        ))
    logger.info(f"[Trace:{trace_id}] Retrieved {len(result)} conversations for user_id:{current_user.id}")
    return result


@router.post("/conversations", response_model=ChatConversationDetail)
def create_new_conversation(
    req: CreateConversationRequest = CreateConversationRequest(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Creates a new empty chat conversation for the authenticated user."""
    trace_id = str(uuid.uuid4())[:8]
    conv_title = req.title or "New Chat"
    logger.info(f"[Trace:{trace_id}] User:{current_user.id} creating new conversation '{conv_title}'")
    conv = ChatConversation(
        user_id=current_user.id,
        title=conv_title
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)
    logger.info(f"[Trace:{trace_id}] Created conversation_id:{conv.id} for user_id:{current_user.id}")
    return ChatConversationDetail(
        id=conv.id,
        user_id=conv.user_id,
        title=conv.title,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        messages=[]
    )


@router.get("/conversations/{conversation_id}", response_model=ChatConversationDetail)
def get_conversation_detail(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Fetches all messages in a conversation. Enforces strict user ownership."""
    trace_id = str(uuid.uuid4())[:8]
    logger.info(f"[Trace:{trace_id}] User:{current_user.id} requested conversation_id:{conversation_id}")
    conv = db.query(ChatConversation).filter(
        ChatConversation.id == conversation_id
    ).first()
    if not conv:
        logger.warning(f"[Trace:{trace_id}] Conversation:{conversation_id} not found in database")
        raise HTTPException(status_code=404, detail="Conversation not found")

    if conv.user_id != current_user.id:
        logger.warning(
            f"[Trace:{trace_id}] Ownership DENIED: Conversation:{conversation_id} belongs to user:{conv.user_id}, "
            f"but accessed by user:{current_user.id}"
        )
        raise HTTPException(status_code=403, detail="Not authorized to access this conversation")

    logger.info(f"[Trace:{trace_id}] Ownership GRANTED: Conversation:{conversation_id} belongs to user:{current_user.id}")

    messages = db.query(ChatMessage).filter(
        ChatMessage.conversation_id == conv.id
    ).order_by(ChatMessage.created_at.asc()).all()

    logger.info(f"[Trace:{trace_id}] Returning {len(messages)} messages for conversation_id:{conversation_id}")

    return ChatConversationDetail(
        id=conv.id,
        user_id=conv.user_id,
        title=conv.title,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        messages=[ChatMessageResponse.model_validate(m) for m in messages]
    )


@router.delete("/conversations/{conversation_id}")
def delete_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Deletes a conversation and cascades message deletions. Enforces strict user ownership."""
    trace_id = str(uuid.uuid4())[:8]
    logger.info(f"[Trace:{trace_id}] User:{current_user.id} requested deletion of conversation_id:{conversation_id}")
    conv = db.query(ChatConversation).filter(
        ChatConversation.id == conversation_id
    ).first()
    if not conv:
        logger.warning(f"[Trace:{trace_id}] Conversation:{conversation_id} not found for deletion")
        raise HTTPException(status_code=404, detail="Conversation not found")

    if conv.user_id != current_user.id:
        logger.warning(
            f"[Trace:{trace_id}] Deletion DENIED: Conversation:{conversation_id} belongs to user:{conv.user_id}, "
            f"not user:{current_user.id}"
        )
        raise HTTPException(status_code=403, detail="Not authorized to delete this conversation")

    logger.info(f"[Trace:{trace_id}] Ownership GRANTED: Deleting conversation_id:{conversation_id} and cascading messages")
    db.delete(conv)
    db.commit()
    logger.info(f"[Trace:{trace_id}] Conversation:{conversation_id} successfully deleted")
    return {"message": "Conversation deleted successfully"}


# ----------------------------------------------------
# TMDB AUTO-CORRECT SEARCH HELPER
# ----------------------------------------------------

def auto_correct_tmdb_search(query: str, params: dict = None) -> list:
    if params is None:
        params = {}
    params["query"] = query
    params["include_adult"] = "false"

    data = tmdb_get("/search/movie", params)
    if data.get("results"):
        return data["results"]

    fixed = re.sub(r'(.)\1+', r'\1', query, flags=re.IGNORECASE)
    if fixed != query:
        params["query"] = fixed
        data = tmdb_get("/search/movie", params)
        if data.get("results"):
            return data["results"]

    return []


# ----------------------------------------------------
# MULTI-AGENT SPECIALIZED TOOLS
# ----------------------------------------------------

@tool
def subtitle_rag_agent(question: str) -> str:
    """Invoked when the user asks about the story, plot, events, dialogue, quotes, timestamps, scenes, or characters of Interstellar (or any movie subtitle questions).
    Answers are grounded strictly in the spoken dialogue from the movie's subtitles with verified timestamps.
    """
    try:
        res = answer_movie_subtitle_question(question=question, movie_title="Interstellar")
        ans = res.get("answer", "This information is not available in the provided subtitles.")
        sources = res.get("sources", [])
        if sources and "not available in the provided subtitles" not in ans.lower():
            lines = []
            for s in sources[:3]:
                st = s.get("start_time")
                et = s.get("end_time")
                txt = s.get("text", "")
                if len(txt) > 85:
                    txt = txt[:82] + "..."
                lines.append(f"• `[{st} → {et}]` *\"{txt}\"*")
            if lines:
                ans += "\n\n**Subtitle Sources:**\n" + "\n".join(lines)
        return ans
    except Exception as e:
        return f"Subtitle RAG Agent Error: {str(e)}"


@tool
def profile_agent(action: Optional[str] = "view") -> str:
    """Invoked when the user asks about their personal profile, settings, account details, or name."""
    return "Profile Agent: Tell the user they can view or edit their profile and account details by clicking the User Icon in the top right corner of the Navbar."


@tool
def time_agent() -> str:
    """Invoked when the user asks for the current time, date, or day of the week."""
    now = datetime.now()
    return f"Time Agent: The current system time is {now.strftime('%I:%M %p on %A, %B %d, %Y')}."


@tool
def movie_agent_search(query: str, year: Optional[str] = None) -> str:
    """Invoked by the Movie Agent or Recommendation Agent when the user wants to search for specific movies."""
    params = {}
    if year:
        params["primary_release_year"] = year
    try:
        results = auto_correct_tmdb_search(query, params)
        if not results:
            return f"Movie Agent: No movies found on TMDB with that title."
        movies = []
        for r in results[:4]:
            p = f"https://image.tmdb.org/t/p/w200{r.get('poster_path')}" if r.get('poster_path') else ""
            img = f"![{r.get('title')}]({p})" if p else ""
            movies.append(f"{img} **{r.get('title')}** ({r.get('release_date', 'N/A')[:4]})")
        return "Movie Agent found these:\n\n" + "\n\n".join(movies)
    except Exception as e:
        return f"Movie Agent Error: {str(e)}"


@tool
def movie_agent_discover(genre: Optional[str] = None, language: Optional[str] = None, keyword: Optional[str] = None) -> str:
    """Invoked by the Movie Agent when asked to recommend or discover movies by genre, language, or specific concept/vibe (e.g., 'relaxing', 'mind-bending', 'space', 'zombies', 'epic')."""
    params = {"sort_by": "popularity.desc"}

    genre_map = {"action": 28, "comedy": 35, "drama": 18, "horror": 27, "sci-fi": 878, "family": 10751, "romance": 10749, "thriller": 53, "animation": 16}
    if genre and genre.lower() in genre_map:
        params["with_genres"] = genre_map[genre.lower()]

    language_map = {"tamil": "ta", "telugu": "te", "hindi": "hi", "malayalam": "ml", "korean": "ko", "english": "en", "spanish": "es", "french": "fr"}
    if language and language.lower() in language_map:
        params["with_original_language"] = language_map[language.lower()]

    try:
        kw_status = ""
        if keyword:
            kw_data = tmdb_get("/search/keyword", {"query": keyword, "page": 1})
            if kw_data.get("results"):
                params["with_keywords"] = kw_data["results"][0]["id"]
            else:
                kw_status = f" (No TMDB concept exactly matches '{keyword}')"

        data = tmdb_get("/discover/movie", params)
        results = data.get("results", [])

        if not results and "with_keywords" in params:
            del params["with_keywords"]
            data = tmdb_get("/discover/movie", params)
            results = data.get("results", [])
            kw_status = f" (Note: Keyword '{keyword}' was too restrictive, showing relevant popular movies instead)"

        if not results:
            return "Movie Agent: Could not fetch recommendations for these filters."

        movies = []
        for r in results[:10]:
            p = f"https://image.tmdb.org/t/p/w200{r.get('poster_path')}" if r.get('poster_path') else ""
            img = f"![{r.get('title')}]({p})" if p else ""
            movies.append(f"{img} **{r.get('title')}** (Rating: {r.get('vote_average')}/10)")

        desc = []
        if language:
            desc.append(language.capitalize())
        if genre:
            desc.append(genre.capitalize())
        if keyword and not kw_status:
            desc.append(f"about '{keyword}'")
        desc_str = " ".join(desc) if desc else "popular"

        return f"Recommendation Agent found these top {desc_str} hits{kw_status}:\n\n" + "\n\n".join(movies)
    except Exception as e:
        return f"Recommendation Agent Error: {str(e)}"


@tool
def music_agent(query: Optional[str] = None, genre: Optional[str] = None) -> str:
    """Invoked when the user asks about songs, music, bands, playlists, artists, or soundtracks."""
    return (
        "The StreamHub Chat Assistant is focused on movies and TV shows. "
        "For streaming music, artists, and playlists, please visit the Music page in the top navigation bar."
    )


@tool
def actor_movie_search(actor_name: str) -> str:
    """Invoked when the user asks for movies starring a specific actor or actress."""
    try:
        actor_data = tmdb_get("/search/person", {"query": actor_name})
        results = actor_data.get("results", [])
        if not results:
            return f"Actor Agent: Could not find any actor named {actor_name}."
        person_id = results[0].get("id")
        person_name = results[0].get("name")

        data = tmdb_get(f"/person/{person_id}/movie_credits")
        cast_roles = data.get("cast", [])

        filtered = [
            m for m in cast_roles
            if m.get("character") is not None
            and "cameo" not in m.get("character").lower()
            and "uncredited" not in m.get("character").lower()
            and "special appearance" not in m.get("character").lower()
            and "himself" not in m.get("character").lower()
        ]
        if not filtered:
            filtered = cast_roles

        filtered.sort(key=lambda x: x.get("vote_count", 0), reverse=True)
        movies_results = filtered[:20]

        if not movies_results:
            return f"Actor Agent: No movies found for {person_name}."

        movies = []
        for r in movies_results:
            p = f"https://image.tmdb.org/t/p/w200{r.get('poster_path')}" if r.get('poster_path') else ""
            img = f"![{r.get('title')}]({p})" if p else ""
            movies.append(f"{img} **{r.get('title')}** (Rating: {r.get('vote_average')}/10, Role: {r.get('character')})")
        return f"Actor Agent found top {len(movies)} movies for {person_name}:\n\n" + "\n\n".join(movies)
    except Exception as e:
        return f"Actor Agent Error: {str(e)}"


@tool
def director_movie_search(director_name: str) -> str:
    """Invoked when the user asks for movies directed by a specific director."""
    try:
        actor_data = tmdb_get("/search/person", {"query": director_name})
        results = actor_data.get("results", [])
        if not results:
            return f"Director Agent: Could not find any director named {director_name}."
        person_id = results[0].get("id")
        person_name = results[0].get("name")

        data = tmdb_get(f"/person/{person_id}/movie_credits")
        crew_roles = data.get("crew", [])
        filtered = [m for m in crew_roles if m.get("job") and m.get("job").lower() == "director"]
        filtered.sort(key=lambda x: x.get("vote_count", 0), reverse=True)
        movies_results = filtered[:20]

        if not movies_results:
            return f"Director Agent: No directed movies found for {person_name}."

        movies = []
        for r in movies_results:
            p = f"https://image.tmdb.org/t/p/w200{r.get('poster_path')}" if r.get('poster_path') else ""
            img = f"![{r.get('title')}]({p})" if p else ""
            movies.append(f"{img} **{r.get('title')}** (Rating: {r.get('vote_average')}/10)")
        return f"Director Agent found top {len(movies)} directed by {person_name}:\n\n" + "\n\n".join(movies)
    except Exception as e:
        return f"Director Agent Error: {str(e)}"


@tool
def tv_show_agent(query: str) -> str:
    """Invoked when the user wants to search for TV shows, series, or web series."""
    try:
        data = tmdb_get("/search/tv", {"query": query, "include_adult": "false"})
        results = data.get("results", [])
        if not results:
            return "TV Show Agent: No TV shows found with that name."
        shows = []
        for r in results[:4]:
            p = f"https://image.tmdb.org/t/p/w200{r.get('poster_path')}" if r.get('poster_path') else ""
            img = f"![{r.get('name')}]({p})" if p else ""
            shows.append(f"{img} **{r.get('name')}** ({r.get('first_air_date', 'N/A')[:4]})")
        return "TV Show Agent found these series:\n\n" + "\n\n".join(shows)
    except Exception as e:
        return f"TV Show Agent Error: {str(e)}"


@tool
def rating_agent(min_rating: Optional[float] = None, genre: Optional[str] = None) -> str:
    """Invoked when the user asks to show movies according to ratings, highest rated movies, or top-rated movies."""
    params = {
        "sort_by": "vote_average.desc",
        "vote_count.gte": 1000,
        "include_adult": "false"
    }

    genre_map = {"action": 28, "comedy": 35, "drama": 18, "horror": 27, "sci-fi": 878, "family": 10751, "romance": 10749, "thriller": 53, "animation": 16}
    if genre and genre.lower() in genre_map:
        params["with_genres"] = genre_map[genre.lower()]

    if min_rating:
        params["vote_average.gte"] = min_rating

    try:
        data = tmdb_get("/discover/movie", params)
        results = data.get("results", [])
        if not results:
            return "Rating Agent: Could not fetch highly rated movies for the given criteria."

        movies = []
        for r in results[:10]:
            p = f"https://image.tmdb.org/t/p/w200{r.get('poster_path')}" if r.get('poster_path') else ""
            img = f"![{r.get('title')}]({p})" if p else ""
            movies.append(f"{img} **{r.get('title')}** (Rating: {r.get('vote_average')}/10, Votes: {r.get('vote_count')})")

        desc = "Top Rated Movies"
        if genre:
            desc += f" in {genre.capitalize()}"
        if min_rating:
            desc += f" above {min_rating} stars"

        return f"Rating Agent found these {desc}:\n\n" + "\n\n".join(movies)
    except Exception as e:
        return f"Rating Agent Error: {str(e)}"


@tool
def movie_details_agent(movie_name: str) -> str:
    """Invoked when the user asks for the cast, crew, director, actors, or plot of a specific movie.
    Important: Correct obvious spelling mistakes before passing the movie_name, but respect the exact name if the user insists.
    """
    try:
        results = auto_correct_tmdb_search(movie_name)
        if not results:
            return f"Movie Details Agent: Could not find any movie named '{movie_name}'."

        movie = results[0]
        movie_id = movie.get("id")
        title = movie.get("title")
        year = movie.get("release_date", "")[:4]

        credits = tmdb_get(f"/movie/{movie_id}/credits")
        cast = credits.get("cast", [])[:10]
        crew = credits.get("crew", [])

        director = next((c.get("name") for c in crew if c.get("job") == "Director"), "Unknown")
        cast_names = ", ".join([f"{c.get('name')} (as {c.get('character')})" for c in cast])

        return f"**{title} ({year})**\n\n**Director**: {director}\n**Main Cast**: {cast_names}\n**Overview**: {movie.get('overview')}"
    except Exception as e:
        return f"Movie Details Agent Error: {str(e)}"


@tool
def similar_movies_agent(movie_name: str) -> str:
    """Invoked when the user asks for movies similar to a specific movie, or 'movies like [X]'."""
    try:
        results = auto_correct_tmdb_search(movie_name)
        if not results:
            return f"Similar Movies Agent: Could not find any movie named '{movie_name}' to base recommendations on."

        movie = results[0]
        movie_id = movie.get("id")
        title = movie.get("title")

        rec_data = tmdb_get(f"/movie/{movie_id}/recommendations")
        rec_results = rec_data.get("results", [])

        if not rec_results:
            rec_data = tmdb_get(f"/movie/{movie_id}/similar")
            rec_results = rec_data.get("results", [])

        if not rec_results:
            return f"Similar Movies Agent: Found '{title}' but TMDB has no similar movies for it."

        movies = []
        for r in rec_results[:10]:
            p = f"https://image.tmdb.org/t/p/w200{r.get('poster_path')}" if r.get('poster_path') else ""
            img = f"![{r.get('title')}]({p})" if p else ""
            movies.append(f"{img} **{r.get('title')}** (Rating: {r.get('vote_average')}/10)")

        return f"Similar Movies Agent found these movies like **{title}**:\n\n" + "\n\n".join(movies)
    except Exception as e:
        return f"Similar Movies Agent Error: {str(e)}"


# ----------------------------------------------------
# MAIN CHAT ROUTER ENDPOINT
# ----------------------------------------------------

@router.post("", response_model=ChatResponse)
async def chat_with_agent(
    req: ChatRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """
    StreamHub Multi-Agent Chat Endpoint.
    - Seamlessly supports both unauthenticated guests and logged-in users (no 401 error).
    - Features all specialized sub-agents: Subtitle RAG Agent, Movie Agent, Actor Agent, Director Agent,
      TV Show Agent, Rating Agent, Details Agent, Similar Movies Agent, Profile Agent, Time Agent, Music Agent.
    - Grounded in real TMDB and ChromaDB Subtitle RAG.
    - Persists conversations and messages in MySQL for authenticated users with strict user isolation.
    """
    prompt = (req.prompt or "").strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt cannot be empty.")

    # 1. Manage Conversation Persistence
    conv = None
    history_context = []
    if current_user:
        trace_id = str(uuid.uuid4())[:8]
        if req.conversation_id:
            logger.info(f"[Trace:{trace_id}] User:{current_user.id} sending message in conversation_id:{req.conversation_id}")
            conv = db.query(ChatConversation).filter(
                ChatConversation.id == req.conversation_id
            ).first()
            if not conv:
                logger.warning(f"[Trace:{trace_id}] Conversation:{req.conversation_id} not found in database")
                raise HTTPException(status_code=404, detail="Conversation not found")
            if conv.user_id != current_user.id:
                logger.warning(
                    f"[Trace:{trace_id}] Ownership DENIED: Conversation:{req.conversation_id} belongs to user:{conv.user_id}, "
                    f"attempted by user:{current_user.id}"
                )
                raise HTTPException(status_code=403, detail="Not authorized to access this conversation")
            logger.info(f"[Trace:{trace_id}] Ownership GRANTED: continuing conversation_id:{req.conversation_id}")
        else:
            # Create a brand new conversation explicitly for this message
            conv_title = generate_conversation_title(prompt)
            logger.info(f"[Trace:{trace_id}] User:{current_user.id} creating new conversation '{conv_title}'")
            conv = ChatConversation(
                user_id=current_user.id,
                title=conv_title
            )
            db.add(conv)
            db.commit()
            db.refresh(conv)
            logger.info(f"[Trace:{trace_id}] Created new conversation_id:{conv.id} for user_id:{current_user.id}")

        # Persist user message
        user_msg = ChatMessage(
            conversation_id=conv.id,
            role="user",
            content=prompt
        )
        db.add(user_msg)
        conv.updated_at = datetime.utcnow()
        db.commit()

        # Fetch bounded multi-turn context (last 15 messages)
        recent_db_msgs = db.query(ChatMessage).filter(
            ChatMessage.conversation_id == conv.id
        ).order_by(ChatMessage.created_at.desc()).limit(15).all()
        history_context = [
            {"role": m.role, "content": m.content, "agent_name": m.agent_name}
            for m in reversed(recent_db_msgs)
        ]
    else:
        # Unauthenticated guest
        if req.history:
            for h in req.history[-15:]:
                if isinstance(h, dict):
                    history_context.append({
                        "role": h.get("role") or h.get("sender") or "user",
                        "content": h.get("content") or h.get("text") or ""
                    })

    # Execute multi-agent LangGraph workflow
    try:
        from app.graph.workflow import movie_assistant_graph
        mid = None
        m_title = None
        if req.state and isinstance(req.state, dict):
            if req.state.get("movie_id"):
                mid = str(req.state.get("movie_id"))
            if req.state.get("movie_title"):
                m_title = str(req.state.get("movie_title"))

        graph_input = {
            "query": prompt,
            "selected_movie_id": mid,
            "selected_movie_title": m_title,
            "user_id": str(current_user.id) if current_user else None,
            "conversation_history": history_context
        }
        res = movie_assistant_graph.invoke(graph_input)

        intent = res.get("intent", "TITLE_SEARCH")
        final_ans = res.get("final_answer") or res.get("draft_answer") or "I could not generate an answer."
        agent_name = res.get("agent", "StreamHub Agent")

        msg_type = "text"
        results = res.get("recommendation_candidates", [])
        movies = res.get("recommendation_candidates", [])

        if intent in ["SUBTITLE_QA", "TIMELINE_QA"]:
            agent_name = "Subtitle RAG Agent"
            msg_type = "subtitle_qa"
        elif intent in ["TITLE_SEARCH", "MOVIE_SEARCH", "TV_SEARCH", "MULTI_SEARCH", "SIMILAR_TITLES"]:
            agent_name = "Title Search Agent"
            if results:
                msg_type = "movie_results"
        elif intent in ["MOVIE_METADATA", "TV_METADATA", "CREDITS_QUERY"]:
            agent_name = "Movie Metadata Agent"
            if results:
                msg_type = "movie_results"
        elif intent == "RECOMMENDATION":
            agent_name = "Recommendation Agent"
            msg_type = "movie_results"
        elif intent == "FILTERED_DISCOVERY":
            agent_name = "Discovery Agent"
            msg_type = "movie_results"
        elif intent == "WATCHLIST_ACTION":
            agent_name = "Watchlist Agent"
        elif intent in ["MUSIC_SEARCH", "MUSIC_RECOMMENDATION", "MOVIE_MUSIC"]:
            agent_name = "StreamHub Agent"
            if results:
                msg_type = "movie_results"
            else:
                msg_type = "text"
        elif intent == "COMBINED_MOVIE_MUSIC":
            agent_name = "Recommendation Agent"
            msg_type = "movie_results"

        # Update conversation state with newly resolved entity
        updated_state = dict(req.state or {})
        if res.get("selected_movie_id"):
            updated_state["movie_id"] = res.get("selected_movie_id")
        if res.get("selected_movie_title"):
            updated_state["movie_title"] = res.get("selected_movie_title")

        # Persist assistant message in MySQL if conversation exists
        if conv:
            assistant_msg = ChatMessage(
                conversation_id=conv.id,
                role="assistant",
                content=final_ans,
                agent_name=agent_name
            )
            db.add(assistant_msg)
            conv.updated_at = datetime.utcnow()
            db.commit()

        evidence = res.get("retrieved_evidence", [])
        return ChatResponse(
            conversation_id=conv.id if conv else None,
            response=final_ans,
            agent=agent_name,
            type=msg_type,
            query=prompt,
            state=updated_state,
            results=results,
            movies=movies,
            songs=[],
            action=res.get("action"),
            sources=evidence
        )
    except Exception as e:
        print(f"Graph invocation failed, falling back to react agent: {e}")

    try:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key or api_key == "your_groq_api_key_here":
            return ChatResponse(
                conversation_id=conv.id if conv else None,
                response="GROQ API Key is missing. Please configure backend/.env"
            )

        http_client = httpx.Client(verify=False)

        # Primary model: qwen/qwen3.8-27b or openai/gpt-oss-20b
        model_name = "qwen/qwen3.8-27b"
        try:
            llm = ChatGroq(
                api_key=api_key,
                model_name=model_name,
                temperature=0.2,
                http_client=http_client
            )
        except Exception:
            llm = ChatGroq(
                api_key=api_key,
                model_name="openai/gpt-oss-20b",
                temperature=0.2,
                http_client=http_client
            )

        tools = [
            subtitle_rag_agent,
            profile_agent,
            time_agent,
            movie_agent_search,
            movie_agent_discover,
            music_agent,
            actor_movie_search,
            director_movie_search,
            tv_show_agent,
            rating_agent,
            movie_details_agent,
            similar_movies_agent
        ]

        agent_executor = create_react_agent(llm, tools=tools)

        system_instruction = SystemMessage(content=(
            "You are the StreamHub Supervisor AI. Your primary crucial role is to intelligently route the user's intent "
            "to one of the specialized sub-agents: Subtitle RAG Agent, Profile Agent, Time Agent, Movie Search Agent, Actor Agent, Director Agent, TV Show Agent, Rating Agent, Movie Details Agent, Similar Movies Agent, Movie Recommendation Agent, or Music Agent.\n\n"
            "CRITICAL AGENT RULES:\n"
            "1. SUBTITLE RAG FOR INTERSTELLAR: If the user asks about the story, plot, events, dialogue, quotes, timestamps, scenes, or characters of Interstellar, call 'subtitle_rag_agent'. Do NOT invent facts.\n"
            "2. If user asks for who directed Interstellar, call 'director_movie_search' or 'movie_details_agent'. If user asks for similar movies, call 'similar_movies_agent'.\n"
            "3. If user asks for movies by language, genre, or vibe, call 'movie_agent_discover'.\n"
            "4. ALWAYS call a tool to get verified facts. If a tool explicitly says no results, apologize naturally without hallucinating facts.\n"
            "5. Users may misspell names. The tools auto-handle spelling fixes. However, if the user explicitly clarifies, use their provided spelling."
        ))

        response = agent_executor.invoke({
            "messages": [
                system_instruction,
                HumanMessage(content=prompt)
            ]
        })

        messages = response.get("messages", [])
        if messages:
            last_msg = messages[-1].content
        else:
            last_msg = "Supervisor AI: Sorry, I am out of ideas at the moment."

        # Detect which tool was called to set agent name
        agent_name = "StreamHub Agent"
        msg_type = "text"
        for m in messages:
            if hasattr(m, 'tool_calls') and m.tool_calls:
                t_name = m.tool_calls[0].get('name', '')
                if 'subtitle' in t_name:
                    agent_name = "Subtitle RAG Agent"
                    msg_type = "subtitle_qa"
                elif 'director' in t_name:
                    agent_name = "Director Agent"
                elif 'actor' in t_name:
                    agent_name = "Actor Agent"
                elif 'rating' in t_name:
                    agent_name = "Rating Agent"
                elif 'details' in t_name:
                    agent_name = "Movie Details Agent"
                elif 'tv' in t_name:
                    agent_name = "TV Show Agent"
                elif 'music' in t_name:
                    agent_name = "StreamHub Agent"
                elif 'time' in t_name:
                    agent_name = "Time Agent"
                elif 'profile' in t_name:
                    agent_name = "Profile Agent"
                elif 'discover' in t_name or 'search' in t_name:
                    agent_name = "Movie Agent"
                    msg_type = "movie_results"

        # Persist assistant message in MySQL if conversation exists
        if conv:
            assistant_msg = ChatMessage(
                conversation_id=conv.id,
                role="assistant",
                content=last_msg,
                agent_name=agent_name
            )
            db.add(assistant_msg)
            conv.updated_at = datetime.utcnow()
            db.commit()

        return ChatResponse(
            conversation_id=conv.id if conv else None,
            response=last_msg,
            agent=agent_name,
            type=msg_type,
            query=prompt
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))