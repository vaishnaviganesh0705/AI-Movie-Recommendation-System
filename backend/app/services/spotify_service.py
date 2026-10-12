import os
import time
from typing import Optional, List, Dict, Any
import httpx
from dotenv import load_dotenv

# Ensure environment variables are loaded
load_dotenv()

SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_BASE_URL = "https://api.spotify.com/v1"
DEFAULT_MARKET = "IN"


class SpotifyService:
    """
    Centralized service responsible for official Spotify Web API integration.
    - Uses Client Credentials flow for public catalog data.
    - Caches access token until expiration.
    - Implements automatic retry on 401.
    - Provides standardized track/artist/album normalization.
    - Strictly avoids logging secrets or tokens.
    - Explicitly reports developer account restrictions when endpoints return 403.
    """

    def __init__(self):
        self._access_token: Optional[str] = None
        self._token_expiry: float = 0.0
        self._last_error: Optional[str] = None

    def _get_credentials(self) -> tuple[Optional[str], Optional[str]]:
        client_id = os.getenv("SPOTIFY_CLIENT_ID")
        client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
        if client_id:
            client_id = client_id.strip()
        if client_secret:
            client_secret = client_secret.strip()
        return client_id, client_secret

    def is_configured(self) -> bool:
        cid, sec = self._get_credentials()
        return bool(cid and sec and cid != "your_spotify_client_id" and sec != "your_spotify_client_secret")

    def get_access_token(self, force_refresh: bool = False) -> Optional[str]:
        """
        Retrieves or returns cached Spotify access token using Client Credentials flow.
        Caches token until 60 seconds before expiration.
        """
        now = time.time()
        if not force_refresh and self._access_token and now < (self._token_expiry - 60):
            return self._access_token

        client_id, client_secret = self._get_credentials()
        if not client_id or not client_secret or client_id == "your_spotify_client_id":
            self._last_error = "Spotify credentials are not configured in backend/.env"
            return None

        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.post(
                    SPOTIFY_TOKEN_URL,
                    data={"grant_type": "client_credentials"},
                    auth=(client_id, client_secret),
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )

                if res.status_code == 200:
                    data = res.json()
                    self._access_token = data.get("access_token")
                    expires_in = data.get("expires_in", 3600)
                    self._token_expiry = now + expires_in
                    self._last_error = None
                    return self._access_token
                elif res.status_code in [400, 401]:
                    self._last_error = "Invalid Spotify client credentials"
                    self._access_token = None
                    return None
                else:
                    self._last_error = f"Spotify auth failed with HTTP status {res.status_code}"
                    self._access_token = None
                    return None

        except httpx.TimeoutException:
            self._last_error = "Spotify authentication timed out"
            return None
        except Exception as e:
            self._last_error = f"Spotify auth error: {type(e).__name__}"
            return None

    def _normalize_track(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalizes a Spotify track dictionary into a clean internal structure.
        """
        if not item or not isinstance(item, dict):
            return {}

        album = item.get("album") or {}
        images = album.get("images") or []
        album_img = images[0].get("url") if images else None

        artists_list = []
        for art in item.get("artists") or []:
            if isinstance(art, dict) and art.get("name"):
                artists_list.append(art["name"])

        external_urls = item.get("external_urls") or {}

        return {
            "id": item.get("id"),
            "name": item.get("name"),
            "artists": artists_list,
            "album_name": album.get("name"),
            "album_image": album_img,
            "spotify_url": external_urls.get("spotify"),
            "uri": item.get("uri"),
            "duration_ms": item.get("duration_ms"),
            "preview_url": item.get("preview_url"),
            "source": "spotify"
        }

    def _get_headers(self, token: str) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {token}",
            "User-Agent": "StreamHub/1.0 (Windows NT 10.0; Win64; x64)",
            "Accept": "application/json"
        }

    def search_tracks(self, query: str, limit: int = 10, market: str = DEFAULT_MARKET) -> Dict[str, Any]:
        """
        Searches Spotify catalog for tracks matching the query.
        """
        q = (query or "").strip()
        if not q:
            return {"success": True, "tracks": [], "total": 0, "query": q}

        if not self.is_configured():
            return {
                "success": False,
                "error": "Spotify credentials are not configured in backend/.env",
                "tracks": [],
                "total": 0
            }

        token = self.get_access_token()
        if not token:
            return {
                "success": False,
                "error": self._last_error or "Spotify music service is currently unavailable.",
                "tracks": [],
                "total": 0
            }

        url = f"{SPOTIFY_API_BASE_URL}/search"
        params = {
            "q": q,
            "type": "track",
            "limit": min(max(limit, 1), 50),
            "market": market
        }

        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.get(url, params=params, headers=self._get_headers(token))

                # Handle token expiry (401) by refreshing once
                if res.status_code == 401:
                    token = self.get_access_token(force_refresh=True)
                    if token:
                        res = client.get(url, params=params, headers=self._get_headers(token))

                if res.status_code == 200:
                    data = res.json()
                    track_items = data.get("tracks", {}).get("items", [])
                    normalized = [self._normalize_track(t) for t in track_items if t]
                    return {
                        "success": True,
                        "tracks": normalized,
                        "total": data.get("tracks", {}).get("total", len(normalized)),
                        "query": q
                    }

                elif res.status_code == 403:
                    resp_text = res.text
                    is_dev_restricted = "Active premium subscription required" in resp_text or "restricted" in resp_text.lower()
                    err_msg = (
                        "Spotify API access for this feature is unavailable for the current developer account."
                        if is_dev_restricted else
                        f"Spotify request forbidden (403): {resp_text}"
                    )
                    return {
                        "success": False,
                        "status_code": 403,
                        "error": err_msg,
                        "developer_restricted": True,
                        "tracks": [],
                        "total": 0
                    }

                elif res.status_code == 429:
                    retry_after = res.headers.get("Retry-After", "5")
                    return {
                        "success": False,
                        "status_code": 429,
                        "error": f"Spotify rate limit exceeded. Please retry after {retry_after} seconds.",
                        "tracks": [],
                        "total": 0
                    }

                else:
                    return {
                        "success": False,
                        "status_code": res.status_code,
                        "error": f"Spotify API returned status {res.status_code}",
                        "tracks": [],
                        "total": 0
                    }

        except httpx.TimeoutException:
            return {
                "success": False,
                "error": "Spotify API request timed out.",
                "tracks": [],
                "total": 0
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Spotify connection error: {type(e).__name__}",
                "tracks": [],
                "total": 0
            }

    def get_track(self, track_id: str, market: str = DEFAULT_MARKET) -> Dict[str, Any]:
        """
        Retrieves detailed information for a single Spotify track by ID.
        """
        tid = (track_id or "").strip()
        if not tid:
            return {"success": False, "error": "Track ID is required", "track": None}

        if not self.is_configured():
            return {
                "success": False,
                "error": "Spotify credentials are not configured in backend/.env",
                "track": None
            }

        token = self.get_access_token()
        if not token:
            return {
                "success": False,
                "error": self._last_error or "Spotify music service is currently unavailable.",
                "track": None
            }

        url = f"{SPOTIFY_API_BASE_URL}/tracks/{tid}"
        params = {"market": market}

        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.get(url, params=params, headers=self._get_headers(token))

                if res.status_code == 401:
                    token = self.get_access_token(force_refresh=True)
                    if token:
                        res = client.get(url, params=params, headers=self._get_headers(token))

                if res.status_code == 200:
                    data = res.json()
                    return {"success": True, "track": self._normalize_track(data)}
                elif res.status_code == 403:
                    resp_text = res.text
                    is_dev_restricted = "Active premium subscription required" in resp_text or "restricted" in resp_text.lower()
                    return {
                        "success": False,
                        "status_code": 403,
                        "error": "Spotify API access for this feature is unavailable for the current developer account." if is_dev_restricted else f"Spotify request forbidden (403): {resp_text}",
                        "developer_restricted": True,
                        "track": None
                    }
                elif res.status_code == 404:
                    return {"success": False, "error": "Track not found on Spotify", "track": None}
                else:
                    return {"success": False, "error": f"Spotify error: {res.status_code}", "track": None}

        except Exception as e:
            return {"success": False, "error": f"Spotify connection error: {type(e).__name__}", "track": None}

    def search_artists(self, query: str, limit: int = 10, market: str = DEFAULT_MARKET) -> Dict[str, Any]:
        """
        Searches Spotify catalog for artists matching query.
        """
        q = (query or "").strip()
        if not q:
            return {"success": True, "artists": [], "total": 0}

        if not self.is_configured():
            return {"success": False, "error": "Spotify credentials are not configured in backend/.env", "artists": []}

        token = self.get_access_token()
        if not token:
            return {"success": False, "error": self._last_error or "Spotify music service unavailable", "artists": []}

        url = f"{SPOTIFY_API_BASE_URL}/search"
        params = {"q": q, "type": "artist", "limit": min(max(limit, 1), 50), "market": market}

        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.get(url, params=params, headers=self._get_headers(token))
                if res.status_code == 200:
                    data = res.json()
                    items = data.get("artists", {}).get("items", [])
                    artists = []
                    for a in items:
                        images = a.get("images") or []
                        artists.append({
                            "id": a.get("id"),
                            "name": a.get("name"),
                            "genres": a.get("genres", []),
                            "image": images[0].get("url") if images else None,
                            "spotify_url": (a.get("external_urls") or {}).get("spotify"),
                            "popularity": a.get("popularity")
                        })
                    return {"success": True, "artists": artists, "total": data.get("artists", {}).get("total", len(artists))}
                elif res.status_code == 403:
                    return {
                        "success": False,
                        "error": "Spotify API access for this feature is unavailable for the current developer account.",
                        "developer_restricted": True,
                        "artists": []
                    }
                else:
                    return {"success": False, "error": f"Spotify status {res.status_code}", "artists": []}
        except Exception as e:
            return {"success": False, "error": str(e), "artists": []}

    def search_albums(self, query: str, limit: int = 10, market: str = DEFAULT_MARKET) -> Dict[str, Any]:
        """
        Searches Spotify catalog for albums matching query.
        """
        q = (query or "").strip()
        if not q:
            return {"success": True, "albums": [], "total": 0}

        if not self.is_configured():
            return {"success": False, "error": "Spotify credentials are not configured in backend/.env", "albums": []}

        token = self.get_access_token()
        if not token:
            return {"success": False, "error": self._last_error or "Spotify music service unavailable", "albums": []}

        url = f"{SPOTIFY_API_BASE_URL}/search"
        params = {"q": q, "type": "album", "limit": min(max(limit, 1), 50), "market": market}

        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.get(url, params=params, headers=self._get_headers(token))
                if res.status_code == 200:
                    data = res.json()
                    items = data.get("albums", {}).get("items", [])
                    albums = []
                    for a in items:
                        images = a.get("images") or []
                        artists = [art["name"] for art in a.get("artists", []) if art.get("name")]
                        albums.append({
                            "id": a.get("id"),
                            "name": a.get("name"),
                            "artists": artists,
                            "release_date": a.get("release_date"),
                            "total_tracks": a.get("total_tracks"),
                            "image": images[0].get("url") if images else None,
                            "spotify_url": (a.get("external_urls") or {}).get("spotify")
                        })
                    return {"success": True, "albums": albums, "total": data.get("albums", {}).get("total", len(albums))}
                elif res.status_code == 403:
                    return {
                        "success": False,
                        "error": "Spotify API access for this feature is unavailable for the current developer account.",
                        "developer_restricted": True,
                        "albums": []
                    }
                else:
                    return {"success": False, "error": f"Spotify status {res.status_code}", "albums": []}
        except Exception as e:
            return {"success": False, "error": str(e), "albums": []}


# Singleton instance
spotify_service = SpotifyService()
