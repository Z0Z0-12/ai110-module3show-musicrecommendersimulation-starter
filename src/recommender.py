"""Core recommendation logic: data loading, scoring, ranking, and playlists."""

import csv
from typing import List, Dict, Tuple
from dataclasses import dataclass


@dataclass
class Song:
    """Represents a song and its audio attributes."""
    id: int
    title: str
    artist: str
    genre: str
    mood: str
    energy: float
    tempo_bpm: float
    valence: float
    danceability: float
    acousticness: float
    explicit: bool = False
    popularity: int = 50
    release_decade: str = "2020s"
    vocal_style: str = "vocal"
    language: str = "English"
    artist_similarity: str = ""


@dataclass
class UserProfile:
    """Stores a user's musical taste preferences."""
    favorite_genre: str
    favorite_mood: str
    target_energy: float
    likes_acoustic: bool


class Recommender:
    """OOP wrapper around the scoring logic; required by tests/test_recommender.py."""

    def __init__(self, songs: List[Song]):
        self.songs = songs

    def _score(self, user: UserProfile, song: Song) -> Tuple[float, List[str]]:
        """Return (total_score, reasons) for one Song against a UserProfile."""
        score = 0.0
        reasons: List[str] = []

        if song.genre == user.favorite_genre:
            score += 2.0
            reasons.append("genre match (+2.0)")

        if song.mood == user.favorite_mood:
            score += 1.0
            reasons.append("mood match (+1.0)")

        energy_sim = 1.0 - abs(user.target_energy - song.energy)
        energy_pts = round(energy_sim * 1.5, 2)
        score += energy_pts
        reasons.append(f"energy proximity {energy_sim:.2f} (+{energy_pts})")

        if user.likes_acoustic and song.acousticness > 0.6:
            score += 1.0
            reasons.append("acoustic preference (+1.0)")

        return score, reasons

    def recommend(self, user: UserProfile, k: int = 5) -> List[Song]:
        """Return the top-k Song objects ranked by score for the given user."""
        # .sort() mutates the list in place — avoids creating a second list.
        scored = [(song, self._score(user, song)[0]) for song in self.songs]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [song for song, _ in scored[:k]]

    def explain_recommendation(self, user: UserProfile, song: Song) -> str:
        """Return a human-readable explanation of why a song was recommended."""
        _, reasons = self._score(user, song)
        if not reasons:
            return "General match based on available features."
        return "Recommended because: " + ", ".join(reasons) + "."


def load_songs(csv_path: str) -> List[Dict]:
    """Read songs.csv and return a list of dicts with numeric columns cast to float/int."""
    songs: List[Dict] = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row["id"] = int(row["id"])
            row["energy"] = float(row["energy"])
            row["tempo_bpm"] = float(row["tempo_bpm"])
            row["valence"] = float(row["valence"])
            row["danceability"] = float(row["danceability"])
            row["acousticness"] = float(row["acousticness"])
            row["explicit"] = parse_bool(row.get("explicit", False))
            row["popularity"] = int(row.get("popularity", 50))
            row["release_decade"] = row.get("release_decade", "2020s")
            row["vocal_style"] = row.get("vocal_style", "vocal")
            row["language"] = row.get("language", "English")
            row["artist_similarity"] = row.get("artist_similarity", "")
            songs.append(row)
    print(f"Loaded songs: {len(songs)}")
    return songs



# Default weights used by score_song. Pass a different dict to experiment without
# touching the production values.
DEFAULT_WEIGHTS = {
    "genre": 2.0,   # genre is the strongest signal
    "mood": 1.0,    # mood refines within a genre
    "energy": 1.5,  # continuous proximity reward
    "popularity": 0.5,
    "decade": 0.4,
    "vocal_style": 0.4,
    "language": 0.3,
    "artist_similarity": 0.6,
}


PLAYLIST_PRESETS = {
    "workout": {
        "label": "Workout Playlist",
        "prefs": {
            "genre": "pop",
            "mood": "intense",
            "energy": 0.9,
            "min_danceability": 0.7,
            "min_tempo_bpm": 115,
            "allow_explicit": True,
        },
        "description": "High-energy tracks with strong tempo and danceability.",
    },
    "study": {
        "label": "Study Playlist",
        "prefs": {
            "genre": "lofi",
            "mood": "focused",
            "energy": 0.35,
            "max_energy": 0.55,
            "vocal_style": "instrumental",
            "allow_explicit": False,
        },
        "description": "Lower-energy, mostly instrumental music for focus.",
    },
    "relaxing_evening": {
        "label": "Relaxing Evening Playlist",
        "prefs": {
            "genre": "jazz",
            "mood": "relaxed",
            "energy": 0.35,
            "likes_acoustic": True,
            "max_energy": 0.6,
            "allow_explicit": False,
        },
        "description": "Warm, acoustic-leaning tracks for winding down.",
    },
    "party": {
        "label": "High-Energy Party Playlist",
        "prefs": {
            "genre": "electronic",
            "mood": "euphoric",
            "energy": 0.92,
            "min_danceability": 0.78,
            "min_popularity": 65,
            "allow_explicit": True,
        },
        "description": "Popular, danceable tracks that keep the energy high.",
    },
}


