"""
Claude API integration for MoodMatch.

Three functions:
  parse_vibe_to_profile  — free-text vibe → structured UserProfile (RAG-enhanced)
  refine_profile         — follow-up message → preference delta + ack string
  generate_explanations  — ranked songs → one natural-language sentence each

RAG enhancement: parse_vibe_to_profile retrieves relevant genre/mood knowledge
cards from music_knowledge.json and injects them into the Claude prompt before
parsing. This measurably improves accuracy for niche, ambiguous, or cross-genre
vibe descriptions (e.g. "something like post-rock shoegaze" or "meditative but
with a pulse") where Claude's generic training data may produce poor mappings.
"""

import json
import os
import sys
from dataclasses import asdict
from typing import Dict, List, Optional, Tuple

import anthropic

from .recommender import UserProfile
from .rag_retriever import retrieve_context

_KEY = os.environ.get("ANTHROPIC_API_KEY")
if not _KEY:
    print(
        "\nError: ANTHROPIC_API_KEY is not set.\n"
        "Run:  export ANTHROPIC_API_KEY=<your-key>\n"
        "Then retry.\n"
    )
    sys.exit(1)

_client = anthropic.Anthropic(api_key=_KEY)
_MODEL = "claude-opus-4-6"

_VALID_GENRES = {
    "pop", "lofi", "rock", "jazz", "edm", "ambient", "synthwave",
    "indie pop", "soul", "hip-hop", "r&b", "classical", "folk",
    "reggae", "metal", "blues", "country",
}
_VALID_MOODS = {
    "happy", "chill", "intense", "relaxed", "focused", "moody",
    "energetic", "romantic", "peaceful", "melancholy", "nostalgic",
    "angry", "sad",
}

_PARSE_SYSTEM = """You are a music taste interpreter. The user describes what \
they want to listen to right now — their mood, activity, energy level, or vibe \
— in plain English. Map that description onto a structured music profile.

Respond with ONLY valid JSON. No prose, no markdown fences.

Required fields:
{
  "favorite_genre":  string,   // one of: pop, lofi, rock, jazz, edm, ambient,
                               //   synthwave, indie pop, soul, hip-hop, r&b,
                               //   classical, folk, reggae, metal, blues, country
  "favorite_mood":   string,   // one of: happy, chill, intense, relaxed,
                               //   focused, moody, energetic, romantic,
                               //   peaceful, melancholy, nostalgic, angry, sad
  "target_energy":   float,    // 0.0 (extremely calm) to 1.0 (maximum energy)
                               //   0.25=quiet/sleepy  0.4=calm study  0.6=upbeat
                               //   0.75=running       0.9=workout     0.95=rave
  "likes_acoustic":  boolean   // true if description suggests acoustic/organic/
                               //   unplugged. false for electronic/produced/beat-heavy
}

Examples:
- "studying late, stressed, need calm focus"
  -> {"favorite_genre":"lofi","favorite_mood":"focused","target_energy":0.38,"likes_acoustic":false}
- "dance party, give me energy"
  -> {"favorite_genre":"edm","favorite_mood":"energetic","target_energy":0.92,"likes_acoustic":false}
- "Sunday morning coffee, very chill"
  -> {"favorite_genre":"jazz","favorite_mood":"relaxed","target_energy":0.35,"likes_acoustic":true}
- "I'm sad and want to wallow"
  -> {"favorite_genre":"blues","favorite_mood":"sad","target_energy":0.3,"likes_acoustic":true}"""

_REFINE_SYSTEM_TEMPLATE = """You are managing a music preference profile that drives song recommendations.
The user just saw recommendations and wants to refine them.

Current profile:
{profile_json}

Songs shown to the user:
{songs_json}

User follow-up: "{followup}"

Respond with ONLY valid JSON:
{{
  "updates": {{
    // Include ONLY fields that should change. Omit unchanged fields.
    // Valid keys: favorite_genre, favorite_mood, target_energy, likes_acoustic
  }},
  "ack": "one-sentence acknowledgement shown to the user"
}}

Refinement rules:
- "more acoustic" / "something acoustic" -> set likes_acoustic=true
- "less acoustic" / "more electronic" -> set likes_acoustic=false
- "more energetic" / "upbeat" / "faster" -> increase target_energy by 0.15 (max 1.0)
- "calmer" / "more chill" / "quieter" / "slower" -> decrease target_energy by 0.15 (min 0.0)
- "happier" / "more positive" -> set favorite_mood to "happy" or "energetic"
- "sadder" / "more melancholy" -> set favorite_mood to "sad" or "melancholy"
- "I liked #N" or "more like #N" -> return empty updates, ack with "Noted — keeping a similar direction."
- "something different" / "switch it up" -> change favorite_genre to an adjacent genre
- If unrelated to music, return empty updates and ack redirecting the user to music preferences.
- Never return updates for fields the user did not mention."""

