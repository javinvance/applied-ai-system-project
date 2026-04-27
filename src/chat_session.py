"""
Conversational session layer for MoodMatch.

Public API:
  run_chat(songs, use_agent)    — start the interactive CLI chat loop
  process_turn(session, text)   — handle one user message (testable, no I/O side effects)
  apply_updates(profile, delta) — apply a partial preference update dict
"""

import dataclasses
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from . import claude_bridge
from .recommender import UserProfile, recommend_songs


@dataclass
class ChatSession:
    songs: List[Dict]
    profile: Optional[UserProfile]
    last_recommendations: List[Tuple]
    turn_count: int
    history: List[str]
    use_agent: bool = False


def apply_updates(profile: UserProfile, updates: dict) -> UserProfile:
    """Apply a partial update dict to a UserProfile, clamping target_energy to [0, 1]."""
    if not updates:
        return profile
    new = dataclasses.replace(profile, **updates)
    clamped_energy = max(0.0, min(1.0, new.target_energy))
    if clamped_energy != new.target_energy:
        new = dataclasses.replace(new, target_energy=round(clamped_energy, 4))
    return new


def process_turn(session: ChatSession, user_input: str) -> None:
    """Handle one conversation turn: parse or refine, score, explain, print."""
    if session.profile is None:
        if session.use_agent:
            # Agentic path: multi-step tool-call reasoning
            from .vibe_agent import parse_vibe_agentic
            session.profile = parse_vibe_agentic(user_input, session.songs, verbose=True)
        else:
            # Standard path: single RAG-enhanced Claude call
            print("\nInterpreting your vibe...")
            session.profile = claude_bridge.parse_vibe_to_profile(user_input)
        _print_profile(session.profile)
    else:
        result = claude_bridge.refine_profile(
            session.profile,
            [r[0] for r in session.last_recommendations],
            user_input,
        )
        if result.get("updates"):
            session.profile = apply_updates(session.profile, result["updates"])
            _print_profile(session.profile)
        print(f"\n  {result.get('ack', 'Got it.')}\n")

    session.last_recommendations = recommend_songs(
        session.profile.__dict__, session.songs, k=5
    )

    explanations = claude_bridge.generate_explanations(
        session.profile, session.last_recommendations
    )

    _print_recommendations(session.last_recommendations, explanations)
    session.turn_count += 1
    session.history.append(user_input)


def run_chat(songs: List[Dict], use_agent: bool = False) -> None:
    """Start the interactive conversational CLI loop."""
    print("\n" + "=" * 50)
    print("  MoodMatch — AI Music Recommender")
    if use_agent:
        print("  Mode: Agentic (multi-step reasoning)")
    print("  Describe your vibe. Type 'quit' to exit.")
    print("=" * 50)
    print("\nExamples: 'studying late, need calm focus'")
    print("          'I want something upbeat for a run'")
    print("          'Sunday morning coffee vibes'\n")

    session = ChatSession(
        songs=songs,
        profile=None,
        last_recommendations=[],
        turn_count=0,
        history=[],
        use_agent=use_agent,
    )

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue

        if user_input.lower() in ("quit", "exit", "q", "bye"):
            print("\nGoodbye! Happy listening.")
            break

        process_turn(session, user_input)

        if session.profile is not None:
            print("\nRefine: 'more acoustic', 'more energetic', 'something different'")
            print("Or describe a whole new vibe.\n")


def _print_profile(profile: UserProfile) -> None:
    acoustic_str = "yes" if profile.likes_acoustic else "no"
    print(
        f"  Profile: {profile.favorite_genre} | {profile.favorite_mood} | "
        f"energy {profile.target_energy:.2f} | acoustic: {acoustic_str}"
    )


def _print_recommendations(
    ranked: List[Tuple], explanations: List[str]
) -> None:
    print()
    for i, ((song, score, _reasons), explanation) in enumerate(
        zip(ranked, explanations), start=1
    ):
        print(f"  #{i}  {song['title']} by {song['artist']}")
        print(f"       Score: {score:.2f} / 5.0")
        print(f"       Why:   {explanation}")
    print()
