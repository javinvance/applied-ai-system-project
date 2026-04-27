# Model Card: MoodMatch — Conversational AI Music Recommender

> Extended from TrackFit 1.0 (CodePath AI110 Module 3)

---

## 1. Model Name and Version

**MoodMatch 1.0**

A conversational AI music recommender that accepts free-text vibe descriptions, maps them to structured audio preferences using Claude, scores a 20-song catalog using a deterministic Python engine, and returns ranked recommendations with natural-language explanations. Users can refine results through follow-up conversation. Two stretch features extend the system: a RAG retrieval layer that grounds Claude's parsing in a curated music knowledge base, and a multi-step agentic workflow that uses Claude tool-calls to inspect the catalog before committing to a user profile.

**Base project:** TrackFit 1.0 — the Module 3 content-based recommender that scored songs against hardcoded user profile dicts using exact genre/mood matching and a linear energy proximity formula. TrackFit's deliberate limitations (unused features, exact-match brittleness, genre dominance) became the roadmap for MoodMatch's extensions.

---

## 2. What It Does

Given a plain-English vibe description like *"studying late at night, stressed, need something calm and focused"*, MoodMatch:

1. Retrieves relevant music knowledge context (RAG) from a curated knowledge base
2. Calls Claude to map the description to a `UserProfile` (genre, mood, target energy, acoustic preference)
3. Scores all 20 catalog songs using a deterministic Python function (max 5.0 points)
4. Calls Claude to write a one-sentence natural-language explanation for each top result
5. Displays ranked recommendations with explanations
6. Accepts follow-up refinements ("more acoustic", "something different") and updates the profile conversationally

Optional `--agent` mode replaces step 2 with a multi-step tool-call agent that inspects the catalog before finalizing the profile, printing each intermediate reasoning step.

---

## 3. Data Used

**Song catalog:** `data/songs.csv` — 20 songs with fields: `id`, `title`, `artist`, `genre`, `mood`, `energy` (0–1), `tempo_bpm`, `valence` (0–1), `danceability` (0–1), `acousticness` (0–1).

The catalog is unchanged from the Module 3 starter. It has 17 genres; 15 appear only once. Energy clusters between 0.3–0.5 with a gap at 0.5–0.7. All genres and artists are Western popular music.

**RAG knowledge base:** `data/music_knowledge.json` — 30 cards: 17 genre cards and 13 mood cards. Each card contains a description in user-facing language, typical energy and valence ranges, related genres, and catalog song examples. Written to match how users naturally describe music ("studying," "campfire," "angry workout").

**Claude model:** `claude-opus-4-6` via the Anthropic API. Used for NL parsing, conversational refinement, and explanation generation. Not fine-tuned — relies on prompting and RAG context.

---

## 4. Algorithm Summary

**Scoring function** (deterministic Python, no AI):

| Component | Max Points | Formula |
|---|---|---|
| Genre exact match | +1.0 | String equality |
| Mood exact match | +1.0 | String equality |
| Energy proximity | +2.0 | `2.0 × (1 − |target − actual|)` |
| Acoustic preference | +0.5 | Threshold on `acousticness` vs. `likes_acoustic` |
| Valence/danceability proxy | +0.5 | Mood-conditional threshold on `valence` + `danceability` |
| **Maximum total** | **5.0** | |

**Claude roles** (AI, non-deterministic):
- `parse_vibe_to_profile` — maps free text to `UserProfile` JSON, guided by RAG context
- `refine_profile` — interprets follow-up messages into preference deltas
- `generate_explanations` — writes one sentence per recommended song

**RAG retrieval** (keyword overlap scoring, no embeddings):
- Scores each knowledge card by keyword overlap with the user's query
- Returns top-3 relevant cards as formatted context injected into Claude's system prompt

**Agentic parser** (tool-call loop):
- Tool 1: `get_catalog_overview()` — all genres, moods, energy range
- Tool 2: `search_songs(genre, mood, min_energy, max_energy)` — filter and inspect
- Claude calls tools iteratively until confident, then outputs final `UserProfile` JSON

---

## 5. Observed Biases and Limitations

**Western catalog bias.** All 20 songs are Western popular music genres. Users whose musical identity falls outside this set — K-pop, Afrobeats, cumbia, Indian classical — receive poor matches with no indication the catalog itself is the problem. The RAG knowledge base has the same bias, since its genre cards were written around the 20-song catalog.

