"""
Deterministic runtime expression parser and verification utilities.
Parses natural language expressions into integer minutes (min_runtime, max_runtime).
No LLM calculations are used.
"""
import re
from typing import Optional, Tuple, Dict, Any

# Standard TMDB movie genre mapping
TMDB_MOVIE_GENRES: Dict[str, int] = {
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

TMDB_TV_GENRES: Dict[str, int] = {
    "action": 10759,
    "action & adventure": 10759,
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
    "science fiction": 10765,
    "sci-fi": 10765,
    "scifi": 10765,
    "soap": 10766,
    "talk": 10767,
    "war & politics": 10768,
    "western": 37
}


def parse_time_to_minutes(text: str) -> Optional[int]:
    """
    Parses a single time token into minutes.
    Examples:
        '1 hr' -> 60
        '1 hour' -> 60
        '1.5 hours' -> 90
        '1 hr 30 min' -> 90
        '90 min' -> 90
        '90 minutes' -> 90
        '2 h' -> 120
    """
    clean = text.strip().lower()

    # Pattern: 1 hr 30 min / 1 hour 30 minutes / 1h 30m
    m_combo = re.search(r'(\d+(?:\.\d+)?)\s*(?:hours?|hrs?|h)\s*(?:and\s*)?(\d+)\s*(?:minutes?|mins?|m)?', clean)
    if m_combo:
        hrs = float(m_combo.group(1))
        mins = int(m_combo.group(2))
        return int(hrs * 60 + mins)

    # Pattern: X.Y hours / X hours / X hrs / X h
    m_hrs = re.search(r'(\d+(?:\.\d+)?)\s*(?:hours?|hrs?|h)\b', clean)
    if m_hrs:
        hrs = float(m_hrs.group(1))
        return int(hrs * 60)

    # Pattern: X minutes / X mins / X min / X m
    m_mins = re.search(r'(\d+)\s*(?:minutes?|mins?|m)\b', clean)
    if m_mins:
        return int(m_mins.group(1))

    # Just an integer if followed or preceded by min context
    m_int = re.search(r'^\s*(\d+)\s*$', clean)
    if m_int:
        return int(m_int.group(1))

    return None


def parse_runtime_expression(query: str, default_tolerance_minutes: int = 15) -> Tuple[Optional[int], Optional[int], Optional[str]]:
    """
    Deterministically parses runtime expressions from a natural language query.
    Returns:
        (min_runtime_minutes, max_runtime_minutes, matched_expression_text)
    
    Supports:
        - '1 hr', '1 hour', '1 h' -> max_runtime = 60
        - '90 min', '90 minutes' -> max_runtime = 90
        - '1 hr 30 min', '1 hour 30 minutes' -> max_runtime = 90
        - 'under 2 hours', 'less than 120 minutes', 'below 90 minutes', 'at most 100 minutes' -> max = 120 / 90 / 100
        - 'over 2 hours', 'more than 120 minutes', 'above 90 minutes', 'at least 100 minutes' -> min = 120 / 90 / 100
        - 'between 90 and 120 minutes', 'from 90 to 120 minutes' -> min = 90, max = 120
        - 'around 100 minutes', 'about 90 minutes', 'approx 100 min' -> min = 85, max = 115 (with tolerance)
        - '1 hr Tamil movies to watch' -> max_runtime = 60
    """
    q = query.lower()

    # 1. Range: between X and Y / from X to Y
    m_range = re.search(
        r'(?:between|from)\s+(\d+(?:\.\d+)?(?:\s*(?:hours?|hrs?|h|minutes?|mins?|m))?)\s+(?:and|to)\s+(\d+(?:\.\d+)?(?:\s*(?:hours?|hrs?|h|minutes?|mins?|m))?)',
        q
    )
    if m_range:
        part1 = m_range.group(1)
        part2 = m_range.group(2)
        # If part1 has no unit, inherit unit from part2
        if not re.search(r'[a-z]', part1):
            unit_m = re.search(r'([a-z]+)', part2)
            if unit_m:
                part1 = f"{part1} {unit_m.group(1)}"
        t1 = parse_time_to_minutes(part1)
        t2 = parse_time_to_minutes(part2)
        if t1 is not None and t2 is not None:
            min_r = min(t1, t2)
            max_r = max(t1, t2)
            return min_r, max_r, m_range.group(0)

    # 2. Around / About / Approx: around X minutes / about 2 hours
    m_around = re.search(
        r'(?:around|about|approx(?:imately)?)\s+(\d+(?:\.\d+)?\s*(?:hours?|hrs?|h|minutes?|mins?|m)?)',
        q
    )
    if m_around:
        target = parse_time_to_minutes(m_around.group(1))
        if target is not None:
            min_r = max(1, target - default_tolerance_minutes)
            max_r = target + default_tolerance_minutes
            return min_r, max_r, m_around.group(0)

    # 3. Upper bound: under / less than / below / at most / shorter than / up to / not more than
    m_upper = re.search(
        r'(?:under|less\s+than|below|at\s+most|shorter\s+than|up\s+to|not\s+more\s+than|maximum\s+of)\s+(\d+(?:\.\d+)?\s*(?:hours?|hrs?|h|minutes?|mins?|m)?(?:\s*(?:and\s*)?\d+\s*(?:minutes?|mins?|m)?)?)',
        q
    )
    if m_upper:
        target = parse_time_to_minutes(m_upper.group(1))
        if target is not None:
            return None, target, m_upper.group(0)

    # 4. Lower bound: over / more than / above / at least / longer than / minimum of
    m_lower = re.search(
        r'(?:over|more\s+than|above|at\s+least|longer\s+than|minimum\s+of)\s+(\d+(?:\.\d+)?\s*(?:hours?|hrs?|h|minutes?|mins?|m)?(?:\s*(?:and\s*)?\d+\s*(?:minutes?|mins?|m)?)?)',
        q
    )
    if m_lower:
        target = parse_time_to_minutes(m_lower.group(1))
        if target is not None:
            return target, None, m_lower.group(0)

    # 5. Standalone or adjectival time:
    # "1 hr", "90 minutes", "1 hr 30 min", "1 hr Tamil movies", "90 minute movie"
    m_standalone = re.search(
        r'\b(\d+(?:\.\d+)?\s*(?:hours?|hrs?|h)\s*(?:and\s*)?(?:\d+\s*(?:minutes?|mins?|m)?)?|\d+\s*(?:minutes?|mins?|m))\b',
        q
    )
    if m_standalone:
        target = parse_time_to_minutes(m_standalone.group(1))
        if target is not None:
            return None, target, m_standalone.group(1)

    return None, None, None


def satisfies_runtime_filter(
    runtime_minutes: Optional[int],
    min_runtime: Optional[int] = None,
    max_runtime: Optional[int] = None
) -> bool:
    """
    Deterministic local runtime verification.
    For a maximum of 60 minutes:
        - 60 is accepted
        - 61 is rejected
        - None is rejected for strict filtering
    For 90-120 minutes:
        - 89 is rejected
        - 90 is accepted
        - 120 is accepted
        - 121 is rejected
    """
    if runtime_minutes is None:
        return False

    if min_runtime is not None and runtime_minutes < min_runtime:
        return False

    if max_runtime is not None and runtime_minutes > max_runtime:
        return False

    return True


def extract_genre_hint(query: str, media_type: str = "movie") -> Optional[str]:
    """
    Detects genre hints from natural language queries.
    Returns matched genre name or None.
    """
    q = query.lower()
    genres_dict = TMDB_MOVIE_GENRES if media_type == "movie" else TMDB_TV_GENRES

    # Check longer names first (e.g. 'science fiction' before 'fiction')
    sorted_genres = sorted(genres_dict.keys(), key=len, reverse=True)
    for g in sorted_genres:
        if re.search(rf'\b{re.escape(g)}\b', q):
            return g
    return None
