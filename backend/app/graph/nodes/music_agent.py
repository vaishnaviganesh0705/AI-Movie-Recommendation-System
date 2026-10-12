"""
Music Handler Node for LangGraph.
Focuses the StreamHub Agent Chat strictly on movie and TV content.
Redirects general music and song requests to the dedicated Music page in the navigation bar.
Ensures no music recommendations, song cards, or Spotify API status warnings appear in the Chat interface.
"""
import re
import logging
from typing import Dict, Any, List, Optional

from app.graph.state import AgentGraphState
from app.services.entity_resolver import resolve_tmdb_entity
from app.services.tmdb_service import get_movie_details, discover_movies

logger = logging.getLogger("music_agent")


def music_agent_node(state: AgentGraphState) -> AgentGraphState:
    """
    Handles any music-related queries routed to the agent by keeping the chat model
    focused strictly on movies, TV shows, and TMDB information, while directing music
    requests to the standalone Music navigation page.
    """
    state.agent = "StreamHub Agent"
    intent = state.intent or "MUSIC_RECOMMENDATION"
    query = state.query.strip()
    query_lower = query.lower()

    # Clear any song candidates so no music cards or Spotify data appear in chat
    state.song_candidates = []

    # ---------------------------------------------------------
    # FLOW 1: MOVIE WITH MUSIC QUERY
    # e.g. "Recommend songs for Interstellar", "Recommend songs for Leo", "Songs for Dune"
    # ---------------------------------------------------------
    if intent == "MOVIE_MUSIC" or re.search(r'(?:for|from|of)\s+([^,\?]+)', query_lower):
        target_movie = state.extracted_title or state.selected_movie_title
        if not target_movie:
            match = re.search(r'(?:for|of|from)\s+([^,\?]+)', query_lower)
            if match:
                target_movie = match.group(1).strip()

        # Resolve movie via TMDB
        resolved = resolve_tmdb_entity(target_movie, media_type_hint="movie") if target_movie else {}
        movie_details = None
        if resolved.get("status") == "verified" and resolved.get("tmdb_id"):
            movie_details = get_movie_details(resolved["tmdb_id"])
        elif resolved.get("candidates") and len(resolved["candidates"]) > 0:
            top_cand = resolved["candidates"][0]
            cand_id = top_cand.get("id") or top_cand.get("tmdb_id")
            if cand_id:
                movie_details = get_movie_details(cand_id)

        if not movie_details and target_movie:
            from app.services.tmdb_service import search_movies
            s_res = search_movies(target_movie)
            if s_res and len(s_res) > 0:
                movie_details = get_movie_details(s_res[0]["id"])

        if movie_details:
            m_title = movie_details.get("title", target_movie)
            m_year = (movie_details.get("release_date") or "")[:4]
            genres_list = [g.get("name") for g in movie_details.get("genres", []) if g.get("name")]
            genres_str = ", ".join(genres_list) if genres_list else "Cinema"
            runtime = movie_details.get("runtime")
            runtime_str = f" | Runtime: {runtime} mins" if runtime else ""
            rating = movie_details.get("vote_average")
            rating_str = f"★ {round(rating, 1)}/10" if rating else ""
            overview = movie_details.get("overview", "No synopsis available.")

            state.selected_movie_id = str(movie_details.get("id")) if movie_details.get("id") else None
            state.selected_movie_title = m_title
            state.recommendation_candidates = [movie_details]

            state.final_answer = (
                f"🎬 **{m_title}** ({m_year})\n"
                f"{rating_str}{runtime_str} | Genres: {genres_str}\n\n"
                f"**Overview:**\n"
                f"{overview}\n\n"
                f"💡 *Note: The Agent Chat is focused on movie and TV recommendations, details, cast, and plot information. "
                f"To listen to songs and soundtrack playlists, please visit the **Music** page in the navigation bar.*"
            )
            state.validation_passed = True
            return state

    # ---------------------------------------------------------
    # FLOW 2: COMBINED MOVIE + MUSIC
    # e.g. "Give me movies and songs for tonight", "Suggest a movie and matching songs"
    # ---------------------------------------------------------
    if intent == "COMBINED_MOVIE_MUSIC":
        pop_res = discover_movies(page=1, sort_by="popularity.desc")
        rec_movie = None
        if isinstance(pop_res, list) and len(pop_res) > 0:
            rec_movie = pop_res[0]
        elif isinstance(pop_res, dict) and pop_res.get("results"):
            rec_movie = pop_res["results"][0]

        if rec_movie:
            state.recommendation_candidates = [rec_movie]
            m_title = rec_movie.get("title", "Popular Movie")
            m_year = (rec_movie.get("release_date") or "")[:4]
            m_rating = rec_movie.get("vote_average", 8.0)
            overview = rec_movie.get("overview", "")
            state.final_answer = (
                f"🎬 **Movie Recommendation:**\n"
                f"**{m_title}** ({m_year})\n"
                f"★ {m_rating}/10 | {overview}\n\n"
                f"💡 *To explore music playlists for your movie night, please check out the **Music** page in the top navigation bar.*"
            )
        else:
            state.final_answer = (
                "The StreamHub Chat Assistant is focused on movie and TV recommendations. "
                "For music playlists, please visit the **Music** page in the navigation bar!"
            )

        state.validation_passed = True
        return state

    # ---------------------------------------------------------
    # FLOW 3: WATCH HISTORY INQUIRY FOR MUSIC
    # e.g. "What music should I listen to based on my watch history?"
    # ---------------------------------------------------------
    if "watch history" in query_lower or "watched" in query_lower:
        state.final_answer = (
            "The StreamHub Chat Assistant focuses on movie and TV recommendations. Based on your watch history, "
            "I can suggest films and TV shows tailored to your taste.\n\n"
            "🎵 To discover music and soundtracks, please visit the **Music** page in the top navigation bar!\n\n"
            "Would you like movie recommendations based on what you have watched instead?"
        )
        state.validation_passed = True
        return state

    # ---------------------------------------------------------
    # FLOW 4: ARTIST OR SPECIFIC SONG SEARCH
    # e.g. "Find songs by A.R. Rahman", "Find Kesariya", "search for songs"
    # ---------------------------------------------------------
    if intent == "MUSIC_SEARCH" or re.search(r'\b(?:find|search)\b.*\b(?:song|songs?|track|tracks?)\b', query_lower):
        search_target = state.extracted_title
        artist_match = re.search(r'songs?\s+by\s+(.+)', query_lower)
        if artist_match:
            search_target = artist_match.group(1).strip()
        elif "kesariya" in query_lower:
            search_target = "Kesariya"
        elif not search_target:
            clean_q = re.sub(r'^(?:find|search(?:\s+for)?|play)\s+(?:the\s+)?(?:song\s+)?', '', query, flags=re.IGNORECASE).strip()
            search_target = clean_q or "music"

        state.final_answer = (
            f"The StreamHub Chat Assistant is specialized for movie and TV show queries—such as movie recommendations, "
            f"plot summaries, cast details, runtimes, genres, and trending films.\n\n"
            f"🎵 To search for and play tracks by **{search_target}**, please head over to the **Music** page in the top navigation bar!\n\n"
            f"Would you like movie recommendations based on a particular genre, actor, or mood instead?"
        )
        state.validation_passed = True
        return state

    # ---------------------------------------------------------
    # FLOW 5: MOOD, ACTIVITY, OR GENERAL MUSIC RECOMMENDATIONS
    # e.g. "Give me relaxing songs", "Recommend some songs", "songs for studying", "songs for gym"
    # ---------------------------------------------------------
    state.final_answer = (
        "The StreamHub Chat Assistant is specialized for movie and TV show queries—such as movie recommendations, "
        "plot summaries, cast details, runtimes, genres, and trending films.\n\n"
        "🎵 To discover and stream music playlists (relaxing tracks, workout beats, study vibes, and trending hits), "
        "please visit the **Music** page in the top navigation bar!\n\n"
        "Would you like movie recommendations for tonight instead?"
    )
    state.validation_passed = True
    return state