**Claude's training data shapes genre/mood mappings.** The NL parser maps vibes using associations embedded in Claude's training data. "Meditative" defaults to ambient or lofi because those genres appear frequently in English-language descriptions of meditative music. A user whose meditative music is throat singing or taiko receives a systematically biased mapping. The RAG layer partially mitigates this by providing catalog-grounded context, but does not eliminate it.

**Energy dominance in tie-breaking.** When no genre or mood match fires, energy proximity is the only remaining signal. Because only four songs in the catalog have energy above 0.9, those same four songs appear in nearly every high-energy recommendation when the user's genre is missing. The catalog is too thin to avoid this.

**`likes_acoustic` as a binary flattens a spectrum.** Acoustic preference is continuous, but the system models it as true/false. The scoring function gives a full +0.5 to songs with `acousticness >= 0.6` and nothing in between. A user who wants a "mostly acoustic with some production" has no way to express that.

**Scoring weights are hand-tuned.** The 1.0/1.0/2.0/0.5/0.5 weight distribution reflects one designer's judgment, not patterns derived from real user listening behavior. Users whose taste doesn't match that intuition will receive worse recommendations with no feedback mechanism to detect or correct the mismatch.

**Agentic parser can over-trust empty search results.** When `search_songs()` returns zero matches (e.g., genre=lofi, mood=intense), Claude must reason about the best fallback without being told what adjacent options exist. In edge cases it sometimes chooses a fallback that is too conservative (e.g., falling back to the only matching genre song regardless of energy mismatch) rather than broadening its search criteria.

---

## 6. Testing Results

**Test suite: 16 tests, all passing. No API key required.**

```
tests/test_recommender.py   7 tests   deterministic scoring, real CSV
tests/test_chat_session.py  9 tests   Claude API fully mocked
```

**What worked reliably:**
- Acoustic and valence bonuses fire precisely on expected songs and produce no false positives
- `apply_updates()` correctly clamps `target_energy` to [0.0, 1.0] at all boundary values
- `recommend_songs()` always returns results sorted descending by score
- The mock-based session tests caught a regression within one turn: when `refine_profile` returns empty updates, the profile stays unchanged

**What required defensive code not in the original design:**
- Claude's JSON responses occasionally include markdown fences (` ```json ... ``` `) even when the system prompt says not to. The `_parse_json()` helper strips these. A one-retry mechanism catches the rare case where the response is still malformed after stripping.
- The `Song` dataclass declares `id` as `int`, but `load_songs()` reads from CSV where all values are strings. `Recommender.recommend()` required an explicit `int(r[0]["id"])` cast to avoid a silent empty-results bug on OOP lookups.
- The batch-mode score display printed `/ 4.00` after the max changed to 5.0. Automated tests don't check formatted print output — only caught by manual regression run.

**Agentic workflow edge case observed:**
When the user description is contradictory ("intense lofi" — no lofi song is intense in the catalog), the agent correctly calls `search_songs(genre='lofi', mood='intense')` → 0 results, then must decide how to proceed. In testing, it generally made a reasonable fallback (dropping the mood constraint and matching on genre + energy), but the fallback strategy was not always consistent across runs — which is expected for a non-deterministic LLM but means the agentic path is inherently less reproducible than the single-call path.

---

## 7. Intended and Non-Intended Use

**Intended:** Educational demonstration of a hybrid AI system — deterministic scoring plus conversational NL interface. Shows where rule-based systems end and AI reasoning begins.

**Not intended for production use.** The 20-song catalog is too thin for real discovery. The weights were not learned from user behavior. There is no persistent memory, no feedback loop, and no diversity optimization. A real music recommender would blend collaborative filtering, user history, and real-time context on a catalog orders of magnitude larger.

---

## 8. AI Collaboration: Helpful and Flawed

### A genuinely helpful suggestion

During architecture planning, the AI proposed separating the three Anthropic API calls into distinct functions with **different failure strategies**: `parse_vibe_to_profile` retries on bad JSON; `generate_explanations` falls back silently to scoring reason strings; `refine_profile` returns an empty update dict rather than raising. I had been thinking of these as one "call Claude" step.

