"""
Command line runner for the Music Recommender Simulation.

This file helps you quickly run and test your recommender.

You will implement the functions in recommender.py:
- load_songs
- score_song
- recommend_songs
"""

import os
from .recommender import load_songs, recommend_songs

CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "songs.csv")


def main() -> None:
    songs = load_songs(CSV_PATH)
    print(f"Loaded songs: {len(songs)}")

    # Starter example profile
    user_prefs = {"favorite_genre": "pop", "favorite_mood": "happy", "target_energy": 0.8}

    recommendations = recommend_songs(user_prefs, songs, k=5)

    print("\n" + "=" * 50)
    print("  Top Recommendations")
    print("=" * 50)

    for rank, (song, score, explanation) in enumerate(recommendations, start=1):
        print(f"\n#{rank}  {song['title']} by {song['artist']}")
        print(f"    Score : {score:.2f} / 4.00")
        print(f"    Why   : {explanation}")


if __name__ == "__main__":
    main()
