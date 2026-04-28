# Feature Changes and New Additions

This document explains how the project has changed from the original command-line music recommender simulation, what new features were added, and how to use each one.

## 1. Web App Interface

### What changed

The original project only ran in the terminal with predefined user profiles. The updated project now includes a Streamlit web app where users can interact with the recommender through a visual interface.

### New files or code

- `src/app.py`
- `.streamlit/config.toml`

### How it is different

Before:

- Users had to run `python -m src.main`
- Recommendations were printed in the terminal
- User preferences were hardcoded in `src/main.py`

Now:

- Users can open a browser-based app
- Preferences can be changed with dropdowns, sliders, and toggles
- Recommendations update visually with ranked cards, scores, and explanations

### How to use it

Run:

```bash
source .venv/bin/activate
streamlit run src/app.py
```

Then open:

```text
http://127.0.0.1:8501
```

## 2. Brighter Redesigned UI

### What changed

The app now has a lighter, happier design instead of relying on Streamlit's default dark theme behavior.

### New UI features

- Light theme configuration
- Bright warm background
- Custom music logo in the header
- Music-themed hero section
- Softer recommendation cards
- Clearer font colors
- Better contrast for headings, labels, tabs, dropdowns, and result cards

### How it is different

Before:

- Some text was hard to read because dark-theme styles were still being inherited
- The app looked plain and default

Now:

- Text is readable on the light background
- The app has a more polished music-product feel
- Recommendation results are easier to scan

### How to use it

No extra steps are needed. The redesigned UI loads automatically when running:

```bash
streamlit run src/app.py
```

If old colors still appear in the browser, hard refresh with:

```text
Cmd + Shift + R
```

## 3. Interactive Recommendation Controls

### What changed

Users can now create their own recommendation profile directly in the app.

### New controls

- Genre dropdown
- Mood dropdown
- Energy slider
- Acoustic preference toggle
- Explicit lyrics toggle
- Number of recommendations slider
- Advanced filters for language, release decade, vocal style, and artist similarity

### How it is different

Before:

- Profiles were fixed in code
- To test a new user preference, the code had to be edited

Now:

- The user can change preferences instantly in the UI
- The recommender can be tested with many combinations without editing Python files

### How to use it

1. Open the web app.
2. Go to the **Recommendations** tab.
3. Choose a genre and mood.
4. Adjust the energy slider.
5. Turn acoustic or explicit lyric options on or off.
6. Open **Advanced preferences** for language, decade, vocal style, or artist similarity.
7. View ranked recommendations on the right.

## 4. Playlist Generator

### What changed

The project now generates full playlists for specific listening situations instead of only returning a generic top-k recommendation list.

### New playlist types

- Workout Playlist
- Study Playlist
- Relaxing Evening Playlist
- High-Energy Party Playlist

### How it is different

Before:

- The recommender only answered: "What songs match this user profile?"

Now:

- The recommender can answer: "What songs fit this activity or situation?"
- Each playlist uses preset constraints such as energy, tempo, danceability, explicit filtering, acoustic preference, and popularity.

### How to use it

1. Open the web app.
2. Go to the **Playlist Generator** tab.
3. Choose a playlist preset.
4. Adjust playlist length.
5. Choose whether explicit lyrics are allowed.
6. Optionally adjust the energy level.
7. View the generated playlist and explanations.

## 5. Expanded Song Catalog

### What changed

The song catalog was expanded from 18 songs to 36 songs.

### Updated file

- `data/songs.csv`

### How it is different

Before:

- The catalog had fewer songs
- Some genres only had one example
- Recommendations could become repetitive or overly dependent on one song

Now:

- The catalog has more variety
- There are more genres and artists
- Playlist generation has more songs to choose from
- The UI includes a Catalog tab for browsing the dataset

### How to use it

In the web app:

1. Open the **Catalog** tab.
2. Browse the full expanded song list.
3. Compare song features such as genre, mood, energy, explicit status, popularity, language, and artist similarity.

## 6. Richer Song Features

### What changed

The recommender now uses additional metadata beyond genre, mood, energy, and acousticness.

### New song fields

- `explicit`
- `popularity`
- `release_decade`
- `vocal_style`
- `language`
- `artist_similarity`

### How it is different

Before:

- Songs were mainly scored using genre, mood, and energy
- Acoustic preference was the only extra preference signal

Now:

- Explicit songs can be filtered out
- Popular songs get a small score boost
- Users can prefer a release decade
- Users can prefer vocal or instrumental tracks
- Users can prefer a language
- Users can discover songs similar to artists they already like

### How to use it

Use the **Recommendations** tab:

- Turn off **Allow explicit lyrics** to remove explicit songs.
- Open **Advanced preferences**.
- Choose a language, release decade, vocal style, or artist similarity option.

## 7. Updated Scoring Logic

### What changed

The scoring logic now includes optional bonuses and hard filters for the richer features.

### Updated file

- `src/recommender.py`

### New scoring and filtering behavior

- Genre match still gives a large score bonus
- Mood match still gives a score bonus
- Energy proximity still rewards songs close to the target energy
- Acoustic preference can add a bonus
- Popularity can add a small bonus
- Vocal style can add a bonus
- Language can add a bonus
- Release decade can add a bonus
- Artist similarity can add a bonus
- Explicit tracks can be filtered out entirely
- Playlist presets can apply hard constraints like minimum danceability or maximum energy

### How it is different

Before:

- The algorithm used a small set of signals
- The same recommendation style was used for every situation

Now:

- Recommendations can be more personalized
- Playlist generation can enforce activity-specific rules
- The recommender is closer to how real music apps combine user preferences, content features, and filters

## 8. New Tests

### What changed

Tests were added for the expanded functionality.

### Updated file

- `tests/test_recommender.py`

### New test coverage

- Confirms the expanded catalog loads correctly
- Confirms new fields are available
- Confirms explicit filtering works
- Confirms playlist generation returns ranked results

### How to use it

Run:

```bash
source .venv/bin/activate
python -m pytest
```

Expected result:

```text
5 passed
```

## 9. Original CLI Still Works

### What changed

The original terminal-based app was kept working.

### How it is different

Before:

- The CLI was the main way to use the project

Now:

- The CLI is still available
- The web app is the primary interactive experience

### How to use it

Run:

```bash
source .venv/bin/activate
python -m src.main
```

## Quick Summary

| Area | Before | Now |
|---|---|---|
| Interface | Terminal output | Browser-based Streamlit app |
| Profiles | Hardcoded | Interactive controls |
| Catalog size | 18 songs | 36 songs |
| Features | Genre, mood, energy, acousticness | Added explicit, popularity, decade, vocal style, language, artist similarity |
| Playlists | Not available | Workout, study, relaxing evening, party |
| UI design | Basic/default | Bright custom music-themed UI |
| Testing | Starter tests | Tests for catalog, filters, and playlists |
| CLI | Available | Still available |

