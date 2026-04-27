"""
Unit tests for the chat session layer.
All Anthropic API calls are mocked — no network required.
"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# Patch ANTHROPIC_API_KEY before claude_bridge is imported so it doesn't sys.exit
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-placeholder")

from src.recommender import UserProfile, load_songs, recommend_songs
from src.chat_session import ChatSession, apply_updates, process_turn

CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "songs.csv")


def make_profile(**overrides) -> UserProfile:
    defaults = dict(
        favorite_genre="lofi",
        favorite_mood="chill",
        target_energy=0.4,
        likes_acoustic=False,
    )
    return UserProfile(**{**defaults, **overrides})


def make_session(profile=None) -> ChatSession:
    songs = load_songs(CSV_PATH)
    recs = recommend_songs(profile.__dict__, songs, k=5) if profile else []
    return ChatSession(
        songs=songs,
        profile=profile,
        last_recommendations=recs,
        turn_count=0,
        history=[],
    )


# ---- apply_updates tests (no mocking needed) ----

def test_apply_updates_changes_energy():
    profile = make_profile(target_energy=0.4)
    updated = apply_updates(profile, {"target_energy": 0.55})
    assert updated.target_energy == 0.55
    assert updated.favorite_genre == "lofi"  # unchanged


def test_apply_updates_clamps_energy_high():
    profile = make_profile(target_energy=0.95)
    updated = apply_updates(profile, {"target_energy": 1.10})
    assert updated.target_energy == 1.0


def test_apply_updates_clamps_energy_low():
    profile = make_profile(target_energy=0.05)
    updated = apply_updates(profile, {"target_energy": -0.10})
    assert updated.target_energy == 0.0


def test_apply_updates_likes_acoustic():
    profile = make_profile(likes_acoustic=False)
    updated = apply_updates(profile, {"likes_acoustic": True})
    assert updated.likes_acoustic is True


def test_apply_updates_empty_dict_is_noop():
    profile = make_profile()
    updated = apply_updates(profile, {})
    assert updated == profile


# ---- process_turn tests (API mocked) ----

@patch("src.chat_session.claude_bridge.generate_explanations")
@patch("src.chat_session.claude_bridge.parse_vibe_to_profile")
def test_first_turn_calls_parse_vibe(mock_parse, mock_explain, capsys):
    mock_parse.return_value = make_profile()
    mock_explain.return_value = ["Great chill track."] * 5

    session = make_session(profile=None)
    process_turn(session, "I want something chill to study to")

    mock_parse.assert_called_once()
    assert session.profile is not None
    assert session.turn_count == 1
    assert len(session.last_recommendations) == 5


@patch("src.chat_session.claude_bridge.generate_explanations")
@patch("src.chat_session.claude_bridge.refine_profile")
def test_second_turn_calls_refine(mock_refine, mock_explain, capsys):
    mock_refine.return_value = {"updates": {"likes_acoustic": True}, "ack": "Going acoustic."}
    mock_explain.return_value = ["Nice acoustic pick."] * 5

    profile = make_profile()
    session = make_session(profile=profile)
    process_turn(session, "more acoustic please")

    mock_refine.assert_called_once()
    assert session.profile.likes_acoustic is True
    assert session.turn_count == 1


@patch("src.chat_session.claude_bridge.generate_explanations")
@patch("src.chat_session.claude_bridge.refine_profile")
def test_empty_updates_leaves_profile_unchanged(mock_refine, mock_explain, capsys):
    mock_refine.return_value = {"updates": {}, "ack": "Noted."}
    mock_explain.return_value = ["Same direction."] * 5

    original_profile = make_profile(target_energy=0.4)
    session = make_session(profile=original_profile)
    process_turn(session, "I liked #2")

    assert session.profile.target_energy == 0.4
    assert session.profile.favorite_genre == "lofi"


@patch("src.chat_session.claude_bridge.generate_explanations")
@patch("src.chat_session.claude_bridge.refine_profile")
def test_energy_increase_applied(mock_refine, mock_explain, capsys):
    mock_refine.return_value = {"updates": {"target_energy": 0.55}, "ack": "More energetic."}
    mock_explain.return_value = ["Higher energy pick."] * 5

    profile = make_profile(target_energy=0.4)
    session = make_session(profile=profile)
    process_turn(session, "more energetic")

    assert session.profile.target_energy == 0.55
