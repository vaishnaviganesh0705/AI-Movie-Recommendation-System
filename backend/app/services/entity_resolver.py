import re
import unicodedata
from typing import Optional, List, Dict, Any, Tuple
from rapidfuzz import fuzz

from app.services.tmdb_service import (
    search_movies,
    search_tv,
    search_multi,
    get_movie_details,
    get_tv_details,
    LANGUAGE_CODES
)


def normalize_title(title: str) -> str:
    """
    Normalizes titles:
    - Unicode normalization (NFKD)
    - Lowercase
    - Strip punctuation and extra whitespace
    """
    if not title:
        return ""
    # Normalize unicode
    nfkd = unicodedata.normalize('NFKD', title)
    ascii_text = "".join([c for c in nfkd if not unicodedata.combining(c)])
    # Lowercase
    lowered = ascii_text.lower()
    # Replace punctuation with spaces
    cleaned = re.sub(r'[^a-z0-9\s]', ' ', lowered)
    # Collapse multiple spaces
    return re.sub(r'\s+', ' ', cleaned).strip()


def calculate_match_score(
    candidate: Dict[str, Any],
    query_title: str,
    media_type_hint: Optional[str] = None,
    language_hint: Optional[str] = None,
    year_hint: Optional[int] = None,
    tmdb_index: int = 0
) -> float:
    """
    Multi-factor ranking score from 0.0 to 1.0.
    1. Exact normalized title match (40%)
    2. Original title match (20%)
    3. Media-type match (15%)
    4. Language match (10%)
    5. Year match (10%)
    6. Popularity & TMDB index bonus (5%)
    """
    norm_query = normalize_title(query_title)
    cand_title = candidate.get("title") or candidate.get("name") or ""
    cand_orig_title = candidate.get("original_title") or candidate.get("original_name") or ""
    cand_media = candidate.get("media_type") or ("movie" if "title" in candidate else "tv")
    cand_lang = candidate.get("original_language", "")
    
    # Release year extraction
    cand_date = candidate.get("release_date") or candidate.get("first_air_date") or ""
    cand_year = None
    if cand_date and len(cand_date) >= 4 and cand_date[:4].isdigit():
        cand_year = int(cand_date[:4])

    norm_cand_title = normalize_title(cand_title)
    norm_cand_orig = normalize_title(cand_orig_title)

    score = 0.0

    # 1. Title Similarity (up to 0.45)
    if norm_query == norm_cand_title:
        score += 0.45
        if norm_query == norm_cand_orig:
            score += 0.10
        else:
            score += 0.08  # International title matched query perfectly
    elif norm_query == norm_cand_orig:
        score += 0.50
    else:
        ratio1 = fuzz.token_sort_ratio(norm_query, norm_cand_title) / 100.0
        ratio2 = fuzz.ratio(norm_query, norm_cand_title) / 100.0
        score += max(ratio1, ratio2) * 0.40
        ratio_orig = fuzz.token_sort_ratio(norm_query, norm_cand_orig) / 100.0
        score += ratio_orig * 0.10

    # 2. Media Type Match (up to 0.15)
    if media_type_hint:
        if media_type_hint.lower() == cand_media.lower():
            score += 0.15
        elif media_type_hint.lower() in ["either", "unknown", "multi"]:
            score += 0.10
    else:
        score += 0.10  # Neutral

    # 3. Language Match (up to 0.15)
    if language_hint:
        mapped_lang = LANGUAGE_CODES.get(language_hint.lower(), language_hint.lower())
        if cand_lang.lower() == mapped_lang:
            score += 0.15
        else:
            score -= 0.10  # Demote candidate not matching explicitly requested language
    else:
        score += 0.05

    # 4. Year Match (up to 0.10)
    if year_hint and cand_year:
        if cand_year == year_hint:
            score += 0.10
        elif abs(cand_year - year_hint) == 1:
            score += 0.05
    elif not year_hint:
        score += 0.05

    # 5. Popularity & Vote Count Signal (up to 0.15)
    pop = candidate.get("popularity", 0.0) or 0.0
    vote_count = candidate.get("vote_count", 0) or 0
    import math
    if vote_count > 0:
        vote_bonus = min(0.12, (math.log10(max(1, vote_count)) / 4.5) * 0.12)
    else:
        vote_bonus = 0.0
    pop_bonus = min(0.03, (pop / 150.0) * 0.03)
    
    # TMDB relevance order bonus (first result gets small tiebreaker)
    rank_signal = max(0.0, 0.01 - (tmdb_index * 0.002))
    score += vote_bonus + pop_bonus + rank_signal

    return min(1.0, round(score, 4))


