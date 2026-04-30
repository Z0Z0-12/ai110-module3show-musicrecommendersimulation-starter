"""Retrieval-augmented assistant for explaining recommendations."""

from __future__ import annotations

import json
import logging
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from src.external_music import format_external_song_answer, search_itunes_songs
from src.recommender import PLAYLIST_PRESETS, recommend_songs


ROOT_DIR = Path(__file__).resolve().parents[1]
PROJECT_DOCS = ("FEATURE_CHANGES.md", "README.md")
DEFAULT_GEMINI_MODEL = "gemini-1.5-flash"
TOKEN_RE = re.compile(r"[a-z0-9]+")
logger = logging.getLogger(__name__)


QUERY_EXPANSIONS = {
    "dramatic": "classical melancholic intense cinematic strings violin orchestral",
    "violin": "classical strings orchestral instrumental acoustic melancholic",
    "violins": "classical strings orchestral instrumental acoustic melancholic",
    "string": "classical strings orchestral instrumental acoustic",
    "strings": "classical strings orchestral instrumental acoustic",
    "orchestra": "classical orchestral strings instrumental",
    "orchestral": "classical orchestral strings instrumental",
    "cinematic": "classical ambient dramatic instrumental",
    "sad": "melancholic moody nostalgic low energy",
    "calm": "peaceful relaxed chill ambient acoustic low energy",
    "relax": "peaceful relaxed chill ambient acoustic low energy",
    "relaxing": "peaceful relaxed chill ambient acoustic low energy",
    "study": "focused lofi instrumental chill low energy",
    "focus": "focused lofi instrumental low energy",
    "coding": "focused lofi instrumental low energy",
    "workout": "intense pop electronic danceability high energy",
    "gym": "intense pop electronic danceability high energy",
    "party": "euphoric electronic danceability high energy",
    "guitar": "rock folk country acoustic vocal",
    "guitars": "rock folk country acoustic vocal",
    "piano": "classical jazz instrumental acoustic peaceful",
    "instrumental": "instrumental lofi classical ambient electronic",
    "clean": "clean non explicit",
}

MUSIC_REQUEST_TERMS = {
    "music",
    "song",
    "songs",
    "track",
    "tracks",
    "listen",
    "listening",
    "vibe",
    "mood",
    "chill",
    "study",
    "studying",
    "exam",
    "dramatic",
    "violin",
    "violins",
    "guitar",
    "piano",
    "instrument",
    "instruments",
    "instrumentation",
    "instrumental",
    "workout",
    "party",
    "relaxing",
    "calm",
    "clean",
}

EXTERNAL_SEARCH_TERMS = {
    "internet",
    "online",
    "itunes",
    "apple",
    "spotify",
    "youtube",
    "real",
    "actual",
    "popular",
    "world",
    "external",
    "any",
}


@dataclass(frozen=True)
class RagChunk:
    """A small unit of context that can be cited in a grounded answer."""

    id: str
    title: str
    source: str
    text: str


def _tokens(text: str) -> set[str]:
    return set(TOKEN_RE.findall(text.lower()))


def expanded_query(query: str) -> str:
    """Append simple domain synonyms so natural-language music asks retrieve well."""
    additions = []
    for token in _tokens(query):
        if token in QUERY_EXPANSIONS:
            additions.append(QUERY_EXPANSIONS[token])
    return " ".join([query, *additions])


def infer_query_preferences(query: str) -> Dict:
    """Infer recommender preferences from a free-form music request."""
    tokens = _tokens(query)
    prefs: Dict = {"allow_explicit": "explicit" in tokens and "clean" not in tokens}

    if tokens & {"violin", "violins", "string", "strings", "orchestra", "orchestral"}:
        prefs.update({"genre": "classical", "mood": "melancholic", "energy": 0.35, "vocal_style": "instrumental"})
    elif tokens & {"study", "studying", "exam", "focus", "focused", "coding", "homework"}:
        prefs.update({"genre": "lofi", "mood": "focused", "energy": 0.35, "vocal_style": "instrumental"})
    elif tokens & {"workout", "gym", "run", "running"}:
        prefs.update({"genre": "pop", "mood": "intense", "energy": 0.9})
    elif tokens & {"party", "dance", "club"}:
        prefs.update({"genre": "electronic", "mood": "euphoric", "energy": 0.92})
    elif tokens & {"calm", "relax", "relaxing", "peaceful", "sleep"}:
        prefs.update({"genre": "ambient", "mood": "peaceful", "energy": 0.25})
    elif tokens & {"guitar", "guitars", "acoustic"}:
        prefs.update({"genre": "folk", "mood": "peaceful", "energy": 0.35, "likes_acoustic": True})
    elif tokens & {"dramatic", "cinematic", "emotional"}:
        prefs.update({"genre": "classical", "mood": "melancholic", "energy": 0.4, "vocal_style": "instrumental"})

    if "clean" in tokens or "nonexplicit" in tokens:
        prefs["allow_explicit"] = False
    return prefs


