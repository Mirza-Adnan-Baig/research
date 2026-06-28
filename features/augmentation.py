"""
Transposition-based data augmentation for chord-progression corpora.

For every song, produces 11 additional copies — one per semitone shift
(1 through 11) — so the augmented corpus is exactly 12× the original.

Rules (from the research pipeline spec):
  - Only chord roots are shifted; chord quality is preserved verbatim.
  - Harmonic relationships within each progression are preserved because
    every chord in a song is shifted by the same amount simultaneously.
  - chord_duration and rhythm lists are copied without modification.
  - Every semitone 1–11 is applied systematically; augmentation is NOT random.

Example:
    Original:      ['C',  'F',  'G',  'C']
    Transpose +2:  ['D',  'G',  'A',  'D']
    Transpose +5:  ['F',  'A#', 'C',  'F']
"""

from typing import Sequence

# Chromatic pitch classes in sharp notation, index 0–11.
CHROMATIC: list[str] = [
    "C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"
]

# Flat-to-sharp aliases for incoming chord names that may use flat notation.
_FLAT_TO_SHARP: dict[str, str] = {
    "Db": "C#", "Eb": "D#", "Fb": "E",  "Gb": "F#",
    "Ab": "G#", "Bb": "A#", "Cb": "B",
}


def _parse_chord(chord_name: str) -> tuple[str, str]:
    """
    Split a chord name into (root, quality).

    Root is normalised to sharp notation.  Quality is everything after
    the root (e.g. 'm', 'M7', 'dim', '7', '').

    Examples:
        'Am'  → ('A',  'm')
        'C#m' → ('C#', 'm')
        'Bb7' → ('A#', '7')
        'G'   → ('G',  '')
    """
    # Two-character root: letter + '#' or 'b'
    if len(chord_name) >= 2 and chord_name[1] in ("#", "b"):
        root, quality = chord_name[:2], chord_name[2:]
    else:
        root, quality = chord_name[:1], chord_name[1:]

    root = _FLAT_TO_SHARP.get(root, root)
    return root, quality


def _transpose_chord(chord_name: str, semitones: int) -> str:
    """
    Shift the root of a chord name by `semitones` steps on the chromatic
    scale, preserving chord quality exactly.

    Unknown roots (not in CHROMATIC) are returned unchanged.
    """
    root, quality = _parse_chord(chord_name)
    if root not in CHROMATIC:
        return chord_name
    new_root = CHROMATIC[(CHROMATIC.index(root) + semitones) % 12]
    return new_root + quality


def transpose_dataset(
    songs: list[dict],
    semitone_range: Sequence[int] = range(1, 12),
) -> list[dict]:
    """
    Return the original songs plus one transposed copy per semitone shift.

    Args:
        songs:          Corpus dicts with keys chord_progression,
                        chord_duration, and rhythm.
        semitone_range: Shifts to apply (default 1–11, giving 12× output).

    Returns:
        Original songs concatenated with all transposed copies.
        Output length == len(songs) * (1 + len(semitone_range)).
    """
    shifts = list(semitone_range)
    augmented: list[dict] = list(songs)  # originals first

    for shift in shifts:
        for song in songs:
            augmented.append(
                {
                    "chord_progression": [
                        _transpose_chord(c, shift)
                        for c in song["chord_progression"]
                    ],
                    # Duration and rhythm are metre, not harmony — leave unchanged.
                    "chord_duration": song["chord_duration"],
                    "rhythm": song["rhythm"],
                }
            )

    expected = len(songs) * (1 + len(shifts))
    assert len(augmented) == expected, (
        f"Augmented corpus size mismatch: expected {expected}, got {len(augmented)}"
    )

    return augmented