def resolve_tmdb_entity(
    query_title: str,
    media_type_hint: Optional[str] = None,
    language_hint: Optional[str] = None,
    year_hint: Optional[int] = None
) -> Dict[str, Any]:
    """
    Dynamically resolves any user query title to a validated TMDB entity.
    Never falls back to hardcoded titles or the selected movie.
    Handles movies, TV shows, and multi-search.
    """
    clean_query = query_title.strip()
    if not clean_query:
        return {
            "status": "not_found",
            "media_type": "unknown",
            "tmdb_id": None,
            "title": "",
            "resolution_confidence": 0.0,
            "candidates": [],
            "ranking_breakdown": [],
            "message": "Title query cannot be empty."
        }

    lang_code = LANGUAGE_CODES.get(language_hint.lower()) if language_hint else None
    
    # Step 1: Perform Search based on media type
    candidates: List[Dict[str, Any]] = []
    
    if media_type_hint == "movie":
        candidates = search_movies(clean_query, year=year_hint)
    elif media_type_hint == "tv":
        candidates = search_tv(clean_query, year=year_hint)
    else:
        # Multi search by default for universal title discovery
        candidates = search_multi(clean_query)
        if not candidates:
            # Fallback to combined search if multi returns empty
            m_res = search_movies(clean_query, year=year_hint)
            t_res = search_tv(clean_query, year=year_hint)
            candidates = m_res + t_res

    # If language hint was provided and no candidates or zero language matches:
    # ensure we have searched without language barrier
    if not candidates:
        return {
            "status": "not_found",
            "media_type": media_type_hint or "unknown",
            "tmdb_id": None,
            "title": clean_query,
            "resolution_confidence": 0.0,
            "candidates": [],
            "ranking_breakdown": [],
            "message": f"I could not find a matching movie or TV show in TMDB for \"{clean_query}\"."
        }

    # Step 2: Score & Rank Candidates
    scored_candidates = []
    for idx, c in enumerate(candidates):
        s = calculate_match_score(
            candidate=c,
            query_title=clean_query,
            media_type_hint=media_type_hint,
            language_hint=language_hint,
            year_hint=year_hint,
            tmdb_index=idx
        )
        c_copy = dict(c)
        c_copy["match_score"] = s
        scored_candidates.append(c_copy)

    # Sort descending by match score
    scored_candidates.sort(key=lambda x: x["match_score"], reverse=True)

    ranking_breakdown = [
        {
            "id": c.get("id"),
            "title": c.get("title") or c.get("name"),
            "score": c.get("match_score"),
            "pop": c.get("popularity"),
            "votes": c.get("vote_count"),
            "lang": c.get("original_language"),
            "media_type": c.get("media_type") or ("movie" if "title" in c else "tv")
        }
        for c in scored_candidates[:5]
    ]

    top_candidate = scored_candidates[0]
    top_score = top_candidate["match_score"]

    # Step 3: Determine Ambiguity vs Verified Match (Section 9)
    is_ambiguous = False
    ambiguous_options = []

    if len(scored_candidates) > 1:
        runner_up = scored_candidates[1]
        runner_score = runner_up["match_score"]

        top_pop = float(top_candidate.get("popularity", 0.0) or 0.0)
        runner_pop = float(runner_up.get("popularity", 0.0) or 0.0)
        top_votes = int(top_candidate.get("vote_count", 0) or 0)
        runner_votes = int(runner_up.get("vote_count", 0) or 0)

        # A candidate is dominant if it has significantly higher votes or popularity
        is_dominant = False
        if top_votes >= 50 and top_votes >= (runner_votes * 4 + 20):
            is_dominant = True
        elif top_pop >= 20.0 and top_pop >= (runner_pop * 2.5 + 5.0):
            is_dominant = True
        elif (top_score - runner_score) >= 0.08:
            is_dominant = True

        if not is_dominant:
            # Check if both are prominent (both have meaningful popularity/votes)
            both_prominent = (top_votes > 30 and runner_votes > 30) or (top_pop > 10 and runner_pop > 10)
            close_score = (top_score - runner_score) < 0.06
            if both_prominent and close_score:
                is_ambiguous = True
            elif top_score < 0.65 and close_score:
                # Query was too vague/generic and top results are weak
                is_ambiguous = True

    if is_ambiguous:
        for c in scored_candidates[:5]:
            m_type = c.get("media_type") or ("movie" if "title" in c else "tv")
            title_str = c.get("title") or c.get("name") or ""
            date_str = c.get("release_date") or c.get("first_air_date") or ""
            yr = date_str[:4] if date_str else "N/A"
            lang = c.get("original_language", "en").upper()
            ambiguous_options.append({
                "tmdb_id": c.get("id"),
                "media_type": m_type,
                "title": title_str,
                "year": yr,
                "language": lang,
                "overview": c.get("overview", "")
            })

        return {
            "status": "ambiguous",
            "media_type": top_candidate.get("media_type") or "movie",
            "tmdb_id": None,
            "title": clean_query,
            "resolution_confidence": top_score,
            "candidates": ambiguous_options,
            "ranking_breakdown": ranking_breakdown,
            "message": f"I found multiple TMDB results for \"{clean_query}\". Please choose the title you mean."
        }

    # Step 4: High Confidence Verified Match
    resolved_id = top_candidate.get("id")
    resolved_media = top_candidate.get("media_type") or ("movie" if "title" in top_candidate else "tv")
    resolved_title = top_candidate.get("title") or top_candidate.get("name") or clean_query
    orig_title = top_candidate.get("original_title") or top_candidate.get("original_name") or resolved_title
    rel_date = top_candidate.get("release_date") or top_candidate.get("first_air_date") or ""
    orig_lang = top_candidate.get("original_language") or "en"

    # Fetch full details
    details: Dict[str, Any] = {}
    try:
        if resolved_media == "movie":
            details = get_movie_details(resolved_id)
        else:
            details = get_tv_details(resolved_id)
    except Exception as e:
        # Gracefully preserve search candidate if details endpoint fails
        details = top_candidate

    return {
        "status": "verified",
        "media_type": resolved_media,
        "tmdb_id": resolved_id,
        "title": resolved_title,
        "original_title": orig_title,
        "release_date": rel_date,
        "original_language": orig_lang,
        "source": "tmdb",
        "resolution_confidence": top_score,
        "details": details,
        "candidates": scored_candidates[:5],
        "ranking_breakdown": ranking_breakdown
    }
