import re
import os
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.activity import Watchlist, WatchHistory
from app.models.music import Artist, Song
from app.models.subscription import SubscriptionPlan, UserSubscription
from app.agents.state import ConversationState
from app.services.tmdb_service import MOVIE_GENRES, TV_GENRES, LANGUAGE_CODES
from app.tools import tmdb_tools, watchlist_tools, subtitle_rag_tools


def log_debug(user_query: str, intent: str, tool_name: str, tmdb_params: Any = None, candidates_count: int = 0, runtime_filter: str = "None", matches_count: int = 0):
    print("=" * 60)
    print(f"USER QUERY: {user_query}")
    print(f"INTENT: {intent}")
    print(f"SELECTED TOOL: {tool_name}")
    if tmdb_params is not None:
        print(f"TMDB REQUEST: {tmdb_params}")
    if candidates_count > 0:
        print(f"CANDIDATES: {candidates_count}")
    print(f"RUNTIME FILTER: {runtime_filter}")
    print(f"MATCHES: {matches_count}")
    print("=" * 60)


class StreamHubAgent:
    """
    Real TMDB-Grounded Data Agent that dynamically understands user intent,
    maintains structured conversational context, calls real TMDB tools,
    applies runtime/rating/genre/language filtering, and returns structured movie/TV results.
    """

    def parse_intent_and_entities(
        self,
        prompt: str,
        state: ConversationState,
        history: Optional[List[Dict[str, str]]] = None
    ) -> Tuple[str, Dict[str, Any]]:
        p = prompt.lower().strip()
        entities = {}

        # 1. Watchlist Intents
        if any(w in p for w in ["show my watchlist", "my watchlist", "what is in my watchlist", "view watchlist"]):
            return "WATCHLIST_VIEW", entities

        add_match = re.search(r'(?:add|save)\s+(?:the\s+)?(.*?)\s+to\s+(?:my\s+)?watchlist', p)
        if add_match:
            entities["movie_title"] = add_match.group(1).strip().strip('"\'')
            return "WATCHLIST_ADD", entities

        remove_match = re.search(r'(?:remove|delete)\s+(?:the\s+)?(.*?)(?:\s+from\s+(?:my\s+)?watchlist)?$', p)
        if ("remove" in p or "delete" in p) and "watchlist" in p:
            raw_title = remove_match.group(1).replace("from my watchlist", "").replace("from watchlist", "").strip().strip('"\'')
            entities["movie_title"] = raw_title
            return "WATCHLIST_REMOVE", entities

        if "is" in p and "in my watchlist" in p:
            check_match = re.search(r'is\s+(.*?)\s+in\s+(?:my\s+)?watchlist', p)
            if check_match:
                entities["movie_title"] = check_match.group(1).strip().strip('"\'')
                return "WATCHLIST_CHECK", entities

        # 1.5 Subtitle RAG Questions ("What did Cooper say?", "What happened around 1 hour?", etc.)
        subtitle_characters = [
            "cooper", "murph", "murphy", "brand", "amelia", "tars", "case", "romilly",
            "donald", "professor brand", "mann", "dr mann", "dr. mann", "getty", "doyle"
        ]
        dialogue_keywords = [
            "what did", "who said", "what was said", "what they said", "what were they saying",
            "did anyone mention", "talked about", "discuss", "conversation about", "say about",
            "say to", "spoke", "talking about", "tell me about that conversation", "what was the conversation",
            "first mentioned", "worried about", "tell me everything the subtitles say", "in the subtitle"
        ]
        temporal_keywords = [
            "around 30 minutes", "around 1 hour", "around one hour", "around 2 hours", "around 45 minutes",
            "between 01:", "between 00:", "at 01:", "at 00:", "near the beginning", "near the end",
            "what happened around", "what happened at", "what happened between"
        ]
        continuity_keywords = [
            "after that", "after this", "what happened next", "what did they say next",
            "before that", "before this", "who was talking", "what occurred next", "what did they talk about next"
        ]

        # 1.5 Subtitle RAG Questions ("Tell me about Interstellar", "What happened in Interstellar", "What did Cooper say?", "What happened around 1 hour?", etc.)
        subtitle_characters = [
            "cooper", "murph", "murphy", "brand", "amelia", "tars", "case", "romilly",
            "donald", "professor brand", "mann", "dr mann", "dr. mann", "getty", "doyle"
        ]
        dialogue_keywords = [
            "what did", "who said", "what was said", "what they said", "what were they saying",
            "did anyone mention", "talked about", "discuss", "conversation about", "say about",
            "say to", "spoke", "talking about", "tell me about that conversation", "what was the conversation",
            "first mentioned", "worried about", "tell me everything the subtitles say", "in the subtitle",
            "tell me about", "what is", "what happened", "story of", "plot of", "what happens",
            "explain", "mission", "wormhole", "ghost", "gravity", "black hole", "gargantua", "miller", "edmund"
        ]
        temporal_keywords = [
            "around 30 minutes", "around 1 hour", "around one hour", "around 2 hours", "around 45 minutes",
            "between 01:", "between 00:", "at 01:", "at 00:", "near the beginning", "near the end",
            "what happened around", "what happened at", "what happened between"
        ]
        continuity_keywords = [
            "after that", "after this", "what happened next", "what did they say next",
            "before that", "before this", "who was talking", "what occurred next", "what did they talk about next"
        ]

        metadata_keywords = [
            "who directed", "director of", "director", "who made", "directed by",
            "runtime of", "what is the runtime", "how long is", "duration of",
            "rating of", "vote count", "score of", "reviews of",
            "who acted in", "cast of", "actors in", "starring in", "actors of",
            "similar to", "movies like", "recommend movies like", "films like"
        ]

        is_sub_qa = False
        target_sub_movie = "Interstellar"
        is_interstellar_context = "interstellar" in p or (state and state.last_movie_title == "Interstellar")

        if is_interstellar_context:
            target_sub_movie = "Interstellar"
            # If asking about Interstellar and NOT asking purely for external TMDB metadata (director, runtime, cast, similar)
            if not any(k in p for k in metadata_keywords):
                is_sub_qa = True

        # Explicit character dialogue or scene question without movie name mentioned
        if not is_sub_qa and any(c in p for c in subtitle_characters):
            if not any(k in p for k in metadata_keywords):
                is_sub_qa = True

        # Multi-turn continuity from previous subtitle interaction
        if not is_sub_qa and any(k in p for k in continuity_keywords) and state and state.last_subtitle_chunk_index is not None:
            is_sub_qa = True

        if is_sub_qa:
            entities["movie_title"] = target_sub_movie
            return "SUBTITLE_QA", entities

        # 2. Movie Credits ("Who acted in...", "Cast of...")
        credits_match = re.search(r'(?:who\s+acted\s+in|cast\s+of|actors\s+in|starring\s+in)\s+(.*)', p)
        if credits_match:
            entities["movie_title"] = credits_match.group(1).replace("?", "").strip().strip('"\'')
            return "MOVIE_CREDITS", entities

        # 3. Movie Details ("Who directed...", "Runtime of...", "Tell me about...", "What is X about", "Plot of X")
        director_match = re.search(r'(?:who\s+directed|director\s+of)\s+(.*)', p)
        if director_match:
            entities["movie_title"] = director_match.group(1).replace("?", "").strip().strip('"\'')
            return "MOVIE_DETAILS", entities

        runtime_match = re.search(r'(?:what\s+is\s+the\s+runtime\s+of|runtime\s+of|how\s+long\s+is)\s+(.*)', p)
        if runtime_match:
            entities["movie_title"] = runtime_match.group(1).replace("?", "").strip().strip('"\'')
            return "MOVIE_DETAILS", entities

        details_match = re.search(r'(?:tell\s+me\s+about|what\s+is\s+(.*?)\s+about|overview\s+of|plot\s+of)\s*(.*)', p)
        if details_match:
            m_title = details_match.group(2) if details_match.group(2) else details_match.group(1)
            if m_title:
                entities["movie_title"] = m_title.replace("?", "").strip().strip('"\'')
                return "MOVIE_DETAILS", entities

        # 4. Similar Movies ("Movies similar to X", "Movies like X")
        similar_match = re.search(r'(?:similar\s+to|movies\s+like|like)\s+(.*)', p)
        if similar_match and not any(k in p for k in ["i like", "do you like"]):
            entities["movie_title"] = similar_match.group(1).replace("?", "").strip().strip('"\'')
            return "SIMILAR_MOVIES", entities

        # 5. Trending & Top Rated
        if any(w in p for w in ["trending movies", "trending now", "what is trending"]):
            return "TRENDING_MOVIES", entities

        if any(w in p for w in ["top rated movies", "top rated", "best rated movies", "highest rated movies"]) and not state.language and not state.genre_ids:
            return "TOP_RATED_MOVIES", entities

        # 6. Specific Search ("Search for X", "Find Spider-Man movies")
        search_match = re.search(r'(?:search\s+for|find)\s+(.*)', p)
        if search_match and not any(w in p for w in ["movies under", "movies rated", "comedy", "action", "tamil"]):
            raw_query = search_match.group(1).replace("movies", "").replace("movie", "").strip().strip('"\'')
            if raw_query:
                entities["search_query"] = raw_query
                return "SEARCH_MOVIE", entities

        # 7. Recommendations ("Recommend something for me", "What should I watch")
        if any(w in p for w in ["recommend something for me", "what should i watch", "recommend a movie for me", "surprise me"]):
            return "RECOMMEND_FOR_ME", entities

        # 8. Music Queries
        if any(w in p for w in ["music", "song", "album", "artist", "tracks", "rahman", "zimmer", "anirudh", "coldplay", "weeknd"]):
            return "MUSIC_QUERY", entities

        # 9. Subscription / Billing Queries
        if any(w in p for w in ["subscription", "pricing", "plans", "membership", "how much does it cost", "billing"]):
            return "SUBSCRIPTION_QUERY", entities

        # 10. Profile Queries
        if any(w in p for w in ["my profile", "account settings", "my email", "who am i"]):
            return "PROFILE_QUERY", entities

        # 11. TV Shows
        if any(w in p for w in ["tv shows", "tv series", "series", "season"]):
            return "DISCOVER_TV", entities

        # 12. Default to DISCOVER / FILTER MOVIES
        return "DISCOVER_MOVIES", entities

    def update_state_from_prompt(self, prompt: str, state: ConversationState) -> ConversationState:
        p = prompt.lower()

        # Check Language
        for lang_name, code in LANGUAGE_CODES.items():
            if lang_name in p:
                state.language = code
                state.language_name = lang_name.capitalize()
                break

        # Check Genres
        for g_name, g_id in MOVIE_GENRES.items():
            if g_name in p:
                if g_name not in state.genres:
                    state.genres.append(g_name)
                if g_id not in state.genre_ids:
                    state.genre_ids.append(g_id)

        # Check Runtime
        if re.search(r'(?:under|less than|within)\s*(?:1\s*hour|60\s*(?:mins|minutes))', p):
            state.min_runtime = None
            state.max_runtime = 60
        elif re.search(r'(?:under|less than|within)\s*(?:2\s*hours?|120\s*(?:mins|minutes))', p):
            state.min_runtime = None
            state.max_runtime = 120
        elif re.search(r'(?:over|more than|longer than)\s*(?:2\s*hours?|120\s*(?:mins|minutes))', p):
            state.min_runtime = 120
            state.max_runtime = None
        elif re.search(r'between\s*1\s*(?:and|to)\s*2\s*hours?', p) or re.search(r'between\s*60\s*(?:and|to)\s*120', p):
            state.min_runtime = 60
            state.max_runtime = 120

        # Check Rating
        rating_match = re.search(r'(?:rated\s+above|rating\s*(?:>|above|higher than))\s*(\d+(?:\.\d+)?)', p)
        if rating_match:
            state.min_rating = float(rating_match.group(1))

        # Check Year
        year_gte_match = re.search(r'(?:after|since|from)\s*(20\d\d)', p)
        if year_gte_match:
            state.year_gte = int(year_gte_match.group(1))

        year_exact_match = re.search(r'(?:from|in|year)\s*(20\d\d)', p)
        if year_exact_match and not year_gte_match:
            state.year = int(year_exact_match.group(1))

        # Check Sorting
        if any(w in p for w in ["highest rated", "top rated", "best rated", "highest rating"]):
            state.sort_by = "vote_average.desc"
            if not state.min_rating:
                state.min_rating = 6.0  # sensible quality threshold when sorting by rating
        elif any(w in p for w in ["most popular", "popular"]):
            state.sort_by = "popularity.desc"
        elif any(w in p for w in ["newest", "latest", "recent"]):
            state.sort_by = "primary_release_date.desc"

        return state

    def execute(
        self,
        prompt: str,
        state: ConversationState,
        db: Session,
        current_user: Optional[User] = None,
        history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Main execution pipeline:
        Intent Extraction -> Tool Selection -> Real TMDB/DB Query -> Verified Filtering -> Formatted Output.
        """
        intent, entities = self.parse_intent_and_entities(prompt, state, history)

        # Update cumulative structured state
        state = self.update_state_from_prompt(prompt, state)

        # -------------------------------------------------------------
        # 1. WATCHLIST INTENTS
        # -------------------------------------------------------------
        if intent == "WATCHLIST_VIEW":
            log_debug(prompt, intent, "tool_view_watchlist")
            if not current_user:
                return {
                    "type": "text",
                    "agent": "Watchlist Agent",
                    "response": "Please log in to your StreamHub account to view and manage your watchlist.",
                    "query": prompt,
                    "state": state.to_dict(),
                    "results": []
                }
            data = watchlist_tools.tool_view_watchlist(current_user.id, db)
            return {
                "type": "watchlist_results",
                "agent": "Watchlist Agent",
                "response": data["message"],
                "query": prompt,
                "state": state.to_dict(),
                "results": data["results"]
            }

        if intent == "WATCHLIST_ADD":
            if not current_user:
                return {
                    "type": "text",
                    "agent": "Watchlist Agent",
                    "response": "Please log in to your StreamHub account to add titles to your watchlist.",
                    "query": prompt,
                    "state": state.to_dict(),
                    "results": []
                }
            # If user refers to positional index e.g. "Add the second movie"
            title_ref = entities.get("movie_title", "")
            if "second" in title_ref.lower() and len(state.last_results) >= 2:
                title_ref = state.last_results[1].get("title") or state.last_results[1].get("id")
            elif "first" in title_ref.lower() and len(state.last_results) >= 1:
                title_ref = state.last_results[0].get("title") or state.last_results[0].get("id")

            log_debug(prompt, intent, "tool_add_to_watchlist", tmdb_params={"movie": title_ref})
            data = watchlist_tools.tool_add_to_watchlist(current_user.id, title_ref, db)
            return {
                "type": "action_result",
                "agent": "Watchlist Agent",
                "response": data["message"],
                "query": prompt,
                "state": state.to_dict(),
                "action": data
            }

        if intent == "WATCHLIST_REMOVE":
            if not current_user:
                return {
                    "type": "text",
                    "agent": "Watchlist Agent",
                    "response": "Please log in to your StreamHub account to manage your watchlist.",
                    "query": prompt,
                    "state": state.to_dict(),
                    "results": []
                }
            title_ref = entities.get("movie_title", "")
            log_debug(prompt, intent, "tool_remove_from_watchlist", tmdb_params={"movie": title_ref})
            data = watchlist_tools.tool_remove_from_watchlist(current_user.id, title_ref, db)
            return {
                "type": "action_result",
                "agent": "Watchlist Agent",
                "response": data["message"],
                "query": prompt,
                "state": state.to_dict(),
                "action": data
            }

        # -------------------------------------------------------------
        # 1.5 SUBTITLE RAG INTENT (Real Subtitle Q&A with timestamps)
        # -------------------------------------------------------------
        if intent == "SUBTITLE_QA":
            movie_title = entities.get("movie_title") or state.last_movie_title or "Interstellar"
            log_debug(
                user_query=prompt,
                intent=intent,
                tool_name="tool_answer_movie_subtitle_question",
                tmdb_params={"movie_title": movie_title}
            )

            rag_out = subtitle_rag_tools.answer_movie_subtitle_question(
                question=prompt,
                movie_title=movie_title,
                state=state.to_dict()
            )

            # Update conversation state with subtitle temporal memory
            state.last_movie_title = movie_title
            state_up = rag_out.get("state_update", {})
            if state_up:
                state.last_subtitle_chunk_index = state_up.get("last_subtitle_chunk_index")
                state.last_subtitle_seconds = state_up.get("last_subtitle_seconds")
                state.last_subtitle_start_time = state_up.get("last_subtitle_start_time")
                state.last_subtitle_end_time = state_up.get("last_subtitle_end_time")

            # Format source timestamps citation
            source_lines = []
            for s in rag_out.get("sources", [])[:3]:
                st = s.get("start_time")
                et = s.get("end_time")
                txt = s.get("text", "")
                if len(txt) > 90:
                    txt = txt[:87] + "..."
                source_lines.append(f"• `[{st} → {et}]` *\"{txt}\"*")

            sources_text = ""
            if source_lines and "not available in the provided subtitles" not in rag_out["answer"].lower():
                sources_text = "\n\n**Subtitle Sources:**\n" + "\n".join(source_lines)

            full_response = f"{rag_out['answer']}{sources_text}"

            # Fetch movie card details from TMDB so ChatModal can visually render the card
            interstellar_details = tmdb_tools.tool_movie_details(title=movie_title)
            movie_cards = [interstellar_details] if interstellar_details else []

            return {
                "type": "subtitle_qa",
                "agent": "Subtitle RAG Agent",
                "response": full_response,
                "query": prompt,
                "state": state.to_dict(),
                "sources": rag_out.get("sources", []),
                "results": movie_cards,
                "movies": movie_cards,
                "movie_title": movie_title,
                "data": rag_out
            }

        # -------------------------------------------------------------
        # 2. MOVIE DETAILS INTENT
        # -------------------------------------------------------------
        if intent == "MOVIE_DETAILS":
            m_title = entities.get("movie_title") or state.last_movie_title or prompt
            log_debug(prompt, intent, "tool_movie_details", tmdb_params={"title": m_title})
            details = tmdb_tools.tool_movie_details(title=m_title)
            
            if not details:
                return {
                    "type": "text",
                    "agent": "Movie Agent",
                    "response": f"TMDB does not provide information for '{m_title}'. I couldn't find that title on TMDB.",
                    "query": prompt,
                    "state": state.to_dict(),
                    "results": []
                }

            state.last_movie_id = details["id"]
            state.last_movie_title = details["title"]
            state.last_results = [details]

            # Construct factual summary strictly from TMDB data
            genres_str = ", ".join(details["genres"]) if details["genres"] else "Film"
            runtime_str = f"{details['runtime']} mins" if details.get("runtime") else "Runtime unlisted"
            rating_str = f"{details['rating']}/10" if details.get("rating") else "Unrated"
            director_str = f" directed by {details['director']}" if details.get("director") else ""

            text_resp = (
                f"**{details['title']}** ({details['release_date'][:4] if details['release_date'] else 'N/A'}){director_str} "
                f"is a {genres_str} with a TMDB rating of {rating_str} and runtime of {runtime_str}.\n\n"
                f"**Overview:** {details['overview'] or 'No synopsis available on TMDB.'}"
            )

            return {
                "type": "movie_details",
                "agent": "Movie Agent",
                "response": text_resp,
                "query": prompt,
                "state": state.to_dict(),
                "results": [details]
            }

        # -------------------------------------------------------------
        # 3. MOVIE CREDITS INTENT
        # -------------------------------------------------------------
        if intent == "MOVIE_CREDITS":
            m_title = entities.get("movie_title") or state.last_movie_title or prompt
            log_debug(prompt, intent, "tool_movie_credits", tmdb_params={"title": m_title})
            credits_data = tmdb_tools.tool_movie_credits(title=m_title)

            if not credits_data or not credits_data.get("cast"):
                return {
                    "type": "text",
                    "agent": "Movie Agent",
                    "response": f"TMDB does not list cast credits for '{m_title}'.",
                    "query": prompt,
                    "state": state.to_dict()
                }

            cast_list = ", ".join(credits_data["cast"][:6])
            dir_text = f" directed by **{credits_data['director']}**" if credits_data.get("director") else ""
            response_text = f"Top cast members for **{credits_data['title']}**{dir_text} according to TMDB: {cast_list}."

            return {
                "type": "credits_result",
                "agent": "Movie Agent",
                "response": response_text,
                "query": prompt,
                "state": state.to_dict(),
                "data": credits_data
            }

        # -------------------------------------------------------------
        # 4. SIMILAR MOVIES INTENT
        # -------------------------------------------------------------
        if intent == "SIMILAR_MOVIES":
            m_title = entities.get("movie_title") or state.last_movie_title or prompt
            log_debug(prompt, intent, "tool_similar_movies", tmdb_params={"title": m_title})
            similar_data = tmdb_tools.tool_similar_movies(title=m_title, limit=8)
            movies = similar_data.get("results", [])

            state.last_results = movies
            response_text = f"Here are movies similar to **{similar_data.get('title') or m_title}** retrieved from TMDB:"
            if not movies:
                response_text = f"TMDB did not find similar recommendations for '{m_title}'."

            return {
                "type": "movie_results",
                "agent": "Movie Agent",
                "response": response_text,
                "query": prompt,
                "state": state.to_dict(),
                "results": movies
            }

        # -------------------------------------------------------------
        # 5. TRENDING MOVIES
        # -------------------------------------------------------------
        if intent == "TRENDING_MOVIES":
            log_debug(prompt, intent, "tool_trending_movies")
            movies = tmdb_tools.tool_trending_movies(limit=10)
            state.last_results = movies
            return {
                "type": "movie_results",
                "agent": "Movie Agent",
                "response": "Here are the top trending movies right now on TMDB:",
                "query": prompt,
                "state": state.to_dict(),
                "results": movies
            }

        # -------------------------------------------------------------
        # 6. TOP RATED MOVIES
        # -------------------------------------------------------------
        if intent == "TOP_RATED_MOVIES":
            log_debug(prompt, intent, "tool_top_rated_movies")
            movies = tmdb_tools.tool_top_rated_movies(limit=10)
            state.last_results = movies
            return {
                "type": "movie_results",
                "agent": "Movie Agent",
                "response": "Here are the highest rated movies of all time on TMDB:",
                "query": prompt,
                "state": state.to_dict(),
                "results": movies
            }

        # -------------------------------------------------------------
        # 7. SEARCH MOVIES
        # -------------------------------------------------------------
        if intent == "SEARCH_MOVIE":
            query = entities.get("search_query") or prompt
            log_debug(prompt, intent, "tool_search_movies", tmdb_params={"query": query})
            movies = tmdb_tools.tool_search_movies(query=query, limit=10)
            state.last_search_query = query
            state.last_results = movies
            return {
                "type": "movie_results",
                "agent": "Movie Agent",
                "response": f"TMDB search results matching '{query}':",
                "query": prompt,
                "state": state.to_dict(),
                "results": movies
            }

        # -------------------------------------------------------------
        # 8. RECOMMENDATIONS ("Recommend something for me")
        # -------------------------------------------------------------
        if intent == "RECOMMEND_FOR_ME":
            # Inspect user history / watchlist for grounded recommendation if logged in
            history_entries = []
            if current_user:
                history_entries = db.query(WatchHistory).filter(WatchHistory.user_id == current_user.id).order_by(WatchHistory.last_watched_at.desc()).limit(3).all()

            if history_entries:
                fav_id = history_entries[0].tmdb_id
                movies = tmdb_tools.tool_similar_movies(movie_id=fav_id, limit=8).get("results", [])
                msg = "Based on your recent viewing history, here are recommendations from TMDB:"
            else:
                movies = tmdb_tools.tool_trending_movies(limit=8)
                msg = "Here are top-rated and trending recommendations to start your StreamHub journey:"

            state.last_results = movies
            return {
                "type": "movie_results",
                "agent": "Recommendation Agent",
                "response": msg,
                "query": prompt,
                "state": state.to_dict(),
                "results": movies
            }

        # -------------------------------------------------------------
        # 9. MUSIC QUERIES
        # -------------------------------------------------------------
        if intent == "MUSIC_QUERY":
            artists = db.query(Artist).all()
            matched_artist = next((a for a in artists if a.name.lower() in prompt.lower()), None)
            if matched_artist:
                songs = db.query(Song).filter(Song.artist_id == matched_artist.id).limit(5).all()
                res_list = [{"id": s.id, "title": s.title, "genre": s.genre, "artist_name": matched_artist.name} for s in songs]
                return {
                    "type": "music_results",
                    "agent": "Music Agent",
                    "response": f"Music Agent: Here are top tracks by **{matched_artist.name}** in the StreamHub catalog:",
                    "query": prompt,
                    "state": state.to_dict(),
                    "results": res_list
                }

            all_songs = db.query(Song).limit(6).all()
            res_list = [{"id": s.id, "title": s.title, "genre": s.genre, "artist_name": s.artist.name if s.artist else "Artist"} for s in all_songs]
            return {
                "type": "music_results",
                "agent": "Music Agent",
                "response": "Music Agent: Browse through popular tracks on StreamHub Music:",
                "query": prompt,
                "state": state.to_dict(),
                "results": res_list
            }

        # -------------------------------------------------------------
        # 10. SUBSCRIPTION & PAYMENT QUERIES
        # -------------------------------------------------------------
        if intent in ["SUBSCRIPTION_QUERY", "PAYMENT_QUERY"]:
            plans = db.query(SubscriptionPlan).all()
            plan_lines = "\n".join([f"• **{p.name}**: ${p.price}/mo — {p.features}" for p in plans])
            return {
                "type": "text",
                "agent": "Payment & Subscription Agent",
                "response": f"Here are the available StreamHub membership plans:\n\n{plan_lines}\n\nYou can subscribe or manage your plan on the **Subscription** page.",
                "query": prompt,
                "state": state.to_dict()
            }

        # -------------------------------------------------------------
        # 11. PROFILE QUERIES
        # -------------------------------------------------------------
        if intent == "PROFILE_QUERY":
            if not current_user:
                return {
                    "type": "text",
                    "agent": "Profile Agent",
                    "response": "Please log in to your StreamHub account to view your account details and profile information.",
                    "query": prompt,
                    "state": state.to_dict()
                }
            sub = db.query(UserSubscription).filter(UserSubscription.user_id == current_user.id, UserSubscription.status == "active").first()
            plan_name = sub.plan.name if sub and sub.plan else "Free Tier"
            return {
                "type": "text",
                "agent": "Profile Agent",
                "response": (
                    f"**Account Overview**:\n"
                    f"• Name: {current_user.name}\n"
                    f"• Email: {current_user.email}\n"
                    f"• Active Plan: {plan_name}\n"
                    f"• Preferred Language: {current_user.preferred_language or 'English'}\n\n"
                    f"You can update your avatar and details in the Profile page."
                ),
                "query": prompt,
                "state": state.to_dict()
            }

        # -------------------------------------------------------------
        # 12. TV DISCOVERY
        # -------------------------------------------------------------
        if intent == "DISCOVER_TV":
            log_debug(prompt, intent, "tool_discover_tv", tmdb_params=state.to_dict())
            tv_shows = tmdb_tools.tool_discover_tv(state, limit=8)
            state.last_results = tv_shows
            return {
                "type": "tv_results",
                "agent": "TV Agent",
                "response": "Here are TV series matching your criteria from TMDB:",
                "query": prompt,
                "state": state.to_dict(),
                "results": tv_shows
            }

        # -------------------------------------------------------------
        # 13. DISCOVER & FILTER MOVIES (Core Requirement: Languages, Genres, Runtime, Rating, Year)
        # -------------------------------------------------------------
        runtime_desc = "None"
        if state.max_runtime and state.min_runtime:
            runtime_desc = f"{state.min_runtime}-{state.max_runtime} mins"
        elif state.max_runtime:
            runtime_desc = f"< {state.max_runtime} mins"
        elif state.min_runtime:
            runtime_desc = f"> {state.min_runtime} mins"

        log_debug(
            user_query=prompt,
            intent="FILTER_MOVIES",
            tool_name="tool_discover_and_filter_movies",
            tmdb_params={
                "language": state.language,
                "genres": state.genres,
                "genre_ids": state.genre_ids,
                "year": state.year,
                "year_gte": state.year_gte,
                "min_rating": state.min_rating,
                "sort_by": state.sort_by
            },
            candidates_count=25,
            runtime_filter=runtime_desc
        )

        movies = tmdb_tools.tool_discover_and_filter_movies(state, limit=8)
        state.last_results = movies

        # Construct specific informative response heading
        descriptors = []
        if state.language_name:
            descriptors.append(state.language_name)
        if state.genres:
            descriptors.append("/".join(g.capitalize() for g in state.genres))
        if runtime_desc != "None":
            descriptors.append(f"under {state.max_runtime // 60}h" if state.max_runtime and state.max_runtime % 60 == 0 else runtime_desc)
        if state.min_rating:
            descriptors.append(f"rated > {state.min_rating}")
        if state.year_gte:
            descriptors.append(f"released after {state.year_gte}")
        elif state.year:
            descriptors.append(f"from {state.year}")

        query_summary = " ".join(descriptors) if descriptors else "popular"
        if movies:
            resp_heading = f"Here are {len(movies)} {query_summary} movies verified from TMDB:"
        else:
            resp_heading = f"No movies matching '{query_summary}' were found on TMDB with those exact filters."

        return {
            "type": "movie_results",
            "agent": "Movie Agent",
            "response": resp_heading,
            "query": prompt,
            "state": state.to_dict(),
            "results": movies
        }
