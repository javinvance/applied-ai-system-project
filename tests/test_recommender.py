import os
import pytest
from src.recommender import Song, UserProfile, Recommender, score_song, load_songs, recommend_songs

CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "songs.csv")

def make_small_recommender() -> Recommender:
    songs = [
        Song(
            id=1,
            title="Test Pop Track",
            artist="Test Artist",
            genre="pop",
            mood="happy",
            energy=0.8,
            tempo_bpm=120,
            valence=0.9,
            danceability=0.8,
            acousticness=0.2,
        ),
        Song(
            id=2,
            title="Chill Lofi Loop",
            artist="Test Artist",
            genre="lofi",
            mood="chill",
            energy=0.4,
            tempo_bpm=80,
            valence=0.6,
            danceability=0.5,
            acousticness=0.9,
        ),
    ]
    return Recommender(songs)


def test_recommend_returns_songs_sorted_by_score():
    user = UserProfile(
        favorite_genre="pop",
        favorite_mood="happy",
        target_energy=0.8,
        likes_acoustic=False,
    )
    rec = make_small_recommender()
    results = rec.recommend(user, k=2)

    assert len(results) == 2
    # Starter expectation: the pop, happy, high energy song should score higher
    assert results[0].genre == "pop"
    assert results[0].mood == "happy"


def test_explain_recommendation_returns_non_empty_string():
    user = UserProfile(
        favorite_genre="pop",
        favorite_mood="happy",
        target_energy=0.8,
        likes_acoustic=False,
    )
    rec = make_small_recommender()
    song = rec.songs[0]

    explanation = rec.explain_recommendation(user, song)
    assert isinstance(explanation, str)
    assert explanation.strip() != ""


# --- New scoring tests ---

def test_acoustic_bonus_applied_when_likes_acoustic():
    """Acoustic bonus (+0.5) fires when user likes_acoustic and song acousticness >= 0.6."""
    user = {"favorite_genre": "jazz", "favorite_mood": "relaxed",
            "target_energy": 0.4, "likes_acoustic": True}
    song = {"id": 7, "genre": "jazz", "mood": "relaxed", "energy": 0.37,
            "acousticness": 0.89, "valence": 0.71, "danceability": 0.54, "tempo_bpm": 90}
    score, reasons = score_song(user, song)
    assert any("acoustic" in r.lower() for r in reasons)
    assert score > 4.0  # exceeds the old 4.0 max


def test_no_acoustic_bonus_when_likes_acoustic_false():
    """Electronic bonus fires instead of acoustic when user prefers non-acoustic."""
    user = {"favorite_genre": "edm", "favorite_mood": "energetic",
            "target_energy": 0.9, "likes_acoustic": False}
    song = {"id": 12, "genre": "edm", "mood": "energetic", "energy": 0.95,
            "acousticness": 0.02, "valence": 0.72, "danceability": 0.95, "tempo_bpm": 140}
    score, reasons = score_song(user, song)
    assert score >= 3.0
    assert not any("acoustic match" in r.lower() for r in reasons)


def test_recommend_songs_sorted_descending():
    """Top recommendation must always have the highest score."""
    user = {"favorite_genre": "pop", "favorite_mood": "happy",
            "target_energy": 0.8, "likes_acoustic": False}
    songs = load_songs(CSV_PATH)
    results = recommend_songs(user, songs, k=5)
    scores = [r[1] for r in results]
    assert scores == sorted(scores, reverse=True)


def test_recommend_songs_respects_k():
    """recommend_songs never returns more than k results."""
    user = {"favorite_genre": "pop", "favorite_mood": "happy",
            "target_energy": 0.8, "likes_acoustic": False}
    songs = load_songs(CSV_PATH)
    for k in (1, 3, 5, 10):
        results = recommend_songs(user, songs, k=k)
        assert len(results) <= k


def test_valence_bonus_for_happy_mood():
    """High-valence song earns a bonus when the user wants a happy mood."""
    user = {"favorite_genre": "pop", "favorite_mood": "happy",
            "target_energy": 0.8, "likes_acoustic": False}
    high_valence_song = {"id": 1, "genre": "pop", "mood": "happy", "energy": 0.82,
                         "acousticness": 0.18, "valence": 0.84, "danceability": 0.79, "tempo_bpm": 118}
    score, reasons = score_song(user, high_valence_song)
    assert any("valence" in r.lower() for r in reasons)
