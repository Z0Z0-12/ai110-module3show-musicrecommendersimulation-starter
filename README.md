# 🎵 Music Recommender Simulation

## Project Summary

In this project you will build and explain a small music recommender system.

Your goal is to:

- Represent songs and a user "taste profile" as data
- Design a scoring rule that turns that data into recommendations
- Evaluate what your system gets right and wrong
- Reflect on how this mirrors real world AI recommenders

This simulator builds a content-based music recommender that scores every song in an 18-song catalog against a user's taste profile, then returns the top-k matches ranked by score. It focuses on three core signals—genre, mood, and energy level—and adds an optional acoustic-preference bonus. The goal is to show how a handful of numerical weights can turn raw song attributes into a meaningful ranked list.

---

## How The System Works

Real streaming platforms like Spotify and YouTube use two main strategies to decide what to play next. **Collaborative filtering** looks across millions of users—if people with similar listening habits loved a song, the system predicts you will too. **Content-based filtering** ignores other users entirely and instead compares the attributes of songs you already like (genre, tempo, energy, mood) to every other song in the catalog, surfacing tracks that share those qualities. In practice, production systems blend both approaches. This simulation focuses exclusively on content-based filtering because it is simpler to reason about and does not require a large user database.

This version prioritizes **musical vibe** over popularity. A song scores well when its attributes are close to what the user asked for—matching genre earns the largest bonus, then mood, then proximity in energy level.

---

### Data Flow

```
INPUT                    PROCESS                         OUTPUT
─────────────────────    ─────────────────────────────   ────────────────────
UserProfile              For each of the 18 songs        Ranked list
  favorite_genre    ──►    score_song(user, song)   ──►  Top-K songs
  favorite_mood            └─ genre match check          with scores +
  target_energy            └─ mood match check           explanations
  likes_acoustic           └─ energy proximity
                           └─ acoustic bonus
                           Sort all scores ↓
```

---

### Song features

| Feature | Type | Role in scoring |
|---|---|---|
| `genre` | string | Primary signal — exact match awards +2.0 pts |
| `mood` | string | Emotional-context signal — exact match awards +1.0 pt |
| `energy` | float 0–1 | Proximity score — rewards closeness to target (up to +1.5 pts) |
| `valence` | float 0–1 | Positivity/happiness of the track; stored for future experiments |
| `danceability` | float 0–1 | Rhythmic drivability; useful for workout-profile experiments |
| `acousticness` | float 0–1 | Acoustic bonus (+1.0) when `likes_acoustic = True` and value > 0.6 |
| `tempo_bpm` | float | Beats per minute; stored for tempo-range experiments |

The catalog covers 10 genres (pop, lofi, rock, ambient, jazz, synthwave, indie pop, r&b, electronic, soul, classical, metal, country, hip-hop, reggae) and 11 moods (happy, chill, intense, relaxed, moody, focused, romantic, euphoric, nostalgic, melancholic, angry, peaceful, dreamy).

### UserProfile fields

| Field | Type | Meaning |
|---|---|---|
| `favorite_genre` | string | The genre the user listens to most |
| `favorite_mood` | string | The emotional mood they want right now |
| `target_energy` | float 0–1 | How energetic the music should feel |
| `likes_acoustic` | bool | Whether the user prefers acoustic over produced sound |

---

### Algorithm Recipe (Scoring Rule)

```
score(song) = genre_match  × 2.0      ← +2.0 if genres are equal, else 0
            + mood_match   × 1.0      ← +1.0 if moods are equal, else 0
            + (1 − |target_energy − song.energy|) × 1.5   ← energy proximity
            + acoustic_bonus × 1.0    ← only when likes_acoustic = True
                                         and song.acousticness > 0.6
```

**Why these weights?**
Genre is worth twice as much as mood because listeners tend to stay within a genre regardless of their current emotional state (you rarely listen to metal when you asked for jazz). Mood is a secondary filter within the genre space. Energy proximity is continuous so it naturally captures gradations—a song with 0.82 energy vs a target of 0.80 scores nearly the same as a perfect match, while a 0.20-energy song gets penalized heavily.