_EXPLAIN_SYSTEM_TEMPLATE = """Write one short, friendly explanation sentence per song for a music recommendation.

User profile: {profile_summary}

For each song write exactly ONE sentence (15 words or fewer). Be specific: mention \
the matching genre, mood, energy, acousticness, or tempo where relevant to this user's \
preferences. Do not invent facts not present in the song data.

Songs (JSON array):
{songs_json}

Respond with ONLY a JSON array of strings, one per song, in the same order.
Example: ["Perfect lofi chill vibe at 0.42 energy.", "Acoustic jazz matches your relaxed mood."]"""


def _call(system: str, user_content: str, max_tokens: int = 512) -> str:
    """Make a single non-streaming Claude call and return the text content."""
    response = _client.messages.create(
        model=_MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user_content}],
    )
    return response.content[0].text.strip()


def _parse_json(text: str) -> dict:
    """Strip optional markdown fences then parse JSON."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
    return json.loads(text)


def parse_vibe_to_profile(user_text: str, use_rag: bool = True) -> UserProfile:
    """Convert a free-text vibe description into a UserProfile.

    RAG enhancement: when use_rag=True (default), retrieves the most relevant
    genre and mood knowledge cards from music_knowledge.json and prepends them
    to the system prompt. This grounds Claude's interpretation in the actual
    catalog vocabulary rather than relying solely on training-data associations,
    improving accuracy for niche or cross-genre descriptions.

    Retries once with a stricter prompt if Claude returns invalid JSON.
    """
    system = _PARSE_SYSTEM
    if use_rag:
        context = retrieve_context(user_text, top_k=3)
        if context:
            system = context + "\n\n" + _PARSE_SYSTEM

    raw = _call(system, user_text, max_tokens=256)
    try:
        data = _parse_json(raw)
    except (json.JSONDecodeError, ValueError):
        retry_raw = _call(
            _PARSE_SYSTEM,
            user_text + "\n\nIMPORTANT: Reply with ONLY the JSON object. No other text.",
            max_tokens=256,
        )
        data = _parse_json(retry_raw)

    # Coerce and validate fields
    genre = str(data.get("favorite_genre", "pop")).lower()
    mood = str(data.get("favorite_mood", "chill")).lower()
    energy = max(0.0, min(1.0, float(data.get("target_energy", 0.5))))
    acoustic = bool(data.get("likes_acoustic", False))

    if genre not in _VALID_GENRES:
        genre = "pop"
    if mood not in _VALID_MOODS:
        mood = "chill"

    return UserProfile(
        favorite_genre=genre,
        favorite_mood=mood,
        target_energy=energy,
        likes_acoustic=acoustic,
    )


def refine_profile(
    current_profile: UserProfile,
    songs_shown: List[Dict],
    user_followup: str,
) -> dict:
    """Interpret a follow-up message and return preference updates + ack string.

    Returns: {"updates": {partial UserProfile fields}, "ack": str}
    """
    profile_json = json.dumps(asdict(current_profile), indent=2)
    songs_brief = [
        {"title": s.get("title", ""), "artist": s.get("artist", ""),
         "genre": s.get("genre", ""), "mood": s.get("mood", "")}
        for s in songs_shown
    ]
    songs_json = json.dumps(songs_brief, indent=2)

    system = _REFINE_SYSTEM_TEMPLATE.format(
        profile_json=profile_json,
        songs_json=songs_json,
        followup=user_followup,
    )

    raw = _call(system, user_followup, max_tokens=512)
    try:
        result = _parse_json(raw)
    except (json.JSONDecodeError, ValueError):
        return {"updates": {}, "ack": "I had trouble understanding that. Try 'more acoustic', 'more energetic', or 'something different'."}

    if "updates" not in result:
        result["updates"] = {}
    if "ack" not in result:
        result["ack"] = "Got it."
    return result


def generate_explanations(
    user: UserProfile,
    ranked_songs: List[Tuple],
) -> List[str]:
    """Return a one-sentence explanation for each ranked song.

    Falls back silently to the scoring reason strings on any error.
    """
    fallback = [r[2] if len(r) > 2 else "" for r in ranked_songs]
    try:
        profile_summary = (
            f"{user.favorite_genre} | {user.favorite_mood} | "
            f"energy {user.target_energy:.2f} | "
            f"acoustic: {'yes' if user.likes_acoustic else 'no'}"
        )
        songs_data = [
            {
                "title": r[0].get("title", ""),
                "artist": r[0].get("artist", ""),
                "genre": r[0].get("genre", ""),
                "mood": r[0].get("mood", ""),
                "energy": r[0].get("energy", 0),
                "acousticness": r[0].get("acousticness", 0),
                "tempo_bpm": r[0].get("tempo_bpm", 0),
                "score": round(r[1], 2),
            }
            for r in ranked_songs
        ]
        system = _EXPLAIN_SYSTEM_TEMPLATE.format(
            profile_summary=profile_summary,
            songs_json=json.dumps(songs_data, indent=2),
        )
        raw = _call(system, "Generate the explanation array.", max_tokens=512)
        explanations = json.loads(raw) if raw.startswith("[") else _parse_json(raw)
        if isinstance(explanations, list) and len(explanations) == len(ranked_songs):
            return [str(e) for e in explanations]
    except Exception:
        pass
    return fallback
