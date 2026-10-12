"""
Timestamp utilities for Subtitle RAG.
Provides deterministic parsing, formatting, and time window arithmetic.
Strictly avoids using LLM for numeric/timestamp arithmetic.
"""
import re
from typing import Optional, Tuple, List


def parse_timestamp_to_seconds(timestamp: str) -> Optional[float]:
    """
    Parses timestamp string to total seconds.
    Supports formats:
      - HH:MM:SS,mmm or HH:MM:SS.mmm
      - HH:MM:SS
      - MM:SS,mmm or MM:SS.mmm
      - MM:SS
    Returns float seconds or None if invalid. Negative values are clamped to 0.0.
    """
    if not timestamp or not isinstance(timestamp, str):
        return None

    ts = timestamp.strip().replace(",", ".")
    parts = ts.split(":")
    try:
        if len(parts) == 3:
            h = float(parts[0])
            m = float(parts[1])
            s = float(parts[2])
            total = h * 3600.0 + m * 60.0 + s
            return max(0.0, total)
        elif len(parts) == 2:
            m = float(parts[0])
            s = float(parts[1])
            total = m * 60.0 + s
            return max(0.0, total)
        else:
            return None
    except ValueError:
        return None


# Backward-compatible aliases
timestamp_to_seconds = parse_timestamp_to_seconds
format_timestamp_to_seconds = parse_timestamp_to_seconds


def extract_timestamps_from_text(text: str) -> List[str]:
    """Finds all timestamps in text matching HH:MM:SS or MM:SS."""
    if not text:
        return []
    matches = re.findall(r'\b[0-9]{1,2}:[0-9]{2}(?::[0-9]{2})?(?:[,\.][0-9]{1,3})?\b', text)
    return matches


def seconds_to_timestamp(seconds: float, include_ms: bool = False, include_millis: Optional[bool] = None) -> str:
    """
    Converts total seconds to HH:MM:SS or HH:MM:SS,mmm format.
    Clamps negative seconds to 00:00:00.
    """
    if include_millis is not None:
        include_ms = include_millis
    sec = max(0.0, float(seconds))
    total_sec = int(sec)
    ms = int(round((sec - total_sec) * 1000))
    if ms >= 1000:
        total_sec += 1
        ms -= 1000

    h = total_sec // 3600
    m = (total_sec % 3600) // 60
    s = total_sec % 60

    if include_ms:
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
    return f"{h:02d}:{m:02d}:{s:02d}"


# Backward-compatible alias
format_seconds_to_timestamp = seconds_to_timestamp


def _word_to_number(word: str) -> Optional[float]:
    num_map = {
        "one": 1.0, "two": 2.0, "three": 3.0, "four": 4.0, "five": 5.0,
        "six": 6.0, "seven": 7.0, "eight": 8.0, "nine": 9.0, "ten": 10.0,
        "fifteen": 15.0, "twenty": 20.0, "thirty": 30.0, "forty": 40.0,
        "forty-five": 45.0, "fifty": 50.0, "sixty": 60.0,
        "a": 1.0, "an": 1.0, "half": 0.5
    }
    return num_map.get(word.lower().strip())


# Regex pattern to match timestamps in queries: HH:MM:SS or MM:SS (with optional ms)
TS_REGEX = r'(?:[0-9]{1,2}:[0-9]{2}:[0-9]{2}(?:[,\.][0-9]{1,3})?|[0-9]{1,2}:[0-9]{2}(?:[,\.][0-9]{1,3})?)'