This separation made the system meaningfully more robust. When `generate_explanations` fails — whether from an API timeout, a malformed response, or a rate limit — the user still receives their ranked recommendations, just without the polished one-sentence explanations. The chat continues uninterrupted. If all three calls shared a single failure mode, any error would stop the conversation entirely. The architecture suggestion came from the planning phase and shaped every subsequent design decision.

### A flawed suggestion caught during testing

The initial `Recommender.recommend()` implementation used `s.__dict__` to convert `Song` dataclass instances to dicts before calling `score_song()`. This looked correct and passed a code review pass. The bug: `Song.id` is declared as `int` in the dataclass, so `s.__dict__` produces `{"id": 1, ...}`. But `load_songs()` reads from CSV — where all values are strings — so songs stored as dicts elsewhere in the system have `{"id": "1", ...}`. The lookup at the end of `recommend()` — `song_map[r[0]["id"]]` — silently missed every song because `1 != "1"` as a dict key.

The function returned an empty list with no error or warning. The fix was a one-character change (`int(r[0]["id"])`), but finding it required running the OOP test, observing that results were empty instead of ranked, and tracing through the data types manually. The AI suggestion was internally consistent but did not account for the type contract mismatch between two code paths it had not seen together. This is a recurring pattern: AI-generated code that looks correct in isolation can hide bugs that only surface when integrated with adjacent code.

---

## 9. Ideas for Improvement

**Real listening history.** The system cannot learn that this user reliably skips the first recommendation or that their idea of "chill" skews more acoustic than the genre average. A feedback loop — even a simple "liked / skipped" signal — would allow weights to personalize over time.

**Expand the catalog.** Most of the observed failures — high-energy songs dominating recommendations, single-song genre traps, the energy dead zone between 0.5–0.7 — are catalog problems, not algorithm problems. Integrating a real music API (Spotify, Last.fm) would expose whether the algorithm actually works at scale or just appears to work in a thin dataset.

**Semantic genre/mood matching.** Two adjacent genres ("indie pop" and "pop") share zero points under exact matching. A genre similarity lookup table, or embedding-based matching for a larger catalog, would make the system far more useful for listeners whose taste spans category boundaries.

**Diversity optimization.** The system always returns the five highest-scoring songs even if they are all from the same artist or have nearly identical audio features. Adding a diversity penalty that reduces score for songs too similar to ones already selected would produce more varied and interesting playlists.

**Global music representation.** The catalog, the knowledge base, and Claude's training data all skew heavily toward Western popular music. Expanding the genre cards and catalog to include non-Western traditions would meaningfully reduce geographic and cultural bias.

---

## 10. Personal Reflection

**What this project taught about AI and problem-solving**

The most important thing I learned was where to draw the boundary between AI and deterministic code. The first instinct is to push as much as possible onto the model — let Claude rank the songs, let Claude decide what the user wants, let Claude do everything. But that makes the system untestable and unpredictable. The scoring engine runs in Python because it needs to be auditable: you should be able to read exactly why a song received its score. Claude handles the parts that are genuinely hard to encode as rules: understanding "I want something for my cat napping next to me" or "post-breakup drive with the windows down."

Getting that boundary right — Claude for language, Python for math — is what made the system both flexible and reliable. It is also what made it testable: the 9 session tests run completely offline by mocking Claude's responses, while the 7 scoring tests hit the real CSV. The cleaner the interface between AI and deterministic code, the more confidence you can have in the whole system.

**What surprised me about conversational UX**

Running the system end-to-end surfaced something that doesn't appear in any test suite: users want to feel heard, not just correctly served. The `ack` string that Claude returns in `refine_profile` — "Got it — going more acoustic" — matters as much as the updated profile. A system that silently changes its internal state and re-ranks without acknowledgment feels broken, even when the results improve. Designing for emotional legibility is a completely different problem than designing for recommendation accuracy, and it only becomes visible when you actually use the thing you built.

**The gap between "feels smart" and "is reasoning"**

The original TrackFit showed me this with simple arithmetic: for the easy profiles, three scoring rules felt like genuine understanding. MoodMatch extends that to Claude's responses: a parsed profile and a natural-language explanation can feel deeply personalized even when the underlying reasoning is a prompt template applied to a 20-row CSV. That gap — between *feeling* like intelligent understanding and *being* intelligent understanding — is worth thinking carefully about before deploying any AI system at scale.
