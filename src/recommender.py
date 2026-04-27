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
        user_dict = {
            "favorite_genre": user.favorite_genre,
            "favorite_mood": user.favorite_mood,
            "target_energy": user.target_energy,
            "likes_acoustic": user.likes_acoustic,
        }
        results = recommend_songs(user_dict, [s.__dict__ for s in self.songs], k)
        song_map = {s.id: s for s in self.songs}
        return [song_map[int(r[0]["id"])] for r in results]

    def explain_recommendation(self, user: UserProfile, song: Song) -> str:
        """Return a human-readable string explaining why a song was recommended."""
        user_dict = {
            "favorite_genre": user.favorite_genre,
            "favorite_mood": user.favorite_mood,
            "target_energy": user.target_energy,
            "likes_acoustic": user.likes_acoustic,
        }
        _, reasons = score_song(user_dict, song.__dict__)
        return " | ".join(reasons) if reasons else "No strong match found."

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

_HAPPY_MOODS = {"happy", "romantic", "peaceful", "energetic"}
_SAD_MOODS = {"sad", "melancholy", "angry"}
_DANCE_MOODS = {"happy", "energetic"}


def score_song(user_prefs: Dict, song: Dict) -> Tuple[float, List[str]]:
    """Score one song against user preferences and return (total_score, reasons).

    Max score: 5.0
      - Genre exact match:   +1.0
      - Mood exact match:    +1.0
      - Energy proximity:    up to +2.0
      - Acoustic preference: up to +0.5
      - Valence/dance proxy: up to +0.5
    """
    score = 0.0
    reasons = []

    if song["genre"] == user_prefs.get("favorite_genre", ""):
        score += 1.0
        reasons.append(f"Genre match: {song['genre']} (+1.0)")

    if song["mood"] == user_prefs.get("favorite_mood", ""):
        score += 1.0
        reasons.append(f"Mood match: {song['mood']} (+1.0)")

    target_energy = user_prefs.get("target_energy", 0.5)
    energy_pts = round(max(0.0, 2.0 * (1.0 - abs(target_energy - song["energy"]))), 2)
    if energy_pts > 0:
        score += energy_pts
        reasons.append(f"Energy similarity: {energy_pts:.2f} (+{energy_pts:.2f})")

    # Acoustic preference bonus (uses the previously unused likes_acoustic + acousticness)
    likes_acoustic = user_prefs.get("likes_acoustic", False)
    acousticness = float(song.get("acousticness", 0.0))
    if likes_acoustic:
        if acousticness >= 0.6:
            score += 0.5
            reasons.append(f"Acoustic match: {acousticness:.2f} (+0.5)")
        elif acousticness >= 0.3:
            score += 0.25
            reasons.append(f"Somewhat acoustic: {acousticness:.2f} (+0.25)")
    elif not likes_acoustic and acousticness <= 0.25:
        score += 0.25
        reasons.append(f"Electronic/produced sound (+0.25)")

    # Valence and danceability as mood proxies (previously unused)
    mood = user_prefs.get("favorite_mood", "")
    valence = float(song.get("valence", 0.5))
    danceability = float(song.get("danceability", 0.5))
    if mood in _HAPPY_MOODS and valence >= 0.7:
        score += 0.25
        reasons.append(f"Upbeat valence: {valence:.2f} (+0.25)")
    elif mood in _SAD_MOODS and valence <= 0.4:
        score += 0.25
        reasons.append(f"Low valence fits mood: {valence:.2f} (+0.25)")
    if mood in _DANCE_MOODS and danceability >= 0.75:
        score += 0.25
        reasons.append(f"High danceability: {danceability:.2f} (+0.25)")

    return round(score, 2), reasons

def recommend_songs(user_prefs: Dict, songs: List[Dict], k: int = 5) -> List[Tuple[Dict, float, str]]:
    """Score every song in the catalog and return the top k sorted by score descending."""
    scored = []
    for song in songs:
        score, reasons = score_song(user_prefs, song)
        explanation = " | ".join(reasons) if reasons else "No strong match"
        scored.append((song, score, explanation))

    return sorted(scored, key=lambda x: x[1], reverse=True)[:k]
