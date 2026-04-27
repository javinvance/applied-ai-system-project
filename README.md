# MoodMatch — Conversational AI Music Recommender

> Describe your current vibe in plain English. Get ranked song recommendations. Refine them through conversation.

---

## Demo Walkthrough

**[Watch the full demo on Loom](https://www.loom.com/share/REPLACE_WITH_YOUR_LOOM_ID)**

The walkthrough covers three end-to-end examples:
1. Cold start: "studying late at night, stressed, need something calm and focused"
2. Conversational refinement: "more acoustic please" → updated recommendations
3. Genre shift: "just finished studying, want to celebrate — upbeat and danceable"

![System Architecture](assets/system_diagram.md)

Screenshots from the CLI are in the [`/assets`](assets/) folder.

---

## Original Project

This project extends the **Music Recommender Simulation** from CodePath AI110 Module 3. The original system was a content-based recommender that scored a 20-song catalog against hardcoded user profile dictionaries, using exact string matching on genre and mood plus a linear energy proximity formula. It was built as an educational tool to demonstrate recommendation algorithm mechanics, where algorithmic bias emerges (genre dominance, exact-match brittleness), and why feature weighting matters — surfacing those limitations intentionally through 8 adversarial test profiles including impossible genre requests, conflicting mood/energy signals, and boundary energy values.

---

## Title and Summary

**MoodMatch** evolves that prototype into a full conversational AI system. Instead of filling out a structured dictionary, you describe what you want to hear right now in plain English:

```
You: studying late at night, kind of stressed, need something calm and focused
```

Claude interprets your intent, maps it to a structured music profile, scores all 20 catalog songs, and returns ranked recommendations with human-readable explanations. You can then refine iteratively through natural conversation:

```
You: more acoustic please
You: I liked #2 — give me more like that
You: make it a bit more energetic
```

**Why it matters:** Most music discovery tools require you to already know what you want — a genre, an artist, a playlist name. MoodMatch meets you where you are: a feeling, an activity, a vibe. It demonstrates how large language models can serve as a natural language interface layer on top of a deterministic scoring engine, combining the interpretability of rule-based systems with the flexibility of AI reasoning.

---

## Architecture Overview

```
╔══════════════════════════════════════════════════════════════╗
║                 MoodMatch System Architecture                ║
╚══════════════════════════════════════════════════════════════╝

  INPUT                  AI LAYER                   OUTPUT
  ─────                  ────────                   ──────

  ┌──────────┐
  │   User   │ free-text vibe description
  │  (Human) │ ──────────────────────────────────────────┐
  └──────────┘                                           ▼
                                          ╔══════════════════════╗
                                          ║   claude_bridge.py   ║
                                          ║  parse_vibe_to_      ║ ← Claude API
                                          ║  profile()           ║
                                          ╚══════════╤═══════════╝
                                                     │ UserProfile
                                          ╔══════════▼═══════════╗
  ┌───────────────┐                       ║   chat_session.py    ║
  │ data/songs.csv│ ──────────────────▶   ║   process_turn()     ║
  │  20 songs:    │   full catalog        ║                      ║
  │  genre, mood, │                       ║  Orchestrates all    ║
  │  energy,      │                       ║  steps each turn     ║
  │  valence,     │                       ╚══════════╤═══════════╝
  │  danceability,│                                  │ UserProfile + songs
  │  acousticness │                                  ▼
  └───────────────┘              ╔═════════════════════════════╗
                                 ║      recommender.py         ║
                                 ║   score_song() × 20 songs   ║
                                 ║                             ║
                                 ║  Genre match      +1.0      ║
                                 ║  Mood match       +1.0      ║
                                 ║  Energy proximity +2.0      ║
                                 ║  Acoustic bonus   +0.5      ║
                                 ║  Valence proxy    +0.5      ║
                                 ║  ─────────────────────      ║
                                 ║  Max score:       5.0       ║
                                 ╚═══════════╤═════════════════╝
                                             │ top-5 ranked songs
                                             ▼
                                 ╔═══════════════════════════╗
                                 ║    claude_bridge.py       ║
                                 ║  generate_explanations()  ║ ← Claude API
                                 ║                           ║
                                 ║  "Perfect lofi match at   ║
                                 ║   0.40 energy for your    ║
                                 ║   late-night focus."      ║
                                 ╚═══════════╤═══════════════╝
                                             │ ranked songs + natural
                                             │ language explanations
                                             ▼
                                     ┌──────────────┐
                                     │ CLI Display  │
                                     │ #1 Focus Flow│
                                     │ Score: 4.8   │
                                     │ Why: ...     │
                                     └──────┬───────┘
                                            │
                                            ▼
                           ┌────────────────────────────────┐
                           │         User (Human)           │
                           │  Reviews recommendations and   │
                           │  types a refinement or accepts │
                           └───────────────┬────────────────┘
                                           │ follow-up text
                                           ▼
                           ╔══════════════════════════════╗
                           ║     claude_bridge.py         ║
                           ║   refine_profile()           ║ ← Claude API
                           ║                              ║
                           ║  "more acoustic" →           ║
                           ║  {likes_acoustic: true}      ║
                           ║  ack: "Going more acoustic." ║
                           ╚══════════════╤═══════════════╝
                                          │ updated UserProfile
                                          └────────────────────▶ (loops back)

  ════════════════════════════════════════════════════════════
  WHERE TESTING HAPPENS
  ════════════════════════════════════════════════════════════

  ┌─────────────────────────────────────────────────────────┐
  │  tests/test_recommender.py   (hits real CSV, no mocks)  │
  │  • acoustic/valence/danceability bonus scoring          │
  │  • Recommender OOP class (recommend + explain stubs)    │
  │  • recommend_songs sorted order and k-limit             │
  └─────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────┐
  │  tests/test_chat_session.py  (Claude API fully mocked)  │
  │  • apply_updates: energy clamping, field deltas         │
  │  • process_turn turn-0: verify parse_vibe called        │
  │  • process_turn turn-1+: verify refine_profile called   │
  │  • Profile updates correctly applied to session state   │
  └─────────────────────────────────────────────────────────┘

  Human checkpoint: User reviews ranked results and decides
  whether they match the vibe — then refines or accepts.
```

**Three distinct Claude API calls, each with a different job:**

| Call | Purpose | Failure behavior |
|---|---|---|
| `parse_vibe_to_profile` | Maps free text to UserProfile JSON | Retries once; raises ValueError if still invalid |
| `generate_explanations` | Writes one sentence per song | Silent fallback to scoring reason strings |
| `refine_profile` | Interprets follow-up → preference delta | Returns empty update dict; shows redirect message |

---

## Setup Instructions

### Prerequisites

- Python 3.11+
- An [Anthropic API key](https://console.anthropic.com/)

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd ai110-module3show-musicrecommendersimulation-starter
```

### 2. Create a virtual environment (recommended)

```bash
python -m venv .venv

# Mac / Linux
source .venv/bin/activate

# Windows Command Prompt
.venv\Scripts\activate

# Windows PowerShell
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install anthropic pytest
```

### 4. Set your Anthropic API key

**Mac / Linux:**
```bash
export ANTHROPIC_API_KEY=your_key_here
```

**Windows Command Prompt:**
```cmd
set ANTHROPIC_API_KEY=your_key_here
```

**Windows PowerShell:**
```powershell
$env:ANTHROPIC_API_KEY = "your_key_here"
```

### 5. Run the chat (conversational mode)

```bash
python -m src.main --chat
```

### 6. Run the original batch mode (no API key needed)

```bash
python -m src.main
```

### 7. Run the full test suite (no API key needed)

```bash
python -m pytest tests/ -v
```

Expected output: **16 tests pass**, no network required.

---

## Sample Interactions

### Interaction 1 — Late-night study session

```
==================================================
  MoodMatch — AI Music Recommender
  Describe your vibe. Type 'quit' to exit.
==================================================

You: studying late at night, kind of stressed, need something calm and focused

  Interpreting your vibe...
  Profile: lofi | focused | energy 0.38 | acoustic: no

  #1  Library Rain by Paper Lanterns
       Score: 4.60 / 5.0
       Why:   Calm lofi at 0.35 energy perfectly matches your focused late-night study mood.

  #2  Focus Flow by LoRoom
       Score: 4.55 / 5.0
       Why:   Designed for concentration — lofi at 0.40 energy sits right at your target.

  #3  Midnight Coding by LoRoom
       Score: 4.51 / 5.0
       Why:   Late-night lofi chill at 0.42 energy with a warm, focused atmosphere.

  #4  Spacewalk Thoughts by Orbit Bloom
       Score: 2.60 / 5.0
       Why:   Drifting ambient at very low energy suits your inward, quiet mood.

  #5  Coffee Shop Stories by Slow Stereo
       Score: 1.91 / 5.0
       Why:   Relaxed jazz at 0.37 energy — gentle background sound for focused work.

Refine: 'more acoustic', 'more energetic', 'something different'
```

### Interaction 2 — Conversational refinement

*Continuing directly from Interaction 1:*

```
You: more acoustic please

  Profile: lofi | focused | energy 0.38 | acoustic: yes

  Got it — favoring acoustic, organic-sounding tracks.

  #1  Library Rain by Paper Lanterns
       Score: 5.10 / 5.0
       Why:   High acousticness (0.86) lofi perfectly matches your preference for organic sound.

  #2  Focus Flow by LoRoom
       Score: 4.80 / 5.0
       Why:   Warm acoustic lofi at 0.78 acousticness — unplugged feel for late-night focus.

  #3  Coffee Shop Stories by Slow Stereo
       Score: 2.66 / 5.0
       Why:   Acoustic jazz at 0.89 acousticness — intimate coffeehouse intimacy.

  #4  Campfire Lullaby by The Pine Set
       Score: 1.74 / 5.0
       Why:   Highly acoustic folk at 0.94 — peaceful and organic, if a bit too quiet.

  #5  Midnight Gospel by Blue Crane
       Score: 1.60 / 5.0
       Why:   Acoustic blues at 0.68 — warm and unhurried for quiet concentration.

Refine: 'more acoustic', 'more energetic', 'something different'
```

### Interaction 3 — Genre shift from study to celebration

```
You: just finished studying, want something to celebrate — upbeat and danceable

  Interpreting your vibe...
  Profile: pop | happy | energy 0.85 | acoustic: no

  #1  Gym Hero by Max Pulse
       Score: 4.94 / 5.0
       Why:   High-energy pop at 0.93 with strong danceability (0.88) — built for celebration.

  #2  Sunrise City by Neon Echo
       Score: 4.59 / 5.0
       Why:   Upbeat pop with high valence (0.84) and danceability — bright and energizing.

  #3  Bass Drop by Circuit Pulse
       Score: 3.65 / 5.0
       Why:   Energetic EDM at 0.95 — maximum energy if you want to go even harder.

  #4  Rooftop Lights by Indigo Parade
       Score: 3.51 / 5.0
       Why:   Indie pop with happy mood and strong danceability (0.82) at 0.76 energy.

  #5  Concrete Jungle by Hex Theory
       Score: 2.51 / 5.0
       Why:   Hip-hop at 0.78 energy with high danceability (0.85) — strong and rhythmic.

You: actually dial it back, r&b vibes would be perfect

  Profile: r&b | moody | energy 0.62 | acoustic: no

  Dialing back to something smooth and soulful.

  #1  Neon Shadows by Dusk & Ivory
       Score: 4.24 / 5.0
       Why:   R&B at 0.62 energy with a smooth, moody atmosphere — exactly on target.

  #2  Golden Hour by Velvet Soul
       Score: 2.43 / 5.0
       Why:   Soulful and romantic at 0.55 energy — warm and laid back.
```

---

## Design Decisions

### Why keep the scoring engine in plain Python?

The original project's scoring function is deterministic and interpretable — you can read exactly why a song received its score. Using Claude to do the ranking itself would make results unpredictable across sessions and untestable in a CI environment. The hybrid approach (Claude for language understanding, Python for ranking) gives you the best of both: natural language input with consistent, auditable output.

### Why three separate Claude calls instead of one big prompt?

Each call has a distinct job and a different failure strategy:

- **parse_vibe_to_profile** — must succeed to continue; retries once on bad JSON
- **generate_explanations** — nice to have; silently falls back to raw scoring reasons if it fails, so the chat continues uninterrupted
- **refine_profile** — must return a structured diff, not rewrite the whole profile

Collapsing these into a single prompt would couple their failure modes: one bad response would break everything. Separating them means the system degrades gracefully.

### Why not use embeddings or semantic similarity for genre/mood matching?

The catalog has 20 songs across 17 genres — most genres appear once. Adding semantic embeddings on a 20-item catalog would introduce significant complexity with minimal benefit: a vector-space search over 20 items doesn't outperform a scored sort. If the catalog grew to thousands of songs with real user listening history, embeddings and collaborative filtering would be the right next step.

### Trade-offs made

| Decision | Benefit | Cost |
|---|---|---|
| Claude for NL parsing | Handles any phrasing naturally | API latency and cost per turn |
| Deterministic scorer | Testable, predictable, fast | Cannot learn from user behavior over time |
| Three separate API calls | Graceful degradation | More total latency per turn than one call |
| CLI-only interface | Simple, portable, no frontend | Less polished UX than a web app |
| Session state in memory | Simple, no database needed | All history lost when you quit |
| 20-song catalog | Self-contained, no external APIs | Limited recommendation diversity |

---

## Testing Summary

**16 tests, all passing. No API key required to run the suite.**

```
tests/test_recommender.py    7 tests   real CSV, no mocks
tests/test_chat_session.py   9 tests   Claude API fully mocked
```

### What worked well

**Mocking the Claude API** with `unittest.mock.patch` made the session layer completely testable offline. Each test injects a controlled Claude response and asserts the downstream state change — no real API calls, no flakiness, instant execution.

**Separating the OOP class from the procedural functions** in `recommender.py` meant the original test stubs (`Recommender.recommend()`, `Recommender.explain_recommendation()`) could be wired up by simply delegating to the already-working procedural functions. The stubs became real in ~10 lines.

**Acoustic and valence bonus scoring** worked as expected on the first try — new scoring components fired correctly on matching songs and produced no false positives on non-matching ones.

### What was tricky

**JSON reliability from Claude:** `parse_vibe_to_profile` needed to handle Claude occasionally wrapping its response in markdown fences (` ```json ... ``` `). A `_parse_json` helper strips those before parsing, and a one-retry mechanism handles the rare case of a genuinely malformed response.

**Score display vs. max:** After extending the max score from 4.0 to 5.0, the batch-mode output still printed `/ 4.00`. Automated tests don't catch formatting bugs in print statements — this was only caught by running the program manually. A reminder that testing correctness is not the same as testing user-facing output.

**Song `id` type mismatch:** The CSV loader returns `id` as a string (all CSV values are strings by default), but the `Song` dataclass declares it as `int`. The `Recommender.recommend()` method needed an explicit `int()` cast when looking up songs by id after scoring. This silently returned empty results until caught by running the OOP test.

### What I learned about testing AI systems

Testing AI-integrated code requires drawing a clear boundary between what the AI does and what your code does. Everything inside that boundary — scoring logic, session state, energy clamping — can and should be tested deterministically. Everything outside (Claude's language reasoning) gets mocked. If that boundary is blurry, the system becomes hard to test, hard to trust, and hard to debug. The cleaner the interface between your code and the model, the more testable the whole system becomes.

---

## Reflection

The original Module 3 project taught scoring functions and algorithmic bias. This extension taught something different: **what it means to use AI as an interface layer rather than as the core logic.**

The hardest design question wasn't "how do I call the API" — it was "what should Claude actually be responsible for?" Getting that wrong in either direction has real costs. If Claude does too much (ranking, scoring), you lose transparency and the ability to test. If Claude does too little (just echoing back what the user typed), you haven't solved the real problem. The right boundary here — Claude interprets language, Python computes scores — made the system both flexible and reliable.

The conversational refinement loop also surfaced something interesting: users don't just want better recommendations, they want to feel heard. The `ack` string Claude returns ("Got it — going more acoustic") matters as much as the updated preference. A system that silently changes and re-ranks without acknowledgment feels broken, even when the results improve. Small UX details like that don't show up in a test suite — they only emerge when you run the thing and notice how it actually feels to use.

Building this end-to-end — from a two-function prototype to a tested, multi-module system with a conversational interface — made concrete what "applied AI" means: not replacing logic with a model, but using models to make logic accessible to anyone who can describe what they need.

---

## Responsible AI Reflection

### Limitations and Biases

**The catalog encodes one cultural perspective.** All 20 songs represent Western popular music genres — pop, rock, EDM, jazz, blues, country, folk. There is no representation of cumbia, K-pop, Afrobeats, classical Indian music, or dozens of other global traditions. A user whose entire musical world lives outside this list will always receive poor matches, with no indication that the catalog itself is the problem. The system treats this as a data gap, not a failure, which is itself a bias.

**Claude's genre and mood mappings reflect training data patterns.** When a user says "something meditative," Claude maps that to genres like "ambient" or "lofi" because those appear frequently in English-language discussions of meditative music. A user whose idea of meditative music is taiko drumming or throat singing will be silently misunderstood. The valid genre/mood lists I defined further enforce this — any Claude interpretation that falls outside them gets replaced by a default (`"pop"`, `"chill"`), erasing the user's actual intent.

**`likes_acoustic` is a binary that flattens a spectrum.** Acoustic preference is a sliding scale, but the system treats it as true/false. A user who wants "mostly acoustic with some production" has no way to express that, and the scoring function treats them identically to someone who wants a completely unplugged guitar recording.

**Scoring weights are hand-tuned, not learned.** The decision to weight energy proximity at +2.0 and genre match at +1.0 reflects one designer's intuition about what matters in a recommendation, not patterns derived from real user behavior. Those weights may be badly calibrated for users whose sense of "what fits" doesn't match that intuition — and there's no mechanism to detect or correct the mismatch.

**No memory means no personalization.** Every session starts from scratch. The system cannot learn that this user reliably skips the first recommendation, or that their idea of "chill" skews more acoustic than the genre average. A real recommender would use this feedback to narrow in on individual taste over time.

---

### Could This Be Misused?

MoodMatch itself is low-stakes — the worst outcome is a bad playlist. But the architecture it demonstrates has higher-stakes applications worth thinking about.

**Mood inference from language can be surveillance.** This system captures that a user is "stressed," "sad," or "studying late at night" as a byproduct of parsing their vibe. At scale, a conversational recommender logs emotional states across millions of sessions. That data could be used to target ads, flag users for wellness interventions without consent, or be sold to third parties. MoodMatch has no data retention at all (session state lives in memory and disappears on quit), which is the simplest form of privacy protection — collecting nothing.

**The NL parsing layer could be prompted to produce unexpected structured outputs.** The `parse_vibe_to_profile` system prompt asks Claude to return a fixed JSON schema. A user who sends adversarial input — extremely long strings, injected instructions, or attempts to override the system prompt — could potentially cause unexpected behavior. The current validation layer (clamping energy to [0,1], replacing unknown genres with `"pop"`) catches most malformed outputs, but a production system would need rate limiting, input length caps, and stricter output validation.

**Recommendation systems can reinforce filter bubbles at scale.** A system that always matches users to what they already like never introduces them to anything new. At 20 songs, this is harmless. At Spotify's scale, optimizing purely for preference matching has been shown to homogenize listening habits and reduce the commercial viability of niche artists. MoodMatch has no diversity mechanism; adding one would require explicitly penalizing recommendations that are too similar to each other.

---

### What Surprised Me About Reliability Testing

**Claude's JSON formatting was the first real reliability problem.** The system prompt explicitly says "respond with ONLY valid JSON, no markdown fences" — and Claude still wrapped its output in ` ```json ... ``` ` on roughly one in five calls during early testing. I assumed explicit instructions were sufficient. They weren't. The `_parse_json` helper that strips fences, and the retry mechanism, were not in the original plan — they were added after observing actual Claude behavior. This was an important lesson: model behavior under real prompts can diverge from what the prompt specifies, and defensive parsing is not optional.

**Unusual phrasings parsed more robustly than expected.** I tested inputs like "something for when my cat is napping next to me" and "post-breakup drive with the windows down." Claude consistently produced reasonable UserProfile mappings from both — the first mapped to `lofi / chill / energy 0.35 / acoustic: yes`, the second to `r&b / sad / energy 0.55 / acoustic: false`. The NL understanding was more flexible than the validation layer — Claude often inferred genres and moods not in my predefined lists, which then got silently replaced by defaults. The model's capability exceeded the system's ability to use it.

**A bug that passes all tests can still break the user experience.** The score display showing `/ 4.00` instead of `/ 5.00` after the max score increased passed every automated test because no test checked print output. It was only caught by running `python -m src.main` and reading the terminal. This is a specific instance of a general principle: tests verify that functions return correct values; they don't verify that the system tells the user the truth. Both matter.

---

### Collaboration With AI

This project was built in active collaboration with Claude — not just for code generation, but for architecture planning, system design, and writing this README.

**One instance where the AI gave a genuinely helpful suggestion:**

During the planning phase, Claude proposed separating the three Anthropic API calls (`parse_vibe_to_profile`, `generate_explanations`, `refine_profile`) into distinct functions with *different failure strategies* — the parse function retries on bad JSON, the explanation function falls back silently, and the refine function returns an empty update dict rather than crashing. I had been thinking of this as one "call Claude" step. The suggestion to give each call its own failure mode was the insight that made the system robust instead of brittle. If `generate_explanations` fails, the user still gets their recommendations — they just come with raw scoring reasons instead of polished sentences. That graceful degradation was Claude's idea and it stuck.

**One instance where the AI's suggestion was flawed:**

The initial implementation of `Recommender.recommend()` used `s.__dict__` to convert `Song` dataclass instances into dicts before passing them to `score_song()`. Claude generated this approach without flagging that `Song.id` is typed as `int` in the dataclass, but `load_songs()` reads from CSV and returns `id` as a string (CSV has no types — everything comes back as `str`). The `Recommender` class works on `Song` objects, so `song.__dict__` produced `{"id": 1, ...}`. The lookup at the end of the function — `song_map[r[0]["id"]]` — was then comparing `int` keys against `str` values, silently returning no match. The function returned an empty list with no error. Claude's suggestion was internally consistent but wrong in context because it didn't account for the type contract mismatch between the two code paths. The fix was a one-character change (`int(r[0]["id"])`), but finding it required running the OOP test, seeing an empty result, and tracing the data types manually. The lesson: AI-generated code that looks correct can hide type contract bugs that only surface at runtime.

---

## Stretch Features

### RAG Enhancement

**What it does:** Before calling Claude to parse a user's vibe, MoodMatch retrieves the most relevant genre and mood knowledge cards from `data/music_knowledge.json` and injects them into the system prompt.

**The knowledge base** contains 17 genre cards and 13 mood cards. Each card describes the genre/mood in user-facing language, lists its typical energy and valence ranges, names related genres, and links to actual catalog songs. Retrieval scores cards by keyword overlap with the user query — "studying late, stressed" retrieves the lofi and focused cards; "angry, heavy, aggressive" retrieves the metal and angry cards.

**Why this measurably improves output:** Without RAG, Claude maps ambiguous queries using general training-data associations that may not align with this catalog's vocabulary. With RAG, Claude sees exactly which genres and moods exist, what energy ranges they occupy, and which songs represent them — before it has to commit to a structured UserProfile. This prevents two failure modes:
1. Claude inventing genre names not in the catalog (e.g. returning `"shoegaze"` when only `"rock"` exists)
2. Claude mapping mood incorrectly — e.g. tagging "studying" as `"relaxed"` instead of `"focused"` because the lofi card's keywords explicitly list `"study"` → `"focused"`

**Files:**
- `data/music_knowledge.json` — 30 knowledge cards (17 genres + 13 moods)
- `src/rag_retriever.py` — `retrieve_context(query, top_k=3)` → formatted context string

**Usage:** RAG is on by default in `--chat` mode. To disable: `parse_vibe_to_profile(text, use_rag=False)`.

---

### Agentic Workflow Enhancement

**What it does:** The `--agent` flag replaces the single parse-vibe call with a multi-step Claude agent that uses real tool-calls to inspect the catalog before committing to a UserProfile. Every intermediate step is printed to the terminal.

**Tool-call loop:**
1. Claude receives the user's vibe description
2. Claude calls `get_catalog_overview()` → sees all 20 songs, every available genre and mood, the full energy range
3. Claude optionally calls `search_songs(genre, mood, min_energy, max_energy)` → sees which actual songs match candidate criteria
4. Claude outputs the final UserProfile JSON, grounded in what it confirmed exists

**Observable intermediate steps:**

```
You: sad but I still want high energy, conflicted

  [Agent] Starting multi-step vibe analysis...
  [Tool] get_catalog_overview()
    → 17 genres, 13 moods available
  [Tool] search_songs(mood='sad', min_energy=0.6)
    → 0 match(es): none
  [Tool] search_songs(mood='sad', min_energy=0.3)
    → 1 match(es): Midnight Gospel
  [Tool] search_songs(genre='blues', min_energy=0.5)
    → 0 match(es): none
  [Agent] Profile determined after 4 step(s).

  Profile: blues | sad | energy 0.55 | acoustic: yes
```

**Why this is better than the single-call approach for hard cases:** The one-shot parser must hallucinate what exists. The agent *verifies*. When a user says "I want intense lofi" — a contradiction, since no lofi song has mood=intense — the agent can discover this empirically by calling `search_songs(genre='lofi', mood='intense')` → 0 results, and then reason about the best fallback instead of blindly returning a profile that will produce poor recommendations.

**Files:**
- `src/vibe_agent.py` — `parse_vibe_agentic(user_text, songs, verbose=True) -> UserProfile`

**Usage:**

```bash
python -m src.main --agent
```

---

## Project Structure

```
├── data/
│   ├── songs.csv                   # 20-song catalog with audio features
│   └── music_knowledge.json        # RAG knowledge base: 17 genre + 13 mood cards
├── src/
│   ├── __init__.py
│   ├── main.py                     # CLI entry point (--chat / --batch / --agent)
│   ├── recommender.py              # Song/UserProfile dataclasses + scoring engine
│   ├── claude_bridge.py            # Anthropic API calls (RAG-enhanced)
│   ├── chat_session.py             # Conversation loop + session state
│   ├── rag_retriever.py            # Keyword retrieval from music_knowledge.json
│   ├── vibe_agent.py               # Multi-step tool-call agentic parser
│   └── design_scoring.py           # Original one-shot LLM scoring advisor (Module 3)
├── tests/
│   ├── test_recommender.py         # Scoring engine tests (no API key needed)
│   └── test_chat_session.py        # Chat layer tests (Claude API mocked)
├── model_card.md
└── README.md
```

---

*Built as part of CodePath AI110 — Module 5 Applied AI Systems.*
