"""
Scoring Logic Design — asks Claude for point-weighting strategy recommendations
using the actual songs.csv schema and UserProfile fields as context.

Run once to get AI-generated scoring advice, then implement in recommender.py.

Usage:
    ANTHROPIC_API_KEY=<key> python src/design_scoring.py
"""

import anthropic
import csv
import os

CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "songs.csv")


def load_csv_preview(path: str) -> str:
    """Return the full CSV content as a string for use in the prompt."""
    with open(path, newline="", encoding="utf-8") as f:
        return f.read().strip()


def main():
    csv_content = load_csv_preview(CSV_PATH)

    prompt = f"""
You are a music recommendation algorithm designer.

Here is the complete songs dataset (CSV):

{csv_content}

Each song has these fields:
- id, title, artist
- genre       (categorical: pop, lofi, rock, jazz, edm, etc.)
- mood        (categorical: happy, chill, intense, relaxed, focused, etc.)
- energy      (float 0–1, how energetic the track is)
- tempo_bpm   (integer, beats per minute)
- valence     (float 0–1, musical positivity)
- danceability (float 0–1)
- acousticness (float 0–1, how acoustic vs electronic)

A UserProfile contains:
- favorite_genre  (string)
- favorite_mood   (string)
- target_energy   (float 0–1, preferred energy level)
- likes_acoustic  (bool, true = prefers acoustic tracks)

Design a point-weighting scoring function that compares a single song to a UserProfile.
The function returns a numeric score and a list of human-readable reasons.

Please address all of the following:

1. **Categorical matches (genre, mood)**
   - How many points should an exact genre match earn?
   - How many points should an exact mood match earn?
   - Should genre outweigh mood, or the reverse? Justify the choice.
   - Should partial / related-genre matches (e.g. "indie pop" matching "pop") earn partial points?

2. **Continuous field proximity (energy, tempo_bpm, acousticness)**
   - Recommend a formula for awarding points based on closeness to target_energy.
     (e.g., linear decay, squared error penalty, or bucket thresholds — pick one and justify.)
   - How should tempo_bpm be handled given that UserProfile has no explicit tempo preference?
     (Infer from energy? Ignore? Give partial credit for being in a reasonable range?)
   - How should likes_acoustic be scored? Suggest a threshold on the acousticness field.

3. **Valence and danceability**
   - These have no direct UserProfile counterpart. Should they contribute to the score at all?
     If yes, how? (e.g., use them as tie-breakers, or derive a mood-proxy score from them.)

4. **Suggested weight table**
   - Produce a concrete weight table like:
       genre_match:    X points
       mood_match:     X points
       energy_close:   up to X points
       acoustic_match: X points
       ...
   - Make sure the weights sum to a sensible maximum (e.g., 100) so scores are easy to interpret.

5. **Explanation strings**
   - For each awarded component, suggest the exact reason string to include in the output list,
     e.g. "Mood match: chill" or "Energy within 0.1 of target".

Keep the design simple enough for a beginner programmer to implement in ~30 lines of Python.
Output the weight table and formulas in plain text, followed by a short pseudocode sketch.
"""

    client = anthropic.Anthropic()

    print("Asking Claude for scoring strategy recommendations...\n")
    print("=" * 70)

    with client.messages.stream(
        model="claude-opus-4-6",
        max_tokens=2048,
        thinking={"type": "adaptive"},
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        for event in stream:
            if event.type == "content_block_start":
                if event.content_block.type == "thinking":
                    print("[Claude is thinking...]\n")
            elif event.type == "content_block_delta":
                if event.delta.type == "text_delta":
                    print(event.delta.text, end="", flush=True)

    print("\n" + "=" * 70)
    final = stream.get_final_message()
    print(f"\n[Tokens used — input: {final.usage.input_tokens}, "
          f"output: {final.usage.output_tokens}]")


if __name__ == "__main__":
    main()