**Ranking Rule:** Every song in the catalog receives a score from the formula above. The recommender then sorts all scores in descending order and returns the top-k entries. The scoring rule answers "how good is *this* song?"—the ranking rule answers "which song is *best* relative to all others?"

---

### Mermaid Flowchart

```mermaid
flowchart TD
    A["User Preferences\n(genre · mood · energy · likes_acoustic)"] --> B["Load songs.csv\n18 songs"]
    B --> C{"For each song in catalog"}
    C --> D{"Genre match?"}
    D -- Yes --> E["+2.0 pts"]
    D -- No  --> F["+0.0 pts"]
    E --> G{"Mood match?"}
    F --> G
    G -- Yes --> H["+1.0 pt"]
    G -- No  --> I["+0.0 pts"]
    H --> J["Energy proximity\n1.5 × (1 − |target − song.energy|)"]
    I --> J
    J --> K{"likes_acoustic AND\nacousticness > 0.6?"}
    K -- Yes --> L["+1.0 pt"]
    K -- No  --> M["+0.0 pts"]
    L --> N["Song Score = sum of all points"]
    M --> N
    N --> C
    C --> O["All 18 songs scored"]
    O --> P["Sort by score descending"]
    P --> Q["Return Top-K Recommendations"]
```

---

### Expected Biases

- **Genre dominance**: Because a genre match is worth +2.0 and the max energy bonus is +1.5, any song in the right genre will almost always outscore a perfect-energy song in the wrong genre. A great lofi track could be buried below a mediocre pop track for a pop-preferring user.
- **Narrow mood vocabulary**: The system uses exact string matching for mood. A user who feels "happy" will not match songs tagged "euphoric" even though those moods are closely related.
- **Underrepresented genres**: The 18-song catalog has only 1 song per new genre (metal, reggae, country, etc.). Users who prefer those genres will receive fewer truly matching results and get energy-proximity runners-up instead.
- **Binary acoustic preference**: `likes_acoustic` is a yes/no flag. A user who "sort of" likes acoustic instruments has no way to express partial preference.

---

## Getting Started

### Setup

1. Create a virtual environment (optional but recommended):

   ```bash
   python -m venv .venv
   source .venv/bin/activate      # Mac or Linux
   .venv\Scripts\activate         # Windows

2. Install dependencies

```bash
pip install -r requirements.txt
```

3. Run the app:

```bash
python -m src.main
```

### Running Tests

Run the starter tests with:

```bash
pytest
```

You can add more tests in `tests/test_recommender.py`.

---

## CLI Output — Phase 4 Multi-Profile Evaluation

Running `python -m src.main` with four profiles + one experimental weight-shift run:

### Profile 1 — High-Energy Pop

```
============================================================
  PROFILE: High-Energy Pop
  genre=pop  mood=happy  energy=0.9
  [weights: genre=2.0 mood=1.0 energy=1.5]
============================================================

  Top recommendations:

    1. Sunrise City by Neon Echo
       Score : 4.38
       - genre match (+2.0)
       - mood match (+1.0)
       - energy proximity 0.92 (+1.38)

    2. Gym Hero by Max Pulse
       Score : 3.46
       - genre match (+2.0)
       - energy proximity 0.97 (+1.46)

    3. Rooftop Lights by Indigo Parade
       Score : 2.29
       - mood match (+1.0)
       - energy proximity 0.86 (+1.29)

    4. Storm Runner by Voltline
       Score : 1.48
       - energy proximity 0.99 (+1.48)

    5. Bass Drop Kingdom by XTRCT
       Score : 1.43
       - energy proximity 0.95 (+1.43)
```

**Observation:** Sunrise City is the clear #1 — genre, mood, and energy all match. Gym Hero is #2 even though its mood is "intense" not "happy", because the genre bonus (+2.0) outweighs the missing mood point. Storm Runner (rock) and Bass Drop Kingdom (electronic) sneak into 4th and 5th purely on energy proximity — the system has no candidates in the right genre+mood range left after the top 3.

---

### Profile 2 — Chill Lofi Study

```
============================================================
  PROFILE: Chill Lofi Study
  genre=lofi  mood=chill  energy=0.38
  [weights: genre=2.0 mood=1.0 energy=1.5]
