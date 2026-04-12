"""Command-line runner for the Music Recommender Simulation."""

from src.recommender import load_songs, recommend_songs, DEFAULT_WEIGHTS


def print_profile_results(label: str, user_prefs: dict, songs: list, weights: dict = None) -> None:
    """Print a labeled block of recommendations for one user profile."""
    w = weights or DEFAULT_WEIGHTS
    weight_note = f"  [weights: genre={w['genre']} mood={w['mood']} energy={w['energy']}]"
    print(f"\n{'=' * 60}")
    print(f"  PROFILE: {label}")
    print(f"  genre={user_prefs.get('genre')}  "
          f"mood={user_prefs.get('mood')}  "
          f"energy={user_prefs.get('energy')}")
    print(weight_note)
    print("=" * 60)

    recs = recommend_songs(user_prefs, songs, k=5, weights=weights)
    print("\n  Top recommendations:\n")
    for rank, (song, score, reasons) in enumerate(recs, start=1):
        print(f"    {rank}. {song['title']} by {song['artist']}")
        print(f"       Score : {score:.2f}")
        for reason in reasons:
            print(f"       - {reason}")
        print()


def main() -> None:
    songs = load_songs("data/songs.csv")

    # ── Standard profiles ───────────────────────────────────────────────────
    print_profile_results(
        "High-Energy Pop",
        {"genre": "pop", "mood": "happy", "energy": 0.9},
        songs,
    )

    print_profile_results(
        "Chill Lofi Study",
        {"genre": "lofi", "mood": "chill", "energy": 0.38},
        songs,
    )

    print_profile_results(
        "Deep Intense Rock",
        {"genre": "rock", "mood": "intense", "energy": 0.93},
        songs,
    )

    # ── Adversarial profile: conflicting genre + mood + energy ───────────────
    # Metal genre exists in the catalog but only as a high-energy/angry song.
    # A user who wants metal but with peaceful low-energy vibes has no real match.
    print_profile_results(
        "Adversarial — Peaceful Metal (genre vs energy conflict)",
        {"genre": "metal", "mood": "peaceful", "energy": 0.2},
        songs,
    )

    # ── Experiment: halve genre weight, double energy weight ─────────────────
    # Hypothesis: Iron Curtain should drop; energy-close soft songs should rise.
    print_profile_results(
        "EXPERIMENT — Peaceful Metal  [genre=1.0  energy=3.0]",
        {"genre": "metal", "mood": "peaceful", "energy": 0.2},
        songs,
        weights={"genre": 1.0, "mood": 1.0, "energy": 3.0},
    )


if __name__ == "__main__":
    main()
