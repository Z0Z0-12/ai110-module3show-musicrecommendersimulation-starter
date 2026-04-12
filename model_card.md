# Model Card: Music Recommender Simulation

## 1. Model Name

**VibeFinder 1.0**

---

## 2. Goal / Task

VibeFinder 1.0 suggests up to 5 songs from an 18-song catalog based on a user's preferred genre, mood, and energy level. It predicts which songs will feel like the best match for a specific taste profile by computing a numerical score for each song and returning the highest-ranked ones.

**Intended use:** Classroom exploration of content-based recommendation logic. Students, instructors, or developers who want to understand how simple weighted scoring turns song attributes into ranked suggestions.

**Non-intended use:**
- Do not use this to make real playlist recommendations for real users. The catalog is fictional and contains only 18 songs.
- Do not use this as a substitute for accessibility or mental-health-aware music tools. The system has no concept of emotional sensitivity or trigger avoidance.
- Do not use this for commercial products without significantly expanding the dataset, adding collaborative signals, and auditing for demographic bias.
- Do not assume high scores mean "objectively good" songs. Scores are relative to one profile's weights — a score of 4.0 for one user means nothing to another user with different preferences.

---

## 3. How the Model Works

Every song in the catalog gets a numerical score when compared to the user's preferences. The score is built from three signals:

1. **Genre match** — the biggest reward. If the user wants pop and the song is pop, the song earns 2 bonus points. There is no partial credit; it's all or nothing.
2. **Mood match** — a smaller bonus of 1 point for an exact match (e.g., "happy" must equal "happy" — "euphoric" does not count).
3. **Energy closeness** — the only signal that is *gradual*. The closer a song's energy level is to what the user wants, the higher the reward, up to 1.5 points. A song with exactly the right energy scores the full 1.5; a song at the opposite extreme scores near 0.

After every song has been scored, they are sorted from highest to lowest and the top 5 are returned along with a short explanation of each signal that contributed.

---

## 4. Data

The catalog contains **18 songs** stored in `data/songs.csv`. Each song has 10 attributes: id, title, artist, genre, mood, energy (0–1), tempo_bpm, valence (0–1), danceability (0–1), and acousticness (0–1).

The 10 starter songs were provided with the project. I added 8 new songs (ids 11–18) to increase diversity:

| Added genre | Added mood |
|---|---|
| r&b | romantic |
| electronic | euphoric |
| soul | nostalgic |
| classical | melancholic |
| metal | angry |
| country | peaceful |
| hip-hop | dreamy |
| reggae | (relaxed — already existed) |

The catalog now covers **15 genres** and **13 distinct moods**. However, each new genre has only one representative song, which creates coverage gaps. The data is fictional and does not reflect real listening trends, streaming charts, or demographic preferences. Whose taste it reflects is effectively the taste of whoever designed the catalog — in this case, a general Western popular music listener.

---

## 5. Strengths

- **Well-represented genres work well.** For lofi (3 songs) and pop (2 songs), the top results consistently match all three signals and the score gap between #1 and a wrong-genre song is large and clear.
- **Transparent and explainable.** Every recommendation comes with a per-signal reason list (e.g., "genre match (+2.0)"), so the user can immediately see exactly why a song ranked where it did. No black box.
- **Continuous energy scoring avoids hard cutoffs.** A song with energy 0.79 vs a target of 0.80 is treated almost identically to a perfect match, which is more realistic than a binary "close enough / not close enough" check.

---

## 6. Limitations and Bias

**Genre dominance:** The genre weight (2.0) is so large relative to the energy proximity ceiling (1.5) that a matching genre overrides a nearly perfect energy match from a different genre. In the adversarial "Peaceful Metal" test, Iron Curtain (metal, energy=0.97) was ranked #1 for a user who asked for low-energy peaceful music (energy=0.2), simply because the genre matched. The system recommended a song with roughly 5× the desired energy level.

**Exact-string mood matching creates synonym blindness:** The system treats "happy" and "euphoric" as completely different moods even though a listener would likely enjoy both. Any song tagged with a mood that doesn't appear in the user's profile contributes zero mood points, regardless of emotional closeness.

**Genre scarcity amplifies the first problem:** Because genres like rock, metal, reggae, and classical have only one song each, the single genre-matching song wins unconditionally. A user who wants "chill reggae" gets Island Drift at the top — forever — regardless of whether its actual energy or mood match what they asked for.

**Binary acoustic preference:** The `likes_acoustic` field in `UserProfile` is a yes/no flag. A user who *somewhat* likes acoustic textures cannot express a partial preference, and the bonus (+1.0) either fires or doesn't.

**No diversity enforcement:** If all five top results share the same genre, the user gets no exposure to adjacent styles they might enjoy. A real recommender would inject occasional diversity to prevent the system from locking users into a narrow genre loop (a "filter bubble").

