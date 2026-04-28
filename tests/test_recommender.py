from src.recommender import (
    Song,
    UserProfile,
    Recommender,
    generate_playlist,
    load_songs,
    recommend_songs,
)

def make_small_recommender() -> Recommender:
    songs = [
        Song(
            id=1,
            title="Test Pop Track",
            artist="Test Artist",
            genre="pop",
            mood="happy",
            energy=0.8,
            tempo_bpm=120,
            valence=0.9,
            danceability=0.8,
            acousticness=0.2,
        ),
        Song(
            id=2,
            title="Chill Lofi Loop",
            artist="Test Artist",
            genre="lofi",
            mood="chill",
            energy=0.4,
            tempo_bpm=80,
            valence=0.6,
            danceability=0.5,
            acousticness=0.9,
        ),
    ]
    return Recommender(songs)


def test_recommend_returns_songs_sorted_by_score():
    user = UserProfile(
        favorite_genre="pop",
        favorite_mood="happy",
        target_energy=0.8,
        likes_acoustic=False,
    )
    rec = make_small_recommender()
    results = rec.recommend(user, k=2)

    assert len(results) == 2
    # Starter expectation: the pop, happy, high energy song should score higher
    assert results[0].genre == "pop"
    assert results[0].mood == "happy"


def test_explain_recommendation_returns_non_empty_string():
    user = UserProfile(
        favorite_genre="pop",
        favorite_mood="happy",
        target_energy=0.8,
        likes_acoustic=False,
    )
    rec = make_small_recommender()
    song = rec.songs[0]

    explanation = rec.explain_recommendation(user, song)
    assert isinstance(explanation, str)
    assert explanation.strip() != ""


def test_load_songs_includes_expanded_catalog_fields():
    songs = load_songs("data/songs.csv")

    assert len(songs) >= 30
    assert {"explicit", "popularity", "release_decade", "vocal_style", "language", "artist_similarity"} <= set(songs[0])
    assert isinstance(songs[0]["explicit"], bool)
    assert isinstance(songs[0]["popularity"], int)


def test_recommend_songs_can_filter_explicit_tracks():
    songs = [
        {
            "id": 1,
            "title": "Clean Track",
            "artist": "A",
            "genre": "pop",
            "mood": "happy",
            "energy": 0.8,
            "tempo_bpm": 120,
            "valence": 0.8,
            "danceability": 0.8,
            "acousticness": 0.2,
            "explicit": False,
            "popularity": 60,
        },
        {
            "id": 2,
            "title": "Explicit Track",
            "artist": "B",
            "genre": "pop",
            "mood": "happy",
            "energy": 0.8,
            "tempo_bpm": 120,
            "valence": 0.8,
            "danceability": 0.8,
            "acousticness": 0.2,
            "explicit": True,
            "popularity": 90,
        },
    ]

    results = recommend_songs(
        {"genre": "pop", "mood": "happy", "energy": 0.8, "allow_explicit": False},
        songs,
        k=5,
    )

    assert len(results) == 1
    assert results[0][0]["title"] == "Clean Track"


def test_generate_playlist_returns_named_playlist_results():
    songs = load_songs("data/songs.csv")
    results = generate_playlist("study", songs, k=5)

    assert len(results) == 5
    assert all(not song["explicit"] for song, _, _ in results)
    assert results[0][1] >= results[-1][1]
