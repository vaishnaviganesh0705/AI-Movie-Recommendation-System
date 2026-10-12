"""
Time-aware and dialogue-aware sliding window chunker for Subtitle RAG.
Groups nearby subtitle dialogue entries while respecting scene transitions and time limits.
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict

from app.rag.subtitle_parser import SubtitleEntry


@dataclass
class SubtitleChunk:
    chunk_id: str
    movie_id: str
    movie_title: str
    chunk_index: int
    start_timestamp: str
    end_timestamp: str
    start_seconds: float
    end_seconds: float
    text: str
    source_sequence_start: int
    source_sequence_end: int
    speakers: List[str]
    entry_count: int
    source_type: str = "subtitle"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SubtitleChunker:
    """
    Groups consecutive subtitle entries into time-bounded and dialogue-coherent chunks.
    - Preserves exact source sequence boundaries and timestamp ranges.
    - Detects scene gaps (> 30s) to avoid bridging across distant scenes.
    - Maintains speaker lists for character-aware retrieval.
    - Employs controlled overlap (2 entries) between adjacent chunks.
    """

    def __init__(
        self,
        target_duration_seconds: float = 45.0,
        max_duration_seconds: float = 75.0,
        max_gap_seconds: float = 30.0,
        overlap_entries: int = 2,
        max_characters: int = 1200
    ):
        self.target_duration_seconds = target_duration_seconds
        self.max_duration_seconds = max_duration_seconds
        self.max_gap_seconds = max_gap_seconds
        self.overlap_entries = overlap_entries
        self.max_characters = max_characters

    def chunk_entries(
        self,
        entries: List[SubtitleEntry],
        movie_id: str = "157336",
        movie_title: str = "Interstellar"
    ) -> List[SubtitleChunk]:
        """Creates sliding-window chunks from subtitle entries in strict chronological order."""
        if not entries:
            return []

        chunks: List[SubtitleChunk] = []
        n = len(entries)
        i = 0
        chunk_idx = 0
        slug = "".join(c if c.isalnum() else "_" for c in str(movie_id).lower()).strip("_")

        while i < n:
            current_entries: List[SubtitleEntry] = [entries[i]]
            current_chars = len(entries[i].text)

            j = i + 1
            while j < n:
                next_entry = entries[j]
                gap = next_entry.start_seconds - current_entries[-1].end_seconds
                span = next_entry.end_seconds - current_entries[0].start_seconds
                potential_chars = current_chars + len(next_entry.text) + 1

                # Stop chunk if there's a big scene gap (> max_gap_seconds)
                if gap > self.max_gap_seconds and len(current_entries) >= 2:
                    break

                # Stop chunk if target duration reached and has enough content (>= 4 entries)
                if span >= self.target_duration_seconds and len(current_entries) >= 4:
                    current_entries.append(next_entry)
                    break

                # Stop if exceeding hard duration or character limits
                if span > self.max_duration_seconds or potential_chars > self.max_characters:
                    break

                current_entries.append(next_entry)
                current_chars = potential_chars
                j += 1

            # Build text and speaker list
            chunk_text = " ".join(e.text for e in current_entries)
            speakers = []
            for e in current_entries:
                if e.speaker and e.speaker.upper() not in speakers:
                    speakers.append(e.speaker.upper())

            chunk_id = f"{slug}_chunk_{chunk_idx:04d}"

            chunk = SubtitleChunk(
                chunk_id=chunk_id,
                movie_id=str(movie_id),
                movie_title=movie_title,
                chunk_index=chunk_idx,
                start_timestamp=current_entries[0].start_timestamp,
                end_timestamp=current_entries[-1].end_timestamp,
                start_seconds=current_entries[0].start_seconds,
                end_seconds=current_entries[-1].end_seconds,
                text=chunk_text,
                source_sequence_start=current_entries[0].sequence_number,
                source_sequence_end=current_entries[-1].sequence_number,
                speakers=speakers,
                entry_count=len(current_entries),
                source_type="subtitle"
            )
            chunks.append(chunk)
            chunk_idx += 1

            # Advance index with overlap
            advance = max(1, len(current_entries) - self.overlap_entries)
            i += advance

        return chunks
