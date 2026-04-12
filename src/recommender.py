"""Core recommendation logic: data loading, scoring, and ranking."""

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
            songs.append(row)
    print(f"Loaded songs: {len(songs)}")
    return songs



# Default weights used by score_song. Pass a different dict to experiment without
# touching the production values.
DEFAULT_WEIGHTS = {
    "genre": 2.0,   # genre is the strongest signal
    "mood": 1.0,    # mood refines within a genre
    "energy": 1.5,  # continuous proximity reward
}


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

    return score, reasons


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
        score, reasons = score_song(user_prefs, song, weights=weights)
        scored.append((song, score, reasons))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:k]
