import os
import re
import hashlib
from typing import List, Dict, Any, Optional, Tuple
import chromadb
from chromadb.config import Settings

# Base paths: Support both repo-root/data/subtitles and backend/data/subtitles
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

CANDIDATE_SUBTITLE_DIRS = [
    os.path.join(REPO_ROOT, "data", "subtitles"),
    os.path.join(BACKEND_DIR, "data", "subtitles"),
]

CHROMA_DIR = os.path.join(REPO_ROOT, "data", "chroma_db")

# Known movie ID mappings for discovered files
MOVIE_ID_MAPPINGS = {
    "interstellar": 157336,
    "inception": 27205,
}

_chroma_client = None


def get_chroma_client() -> chromadb.PersistentClient:
    """Returns singleton persistent ChromaDB client."""
    global _chroma_client
    if _chroma_client is None:
        os.makedirs(CHROMA_DIR, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)
    return _chroma_client


def get_subtitles_collection() -> chromadb.Collection:
    """Returns or creates the movie_subtitles ChromaDB collection."""
    client = get_chroma_client()
    return client.get_or_create_collection(
        name="movie_subtitles",
        metadata={"description": "Movie subtitles RAG vector store"}
    )


def parse_timestamp_to_seconds(ts_str: str) -> float:
    """
    Parses SRT timestamp '00:01:14,909' or VTT '00:01:14.909' into total seconds (float).
    """
    cleaned = ts_str.strip().replace(",", ".")
    parts = cleaned.split(":")
    if len(parts) == 3:
        h, m, s = parts
        return int(h) * 3600 + int(m) * 60 + float(s)
    elif len(parts) == 2:
        m, s = parts
        return int(m) * 60 + float(s)
    return 0.0


def format_seconds_to_timestamp(seconds: float) -> str:
    """Converts seconds back to HH:MM:SS format."""
    total_sec = int(seconds)
    hours = total_sec // 3600
    minutes = (total_sec % 3600) // 60
    secs = total_sec % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def calculate_file_hash(file_path: str) -> str:
    """Calculates SHA256 of file content to detect changes."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


class SubtitleParser:
    """
    Parses and cleans SRT and VTT subtitle files, preserving timestamps and speaker labels.
    """

    @staticmethod
    def clean_text(raw_text: str) -> str:
        # Remove HTML and styling tags (<font...>, </font>, <i>, </i>, <b>, </b>, etc.)
        cleaned = re.sub(r"<[^>]+>", "", raw_text)
        # Normalize whitespace and strip
        cleaned = re.sub(r"[\r\n\t]+", " ", cleaned).strip()
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned

    @classmethod
    def parse_file(cls, file_path: str, movie_title: str, movie_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Parses every subtitle entry in the file and returns structured entries.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Subtitle file not found: {file_path}")

        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        # Split into blocks separated by blank lines
        blocks = re.split(r"\n\s*\n", content.strip())
        entries = []
        entry_idx = 1

        for b in blocks:
            lines = [line.strip() for line in b.split("\n") if line.strip()]
            if len(lines) < 2:
                continue

            # Identify timestamp line containing '-->'
            time_line = next((l for l in lines[:3] if "-->" in l), None)
            if not time_line:
                continue

            parts = time_line.split("-->")
            start_str = parts[0].strip()
            end_str = parts[1].strip()

            time_idx = lines.index(time_line)
            raw_text = " ".join(lines[time_idx + 1:])
            cleaned = cls.clean_text(raw_text)

            # Filter subtitle sync author credits and animation typing artifacts
            if any(k in cleaned for k in ["Tharindu", "Re-Sync", "Sync & Edit", "Subtitles by"]):
                continue
            if cleaned.startswith(movie_title) and len(cleaned.split()) <= 3:
                continue
            if cleaned in ["I", "In", "Int", "Inte", "Inter", "Inters", "Interst", "Interste", "Interstel", "Interstell", "Interstella"]:
                continue
            if not cleaned:
                continue

            start_seconds = parse_timestamp_to_seconds(start_str)
            end_seconds = parse_timestamp_to_seconds(end_str)

            entries.append({
                "subtitle_index": entry_idx,
                "movie_title": movie_title,
                "movie_id": movie_id or MOVIE_ID_MAPPINGS.get(movie_title.lower(), 0),
                "start_time": start_str,
                "end_time": end_str,
                "start_seconds": round(start_seconds, 3),
                "end_seconds": round(end_seconds, 3),
                "text": cleaned
            })
            entry_idx += 1

        return entries


class SubtitleChunker:
    """
    Groups consecutive subtitle entries into meaningful dialogue chunks with overlap.
    """

    @staticmethod
    def create_chunks(
        entries: List[Dict[str, Any]],
        chunk_size: int = 7,
        overlap: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Creates sliding window chunks from subtitle entries in chronological order.
        """
        if not entries:
            return []

        chunks = []
        step = max(1, chunk_size - overlap)
        chunk_index = 0

        for i in range(0, len(entries), step):
            window = entries[i:i + chunk_size]
            if not window:
                break

            first_entry = window[0]
            last_entry = window[-1]

            # Build chunk text with chronological speaker dialogue
            combined_lines = []
            for entry in window:
                combined_lines.append(entry["text"])

            combined_text = " ".join(combined_lines)

            chunks.append({
                "chunk_index": chunk_index,
                "movie_title": first_entry["movie_title"],
                "movie_id": str(first_entry["movie_id"]),
                "start_time": first_entry["start_time"],
                "end_time": last_entry["end_time"],
                "start_seconds": first_entry["start_seconds"],
                "end_seconds": last_entry["end_seconds"],
                "num_entries": len(window),
                "text": combined_text
            })
            chunk_index += 1

            if i + chunk_size >= len(entries):
                break

        return chunks


