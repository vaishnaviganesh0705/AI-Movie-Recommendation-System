"""
Vector indexer for Subtitle RAG.
Manages persistent ChromaDB vector storage under the 'movie_subtitles' collection.
Ensures strict per-movie isolation, idempotent indexing, and deterministic document IDs.
"""
import os
import hashlib
from typing import Dict, Any, List, Optional
import chromadb
from chromadb.utils import embedding_functions

from app.rag.subtitle_parser import SubtitleParser
from app.rag.chunker import SubtitleChunker, SubtitleChunk

# Project-relative persistent chroma path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", "..", ".."))
BACKEND_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))

# Prefer repo root data/chroma_db if exists, else backend data/chroma_db
if os.path.exists(os.path.join(REPO_ROOT, "data", "chroma_db")):
    CHROMA_DIR = os.path.join(REPO_ROOT, "data", "chroma_db")
else:
    CHROMA_DIR = os.path.join(BACKEND_ROOT, "data", "chroma_db")

COLLECTION_NAME = "movie_subtitles"

_client: Optional[chromadb.PersistentClient] = None
_embedding_fn = None


def get_embedding_function():
    global _embedding_fn
    if _embedding_fn is None:
        try:
            _embedding_fn = embedding_functions.ONNXMiniLM_L6_V2()
        except Exception:
            _embedding_fn = embedding_functions.DefaultEmbeddingFunction()
    return _embedding_fn


def get_chroma_client() -> chromadb.PersistentClient:
    global _client
    if _client is None:
        os.makedirs(CHROMA_DIR, exist_ok=True)
        _client = chromadb.PersistentClient(path=CHROMA_DIR)
    return _client


def get_subtitles_collection():
    client = get_chroma_client()
    try:
        return client.get_collection(name=COLLECTION_NAME)
    except Exception:
        return client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"description": "Movie subtitles RAG vector store"}
        )


