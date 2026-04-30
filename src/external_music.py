"""External song search through Apple's public iTunes Search API."""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import List, Optional


ITUNES_SEARCH_URL = "https://itunes.apple.com/search"
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ExternalSong:
    """A song result from an external catalog."""

    title: str
    artist: str
    album: str
    genre: str
    release_date: str
    explicitness: str
    track_url: str
    preview_url: Optional[str] = None


def search_itunes_songs(query: str, limit: int = 5, country: str = "US") -> List[ExternalSong]:
    """Search the iTunes catalog for songs matching a free-form query."""
    logger.info("Searching external iTunes catalog", extra={"query": query, "limit": limit, "country": country})
    params = {
        "term": query,
        "media": "music",
        "entity": "song",
        "limit": str(limit),
        "country": country,
    }
    url = f"{ITUNES_SEARCH_URL}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url, headers={"User-Agent": "MusicRecommenderSimulation/1.0"})

    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        logger.warning("External iTunes search failed", extra={"query": query, "error": str(exc)})
        return []

    songs: List[ExternalSong] = []
    for item in payload.get("results", []):
        title = item.get("trackName")
        artist = item.get("artistName")
        track_url = item.get("trackViewUrl")
        if not title or not artist or not track_url:
            continue
        songs.append(
            ExternalSong(
                title=title,
                artist=artist,
                album=item.get("collectionName", "Unknown album"),
                genre=item.get("primaryGenreName", "Unknown genre"),
                release_date=item.get("releaseDate", "")[:10],
                explicitness=item.get("trackExplicitness", "notExplicit"),
                track_url=track_url,
                preview_url=item.get("previewUrl"),
            )
        )
    logger.info("External iTunes search completed", extra={"query": query, "result_count": len(songs)})
    return songs


def format_external_song_answer(query: str, songs: List[ExternalSong]) -> str:
    """Format external search results for the chat assistant."""
    if not songs:
        return "I could not find a reliable external song match for that request."

    lines = [
        "I could not answer that from the local 36-song project catalog, so I searched the iTunes music catalog and found:",
        "",
    ]
    for song in songs[:3]:
        release = f", released {song.release_date}" if song.release_date else ""
        explicit = "explicit" if song.explicitness == "explicit" else "clean"
        lines.append(
            f"- **{song.title}** by **{song.artist}** - {song.album} ({song.genre}{release}, {explicit}). [Open in iTunes]({song.track_url})"
        )
    lines.append("")
    lines.append("These external results are catalog search matches, not scored with the local mood/energy recommender.")
    return "\n".join(lines)