class SubtitleService:
    """
    High-level service for scanning data/subtitles/, parsing, chunking, and ChromaDB indexing.
    """

    @classmethod
    def discover_subtitle_files(cls) -> List[Dict[str, str]]:
        """Scans candidate data/subtitles/ directories for .srt and .vtt files."""
        discovered = []
        seen_filenames = set()

        for s_dir in CANDIDATE_SUBTITLE_DIRS:
            if not os.path.exists(s_dir):
                continue
            for fname in os.listdir(s_dir):
                if fname.lower().endswith((".srt", ".vtt")) and fname not in seen_filenames:
                    seen_filenames.add(fname)
                    full_path = os.path.join(s_dir, fname)
                    movie_title = os.path.splitext(fname)[0]
                    discovered.append({
                        "filename": fname,
                        "filepath": full_path,
                        "movie_title": movie_title,
                        "movie_id": MOVIE_ID_MAPPINGS.get(movie_title.lower(), 0)
                    })
        return discovered

    @classmethod
    def index_subtitle_file(
        cls,
        filepath: str,
        movie_title: Optional[str] = None,
        movie_id: Optional[int] = None,
        force_reindex: bool = False
    ) -> Dict[str, Any]:
        """
        Parses, chunks, and indexes a single subtitle file into ChromaDB idempotently via SubtitleIndexer.
        """
        from app.rag.indexer import SubtitleIndexer
        if not movie_title:
            movie_title = os.path.splitext(os.path.basename(filepath))[0]

        movie_id_val = movie_id or MOVIE_ID_MAPPINGS.get(movie_title.lower(), 157336)
        return SubtitleIndexer.index_movie_file(
            file_path=filepath,
            movie_id=str(movie_id_val),
            movie_title=movie_title,
            force_reindex=force_reindex
        )

    @classmethod
    def index_all_subtitles(cls) -> List[Dict[str, Any]]:
        """Discovers and indexes all subtitle files in data/subtitles/."""
        files = cls.discover_subtitle_files()
        results = []
        for item in files:
            res = cls.index_subtitle_file(item["filepath"], item["movie_title"], item["movie_id"])
            results.append(res)
        return results

    @classmethod
    def get_status(cls) -> Dict[str, Any]:
        """Returns the current ChromaDB subtitle collection status."""
        from app.rag.indexer import SubtitleIndexer
        stats = SubtitleIndexer.get_index_statistics()
        files = cls.discover_subtitle_files()
        return {
            "total_chunks_in_chromadb": stats.get("total_chunks", 0),
            "discovered_files": files,
            "details": stats
        }

