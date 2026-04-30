"""Streamlit web app for the Music Recommender Simulation."""

import logging
from pathlib import Path
import sys

import streamlit as st

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.recommender import (
    PLAYLIST_PRESETS,
    generate_playlist,
    load_songs,
    recommend_songs,
)
from src.rag import DEFAULT_GEMINI_MODEL, answer_with_rag


DATA_PATH = ROOT_DIR / "data" / "songs.csv"
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger(__name__)


@st.cache_data
def cached_songs():
    """Load the song catalog once per Streamlit session."""
    logger.info("Loading song catalog", extra={"path": str(DATA_PATH)})
    return load_songs(str(DATA_PATH))


def unique_values(songs, key):
    return sorted({song[key] for song in songs if song.get(key)})


def render_song_card(rank, song, score, reasons):
    explicit_label = "Explicit" if song["explicit"] else "Clean"
    st.markdown(
        f"""
        <section class="song-card">
            <div class="song-rank">#{rank}</div>
            <div class="song-main">
                <h3>{song["title"]}</h3>
                <p class="artist">{song["artist"]}</p>
                <div class="meta">
                    <span>{song["genre"]}</span>
                    <span>{song["mood"]}</span>
                    <span>{song["release_decade"]}</span>
                    <span>{song["language"]}</span>
                    <span>{explicit_label}</span>
                </div>
            </div>
            <div class="score">
                <span>{score:.2f}</span>
                <small>score</small>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )
    with st.expander("Why this recommendation?"):
        for reason in reasons:
            st.write(f"- {reason}")
        st.write(
            f"Energy {song['energy']:.2f} | Tempo {song['tempo_bpm']:.0f} BPM | "
            f"Danceability {song['danceability']:.2f} | Popularity {song['popularity']}/100"
        )
        st.write(f"Similar artists: {song['artist_similarity']}")


def render_results(results):
    if not results:
        st.warning("No songs matched the selected hard filters. Try allowing explicit tracks or loosening playlist constraints.")
        return

    for rank, (song, score, reasons) in enumerate(results, start=1):
        render_song_card(rank, song, score, reasons)


def streamlit_gemini_key():
    """Read Gemini credentials from Streamlit secrets when available."""
    try:
        return st.secrets.get("GEMINI_API_KEY") or st.secrets.get("GOOGLE_API_KEY")
    except Exception:
        return None


def main():
    st.set_page_config(page_title="Music Recommender", page_icon="🎵", layout="wide")
    st.markdown(
        """
        <style>
            :root {
                --ink: #22314a;
                --muted: #667085;
                --rose: #f25f7a;
                --coral: #ff8a5c;
                --sun: #ffd166;
                --mint: #4ecdc4;
                --sky: #4d96ff;
                --line: #f3d8a2;
                --card: rgba(255, 255, 255, 0.96);
            }

            .stApp {
                background:
                    radial-gradient(circle at 16% 12%, rgba(255, 209, 102, 0.42), transparent 28%),
                    radial-gradient(circle at 88% 8%, rgba(77, 150, 255, 0.18), transparent 25%),
                    linear-gradient(180deg, #fff8e7 0%, #f8fcff 48%, #ffffff 100%);
                color: var(--ink);
            }

            .block-container { padding-top: 1.25rem; max-width: 1180px; }
            header[data-testid="stHeader"] { background: transparent; }
            div[data-testid="stToolbar"] { color: var(--ink); }

            h1, h2, h3,
            .stMarkdown h1,
            .stMarkdown h2,
            .stMarkdown h3 {
                letter-spacing: 0;
                color: var(--ink) !important;
            }

            p, label, .stMarkdown, .stCaption, div[data-testid="stMarkdownContainer"] {
                color: var(--ink);
            }

            .app-hero {
                position: relative;
                overflow: hidden;
                border: 1px solid rgba(242, 95, 122, 0.18);
                border-radius: 18px;
                padding: 26px 30px;
                margin-bottom: 22px;
                background:
                    linear-gradient(135deg, rgba(255, 255, 255, 0.94), rgba(255, 244, 203, 0.92)),
                    linear-gradient(135deg, rgba(242, 95, 122, 0.13), rgba(77, 150, 255, 0.10));
                box-shadow: 0 24px 60px rgba(34, 49, 74, 0.10);
            }

            .app-hero::after {
                content: "";
                position: absolute;
                right: 26px;
                top: 24px;
                width: 210px;
                height: 96px;
                opacity: 0.18;
                background:
                    linear-gradient(90deg, transparent 0 16px, #f25f7a 16px 20px, transparent 20px 36px),
                    linear-gradient(90deg, transparent 0 48px, #4d96ff 48px 52px, transparent 52px 72px),
                    linear-gradient(90deg, transparent 0 86px, #4ecdc4 86px 90px, transparent 90px 112px),
                    linear-gradient(90deg, transparent 0 126px, #ff8a5c 126px 130px, transparent 130px 156px);
                border-radius: 18px;
            }

            .brand-row {
                display: flex;
                align-items: center;
                gap: 14px;
                position: relative;
                z-index: 1;
            }

            .music-logo {
                width: 58px;
                height: 58px;
                border-radius: 16px;
                display: grid;
                place-items: center;
                background: linear-gradient(135deg, var(--rose), var(--sun));
                box-shadow: 0 16px 34px rgba(242, 95, 122, 0.28);
            }

            .music-logo svg {
                width: 34px;
                height: 34px;
                fill: none;
                stroke: white;
                stroke-width: 2.6;
                stroke-linecap: round;
                stroke-linejoin: round;
            }

            .brand-copy h1 {
                margin: 0;
                font-size: clamp(2rem, 4vw, 3.15rem);
                line-height: 1.02;
                color: var(--ink) !important;
            }

            .app-subtitle {
                color: #52627a !important;
                margin: 8px 0 0;
                font-size: 1.02rem;
                font-weight: 500;
            }

            .hero-pills {
                display: flex;
                flex-wrap: wrap;
                gap: 8px;
                margin-top: 18px;
                position: relative;
                z-index: 1;
            }

            .hero-pills span {
                border: 1px solid rgba(242, 95, 122, 0.18);
                border-radius: 999px;
                padding: 6px 12px;
                color: #3c4d66;
                background: rgba(255, 255, 255, 0.70);
                font-size: 0.84rem;
                font-weight: 700;
            }

            div[data-testid="stTabs"] button {
                color: #35506d !important;
                font-weight: 700;
            }
            div[data-testid="stTabs"] button[aria-selected="true"] {
                color: var(--rose) !important;
            }
            div[data-testid="stTabs"] [data-baseweb="tab-highlight"] {
                background-color: var(--rose);
            }

            div[data-testid="stVerticalBlock"] > div:has(.stSelectbox),
            div[data-testid="stVerticalBlock"] > div:has(.stSlider),
            div[data-testid="stVerticalBlock"] > div:has(.stCheckbox) {
                color: var(--ink);
            }

            .stSelectbox label,
            .stSlider label,
            .stCheckbox label,
            .stToggle label,
            .stNumberInput label,
            .stTextInput label {
                color: var(--ink) !important;
                font-weight: 800 !important;
            }

            div[data-baseweb="select"] > div {
                background: #ffffff !important;
                border: 1px solid #f0c985 !important;
                color: var(--ink) !important;
                border-radius: 12px !important;
                min-height: 44px;
                box-shadow: 0 8px 20px rgba(34, 49, 74, 0.06);
            }

            div[data-baseweb="select"] span,
            div[data-baseweb="select"] svg {
                color: var(--ink) !important;
                fill: var(--ink) !important;
            }

            div[data-testid="stExpander"] {
                border: 1px solid #f1d6a0 !important;
                border-radius: 12px !important;
                background: rgba(255, 255, 255, 0.78) !important;
                box-shadow: 0 8px 20px rgba(34, 49, 74, 0.05);
            }
            div[data-testid="stExpander"] summary,
            div[data-testid="stExpander"] p {
                color: var(--ink) !important;
            }

            .section-title {
                display: inline-flex;
                align-items: center;
                gap: 9px;
                margin: 10px 0 14px;
                color: var(--ink);
                font-size: 1.28rem;
                font-weight: 900;
            }

            .section-title::before {
                content: "";
                width: 12px;
                height: 28px;
                border-radius: 999px;
                background: linear-gradient(180deg, var(--rose), var(--sun));
            }

            .song-card {
                display: grid;
                grid-template-columns: 48px minmax(0, 1fr) 96px;
                gap: 16px;
                align-items: center;
                border: 1px solid var(--line);
                border-radius: 16px;
                padding: 16px 18px;
                margin: 12px 0 8px;
                background: var(--card);
                box-shadow: 0 18px 44px rgba(34, 49, 74, 0.09);
            }
            .song-rank {
                width: 40px;
                height: 40px;
                border-radius: 14px;
                display: grid;
                place-items: center;
                background: linear-gradient(135deg, #ff8fab 0%, #ffd166 100%);
                color: #ffffff;
                font-weight: 900;
                box-shadow: 0 6px 16px rgba(255, 143, 171, 0.28);
            }
            .song-main h3 {
                margin: 0;
                font-size: 1.08rem;
                color: var(--ink) !important;
                font-weight: 900;
            }
            .artist {
                margin: 4px 0 10px;
                color: #53637b !important;
                font-weight: 700;
            }
            .meta { display: flex; flex-wrap: wrap; gap: 6px; }
            .meta span {
                border: 1px solid #f4d7a1;
                border-radius: 999px;
                padding: 2px 9px;
                font-size: 0.78rem;
                color: #33445d;
                background: #fff7df;
                font-weight: 700;
            }
            .score { text-align: right; }
            .score span { display: block; font-size: 1.45rem; font-weight: 800; color: #db6b32; }
            .score small { color: #7a8494; text-transform: uppercase; font-size: 0.7rem; }

            .stSlider [data-baseweb="slider"] [role="slider"] {
                background-color: var(--rose) !important;
                border-color: var(--rose) !important;
            }
            .stSlider [data-baseweb="slider"] div {
                color: var(--rose) !important;
            }

            button[kind="secondary"],
            button[data-testid="baseButton-secondary"] {
                color: var(--ink) !important;
                border-color: #f0c985 !important;
                background: #ffffff !important;
            }

            div[data-testid="stDataFrame"] {
                border-radius: 16px;
                overflow: hidden;
                box-shadow: 0 18px 44px rgba(34, 49, 74, 0.08);
            }

            @media (max-width: 640px) {
                .song-card { grid-template-columns: 40px minmax(0, 1fr); }
                .score { grid-column: 2; text-align: left; }
                .app-hero { padding: 22px 18px; }
                .brand-row { align-items: flex-start; }
                .music-logo { width: 48px; height: 48px; }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    songs = cached_songs()
    genres = unique_values(songs, "genre")
    moods = unique_values(songs, "mood")
    languages = unique_values(songs, "language")
    decades = unique_values(songs, "release_decade")
    vocal_styles = unique_values(songs, "vocal_style")
    artists = unique_values(songs, "artist")

    st.markdown(
        """
        <section class="app-hero">
            <div class="brand-row">
                <div class="music-logo" aria-hidden="true">
                    <svg viewBox="0 0 32 32">
                        <path d="M11 22V8l14-3v14" />
                        <circle cx="8" cy="23" r="4" />
                        <circle cx="22" cy="20" r="4" />
                    </svg>
                </div>
                <div class="brand-copy">
                    <h1>Music Recommender Simulation</h1>
                    <p class="app-subtitle">Bright, explainable song picks powered by genre, mood, energy, and catalog signals.</p>
                </div>
            </div>
            <div class="hero-pills">
                <span>36 songs</span>
                <span>Playlist presets</span>
                <span>Clean lyric filter</span>
                <span>Artist similarity</span>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    recommend_tab, playlist_tab, chat_tab, catalog_tab = st.tabs(
        ["Recommendations", "Playlist Generator", "Chat", "Catalog"]
    )

    with recommend_tab:
        controls, results_col = st.columns([0.34, 0.66], gap="large")
        with controls:
            st.markdown('<div class="section-title">Preferences</div>', unsafe_allow_html=True)
            genre = st.selectbox("Genre", genres, index=genres.index("pop") if "pop" in genres else 0)
            mood = st.selectbox("Mood", moods, index=moods.index("happy") if "happy" in moods else 0)
            energy = st.slider("Energy", 0.0, 1.0, 0.8, 0.01)
            likes_acoustic = st.toggle("Prefer acoustic tracks", value=False)
            allow_explicit = st.toggle("Allow explicit lyrics", value=True)
            k = st.slider("Number of recommendations", 3, 12, 5)

            with st.expander("Advanced preferences"):
                language = st.selectbox("Language", ["Any"] + languages)
                release_decade = st.selectbox("Release decade", ["Any"] + decades)
                vocal_style = st.selectbox("Vocal style", ["Any"] + vocal_styles)
                preferred_artist = st.selectbox("Artist similarity", ["None"] + artists)

        prefs = {
            "genre": genre,
            "mood": mood,
            "energy": energy,
            "likes_acoustic": likes_acoustic,
            "allow_explicit": allow_explicit,
        }
        if language != "Any":
            prefs["language"] = language
        if release_decade != "Any":
            prefs["release_decade"] = release_decade
        if vocal_style != "Any":
            prefs["vocal_style"] = vocal_style
        if preferred_artist != "None":
            prefs["preferred_artists"] = [preferred_artist]

        with results_col:
            st.markdown('<div class="section-title">Ranked Results</div>', unsafe_allow_html=True)
            render_results(recommend_songs(prefs, songs, k=k))

    with playlist_tab:
        controls, results_col = st.columns([0.34, 0.66], gap="large")
        preset_options = {value["label"]: key for key, value in PLAYLIST_PRESETS.items()}

        with controls:
            st.markdown('<div class="section-title">Playlist Type</div>', unsafe_allow_html=True)
            selected_label = st.selectbox("Preset", list(preset_options))
            preset_key = preset_options[selected_label]
            preset = PLAYLIST_PRESETS[preset_key]
            st.caption(preset["description"])
            playlist_size = st.slider("Playlist length", 5, 12, 8)
            allow_explicit_override = st.toggle(
                "Allow explicit lyrics",
                value=preset["prefs"].get("allow_explicit", True),
                key="playlist_explicit",
            )
            energy_shift = st.slider("Energy adjustment", -0.2, 0.2, 0.0, 0.01)

        base_energy = preset["prefs"]["energy"]
        overrides = {
            "allow_explicit": allow_explicit_override,
            "energy": min(1.0, max(0.0, base_energy + energy_shift)),
        }

        with results_col:
            st.markdown(f'<div class="section-title">{selected_label}</div>', unsafe_allow_html=True)
            render_results(generate_playlist(preset_key, songs, k=playlist_size, overrides=overrides))

    with chat_tab:
        chat_col, info_col = st.columns([0.66, 0.34], gap="large")

        if "rag_messages" not in st.session_state:
            st.session_state.rag_messages = [
                {
                    "role": "assistant",
                    "content": (
                        "Tell me what kind of music you want, like \"I want dramatic music with violins,\" "
                        "or ask for a real song from the wider music catalog."
                    ),
                    "sources": [],
                }
            ]

        with info_col:
            if st.button("Clear chat"):
                st.session_state.rag_messages = st.session_state.rag_messages[:1]
                st.rerun()

        with chat_col:
            st.markdown('<div class="section-title">Music Chat</div>', unsafe_allow_html=True)
            for message in st.session_state.rag_messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

            prompt = st.chat_input("Describe your mood, vibe, instrument, or song question")
            if "pending_rag_prompt" in st.session_state:
                prompt = st.session_state.pop("pending_rag_prompt")

            if prompt:
                st.session_state.rag_messages.append({"role": "user", "content": prompt, "sources": []})
                with st.chat_message("user"):
                    st.markdown(prompt)

                with st.chat_message("assistant"):
                    try:
                        answer, sources = answer_with_rag(
                            prompt,
                            songs,
                            api_key=streamlit_gemini_key(),
                            model=DEFAULT_GEMINI_MODEL,
                            use_gemini=True,
                        )
                        st.markdown(answer)
                        source_labels = [
                            f"[{chunk.id}] {chunk.title} - {chunk.source} - relevance {score:.2f}"
                            for chunk, score in sources
                        ]
                    except Exception as exc:
                        answer = "I could not answer that from the retrieved catalog context. Try asking for a mood, instrument, or song that appears in the Catalog tab."
                        source_labels = []
                        st.warning(answer)
                st.session_state.rag_messages.append(
                    {"role": "assistant", "content": answer, "sources": source_labels}
                )

    with catalog_tab:
        st.markdown('<div class="section-title">Expanded Song Catalog</div>', unsafe_allow_html=True)
        st.dataframe(
            songs,
            width="stretch",
            hide_index=True,
            column_order=[
                "title",
                "artist",
                "genre",
                "mood",
                "energy",
                "tempo_bpm",
                "danceability",
                "acousticness",
                "explicit",
                "popularity",
                "release_decade",
                "vocal_style",
                "language",
                "artist_similarity",
            ],
        )


if __name__ == "__main__":
    main()