def is_music_request(query: str) -> bool:
    """Return whether the user is asking for song recommendations or song facts."""
    return bool(_tokens(query) & MUSIC_REQUEST_TERMS)


def instrumentation_tags(song: Dict) -> List[str]:
    """Return catalog-grounded/inferred instrument tags for conversational search."""
    tags: List[str] = []
    genre = str(song.get("genre", "")).lower()
    vocal_style = str(song.get("vocal_style", "")).lower()
    acousticness = float(song.get("acousticness", 0.0))

    if genre == "classical":
        tags.extend(["strings", "violins", "piano", "orchestral"])
    if genre in {"folk", "country"} or acousticness > 0.7:
        tags.extend(["acoustic guitar", "warm acoustic texture"])
    if genre in {"rock", "metal"}:
        tags.extend(["electric guitar", "drums"])
    if genre in {"jazz", "soul", "r&b"}:
        tags.extend(["keys", "bass", "drums"])
    if genre in {"electronic", "synthwave", "k-pop", "pop"}:
        tags.extend(["synths", "drums", "programmed beat"])
    if genre in {"lofi", "ambient"}:
        tags.extend(["soft keys", "pads", "light percussion"])
    if vocal_style == "instrumental":
        tags.append("instrumental")
    else:
        tags.append("vocals")
    return sorted(set(tags))


def query_mentions_catalog_title(query: str, songs: Sequence[Dict]) -> bool:
    """Return whether the query names a song in this project's catalog."""
    normalized_query = query.lower()
    return any(str(song.get("title", "")).lower() in normalized_query for song in songs)


def asks_external_song_fact(query: str, songs: Sequence[Dict]) -> bool:
    """Detect fact questions about a named song that is outside the local catalog."""
    tokens = _tokens(query)
    asks_instruments = bool(tokens & {"instrument", "instruments", "instrumentation"})
    song_fact_phrase = bool(re.search(r"\b(song|track|by)\b", query.lower()))
    likely_named_song = len(tokens) > 4
    return asks_instruments and (song_fact_phrase or likely_named_song) and not query_mentions_catalog_title(query, songs)


def wants_external_search(query: str, songs: Sequence[Dict]) -> bool:
    """Return whether the query should use the external music catalog."""
    tokens = _tokens(query)
    if query_mentions_catalog_title(query, songs):
        return False
    if tokens & EXTERNAL_SEARCH_TERMS:
        return True
    if asks_external_song_fact(query, songs):
        return True
    asks_song_fact = bool(tokens & {"who", "what", "when", "where", "album", "artist", "released", "release"})
    mentions_songish_phrase = bool(re.search(r"\b(song|track|music|by)\b", query.lower()))
    return asks_song_fact and mentions_songish_phrase and is_music_request(query)


def song_to_chunk(song: Dict) -> RagChunk:
    """Convert one song row into a searchable RAG chunk."""
    explicit = "explicit" if song.get("explicit") else "clean"
    instruments = ", ".join(instrumentation_tags(song))
    text = (
        f"{song['title']} by {song['artist']} is a {explicit} {song['genre']} song "
        f"with a {song['mood']} mood, energy {float(song['energy']):.2f}, "
        f"tempo {float(song['tempo_bpm']):.0f} BPM, valence {float(song['valence']):.2f}, "
        f"danceability {float(song['danceability']):.2f}, acousticness {float(song['acousticness']):.2f}, "
        f"popularity {int(song['popularity'])}/100, release decade {song['release_decade']}, "
        f"vocal style {song['vocal_style']}, language {song['language']}, "
        f"similar artists {song.get('artist_similarity') or 'none'}, "
        f"and inferred instrument tags for this catalog: {instruments}."
    )
    return RagChunk(
        id=f"song-{song['id']}",
        title=f"{song['title']} by {song['artist']}",
        source="data/songs.csv",
        text=text,
    )


def playlist_chunks() -> List[RagChunk]:
    """Return searchable chunks describing the named playlist presets."""
    chunks: List[RagChunk] = []
    for preset_id, preset in PLAYLIST_PRESETS.items():
        prefs = ", ".join(f"{key}={value}" for key, value in preset["prefs"].items())
        chunks.append(
            RagChunk(
                id=f"playlist-{preset_id}",
                title=preset["label"],
                source="src/recommender.py",
                text=f"{preset['label']}: {preset['description']} Preset preferences: {prefs}.",
            )
        )
    return chunks