def parse_bool(value) -> bool:
    """Parse bool-ish CSV/user values."""
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def score_song(
    user_prefs: Dict,
    song: Dict,
    weights: Dict = None,
) -> Tuple[float, List[str]]:
    """Score one song dict against user preferences; returns (score, reasons)."""
    w = weights if weights is not None else DEFAULT_WEIGHTS
    score = 0.0
    reasons: List[str] = []

    if song.get("genre") == user_prefs.get("genre"):
        pts = w["genre"]
        score += pts
        reasons.append(f"genre match (+{pts})")

    if song.get("mood") == user_prefs.get("mood"):
        pts = w["mood"]
        score += pts
        reasons.append(f"mood match (+{pts})")

    if "energy" in user_prefs and "energy" in song:
        energy_sim = 1.0 - abs(float(user_prefs["energy"]) - float(song["energy"]))
        energy_pts = round(energy_sim * w["energy"], 2)
        score += energy_pts
        reasons.append(f"energy proximity {energy_sim:.2f} (+{energy_pts})")

    if user_prefs.get("likes_acoustic") and float(song.get("acousticness", 0.0)) > 0.6:
        score += 1.0
        reasons.append("acoustic preference (+1.0)")

    if user_prefs.get("vocal_style") and song.get("vocal_style") == user_prefs.get("vocal_style"):
        pts = w.get("vocal_style", 0.0)
        score += pts
        reasons.append(f"{song['vocal_style']} style match (+{pts})")

    if user_prefs.get("language") and song.get("language") == user_prefs.get("language"):
        pts = w.get("language", 0.0)
        score += pts
        reasons.append(f"language match (+{pts})")

    if user_prefs.get("release_decade") and song.get("release_decade") == user_prefs.get("release_decade"):
        pts = w.get("decade", 0.0)
        score += pts
        reasons.append(f"release decade match (+{pts})")

    preferred_artists = user_prefs.get("preferred_artists") or []
    if isinstance(preferred_artists, str):
        preferred_artists = [preferred_artists]
    similar_artists = {
        artist.strip().lower()
        for artist in str(song.get("artist_similarity", "")).split("|")
        if artist.strip()
    }
    if preferred_artists and any(artist.lower() in similar_artists for artist in preferred_artists):
        pts = w.get("artist_similarity", 0.0)
        score += pts
        reasons.append(f"artist similarity match (+{pts})")

    popularity = float(song.get("popularity", 0.0))
    popularity_weight = w.get("popularity", 0.0)
    if popularity and popularity_weight:
        popularity_pts = round((popularity / 100.0) * popularity_weight, 2)
        score += popularity_pts
        reasons.append(f"popularity signal {int(popularity)}/100 (+{popularity_pts})")

    return score, reasons


def song_matches_constraints(song: Dict, user_prefs: Dict) -> bool:
    """Return whether a song passes hard filters before ranking."""
    if not user_prefs.get("allow_explicit", True) and parse_bool(song.get("explicit", False)):
        return False

    if "min_energy" in user_prefs and float(song.get("energy", 0.0)) < float(user_prefs["min_energy"]):
        return False

    if "max_energy" in user_prefs and float(song.get("energy", 0.0)) > float(user_prefs["max_energy"]):
        return False

    if "min_danceability" in user_prefs and float(song.get("danceability", 0.0)) < float(user_prefs["min_danceability"]):
        return False

    if "min_tempo_bpm" in user_prefs and float(song.get("tempo_bpm", 0.0)) < float(user_prefs["min_tempo_bpm"]):
        return False

    if "min_popularity" in user_prefs and int(song.get("popularity", 0)) < int(user_prefs["min_popularity"]):
        return False

    return True


def recommend_songs(
    user_prefs: Dict,
    songs: List[Dict],
    k: int = 5,
    weights: Dict = None,
) -> List[Tuple[Dict, float, List[str]]]:
    """Score all songs, rank by score descending, and return the top-k as (song, score, reasons)."""
    # Why .sort() instead of sorted()?
    # sorted() returns a new list — cleaner when you need to keep the original.
    # .sort() mutates in place with slightly less memory overhead, which is fine
    # here since `scored` is a local throwaway list.
    scored: List[Tuple[Dict, float, List[str]]] = []
    for song in songs:
        if not song_matches_constraints(song, user_prefs):
            continue
        score, reasons = score_song(user_prefs, song, weights=weights)
        scored.append((song, score, reasons))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:k]


def generate_playlist(
    preset_name: str,
    songs: List[Dict],
    k: int = 8,
    overrides: Dict = None,
    weights: Dict = None,
) -> List[Tuple[Dict, float, List[str]]]:
    """Generate a named playlist from preset constraints and optional preference overrides."""
    if preset_name not in PLAYLIST_PRESETS:
        valid = ", ".join(sorted(PLAYLIST_PRESETS))
        raise ValueError(f"Unknown playlist preset '{preset_name}'. Choose one of: {valid}")

    prefs = dict(PLAYLIST_PRESETS[preset_name]["prefs"])
    if overrides:
        prefs.update(overrides)

    return recommend_songs(prefs, songs, k=k, weights=weights)
