"""
RAG retriever for MoodMatch.

Loads music_knowledge.json and retrieves the most relevant genre and mood
cards for a given user query using keyword overlap scoring. Retrieved context
is injected into Claude prompts to improve parsing accuracy for niche,
ambiguous, or cross-genre vibe descriptions.

No embeddings required — keyword overlap is sufficient for a 30-card knowledge
base and keeps the system self-contained without external vector stores.
"""

import json
import os
import re
from typing import List, Tuple

_KB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "music_knowledge.json")

_kb: dict = {}


def _load() -> dict:
    global _kb
    if not _kb:
        with open(_KB_PATH, encoding="utf-8") as f:
            _kb = json.load(f)
    return _kb


def _tokenize(text: str) -> set:
    """Lowercase, strip punctuation, split on whitespace."""
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return set(text.split())


def _score_card(query_tokens: set, card: dict, name: str) -> float:
    """
    Score a knowledge card against query tokens.

    Scoring rules:
    - 3 pts per keyword match (keywords list is curated for user-facing language)
    - 2 pts if the card name itself appears in the query
    - 1 pt per word in the description that appears in the query
    """
    score = 0.0
    keywords = {k.lower() for k in card.get("keywords", [])}
    score += 3 * len(query_tokens & keywords)
    if name.lower() in query_tokens or name.lower().replace(" ", "") in " ".join(query_tokens):
        score += 2
    description_tokens = _tokenize(card.get("description", ""))
    score += len(query_tokens & description_tokens)
    return score


def retrieve_context(user_query: str, top_k: int = 3) -> str:
    """
    Retrieve the top_k most relevant genre and mood cards for the query.

    Returns a formatted string ready to inject into a Claude system prompt.
    Returns an empty string if no cards score above zero (avoids noise).
    """
    kb = _load()
    tokens = _tokenize(user_query)
    if not tokens:
        return ""

    scored: List[Tuple[float, str, str, dict]] = []

    for name, card in kb.get("genres", {}).items():
        s = _score_card(tokens, card, name)
        if s > 0:
            scored.append((s, "genre", name, card))

    for name, card in kb.get("moods", {}).items():
        s = _score_card(tokens, card, name)
        if s > 0:
            scored.append((s, "mood", name, card))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:top_k]

    if not top:
        return ""

    lines = ["RELEVANT MUSIC KNOWLEDGE (use this to interpret the user's vibe):"]
    for _, kind, name, card in top:
        energy = card.get("typical_energy", [])
        valence = card.get("typical_valence", [])
        related = card.get("related_genres", card.get("often_paired_genres", []))
        catalog = card.get("catalog_songs", [])

        lines.append(f"\n[{kind.upper()}: {name}]")
        lines.append(f"  {card['description']}")
        if energy:
            lines.append(f"  Typical energy: {energy[0]}–{energy[1]}")
        if valence:
            lines.append(f"  Typical valence: {valence[0]}–{valence[1]}")
        if related:
            lines.append(f"  Related: {', '.join(related)}")
        if catalog:
            lines.append(f"  In catalog: {', '.join(catalog)}")

    return "\n".join(lines)


def retrieve_for_genre(genre_name: str) -> str:
    """Return the full knowledge card for a specific genre, or empty string."""
    kb = _load()
    card = kb.get("genres", {}).get(genre_name.lower())
    if not card:
        return ""
    energy = card.get("typical_energy", [])
    return (
        f"[GENRE: {genre_name}] {card['description']} "
        f"Typical energy: {energy[0]}–{energy[1]}. "
        f"In catalog: {', '.join(card.get('catalog_songs', []))}."
    )


def list_all_genres() -> List[str]:
    """Return all genre names in the knowledge base."""
    return list(_load().get("genres", {}).keys())


def list_all_moods() -> List[str]:
    """Return all mood names in the knowledge base."""
    return list(_load().get("moods", {}).keys())