---

## 7. Evaluation

**Profiles tested:**

| Profile | Top result | Surprise? |
|---|---|---|
| High-Energy Pop (genre=pop, mood=happy, energy=0.9) | Sunrise City — correct | No. Both genre and mood matched perfectly. |
| Chill Lofi Study (genre=lofi, mood=chill, energy=0.38) | Library Rain — correct | Slight: Library Rain beat Midnight Coding by only 0.02 points (energy proximity tie-break). |
| Deep Intense Rock (genre=rock, mood=intense, energy=0.93) | Storm Runner — correct | The score gap was large (4.47 vs 2.50) because only one rock song exists. |
| Adversarial — Peaceful Metal (genre=metal, mood=peaceful, energy=0.2) | Iron Curtain — **wrong** | Yes. The genre match dominated even though the energy was 0.77 off target. |

**Key experiment — Peaceful Metal with genre=1.0, energy=3.0:**

After halving the genre weight and doubling the energy weight, Iron Curtain dropped out of the top 5 entirely and Porch Sunset (country, peaceful, energy=0.44) took the top spot. Rain on Glass (classical, energy=0.22) rose to #2 purely on energy closeness. The experiment confirmed that the genre weight is the primary driver of the "wrong" recommendation in the adversarial case, and that re-weighting can correct it — at the cost of making the system genre-agnostic.

**What surprised me most:** Gym Hero (pop, intense) appeared in the top 2 for both the High-Energy Pop *and* the Deep Intense Rock profiles. For pop users it wins on genre; for rock users it wins on mood+energy. One song satisfying two very different profiles is a sign that the catalog is too small and the scoring formula doesn't distinguish enough between users who actually have different tastes.

---

## 8. Future Work

- **Expand the catalog** to at least 5–10 songs per genre so that genre-matching produces meaningful variety rather than a single guaranteed winner.
- **Replace exact mood matching with a similarity table.** Map related moods (e.g., happy ↔ euphoric ↔ upbeat) to partial match scores (0.5–0.8) instead of binary 0 or 1.
- **Add valence to the scoring signal.** Valence (musical positivity) is already stored in the CSV. A user who prefers "happy" songs could be matched on valence range (e.g., valence > 0.7) as a soft signal even when the mood string doesn't match exactly.
- **Enforce diversity in results.** After ranking, apply a penalty for recommending more than 2 songs from the same genre in one top-k list, forcing the system to explore adjacent styles.
- **Add a tempo proximity signal** for profiles like "workout playlist" or "sleep music" where BPM matters as much as genre.

---

## 9. Personal Reflection

**What was the biggest learning moment?**

The biggest learning moment came from the adversarial test. I fully expected an "intense metal" song to score poorly for a user who asked for "peaceful, low-energy" music — but Iron Curtain ranked #1 anyway, because a genre match worth 2.0 points overpowered an energy penalty of only −1.16. I hadn't predicted this before running the test. It showed that weight values are not just implementation details; they are *policy decisions* about what matters most to the user, and bad policy choices produce wrong recommendations even when the formula is mathematically correct.

**How did AI tools help, and when did you need to double-check them?**

AI tools were genuinely useful for three things: generating diverse song data for the CSV, suggesting the initial weight values to try, and proposing the adversarial "conflicting preferences" profile I might not have thought of on my own. Where I had to double-check was anywhere the AI made a claim about what the *output would look like*. For example, when I asked whether doubling the energy weight would "fix" the adversarial case, the AI said yes — but I still had to run the code and manually verify that Iron Curtain actually left the top 5 and that the new #1 was genuinely more appropriate. Trusting an explanation without running the experiment would have been the wrong call.

**What surprised you about how simple algorithms can still "feel" like recommendations?**

I was surprised that just three numbers (2.0, 1.0, 1.5) could produce output that *feels* like real curation for well-matched profiles. When I ran the Chill Lofi Study profile, the top three results — Library Rain, Midnight Coding, Focus Flow — were exactly the songs I would have hand-picked for a study session. Nothing in the algorithm "knows" what studying feels like; it just matched numbers. That gap between what the algorithm actually does (arithmetic) and what it appears to do (understand musical vibes) is exactly why it's easy to over-trust these systems in real products.

**What would you try next if you extended this project?**

The most impactful next step would be replacing exact-string mood matching with a soft similarity table that gives partial credit for related moods (happy ↔ euphoric ↔ upbeat = 0.7; happy ↔ melancholic = 0.0). This single change would fix the "synonym blindness" problem without restructuring any other logic. After that, I'd add a diversity pass that prevents all five results from being the same genre — injecting one song from an adjacent style the user might not have considered. Longer term, I'd add a basic listening-history tracker so the system can learn which recommendations the user actually skipped, and lower those songs' effective weights in future runs.