class SubtitleIndexer:
    """
    Manages persistent document indexing, chunk storage, and per-movie lifecycle in ChromaDB.
    """

    @classmethod
    def compute_file_hash(cls, file_path: str) -> str:
        """Computes SHA-256 hash of subtitle document to detect modifications."""
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        return h.hexdigest()

    @classmethod
    def delete_movie_index(cls, movie_id: str) -> int:
        """Deletes all chunks belonging to a specific movie_id."""
        collection = get_subtitles_collection()
        try:
            existing = collection.get(where={"movie_id": str(movie_id)})
            ids_to_delete = existing.get("ids", [])
            if ids_to_delete:
                collection.delete(ids=ids_to_delete)
                return len(ids_to_delete)
        except Exception as e:
            print(f"[SubtitleIndexer] Warning deleting movie {movie_id}: {e}")
        return 0

    @classmethod
    def clean_stale_indices(cls) -> int:
        """Removes any stale, unassigned, or corrupt entries (e.g. movie_id '0')."""
        collection = get_subtitles_collection()
        deleted_count = 0
        try:
            # Clean movie_id '0' or 'unknown'
            for stale_id in ["0", "unknown"]:
                stale = collection.get(where={"movie_id": stale_id})
                if stale and stale.get("ids"):
                    collection.delete(ids=stale["ids"])
                    deleted_count += len(stale["ids"])
        except Exception as e:
            print(f"[SubtitleIndexer] Warning cleaning stale indices: {e}")
        return deleted_count

    @classmethod
    def index_movie_file(
        cls,
        file_path: str,
        movie_id: str = "157336",
        movie_title: str = "Interstellar",
        force_reindex: bool = False
    ) -> Dict[str, Any]:
        """
        Parses, chunks, and indexes a subtitle file into ChromaDB with idempotency.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Subtitle file not found: {file_path}")

        mid_str = str(movie_id).strip()
        file_hash = cls.compute_file_hash(file_path)
        collection = get_subtitles_collection()

        # Clean any stale indices like movie_id='0'
        cls.clean_stale_indices()

        # Check existing chunks for this movie
        existing = collection.get(where={"movie_id": mid_str})
        existing_count = len(existing.get("ids", []))

        if existing_count > 0 and not force_reindex:
            meta_first = existing.get("metadatas", [{}])[0] if existing.get("metadatas") else {}
            if meta_first.get("file_hash") == file_hash:
                # Retrieve time boundaries
                all_metas = existing.get("metadatas", [])
                first_ts = all_metas[0].get("start_timestamp") if all_metas else "00:00:00"
                last_ts = all_metas[-1].get("end_timestamp") if all_metas else "00:00:00"
                return {
                    "movie_id": mid_str,
                    "movie_title": movie_title,
                    "subtitle_file": os.path.basename(file_path),
                    "chunks_indexed": existing_count,
                    "first_timestamp": first_ts,
                    "last_timestamp": last_ts,
                    "file_hash": file_hash,
                    "status": "already_indexed"
                }

        # 1. Parse entries
        entries = SubtitleParser.parse_file(file_path, movie_id=mid_str, movie_title=movie_title)
        if not entries:
            return {
                "movie_id": mid_str,
                "movie_title": movie_title,
                "subtitle_file": os.path.basename(file_path),
                "chunks_indexed": 0,
                "status": "empty_file"
            }

        # 2. Chunk entries
        chunker = SubtitleChunker()
        chunks = chunker.chunk_entries(entries, movie_id=mid_str, movie_title=movie_title)

        # 3. Clean any existing chunks for this movie before fresh insertion
        cls.delete_movie_index(mid_str)

        # 4. Batch upsert into ChromaDB
        batch_size = 64
        docs, metas, ids = [], [], []

        for c in chunks:
            docs.append(c.text)
            ids.append(c.chunk_id)
            metas.append({
                "movie_id": mid_str,
                "movie_title": c.movie_title,
                "chunk_index": c.chunk_index,
                "start_timestamp": c.start_timestamp,
                "end_timestamp": c.end_timestamp,
                "start_time": c.start_timestamp,  # for backward-compatibility
                "end_time": c.end_timestamp,      # for backward-compatibility
                "start_seconds": float(c.start_seconds),
                "end_seconds": float(c.end_seconds),
                "source_seq_start": c.source_sequence_start,
                "source_seq_end": c.source_sequence_end,
                "entry_count": c.entry_count,
                "speakers": ", ".join(c.speakers) if c.speakers else "UNKNOWN",
                "file_hash": file_hash,
                "source_file": os.path.basename(file_path),
                "source_type": "subtitle"
            })

        for k in range(0, len(docs), batch_size):
            collection.upsert(
                documents=docs[k:k+batch_size],
                metadatas=metas[k:k+batch_size],
                ids=ids[k:k+batch_size]
            )

        first_ts = chunks[0].start_timestamp if chunks else "00:00:00"
        last_ts = chunks[-1].end_timestamp if chunks else "00:00:00"

        return {
            "movie_id": mid_str,
            "movie_title": movie_title,
            "subtitle_file": os.path.basename(file_path),
            "subtitle_entries": len(entries),
            "chunks_indexed": len(chunks),
            "first_timestamp": first_ts,
            "last_timestamp": last_ts,
            "file_hash": file_hash,
            "status": "indexed"
        }

    @classmethod
    def reindex_movie(cls, movie_id: str, file_path: Optional[str] = None) -> Dict[str, Any]:
        """Forces reindexing of a movie's subtitle document."""
        mid_str = str(movie_id).strip()
        if not file_path:
            # Default lookup for Interstellar
            candidate_paths = [
                os.path.join(REPO_ROOT, "data", "subtitles", "Interstellar.srt"),
                os.path.join(BACKEND_ROOT, "data", "subtitles", "Interstellar.srt"),
            ]
            file_path = next((p for p in candidate_paths if os.path.exists(p)), None)

        if not file_path or not os.path.exists(file_path):
            raise FileNotFoundError(f"Subtitle file not found for movie {movie_id}")

        return cls.index_movie_file(
            file_path=file_path,
            movie_id=mid_str,
            movie_title="Interstellar" if mid_str == "157336" else f"Movie_{mid_str}",
            force_reindex=True
        )

    @classmethod
    def get_index_statistics(cls, movie_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Reports comprehensive indexing metrics per movie:
        - chunk count
        - entry count
        - time coverage (first and last timestamp)
        - source file and hash
        - status
        """
        collection = get_subtitles_collection()
        where_filter = {"movie_id": str(movie_id)} if movie_id else None

        try:
            if where_filter:
                data = collection.get(where=where_filter, include=["metadatas"])
            else:
                data = collection.get(include=["metadatas"])
        except Exception:
            data = {"ids": [], "metadatas": []}

        metas = data.get("metadatas", [])
        if not metas:
            return {
                "movie_id": movie_id or "unknown",
                "chunks_indexed": 0,
                "status": "not_indexed"
            }

        # Group by movie_id
        movies_map: Dict[str, List[Dict[str, Any]]] = {}
        for m in metas:
            mid = m.get("movie_id", "unknown")
            movies_map.setdefault(mid, []).append(m)

        movie_reports = {}
        for mid, m_list in movies_map.items():
            # Sort by start_seconds
            m_list.sort(key=lambda x: float(x.get("start_seconds", 0.0)))
            first_m = m_list[0]
            last_m = m_list[-1]
            total_entries = sum(int(m.get("entry_count", 0)) for m in m_list)
            movie_reports[mid] = {
                "movie_id": mid,
                "movie_title": first_m.get("movie_title", "Unknown"),
                "subtitle_file": first_m.get("source_file", "Unknown"),
                "subtitle_entries": total_entries,
                "chunks_indexed": len(m_list),
                "first_timestamp": first_m.get("start_timestamp") or first_m.get("start_time"),
                "last_timestamp": last_m.get("end_timestamp") or last_m.get("end_time"),
                "first_seconds": float(first_m.get("start_seconds", 0.0)),
                "last_seconds": float(last_m.get("end_seconds", 0.0)),
                "file_hash": first_m.get("file_hash"),
                "status": "indexed"
            }

        if movie_id and str(movie_id) in movie_reports:
            return movie_reports[str(movie_id)]

        return {
            "total_chunks": len(metas),
            "movies": movie_reports,
            "collection_name": COLLECTION_NAME,
            "chroma_dir": CHROMA_DIR
        }

    @classmethod
    def get_index_status(cls) -> Dict[str, Any]:
        """Returns high-level statistics on ChromaDB index."""
        return cls.get_index_statistics()
