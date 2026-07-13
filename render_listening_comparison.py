"""
Listening-comparison rendering — reproduces the "original" and "improved"
folders under output/generated_files/, which are for A/B listening only and
are never read by the scientific pipeline (pipeline.py) or its metrics.

Requires output/pipeline/generated/order_N/{baseline,augmented}_chord_progression.json
to already exist (produced by `python pipeline.py`).

Outputs:
    output/generated_files/original/original_<n>_<name>.mid
        — the 5 reference chorales, exported to MIDI unmodified.
    output/generated_files/improved/{baseline,augmented}/order_N/*.mid
        — each generated chord_progression, voice-led into block chords,
          rendered with a real chorale's chord_duration and tempo
          (round-robin over the 5 reference chorales) instead of the flat
          1.0-quarter-length placeholder the scientific pipeline uses.

Usage:
    python render_listening_comparison.py
    python render_listening_comparison.py --orders 1 2 3
"""

import argparse
import json
from pathlib import Path

from music21 import corpus

from features.abc_parser import _extract_from_score
from features.midi_export import save_voice_led_block_chords_as_midi

REFERENCE_CHORALES: list[str] = [
    "bach/bwv1.6",
    "bach/bwv10.7",
    "bach/bwv101.7",
    "bach/bwv102.7",
    "bach/bwv103.6",
]

PIPELINE_DIR = Path("output/pipeline/generated")
ORIGINAL_DIR = Path("output/generated_files/original")
IMPROVED_DIR = Path("output/generated_files/improved")


def _load_reference_chorales() -> list[dict]:
    """Parse the 5 reference chorales, keeping the score, its chord_duration
    sequence, and its tempo (BPM) for reuse in the improved/ renders."""
    refs = []
    for name in REFERENCE_CHORALES:
        score = corpus.parse(name)
        song = _extract_from_score(score)
        try:
            bpm = score.metronomeMarkBoundaries()[0][2].getQuarterBPM()
        except Exception:
            bpm = 100.0
        refs.append({
            "name": name.split("/")[-1],
            "score": score,
            "chord_duration": song["chord_duration"],
            "bpm": bpm,
        })
    return refs


def _render_originals(refs: list[dict]) -> None:
    ORIGINAL_DIR.mkdir(parents=True, exist_ok=True)
    for i, ref in enumerate(refs, start=1):
        path = ORIGINAL_DIR / f"original_{i}_{ref['name']}.mid"
        ref["score"].write("midi", str(path))
        print(f"  Saved {path}")


def _render_improved(refs: list[dict], orders: list[int]) -> None:
    for order in orders:
        for label in ("baseline", "augmented"):
            src = PIPELINE_DIR / f"order_{order}" / f"{label}_chord_progression.json"
            if not src.exists():
                print(f"  Skipping order {order} {label}: {src} not found "
                      f"(run `python pipeline.py` first)")
                continue

            with open(src, "r", encoding="utf-8") as f:
                sequences: list[list[str]] = json.load(f)

            out_dir = IMPROVED_DIR / label / f"order_{order}"
            for i, progression in enumerate(sequences):
                ref = refs[i % len(refs)]
                n = min(len(progression), len(ref["chord_duration"]))
                save_voice_led_block_chords_as_midi(
                    progression[:n],
                    ref["chord_duration"][:n],
                    ref["bpm"],
                    str(out_dir / f"{label}_{i + 1}.mid"),
                )
            print(f"  Rendered {len(sequences)} {label} sequences for order {order}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render listening-comparison MIDI (original/ and improved/)"
    )
    parser.add_argument(
        "--orders", type=int, nargs="+", default=[1, 2, 3],
        help="Markov orders to render (default: 1 2 3)"
    )
    args = parser.parse_args()

    print("Loading 5 reference chorales...")
    refs = _load_reference_chorales()

    print("\nRendering output/generated_files/original/ ...")
    _render_originals(refs)

    print("\nRendering output/generated_files/improved/ ...")
    _render_improved(refs, args.orders)

    print("\nDone.")


if __name__ == "__main__":
    main()
