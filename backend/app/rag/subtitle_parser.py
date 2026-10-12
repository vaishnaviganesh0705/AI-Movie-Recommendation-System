"""
Subtitle Parser for Subtitle RAG.
Supports both SRT and WebVTT (.srt, .vtt) subtitle documents.
Extracts exact timestamps, sequence numbers, speaker annotations, and clean dialogue.
"""
import os
import re
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, asdict

from app.rag.timestamp_utils import parse_timestamp_to_seconds, seconds_to_timestamp


@dataclass
class SubtitleEntry:
    sequence_number: int
    start_timestamp: str
    end_timestamp: str
    start_seconds: float
    end_seconds: float
    text: str
    dialogue: str
    speaker: Optional[str] = None
    movie_id: str = "157336"
    movie_title: str = "Interstellar"
    source_file: str = "Interstellar.srt"
    source_type: str = "subtitle"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SubtitleParser:
    """
    Robust production parser for SRT and WebVTT subtitle files.
    - Strips HTML tags, braces, and subtitle styling.
    - Preserves all genuine dialogue words.
    - Extracts explicit speaker names in UPPERCASE (e.g. COOPER, MURPH, DONALD).
    - Removes obvious synchronization advertisements or empty entries.
    """

    SYNC_ARTIFACT_PATTERNS = [
        r"sync\s*(&|and)?\s*correct",
        r"downloaded\s+from",
        r"opensubtitles",
        r"subtitles\s+by",
        r"transcript\s+by",
        r"subdl",
        r"yify",
        r"addic7ed",
        r"captioning\s+by",
        r"translated\s+by",
        r"re-sync\b",
        r"sync\s*(&|and)?\s*edit",
        r"tharindu",
        r"encoded\s+by\b",
        r"^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,4}$",
        r"https?://",
        r"www\.",
    ]

    @classmethod
    def clean_text(cls, raw_text: str) -> str:
        """Strips HTML tags, ASS/SSA tags, and normalizes internal whitespace."""
        if not raw_text:
            return ""
        # Remove HTML tags (e.g. <font color="...">, </i>, <b>)
        text = re.sub(r'<[^>]+>', ' ', raw_text)
        # Remove ASS/SSA style tags (e.g. {\an8})
        text = re.sub(r'\{[^}]+\}', ' ', text)
        # Normalize internal whitespace
        text = re.sub(r'[ \t\r\n]+', ' ', text).strip()
        return text

    @classmethod
    def extract_speaker(cls, text: str) -> Tuple[Optional[str], str]:
        """
        Extracts speaker name if explicitly formatted, e.g.:
        "COOPER : There are no such things as ghosts." -> ("COOPER", "There are no such things as ghosts.")
        "MURPH: Look at this." -> ("MURPH", "Look at this.")
        "PROF. BRAND: Do not go gentle" -> ("PROF. BRAND", "Do not go gentle")
        If no explicit speaker label exists, returns (None, text).
        """
        # Match explicit speaker label at the beginning of the text
        match = re.match(r'^([A-Z0-9\.\s\-\'\(\)]+)\s*[:：]\s*(.*)$', text, flags=re.DOTALL)
        if match:
            candidate = match.group(1).strip()
            # Clean parentheses or brackets from speaker name e.g. "(COOPER)" -> "COOPER"
            cleaned_candidate = re.sub(r'[\(\)\[\]]', '', candidate).strip()
            # Verify it's a realistic character name (not a full sentence or number)
            if cleaned_candidate and len(cleaned_candidate) <= 30 and not cleaned_candidate.isdigit():
                # Avoid matching sound effects like "(DISTANT RUMBLING)" as speakers
                if not re.match(r'^(OVER|RADIO|SOUND|MUSIC|NOISE|WHISPER|SOBBING|COUGHING)$', cleaned_candidate, flags=re.IGNORECASE):
                    remaining_dialogue = match.group(2).strip()
                    return cleaned_candidate.upper(), remaining_dialogue

        # Also match lines like: "COOPER: (PANTING) Go back to bed."
        return None, text

    @classmethod
    def is_sync_artifact(cls, text: str) -> bool:
        """Detects whether text is an advertisement or sync author credit."""
        t_lower = text.lower().strip()
        for pat in cls.SYNC_ARTIFACT_PATTERNS:
            if re.search(pat, t_lower):
                return True
        return False

    @classmethod
    def parse_srt(
        cls,
        file_path: str,
        movie_id: str = "157336",
        movie_title: str = "Interstellar"
    ) -> List[SubtitleEntry]:
        """Parses an SRT file into verified SubtitleEntry objects."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Subtitle file not found: {file_path}")

        filename = os.path.basename(file_path)

        # Read file with multiple encoding fallbacks
        content = ""
        for enc in ["utf-8-sig", "utf-8", "latin-1", "cp1252"]:
            try:
                with open(file_path, "r", encoding=enc) as f:
                    content = f.read()
                break
            except (UnicodeDecodeError, OSError):
                continue

        if not content:
            return []

        # Split content into subtitle blocks separated by double newlines
        blocks = re.split(r'\n\s*\n', content.strip())
        entries: List[SubtitleEntry] = []

        for block in blocks:
            lines = [l.strip() for l in block.splitlines() if l.strip()]
            if len(lines) < 2:
                continue

            # Identify timestamp line containing "-->"
            time_idx = -1
            for idx, line in enumerate(lines[:3]):
                if "-->" in line:
                    time_idx = idx
                    break

            if time_idx == -1:
                continue

            # Extract sequence number
            seq_num = 0
            if time_idx > 0:
                try:
                    seq_num = int(lines[time_idx - 1])
                except ValueError:
                    seq_num = len(entries) + 1
            else:
                seq_num = len(entries) + 1

            # Extract timestamps
            time_line = lines[time_idx]
            parts = time_line.split("-->")
            if len(parts) != 2:
                continue

            start_raw = parts[0].strip()
            end_raw = parts[1].strip().split()[0]  # strip any VTT trailing layout properties

            start_sec = parse_timestamp_to_seconds(start_raw)
            end_sec = parse_timestamp_to_seconds(end_raw)

            if start_sec is None or end_sec is None or end_sec < start_sec:
                continue

            # Extract dialogue text lines
            dialogue_lines = lines[time_idx + 1:]
            raw_text = " ".join(dialogue_lines)
            cleaned = cls.clean_text(raw_text)

            if not cleaned or cls.is_sync_artifact(cleaned):
                continue

            # Extract speaker if explicitly present
            speaker, pure_dialogue = cls.extract_speaker(cleaned)

            # Preserve dialogue words and speaker prefix in text
            if speaker:
                formatted_text = f"{speaker}: {pure_dialogue}"
            else:
                formatted_text = cleaned

            entry = SubtitleEntry(
                sequence_number=seq_num,
                start_timestamp=start_raw,
                end_timestamp=end_raw,
                start_seconds=start_sec,
                end_seconds=end_sec,
                text=formatted_text,
                dialogue=pure_dialogue if speaker else cleaned,
                speaker=speaker,
                movie_id=str(movie_id),
                movie_title=movie_title,
                source_file=filename,
                source_type="subtitle"
            )
            entries.append(entry)

        # Sort chronologically by start_seconds
        entries.sort(key=lambda x: (x.start_seconds, x.end_seconds, x.sequence_number))

        # Re-index sequence numbers cleanly and deduplicate identical consecutive lines
        deduped: List[SubtitleEntry] = []
        for e in entries:
            if deduped and deduped[-1].text == e.text and abs(deduped[-1].start_seconds - e.start_seconds) < 1.0:
                continue
            e.sequence_number = len(deduped) + 1
            deduped.append(e)

        return deduped

    @classmethod
    def parse_vtt(
        cls,
        file_path: str,
        movie_id: str = "157336",
        movie_title: str = "Interstellar"
    ) -> List[SubtitleEntry]:
        """Parses a WebVTT file into verified SubtitleEntry objects."""
        return cls.parse_srt(file_path, movie_id=movie_id, movie_title=movie_title)

    @classmethod
    def parse_file(
        cls,
        file_path: str,
        movie_id: str = "157336",
        movie_title: str = "Interstellar"
    ) -> List[SubtitleEntry]:
        """Universal parser dispatcher for SRT and VTT subtitle files."""
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".vtt":
            return cls.parse_vtt(file_path, movie_id=movie_id, movie_title=movie_title)
        return cls.parse_srt(file_path, movie_id=movie_id, movie_title=movie_title)
