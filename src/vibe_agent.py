"""
Agentic vibe parser for MoodMatch.

Replaces the single parse_vibe_to_profile() call with a multi-step agent that
uses Claude tool-calls to actively inspect the catalog before committing to a
UserProfile. Intermediate steps are printed to the terminal so reasoning is
fully observable.

Tool loop:
  1. Claude receives the user's free-text vibe.
  2. Claude may call get_catalog_overview() to see available genres/moods/energy.
  3. Claude may call search_songs() to see which songs match candidate criteria.
  4. Claude outputs the final UserProfile JSON once it has enough context.

This grounded, multi-step approach handles edge cases that confuse the one-shot
parser: rare genre names, conflicting signals ("sad but high-energy"), or vibes
that span multiple genres ("acoustic but also kind of ambient").
"""

import json
from typing import Any, Dict, List, Optional

import anthropic

from .recommender import UserProfile

_client = anthropic.Anthropic()
_MODEL = "claude-opus-4-6"

_TOOLS = [
    {
        "name": "get_catalog_overview",
        "description": (
            "Returns a summary of the entire song catalog: all available genres, "
            "all available moods, and the energy range of the songs. Use this first "
            "to understand what options exist before searching."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "search_songs",
        "description": (
            "Search the catalog for songs matching specific criteria. Returns matching "
            "song titles with their key audio features. Use this to verify that your "
            "chosen genre/mood/energy combination actually has songs in the catalog."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "genre": {
                    "type": "string",
                    "description": "Filter by exact genre name (optional)",
                },
                "mood": {
                    "type": "string",
                    "description": "Filter by exact mood name (optional)",
                },
                "min_energy": {
                    "type": "number",
                    "description": "Minimum energy value 0.0–1.0 (optional)",
                },
                "max_energy": {
                    "type": "number",
                    "description": "Maximum energy value 0.0–1.0 (optional)",
                },
                "min_acousticness": {
                    "type": "number",
                    "description": "Minimum acousticness 0.0–1.0 for acoustic preference (optional)",
                },
            },
            "required": [],
        },
    },
]

_SYSTEM = """You are a music profile builder. The user will describe their current vibe,
mood, activity, or what they want to listen to. Your job is to determine the best
UserProfile to match their description using the song catalog tools available to you.

Follow this process:
1. Call get_catalog_overview() to understand what genres, moods, and energy ranges exist.
2. Optionally call search_songs() to verify there are actually songs matching your intended profile.
3. When confident, output ONLY a JSON object with these exact fields:

{
  "favorite_genre":  string,   // must be one of the genres in the catalog
  "favorite_mood":   string,   // must be one of the moods in the catalog
  "target_energy":   float,    // 0.0 (calm) to 1.0 (maximum). Match the user's vibe.
  "likes_acoustic":  boolean   // true if user description implies acoustic/organic sound
}

Rules:
- Always call get_catalog_overview() at least once before outputting the final JSON.
- If the user's preferred genre is not in the catalog, find the closest available genre.
- If the user's preferred mood is not in the catalog, find the closest available mood.
- Your final output must be ONLY the JSON object — no other text, no markdown fences.
"""