============================================================

  Top recommendations:

    1. Library Rain by Paper Lanterns
       Score : 4.46
       - genre match (+2.0)
       - mood match (+1.0)
       - energy proximity 0.97 (+1.46)

    2. Midnight Coding by LoRoom
       Score : 4.44
       - genre match (+2.0)
       - mood match (+1.0)
       - energy proximity 0.96 (+1.44)

    3. Focus Flow by LoRoom
       Score : 3.47
       - genre match (+2.0)
       - energy proximity 0.98 (+1.47)

    4. Spacewalk Thoughts by Orbit Bloom
       Score : 2.35
       - mood match (+1.0)
       - energy proximity 0.90 (+1.35)

    5. Coffee Shop Stories by Slow Stereo
       Score : 1.48
       - energy proximity 0.99 (+1.48)
```

**Observation:** This profile works exactly as expected — the three lofi songs dominate the top 3. Coffee Shop Stories (jazz, relaxed, very low energy) edges into 5th place purely on energy closeness. Comparing to Profile 1: when the genre is well-represented in the catalog (3 lofi songs vs 2 pop songs), the top results feel more confident and the scores are tighter between #1 and #2.

---

### Profile 3 — Deep Intense Rock

```
============================================================
  PROFILE: Deep Intense Rock
  genre=rock  mood=intense  energy=0.93
  [weights: genre=2.0 mood=1.0 energy=1.5]
============================================================

  Top recommendations:

    1. Storm Runner by Voltline
       Score : 4.47
       - genre match (+2.0)
       - mood match (+1.0)
       - energy proximity 0.98 (+1.47)

    2. Gym Hero by Max Pulse
       Score : 2.50
       - mood match (+1.0)
       - energy proximity 1.00 (+1.5)

    3. Bass Drop Kingdom by XTRCT
       Score : 1.47
       - energy proximity 0.98 (+1.47)

    4. Iron Curtain by Scarred Earth
       Score : 1.44
       - energy proximity 0.96 (+1.44)

    5. Sunrise City by Neon Echo
       Score : 1.33
       - energy proximity 0.89 (+1.33)
```

**Observation:** Storm Runner is the only rock song, so it dominates at 4.47. The large score gap to #2 (2.50) reveals the **genre scarcity problem**: with only one rock song, the system fills the remaining slots with high-energy songs from unrelated genres. Gym Hero earns #2 by matching "intense" mood + perfect energy — it fits the emotional vibe even though it's pop, not rock.

---

### Profile 4 (Adversarial) — Peaceful Metal

```
============================================================
  PROFILE: Adversarial — Peaceful Metal (genre vs energy conflict)
  genre=metal  mood=peaceful  energy=0.2
  [weights: genre=2.0 mood=1.0 energy=1.5]
============================================================

  Top recommendations:

    1. Iron Curtain by Scarred Earth
       Score : 2.34
       - genre match (+2.0)
       - energy proximity 0.23 (+0.34)

    2. Porch Sunset by Dusty Miles
       Score : 2.14
       - mood match (+1.0)
       - energy proximity 0.76 (+1.14)

    3. Rain on Glass by Arcana Strings
       Score : 1.47
       - energy proximity 0.98 (+1.47)

    4. Spacewalk Thoughts by Orbit Bloom
       Score : 1.38
       - energy proximity 0.92 (+1.38)

    5. Library Rain by Paper Lanterns
       Score : 1.28
       - energy proximity 0.85 (+1.28)
```

**Observation — the key bias finding:** Iron Curtain (metal, angry, energy=0.97) is recommended to a user who asked for *peaceful, low-energy* music. The genre weight (+2.0) is so strong that even a terrible energy match (+0.34 out of a max +1.5) is enough to edge out Porch Sunset, which actually matches the user's mood and energy far better. This is the **genre dominance bias** in action.

---

### Experiment — Peaceful Metal with doubled energy weight

```
============================================================
  PROFILE: EXPERIMENT — Peaceful Metal  [genre=1.0  energy=3.0]
  genre=metal  mood=peaceful  energy=0.2
  [weights: genre=1.0 mood=1.0 energy=3.0]
