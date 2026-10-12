"""
Subtitle indexer module alias for app.rag.indexer.
"""
from app.rag.indexer import SubtitleIndexer, get_subtitles_collection, get_chroma_client

__all__ = ["SubtitleIndexer", "get_subtitles_collection", "get_chroma_client"]