def project_doc_chunks(root_dir: Path = ROOT_DIR) -> List[RagChunk]:
    """Split local project notes into compact chunks for retrieval."""
    chunks: List[RagChunk] = []
    for file_name in PROJECT_DOCS:
        path = root_dir / file_name
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        sections = re.split(r"\n(?=#{1,3}\s+)", text)
        for index, section in enumerate(sections, start=1):
            cleaned = " ".join(section.split())
            if len(cleaned) < 80:
                continue
            title_match = re.match(r"#{1,3}\s+(.+)", section.strip())
            title = title_match.group(1).strip() if title_match else file_name
            chunks.append(
                RagChunk(
                    id=f"{file_name}:{index}",
                    title=title,
                    source=file_name,
                    text=cleaned[:1400],
                )
            )
    return chunks


def build_rag_corpus(songs: Sequence[Dict], include_project_docs: bool = True) -> List[RagChunk]:
    """Build the local retrieval corpus from catalog rows and project docs."""
    chunks = [song_to_chunk(song) for song in songs]
    chunks.extend(playlist_chunks())
    if include_project_docs:
        chunks.extend(project_doc_chunks())
    return chunks


def retrieve_context(
    query: str,
    songs: Sequence[Dict],
    user_prefs: Optional[Dict] = None,
    k: int = 8,
    include_project_docs: bool = True,
) -> List[Tuple[RagChunk, float]]:
    """Retrieve relevant chunks using lexical overlap plus recommender scores."""
    expanded = expanded_query(query)
    query_tokens = _tokens(expanded)
    search_song_first = is_music_request(query)
    chunks = build_rag_corpus(
        songs,
        include_project_docs=include_project_docs and not search_song_first,
    )
    recommendation_boosts: Dict[str, float] = {}

    prefs = user_prefs or infer_query_preferences(query)
    if prefs:
        for rank, (song, score, _) in enumerate(recommend_songs(prefs, list(songs), k=10), start=1):
            recommendation_boosts[f"song-{song['id']}"] = (score / 5.0) + (1.0 / rank)

    scored: List[Tuple[RagChunk, float]] = []
    for chunk in chunks:
        chunk_tokens = _tokens(f"{chunk.title} {chunk.source} {chunk.text}")
        overlap = len(query_tokens & chunk_tokens)
        coverage = overlap / max(len(query_tokens), 1)
        source_boost = 2.0 if chunk.source == "data/songs.csv" else 0.0
        title_boost = 5.0 if chunk.title.lower().split(" by ")[0] in query.lower() else 0.0
        score = overlap + coverage + source_boost + title_boost + recommendation_boosts.get(chunk.id, 0.0)
        if score > 0:
            scored.append((chunk, score))

    scored.sort(key=lambda item: item[1], reverse=True)
    retrieved = scored[:k]
    logger.info(
        "Retrieved RAG context",
        extra={
            "query": query,
            "retrieved_count": len(retrieved),
            "song_first": search_song_first,
            "top_source": retrieved[0][0].source if retrieved else None,
        },
    )
    return retrieved


def format_context(retrieved: Iterable[Tuple[RagChunk, float]]) -> str:
    """Format retrieved chunks for an LLM prompt."""
    lines = []
    for chunk, _ in retrieved:
        lines.append(f"[{chunk.id}] {chunk.title} ({chunk.source})\n{chunk.text}")
    return "\n\n".join(lines)


def build_rag_prompt(query: str, retrieved: Sequence[Tuple[RagChunk, float]]) -> str:
    """Create a grounded answer prompt from retrieved context."""
    context = format_context(retrieved)
    return (
        "You are a music recommendation chat assistant for a classroom project. "
        "Answer only from the provided context. If the context is not enough, say what is missing. "
        "Cite relevant chunk ids in square brackets, such as [song-1]. "
        "When recommending music, give one or two specific catalog songs and briefly explain the match. "
        "If the user asks about a real-world song that is not in the catalog, do not invent facts; say it is outside this project's catalog. "
        "Keep the answer concise, practical, and specific to the catalog.\n\n"
        f"Context:\n{context}\n\n"
        f"User question:\n{query}\n\n"
        "Grounded answer:"
    )


def _is_song_chunk(chunk: RagChunk) -> bool:
    return chunk.source == "data/songs.csv"


