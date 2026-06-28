"""
Corpus loader for the research pipeline.

Returns a list of song dicts, each with three keys:

    chord_progression : list[str]   e.g. ['C', 'Am', 'F', 'G']
    chord_duration    : list[float] e.g. [4.0, 2.0, 2.0, 4.0]
    rhythm            : list[float] e.g. [1.0, 0.5, 0.5, 2.0]

Loading priority:
    1. ABC files at the given path (Nottingham dataset or similar)
    2. MIDI / MusicXML files at the given path (chordified)
    3. music21's embedded Bach chorale corpus (default fallback)
"""

from pathlib import Path
from music21 import converter, corpus, chord, note, harmony


# music21 represents flats with '-' (e.g. 'B-' = B-flat).
# We normalise everything to sharps for a consistent token vocabulary.
_MUSIC21_FLAT_TO_SHARP: dict[str, str] = {
    "C-": "B",
    "D-": "C#",
    "E-": "D#",
    "F-": "E",
    "G-": "F#",
    "A-": "G#",
    "B-": "A#",
}


def _normalise_root(name: str) -> str:
    """Convert a music21 root name (may contain '-' for flat) to sharp notation."""
    return _MUSIC21_FLAT_TO_SHARP.get(name, name)


def _chord_label(c: chord.Chord) -> str:
    """
    Derive a simplified chord label ('C', 'Am', 'Gm', etc.) from a
    music21 Chord object.  Falls back to the lowest pitch name on error.
    """
    try:
        root = _normalise_root(c.root().name)
        quality = "m" if c.quality == "minor" else ""
        return root + quality
    except Exception:
        return _normalise_root(c.pitches[0].name)


def _extract_from_score(score) -> dict | None:
    """
    Extract chord_progression, chord_duration, and rhythm from a
    music21 Score by chordifying the harmonic content and reading the
    melody / soprano part for rhythm.

    Returns None if the score yields no usable data.
    """
    try:
        chordified = score.chordify()
    except Exception:
        return None

    chord_progression: list[str] = []
    chord_duration: list[float] = []

    for c in chordified.flatten().getElementsByClass(chord.Chord):
        if c.duration.quarterLength <= 0:
            continue
        chord_progression.append(_chord_label(c))
        chord_duration.append(float(c.duration.quarterLength))

    if not chord_progression:
        return None

    # Use the first (soprano / melody) part for rhythm
    try:
        part = score.parts[0] if score.parts else score
        rhythm: list[float] = [
            float(n.duration.quarterLength)
            for n in part.flatten().notesAndRests
            if isinstance(n, note.Note) and n.duration.quarterLength > 0
        ]
    except Exception:
        rhythm = []

    if not rhythm:
        return None

    return {
        "chord_progression": chord_progression,
        "chord_duration": chord_duration,
        "rhythm": rhythm,
    }


def _extract_from_abc(path: Path) -> dict | None:
    """
    Parse a single ABC file.  Chord symbols are ChordSymbol objects at
    specific time offsets; their durations are inferred from the offset
    of the next chord symbol.
    """
    try:
        score = converter.parse(str(path))
    except Exception:
        return None

    cs_list = list(score.flatten().getElementsByClass(harmony.ChordSymbol))

    if cs_list:
        total_time = float(score.flatten().highestTime)
        chord_progression: list[str] = []
        chord_duration: list[float] = []

        for i, cs in enumerate(cs_list):
            try:
                root = _normalise_root(cs.root().name)
                quality = "m" if cs.quality == "minor" else ""
            except Exception:
                continue

            next_offset = (
                float(cs_list[i + 1].offset)
                if i + 1 < len(cs_list)
                else total_time
            )
            dur = next_offset - float(cs.offset)
            if dur <= 0:
                continue

            chord_progression.append(root + quality)
            chord_duration.append(dur)

        # Melody rhythm from the first part
        try:
            part = score.parts[0] if score.parts else score
            rhythm: list[float] = [
                float(n.duration.quarterLength)
                for n in part.flatten().notesAndRests
                if isinstance(n, note.Note) and n.duration.quarterLength > 0
            ]
        except Exception:
            rhythm = []

        if chord_progression and rhythm:
            return {
                "chord_progression": chord_progression,
                "chord_duration": chord_duration,
                "rhythm": rhythm,
            }

    # Fall back to chordify if no inline chord symbols were found
    return _extract_from_score(score)


# ------------------------------------------------------------------
# Public entry point
# ------------------------------------------------------------------

def load_corpus(dataset_path: str | None = None) -> list[dict]:
    """
    Load a chord-progression corpus and return a list of song dicts.

    Args:
        dataset_path: Directory path.  Searched for .abc files first,
                      then common score formats (.mid, .xml, etc.).
                      If None or no files found, falls back to the
                      music21 Bach chorale corpus.

    Returns:
        List of dicts, each with keys chord_progression, chord_duration,
        and rhythm.  Empty list if nothing could be loaded.
    """
    if dataset_path is not None:
        p = Path(dataset_path)

        abc_files = sorted(p.glob("**/*.abc"))
        if abc_files:
            print(f"Found {len(abc_files)} ABC file(s) in {p} — parsing...")
            return _load_abc_files(abc_files)

        score_files = [
            f
            for ext in ("*.mid", "*.midi", "*.xml", "*.mxl", "*.musicxml")
            for f in sorted(p.glob(f"**/{ext}"))
        ]
        if score_files:
            print(f"Found {len(score_files)} score file(s) in {p} — parsing...")
            return _load_score_files(score_files)

    print("No dataset path given (or no files found) — loading music21 Bach corpus.")
    return _load_bach_corpus()


def _load_abc_files(files: list[Path]) -> list[dict]:
    songs: list[dict] = []
    for f in files:
        song = _extract_from_abc(f)
        if song:
            songs.append(song)
    print(f"  ABC corpus: {len(songs)} / {len(files)} files loaded successfully.")
    return songs


def _load_score_files(files: list[Path]) -> list[dict]:
    songs: list[dict] = []
    for f in files:
        try:
            score = converter.parse(str(f))
            song = _extract_from_score(score)
            if song:
                songs.append(song)
        except Exception:
            continue
    print(f"  Score corpus: {len(songs)} / {len(files)} files loaded successfully.")
    return songs


def _load_bach_corpus() -> list[dict]:
    paths = corpus.getComposer("bach")
    songs: list[dict] = []
    for path in paths:
        try:
            score = corpus.parse(path)
            song = _extract_from_score(score)
            if song:
                songs.append(song)
        except Exception:
            continue
    print(f"  Bach corpus: {len(songs)} / {len(paths)} scores loaded successfully.")
    return songs
