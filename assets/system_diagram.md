# MoodMatch — System Architecture Diagram

```
╔══════════════════════════════════════════════════════════════════════╗
║                    MoodMatch — System Diagram                        ║
╚══════════════════════════════════════════════════════════════════════╝

  INPUT                  AI LAYER                          OUTPUT
  ─────                  ────────                          ──────

  ┌──────────┐
  │   User   │ "studying late at night,
  │  (Human) │  stressed, need calm focus"
  └────┬─────┘
       │ free-text vibe
       ▼
  ╔══════════════════════════════════╗
  ║        rag_retriever.py         ║
  ║   retrieve_context(query)       ║
  ║                                 ║
  ║  Scores knowledge cards by      ║  ◀── data/music_knowledge.json
  ║  keyword overlap with query.    ║      (17 genre + 13 mood cards)
  ║  Returns top-3 relevant cards   ║
  ║  as formatted context string.   ║
  ╚════════════════╤════════════════╝
                   │ RAG context (injected into system prompt)
                   ▼
  ╔══════════════════════════════════╗
  ║       claude_bridge.py          ║
  ║   parse_vibe_to_profile()       ║ ← Claude API (claude-opus-4-6)
  ║                                 ║
  ║  System prompt = RAG context    ║
  ║               + parsing rules   ║
  ║  Returns UserProfile JSON:      ║
  ║  {genre, mood, energy, acoustic}║
  ╚════════════════╤════════════════╝
                   │ UserProfile
                   │
  ┌────────────────┼──────────────────────────────────────────┐
  │                │   --agent mode (alternative path)        │
  │                │                                          │
  │      ╔═════════▼══════════════════╗                       │
  │      ║      vibe_agent.py         ║                       │
  │      ║  parse_vibe_agentic()      ║                       │
  │      ║                            ║                       │
  │      ║  Tool loop:                ║                       │
  │      ║  1. get_catalog_overview() ║ prints [Tool] steps   │
  │      ║  2. search_songs(...)      ║ to terminal           │
  │      ║  3. output final JSON      ║                       │
  │      ╚════════════════════════════╝                       │
  └───────────────────────────────────────────────────────────┘
                   │ UserProfile
                   ▼
  ╔══════════════════════════════════╗
  ║       recommender.py            ║
  ║   score_song() × 20 songs       ║  ◀── data/songs.csv
  ║   recommend_songs()             ║      (20 songs, 10 audio features)
  ║                                 ║
  ║  For each song:                 ║
  ║  • Genre match       +1.0       ║
  ║  • Mood match        +1.0       ║
  ║  • Energy proximity  +2.0       ║
  ║  • Acoustic bonus    +0.5       ║
  ║  • Valence proxy     +0.5       ║
  ║  ─────────────────────────      ║
  ║  Max score:          5.0        ║
  ╚════════════════╤════════════════╝
                   │ top-5 ranked (song, score, reasons)
                   ▼
  ╔══════════════════════════════════╗
  ║       claude_bridge.py          ║
  ║   generate_explanations()       ║ ← Claude API
  ║                                 ║
  ║  Returns one sentence per song  ║
  ║  Falls back to reason strings   ║
  ║  if API fails (graceful)        ║
  ╚════════════════╤════════════════╝
                   │ recommendations + explanations
                   ▼
          ┌────────────────────┐
          │    CLI Display     │
          │  #1 Focus Flow     │
          │  Score: 4.55 / 5.0 │
          │  Why: ...          │
          └─────────┬──────────┘
                    │
                    ▼
         ┌──────────────────────────────┐
         │        User (Human)          │
         │  Reviews results.            │
         │  Types refinement or accepts │
         └──────────────┬───────────────┘
                        │ "more acoustic" / "something different"
                        ▼
  ╔══════════════════════════════════╗
  ║       claude_bridge.py          ║
  ║   refine_profile()              ║ ← Claude API
  ║                                 ║
  ║  Input: current profile +       ║
  ║         songs shown +           ║
  ║         follow-up text          ║
  ║  Output: {updates, ack}         ║
  ╚════════════════╤════════════════╝
                   │ updated UserProfile
                   └──────────────────────────▶ (loops back to scorer)

══════════════════════════════════════════════════════════════════════

  WHERE TESTING HAPPENS
  ─────────────────────

  ┌─────────────────────────────────────────────────────────────┐
  │  tests/test_recommender.py   (7 tests, no API key needed)   │
  │  • score_song() with all bonus components                   │
  │  • Recommender OOP class (recommend + explain)              │
  │  • recommend_songs() sorted order and k-limit               │
  │  • Valence proxy bonus for happy mood                       │
  └─────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────┐
  │  tests/test_chat_session.py  (9 tests, Claude API mocked)   │
  │  • apply_updates(): energy clamping, field deltas, noop     │
  │  • process_turn() turn-0: parse_vibe_to_profile called      │
  │  • process_turn() turn-1+: refine_profile called            │
  │  • Profile updates correctly applied to session state       │
  └─────────────────────────────────────────────────────────────┘

  Human checkpoints:
  • Reviews recommendations each turn — decides to refine or accept
  • Provides free-text input that drives the next scoring cycle
```