def _run_tool(name: str, tool_input: dict, songs: List[Dict]) -> str:
    """Execute a tool call locally and return the result as a string."""
    if name == "get_catalog_overview":
        genres = sorted({s["genre"] for s in songs})
        moods = sorted({s["mood"] for s in songs})
        energies = [float(s["energy"]) for s in songs]
        return json.dumps({
            "total_songs": len(songs),
            "available_genres": genres,
            "available_moods": moods,
            "energy_range": {"min": round(min(energies), 2), "max": round(max(energies), 2)},
            "note": "Use search_songs() to filter by specific criteria.",
        }, indent=2)

    if name == "search_songs":
        results = []
        for s in songs:
            genre_ok = not tool_input.get("genre") or s["genre"] == tool_input["genre"]
            mood_ok = not tool_input.get("mood") or s["mood"] == tool_input["mood"]
            min_e = tool_input.get("min_energy")
            max_e = tool_input.get("max_energy")
            energy_ok = (
                (min_e is None or float(s["energy"]) >= min_e)
                and (max_e is None or float(s["energy"]) <= max_e)
            )
            min_ac = tool_input.get("min_acousticness")
            acoustic_ok = min_ac is None or float(s["acousticness"]) >= min_ac

            if genre_ok and mood_ok and energy_ok and acoustic_ok:
                results.append({
                    "title": s["title"],
                    "artist": s["artist"],
                    "genre": s["genre"],
                    "mood": s["mood"],
                    "energy": float(s["energy"]),
                    "acousticness": float(s["acousticness"]),
                })

        if not results:
            return json.dumps({"matches": 0, "songs": [], "note": "No songs matched. Try broadening your criteria."})
        return json.dumps({"matches": len(results), "songs": results}, indent=2)

    return json.dumps({"error": f"Unknown tool: {name}"})


def parse_vibe_agentic(user_text: str, songs: List[Dict], verbose: bool = True) -> UserProfile:
    """
    Multi-step agentic vibe parser using Claude tool-calls.

    Claude inspects the catalog via tool calls before committing to a profile,
    making the reasoning grounded in what songs actually exist.

    When verbose=True, each agent step is printed to the terminal.
    """
    messages = [{"role": "user", "content": user_text}]

    if verbose:
        print("\n  [Agent] Starting multi-step vibe analysis...")

    for step in range(6):  # safety cap: max 6 agentic steps
        response = _client.messages.create(
            model=_MODEL,
            max_tokens=1024,
            system=_SYSTEM,
            tools=_TOOLS,
            messages=messages,
        )

        # Collect all content blocks from this response
        tool_uses = [b for b in response.content if b.type == "tool_use"]
        text_blocks = [b for b in response.content if b.type == "text"]

        # If Claude returned text with no tool calls, it's the final JSON output
        if not tool_uses and text_blocks:
            final_text = text_blocks[0].text.strip()
            if verbose:
                print(f"  [Agent] Profile determined after {step + 1} step(s).")
            return _parse_profile(final_text)

        # If Claude stopped without tool calls and without text, something went wrong
        if not tool_uses:
            break

        # Execute each tool call and collect results
        tool_results = []
        for tool_use in tool_uses:
            tool_name = tool_use.name
            tool_input = tool_use.input

            if verbose:
                args_str = ", ".join(f"{k}={v!r}" for k, v in tool_input.items()) if tool_input else ""
                print(f"  [Tool] {tool_name}({args_str})")

            result_str = _run_tool(tool_name, tool_input, songs)

            if verbose:
                try:
                    result_data = json.loads(result_str)
                    # Print a concise summary rather than the full result
                    if tool_name == "get_catalog_overview":
                        genres = result_data.get("available_genres", [])
                        moods = result_data.get("available_moods", [])
                        print(f"    → {len(genres)} genres, {len(moods)} moods available")
                    elif tool_name == "search_songs":
                        n = result_data.get("matches", 0)
                        songs_found = [s["title"] for s in result_data.get("songs", [])]
                        print(f"    → {n} match(es): {', '.join(songs_found[:5]) or 'none'}")
                except Exception:
                    print(f"    → {result_str[:120]}")

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_use.id,
                "content": result_str,
            })

        # Append Claude's response and all tool results to the message thread
        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})

    raise RuntimeError("Agentic parser exceeded maximum steps without producing a profile.")


def _parse_profile(text: str) -> UserProfile:
    """Parse Claude's final JSON output into a UserProfile."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])

    data = json.loads(text)
    return UserProfile(
        favorite_genre=str(data.get("favorite_genre", "pop")).lower(),
        favorite_mood=str(data.get("favorite_mood", "chill")).lower(),
        target_energy=max(0.0, min(1.0, float(data.get("target_energy", 0.5)))),
        likes_acoustic=bool(data.get("likes_acoustic", False)),
    )
