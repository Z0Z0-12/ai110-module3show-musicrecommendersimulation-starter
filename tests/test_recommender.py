from src.recommender import (
    Song,
    UserProfile,
    Recommender,
    generate_playlist,
    load_songs,
    recommend_songs,
)
from src.rag import answer_with_rag, build_rag_prompt, retrieve_context

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


def test_rag_retrieves_catalog_and_project_context():
    songs = load_songs("data/songs.csv")
    results = retrieve_context(
        "clean study playlist with lofi instrumental songs",
        songs,
        user_prefs={"genre": "lofi", "mood": "focused", "energy": 0.35, "allow_explicit": False},
        k=5,
    )

    assert results
    assert any(chunk.source == "data/songs.csv" for chunk, _ in results)


def test_rag_prompt_includes_citations():
    songs = load_songs("data/songs.csv")
    retrieved = retrieve_context("How does the playlist generator work?", songs, k=3)
    prompt = build_rag_prompt("How does the playlist generator work?", retrieved)

    assert "Answer only from the provided context" in prompt
    assert "[" in prompt and "]" in prompt


def test_rag_falls_back_without_gemini_key():
    songs = load_songs("data/songs.csv")
    answer, sources = answer_with_rag(
        "Recommend a relaxing evening option",
        songs,
        use_gemini=False,
    )

    assert "Gemini is not configured" in answer
    assert sources


def test_rag_understands_dramatic_violin_request():
    songs = load_songs("data/songs.csv")
    answer, sources = answer_with_rag(
        "I want very dramatic music with violins",
        songs,
        use_gemini=False,
    )

    assert "Rain on Glass" in answer
    assert any(chunk.id == "song-14" for chunk, _ in sources)


def test_rag_does_not_guess_external_song_facts():
    songs = load_songs("data/songs.csv")
    answer, sources = answer_with_rag(
        "What instruments are used in the song Boulevard of Broken Dreams?",
        songs,
        use_gemini=False,
        allow_external_search=False,
    )

    assert "local catalog" in answer
    assert sources == []


def test_rag_can_use_external_song_search(monkeypatch):
    songs = load_songs("data/songs.csv")

    class FakeExternalSong:
        title = "Boulevard of Broken Dreams"
        artist = "Green Day"
        album = "American Idiot"
        genre = "Alternative"
        release_date = "2004-09-21"
        explicitness = "notExplicit"
        track_url = "https://example.com/song"
        preview_url = None

    monkeypatch.setattr("src.rag.search_itunes_songs", lambda query, limit=3: [FakeExternalSong()])

    answer, sources = answer_with_rag(
        "Find Boulevard of Broken Dreams from the internet",
        songs,
        use_gemini=False,
    )

    assert "iTunes music catalog" in answer
    assert "Boulevard of Broken Dreams" in answer
    assert sources == []
