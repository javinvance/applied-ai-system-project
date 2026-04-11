from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

@dataclass
class Song:
    """A single song and its audio attributes loaded from the CSV catalog."""
    id: int
    title: str
    artist: str
    genre: str
    mood: str
    energy: float
    tempo_bpm: float
    valence: float
    danceability: float
    acousticness: float

@dataclass
class UserProfile:
    """A user's music taste preferences used to score and rank songs."""
    favorite_genre: str
    favorite_mood: str
    target_energy: float
    likes_acoustic: bool

class Recommender:
    """OOP wrapper around the catalog that exposes recommend and explain methods."""

    def __init__(self, songs: List[Song]):
        self.songs = songs

    def recommend(self, user: UserProfile, k: int = 5) -> List[Song]:
        """Return the top k songs ranked by their score against the user profile."""
        return self.songs[:k]

    def explain_recommendation(self, user: UserProfile, song: Song) -> str:
        """Return a human-readable string explaining why a song was recommended."""
        return "Explanation placeholder"

def load_songs(csv_path: str) -> List[Dict]:
    """Read songs.csv and return a list of dicts with numeric fields cast to float."""
    import csv
    print(f"Loading songs from {csv_path}...")
    songs = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row["energy"] = float(row["energy"])
            row["tempo_bpm"] = float(row["tempo_bpm"])
            row["valence"] = float(row["valence"])
            row["danceability"] = float(row["danceability"])
            row["acousticness"] = float(row["acousticness"])
            songs.append(row)
    return songs

def score_song(user_prefs: Dict, song: Dict) -> Tuple[float, List[str]]:
    """Score one song against user preferences and return (total_score, reasons)."""
    score = 0.0
    reasons = []

    if song["genre"] == user_prefs.get("favorite_genre", ""):
        score += 2.0
        reasons.append(f"Genre match: {song['genre']} (+2.0)")

    if song["mood"] == user_prefs.get("favorite_mood", ""):
        score += 1.0
        reasons.append(f"Mood match: {song['mood']} (+1.0)")

    target_energy = user_prefs.get("target_energy", 0.5)
    energy_pts = round(max(0.0, 1.0 - abs(target_energy - song["energy"])), 2)
    if energy_pts > 0:
        score += energy_pts
        reasons.append(f"Energy similarity: {energy_pts:.2f} (+{energy_pts:.2f})")

    return score, reasons

def recommend_songs(user_prefs: Dict, songs: List[Dict], k: int = 5) -> List[Tuple[Dict, float, str]]:
    """Score every song in the catalog and return the top k sorted by score descending."""
    scored = []
    for song in songs:
        score, reasons = score_song(user_prefs, song)
        explanation = " | ".join(reasons) if reasons else "No strong match"
        scored.append((song, score, explanation))

    return sorted(scored, key=lambda x: x[1], reverse=True)[:k]
