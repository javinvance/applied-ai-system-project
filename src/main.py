"""
Command line runner for MoodMatch — AI Music Recommender.

Usage:
  python -m src.main           # batch mode: run all 8 test profiles
  python -m src.main --batch   # same as above
  python -m src.main --chat    # interactive conversational mode
"""

import argparse
import os
from .recommender import load_songs, recommend_songs

CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "songs.csv")


PROFILES = {
    "High-Energy Pop": {
        "favorite_genre": "pop",
        "favorite_mood": "energetic",
        "target_energy": 0.90,
    },
    "Chill Lofi": {
        "favorite_genre": "lofi",
        "favorite_mood": "chill",
        "target_energy": 0.40,
    },
    "Deep Intense Rock": {
        "favorite_genre": "rock",
        "favorite_mood": "intense",
        "target_energy": 0.92,
    },
    # --- Adversarial / edge-case profiles ---
    "Sad But Pumped": {
        "favorite_genre": "blues",
        "favorite_mood": "sad",
        "target_energy": 0.9,
    },
    "Opera Buff": {
        "favorite_genre": "opera",   # not in catalog
        "favorite_mood": "romantic",
        "target_energy": 0.55,
    },
    "Intense Lofi Coder": {
        "favorite_genre": "lofi",
        "favorite_mood": "intense",  # no lofi song has mood=intense
        "target_energy": 0.85,
    },
    "Genre Rules All": {
        "favorite_genre": "ambient",  # 1 song: Spacewalk Thoughts, energy 0.28
        "favorite_mood": "energetic", # 1 song: Bass Drop (edm), energy 0.95
        "target_energy": 0.95,
    },
    "Absolute Silence": {
        "favorite_genre": "classical",
        "favorite_mood": "melancholy",
        "target_energy": 0.0,         # minimum possible
    },
}


def print_recommendations(label: str, user_prefs: dict, songs: list) -> None:
    """Print the top 5 recommendations for a single user profile."""
    recommendations = recommend_songs(user_prefs, songs, k=5)

    print("\n" + "=" * 50)
    print(f"  {label}")
    print(f"  Genre: {user_prefs['favorite_genre']}  |  "
          f"Mood: {user_prefs['favorite_mood']}  |  "
          f"Energy: {user_prefs['target_energy']}")
    print("=" * 50)

    for rank, (song, score, explanation) in enumerate(recommendations, start=1):
        print(f"\n#{rank}  {song['title']} by {song['artist']}")
        print(f"    Score : {score:.2f} / 5.00")
        print(f"    Why   : {explanation}")


def run_batch(songs: list) -> None:
    """Run all 8 hardcoded test profiles and print results."""
    print(f"Loaded songs: {len(songs)}")
    for label, prefs in PROFILES.items():
        print_recommendations(label, prefs, songs)


def main() -> None:
    parser = argparse.ArgumentParser(description="MoodMatch — AI Music Recommender")
    parser.add_argument(
        "--chat",
        action="store_true",
        help="Start an interactive conversational chat session (requires ANTHROPIC_API_KEY)",
    )
    parser.add_argument(
        "--agent",
        action="store_true",
        help=(
            "Use the multi-step agentic vibe parser (implies --chat). "
            "Claude calls tools to inspect the catalog before committing to a profile. "
            "Intermediate reasoning steps are printed to the terminal."
        ),
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Run all hardcoded test profiles in batch mode (default behavior)",
    )
    args = parser.parse_args()

    songs = load_songs(CSV_PATH)

    if args.chat or args.agent:
        from .chat_session import run_chat
        run_chat(songs, use_agent=args.agent)
    else:
        run_batch(songs)


if __name__ == "__main__":
    main()