def parse_relative_time_question(query: str, ref_sec: Optional[float] = None) -> Tuple[Optional[float], Optional[float]]:
    """
    Extracts explicit time intervals or relative time offsets from a query string.
    Examples:
      - "between 00:37:15 and 00:42:15" -> (2235.0, 2535.0)
      - "from 00:20:00 to 00:25:00" -> (1200.0, 1500.0)
      - "five minutes before 00:42:15" -> (2235.0, 2535.0)
      - "two minutes after 00:42:15" -> (2535.0, 2655.0)
      - "after 00:42:15" / "what happened after 00:42:15?" -> (2535.0, 2775.0)
      - "around 00:37:15" -> (2175.0, 2295.0)
      - "around 1 hour" -> (3420.0, 3780.0)
      - "at 01:10:00" / "who was mentioned around 01:10:00?" -> (4140.0, 4260.0)
    Returns (start_seconds, end_seconds) or (None, None) if no timestamp found.
    """
    q = query.lower().strip()

    # Pattern 1: Explicit Range "between <T1> and <T2>" or "from <T1> to <T2>" or "<T1> to <T2>"
    range_match = re.search(
        rf'(?:between|from)?\s*({TS_REGEX})\s+(?:and|to|-)\s+({TS_REGEX})',
        q
    )
    if range_match:
        s1 = parse_timestamp_to_seconds(range_match.group(1))
        s2 = parse_timestamp_to_seconds(range_match.group(2))
        if s1 is not None and s2 is not None:
            return (min(s1, s2), max(s1, s2))

    # Pattern 2: "<N> minutes/mins before <T>"
    before_match = re.search(
        rf'(\d+|[a-zA-Z\-]+)\s*(?:minutes?|mins?)\s+before\s+({TS_REGEX})',
        q
    )
    if before_match:
        n_str = before_match.group(1)
        t_str = before_match.group(2)
        n_val = float(n_str) if n_str.isdigit() else _word_to_number(n_str)
        t_sec = parse_timestamp_to_seconds(t_str)
        if n_val is not None and t_sec is not None:
            offset = n_val * 60.0
            start_sec = max(0.0, t_sec - offset)
            return (start_sec, t_sec)

    # Pattern 3: "<N> minutes/mins after <T>"
    after_match = re.search(
        rf'(\d+|[a-zA-Z\-]+)\s*(?:minutes?|mins?)\s+after\s+({TS_REGEX})',
        q
    )
    if after_match:
        n_str = after_match.group(1)
        t_str = after_match.group(2)
        n_val = float(n_str) if n_str.isdigit() else _word_to_number(n_str)
        t_sec = parse_timestamp_to_seconds(t_str)
        if n_val is not None and t_sec is not None:
            offset = n_val * 60.0
            return (t_sec, t_sec + offset)

    # Pattern 4: "after <T>" or "what happened after <T>"
    direct_after = re.search(rf'\bafter\s+({TS_REGEX})', q)
    if direct_after:
        t_sec = parse_timestamp_to_seconds(direct_after.group(1))
        if t_sec is not None:
            # Default window of 4 minutes after
            return (t_sec, t_sec + 240.0)

    # Pattern 5: "before <T>" or "what happened before <T>"
    direct_before = re.search(rf'\bbefore\s+({TS_REGEX})', q)
    if direct_before:
        t_sec = parse_timestamp_to_seconds(direct_before.group(1))
        if t_sec is not None:
            # Default window of 4 minutes before
            return (max(0.0, t_sec - 240.0), t_sec)

    # Pattern 6: Single explicit timestamp "around <T>", "at <T>", "near <T>", "about <T>", or standalone "<T>"
    single_ts_match = re.search(
        rf'(?:around|at|near|about|in|during)?\s*({TS_REGEX})',
        q
    )
    if single_ts_match:
        # Verify it's an actual timestamp candidate
        matched_str = single_ts_match.group(1)
        t_sec = parse_timestamp_to_seconds(matched_str)
        if t_sec is not None:
            # Symmetrical window: 75 seconds before to 75 seconds after
            return (max(0.0, t_sec - 75.0), t_sec + 75.0)

    # Pattern 7: Natural language hours e.g. "around 1 hour", "at 2 hours", "at 1.5 hours"
    hours_match = re.search(r'(?:around|at|about|after)\s+(\d+(?:\.\d+)?|[a-zA-Z\-]+)\s*(?:hours?|hrs?)', q)
    if hours_match:
        h_str = hours_match.group(1)
        try:
            h_val = float(h_str)
        except ValueError:
            h_val = _word_to_number(h_str)
        if h_val is not None:
            sec = h_val * 3600.0
            return (max(0.0, sec - 120.0), sec + 120.0)

    # Pattern 8: Natural language minutes e.g. "around 45 minutes", "at 30 mins"
    mins_match = re.search(r'(?:around|at|about|after)\s+(\d+(?:\.\d+)?|[a-zA-Z\-]+)\s*(?:minutes?|mins?)', q)
    if mins_match:
        m_str = mins_match.group(1)
        try:
            m_val = float(m_str)
        except ValueError:
            m_val = _word_to_number(m_str)
        if m_val is not None:
            sec = m_val * 60.0
            return (max(0.0, sec - 90.0), sec + 90.0)

    # If reference timestamp provided from previous turn
    if ref_sec is not None:
        if any(k in q for k in ["before that", "before this", "prior to this"]):
            return (max(0.0, ref_sec - 180.0), ref_sec)
        elif any(k in q for k in ["after that", "after this", "what happened next", "next"]):
            return (ref_sec, ref_sec + 180.0)
        elif any(k in q for k in ["more about that", "in that scene"]):
            return (max(0.0, ref_sec - 60.0), ref_sec + 60.0)

    return (None, None)


def calculate_time_window(
    query: str,
    default_window: float = 120.0,
    ref_sec: Optional[float] = None,
    min_val: float = 0.0,
    max_val: Optional[float] = None
) -> Tuple[Optional[float], Optional[float]]:
    """
    Convenience wrapper to get a bounded start and end seconds window for any time-aware query.
    """
    start_sec, end_sec = parse_relative_time_question(query, ref_sec=ref_sec)
    if start_sec is not None and end_sec is not None:
        start_sec = max(min_val, start_sec)
        if max_val is not None:
            end_sec = min(max_val, end_sec)
        return (start_sec, end_sec)
    return (None, None)