============================================================

  Top recommendations:

    1. Porch Sunset by Dusty Miles
       Score : 3.28
       - mood match (+1.0)
       - energy proximity 0.76 (+2.28)

    2. Rain on Glass by Arcana Strings
       Score : 2.94
       - energy proximity 0.98 (+2.94)

    3. Spacewalk Thoughts by Orbit Bloom
       Score : 2.76
       - energy proximity 0.92 (+2.76)

    4. Library Rain by Paper Lanterns
       Score : 2.55
       - energy proximity 0.85 (+2.55)

    5. Coffee Shop Stories by Slow Stereo
       Score : 2.49
       - energy proximity 0.83 (+2.49)
```

**Experiment result:** Iron Curtain drops out of the top 5 entirely. Porch Sunset (country, peaceful, energy=0.44) becomes #1 because mood match + energy closeness now outweigh the single genre point. Rain on Glass (classical, melancholic, energy=0.22) rises to #2 — it has no matching genre or mood, but its energy is extremely close to the target (0.22 vs 0.20). The recommendations now *feel* more appropriate for a peaceful/low-energy user, even though the genre is completely wrong. This shows the trade-off: higher energy weight makes the system more acoustically accurate but genre-agnostic.

---

## Experiments You Tried

- **Weight shift (genre 2.0→1.0, energy 1.5→3.0):** The adversarial Peaceful Metal profile's top result changed from Iron Curtain (wrong energy, right genre) to Porch Sunset (right mood+energy, wrong genre). The system became more vibe-accurate but genre-blind.
- **Genre scarcity effect:** Profiles for underrepresented genres (rock, metal) showed large score gaps between #1 and #2. The single catalog entry for each genre dominates unconditionally.
- **Mood mismatch tolerance:** Gym Hero appears as a top-2 result for both "High-Energy Pop" (wrong mood: intense) and "Deep Intense Rock" (wrong genre: pop) — demonstrating that a single feature match plus energy proximity can beat no-match songs even across two different profiles.

---

## Limitations and Risks

- **Tiny catalog:** 18 songs is enough to demonstrate the logic but not enough to produce useful variety. Genres with only one song always return that song first regardless of how bad the other attributes match.
- **Genre dominance:** The genre weight (2.0) is large enough to push a wrong-energy song to the top of the list. The adversarial test proved this: an angry metal song at energy 0.97 ranked #1 for a user who asked for peaceful energy 0.2.
- **Synonym-blind mood matching:** "happy" and "euphoric" score identically to "happy" and "metal" — both return zero mood points. The system treats unrelated and closely related moods the same way.
- **No memory or feedback loop:** The system cannot learn from skips, replays, or likes. Every run starts fresh from the same static weights.
- **Filter bubble risk:** Nothing prevents five consecutive results from being the same genre. A user who casually typed "pop" as their preference can easily be locked into a pop-only list with no exposure to adjacent styles.

See [model_card.md](model_card.md) for a deeper analysis of each limitation.

---

## Reflection

→ Full analysis in [model_card.md](model_card.md)

Building this project made visible something that is easy to miss when you use Spotify or YouTube: recommendations are the output of arithmetic. A song rises to the top not because the system "understood" what you wanted, but because numbers lined up in a way that produced a high score. The Chill Lofi Study profile returned exactly the right songs — but that felt meaningful only because the weights happened to reflect real musical taste. Change two numbers and the whole system shifts. That is a lot of power to put in a weight table that no one usually sees.

The clearest lesson about bias came from the adversarial test. A metal song with energy 0.97 outranked a country song that genuinely matched the user's peaceful, low-energy request — purely because the genre label string matched. No real listener would accept that result, but the math produced it without hesitation. This is exactly how real systems can silently over-recommend certain genres or artists at scale, and why publishing a model card — documenting what the system does and does not do — is an important practice even for small projects.