def fallback_grounded_answer(query: str, retrieved: Sequence[Tuple[RagChunk, float]]) -> str:
    """Return a deterministic grounded answer when no Gemini key is configured."""
    if not retrieved:
        return "I could not find enough matching context in this project catalog to answer that."

    song_chunks = [chunk for chunk, _ in retrieved if _is_song_chunk(chunk)]
    if song_chunks:
        picks = song_chunks[:2]
        asks_instruments = bool(_tokens(query) & {"instrument", "instruments", "instrumentation"})
        if asks_instruments:
            lines = ["From this catalog, the closest grounded instrumentation answer is:", ""]
        else:
            lines = ["Based on this catalog, I would try:", ""]
        for chunk in picks:
            lines.append(f"- **{chunk.title}** [{chunk.id}]: {chunk.text}")
        lines.append("")
        lines.append("This answer is grounded in the local song catalog. Gemini is not configured, so I used the built-in retriever and scoring fallback.")
        return "\n".join(lines)

    return "I could not find a strong enough song match in this project's catalog to answer that."


def answer_is_grounded(answer: str, retrieved: Sequence[Tuple[RagChunk, float]], query: str) -> bool:
    """Reject weak LLM answers before showing them to users."""
    if not answer or len(answer.strip()) < 20:
        return False
    if is_music_request(query) and not any(_is_song_chunk(chunk) for chunk, _ in retrieved):
        return False
    if "i don't know" in answer.lower() or "cannot answer" in answer.lower():
        return True
    return any(f"[{chunk.id}]" in answer for chunk, _ in retrieved[:6])


def gemini_api_key() -> Optional[str]:
    """Read the Gemini key from the environment without storing it in code."""
    return os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")


def generate_with_gemini(
    prompt: str,
    api_key: Optional[str] = None,
    model: str = DEFAULT_GEMINI_MODEL,
    timeout: int = 30,
) -> str:
    """Call Gemini's generateContent REST API and return the text response."""
    key = api_key or gemini_api_key()
    if not key:
        raise ValueError("Set GEMINI_API_KEY before calling Gemini.")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.35,
            "topP": 0.9,
            "maxOutputTokens": 700,
        },
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Gemini API request failed with HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Gemini API request failed: {exc.reason}") from exc

    candidates = data.get("candidates") or []
    if not candidates:
        raise RuntimeError("Gemini returned no candidates.")
    parts = candidates[0].get("content", {}).get("parts", [])
    text = "".join(part.get("text", "") for part in parts).strip()
    if not text:
        raise RuntimeError("Gemini returned an empty response.")
    return text


def answer_with_rag(
    query: str,
    songs: Sequence[Dict],
    user_prefs: Optional[Dict] = None,
    api_key: Optional[str] = None,
    model: str = DEFAULT_GEMINI_MODEL,
    use_gemini: bool = True,
    allow_external_search: bool = True,
) -> Tuple[str, List[Tuple[RagChunk, float]]]:
    """Retrieve local context and answer with Gemini, falling back when unavailable."""
    if allow_external_search and wants_external_search(query, songs):
        logger.info("Routing chat request to external music search", extra={"query": query})
        external_songs = search_itunes_songs(query, limit=3)
        if external_songs:
            return format_external_song_answer(query, external_songs), []

    if asks_external_song_fact(query, songs):
        if allow_external_search:
            logger.info("Trying external search for outside-catalog song fact", extra={"query": query})
            external_songs = search_itunes_songs(query, limit=3)
            if external_songs:
                return format_external_song_answer(query, external_songs), []
        logger.info("Blocked unsupported outside-catalog song fact", extra={"query": query})
        return (
            "I cannot answer that from this project's local catalog, and I could not find a reliable external song match.",
            [],
        )

    retrieved = retrieve_context(query, songs, user_prefs=user_prefs)
    if is_music_request(query) and not any(_is_song_chunk(chunk) for chunk, _ in retrieved):
        if allow_external_search:
            logger.info("No local song context found; trying external search", extra={"query": query})
            external_songs = search_itunes_songs(query, limit=3)
            if external_songs:
                return format_external_song_answer(query, external_songs), retrieved
        logger.info("No strong local or external song match", extra={"query": query})
        return "I could not find a strong enough song match in this project's catalog to answer that.", retrieved

    prompt = build_rag_prompt(query, retrieved)
    if use_gemini and (api_key or gemini_api_key()):
        logger.info("Generating grounded Gemini answer", extra={"query": query, "context_count": len(retrieved)})
        answer = generate_with_gemini(prompt, api_key=api_key, model=model)
        if answer_is_grounded(answer, retrieved, query):
            return answer, retrieved
        logger.info("Rejected ungrounded Gemini answer", extra={"query": query})
        return "I could not answer that confidently from this project's retrieved catalog context.", retrieved
    logger.info("Using deterministic RAG fallback answer", extra={"query": query, "context_count": len(retrieved)})
    return fallback_grounded_answer(query, retrieved), retrieved
