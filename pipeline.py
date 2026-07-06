"""
Research pipeline — entry point.

Research question:
    Does transposition-based data augmentation improve the statistical
    similarity and perceived musical quality of symbolic music generated
    by n-th order Markov chains?

Usage:
    python pipeline.py
    python pipeline.py --orders 1 2 3 --dataset-path /path/to/abc/files
    python pipeline.py --orders 2 --length 32 --n-sequences 10

Outputs (written to output/pipeline/):
    models/order_N/baseline_<type>.json    — trained baseline model files
    models/order_N/augmented_<type>.json   — trained augmented model files
    generated/order_N/baseline_<type>.json — generated sequences (baseline)
    generated/order_N/augmented_<type>.json
    results.json                           — all metric rows as JSON
    entropy_comparison.png                 — bar chart: mean entropy
    vocabulary_comparison.png              — bar chart: vocabulary coverage
    diversity_comparison.png               — line chart: n-gram diversity vs order

Also written to output/generated_files/{baseline,augmented}/order_N/*.mid —
rendered MIDI files, one per generated sequence.
"""

import argparse
import json
import random
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # non-interactive; saves to file without a display
import matplotlib.pyplot as plt

from features.markov import NthOrderMarkovChain
from features.abc_parser import load_corpus
from features.augmentation import transpose_dataset
from features.evaluate import (
    mean_entropy,
    vocabulary_coverage,
    ngram_diversity,
    js_divergence,
)
from features.midi_export import save_chords_as_midi

# Dimension names that match the song dict keys
CHAIN_TYPES: list[str] = ["chord_progression", "chord_duration", "rhythm"]

OUTPUT_DIR = Path("output/pipeline")
MIDI_OUTPUT_DIR = Path("output/generated_files")


# ------------------------------------------------------------------
# Training helpers
# ------------------------------------------------------------------

def _sequences_from_corpus(songs: list[dict]) -> dict[str, list[list[str]]]:
    """
    Extract three parallel sequence corpora from a list of song dicts.

    Floats (durations, rhythm values) are converted to strings so that
    the Markov chain treats them as discrete tokens.
    """
    return {
        "chord_progression": [s["chord_progression"] for s in songs],
        "chord_duration": [
            [str(round(d, 3)) for d in s["chord_duration"]] for s in songs
        ],
        "rhythm": [
            [str(round(r, 3)) for r in s["rhythm"]] for s in songs
        ],
    }


def _train(seqs: dict[str, list[list[str]]], order: int) -> dict[str, NthOrderMarkovChain]:
    """Train one NthOrderMarkovChain per chain type at the given order."""
    models: dict[str, NthOrderMarkovChain] = {}
    for ct in CHAIN_TYPES:
        chain = NthOrderMarkovChain(order)
        chain.train(seqs[ct])
        models[ct] = chain
    return models


def _generate(
    models: dict[str, NthOrderMarkovChain], n: int, length: int
) -> dict[str, list[list[str]]]:
    """Generate n sequences of the given length from each model."""
    return {
        ct: [models[ct].generate(length) for _ in range(n)]
        for ct in CHAIN_TYPES
    }


# ------------------------------------------------------------------
# Metrics
# ------------------------------------------------------------------

def _compute_metrics(
    baseline: dict[str, NthOrderMarkovChain],
    augmented: dict[str, NthOrderMarkovChain],
    baseline_gen: dict[str, list[list[str]]],
    augmented_gen: dict[str, list[list[str]]],
    order: int,
) -> list[dict]:
    """Return one metric row per chain type for the given order."""
    rows: list[dict] = []
    for ct in CHAIN_TYPES:
        rows.append(
            {
                "order": order,
                "chain": ct,
                "b_entropy": round(mean_entropy(baseline[ct]), 4),
                "a_entropy": round(mean_entropy(augmented[ct]), 4),
                "b_vocab": vocabulary_coverage(baseline[ct]),
                "a_vocab": vocabulary_coverage(augmented[ct]),
                "b_diversity": round(ngram_diversity(baseline_gen[ct], order), 4),
                "a_diversity": round(ngram_diversity(augmented_gen[ct], order), 4),
                "js_div": round(js_divergence(baseline[ct], augmented[ct]), 4),
            }
        )
    return rows


# ------------------------------------------------------------------
# Reporting
# ------------------------------------------------------------------

def _print_table(all_rows: list[dict]) -> None:
    """Print a formatted comparison table to stdout."""
    col = {
        "order": 5, "chain": 18,
        "b_entropy": 11, "a_entropy": 11,
        "b_vocab": 9, "a_vocab": 9,
        "b_diversity": 13, "a_diversity": 13,
        "js_div": 9,
    }
    header = (
        f"{'Ord':>{col['order']}}  "
        f"{'Chain':>{col['chain']}}  "
        f"{'Entropy(B)':>{col['b_entropy']}}  "
        f"{'Entropy(A)':>{col['a_entropy']}}  "
        f"{'Vocab(B)':>{col['b_vocab']}}  "
        f"{'Vocab(A)':>{col['a_vocab']}}  "
        f"{'Divers(B)':>{col['b_diversity']}}  "
        f"{'Divers(A)':>{col['a_diversity']}}  "
        f"{'JS-Div':>{col['js_div']}}"
    )
    sep = "=" * len(header)
    thin = "-" * len(header)

    print(f"\n{sep}")
    print("BASELINE vs AUGMENTED — METRIC COMPARISON")
    print(f"  Entropy : mean Shannon entropy (bits) — higher = more diverse transitions")
    print(f"  Vocab   : unique next-states seen in training")
    print(f"  Divers  : unique n-grams / total n-grams in generated output")
    print(f"  JS-Div  : Jensen-Shannon divergence between models [0,1]")
    print(sep)
    print(header)
    print(thin)

    for r in all_rows:
        print(
            f"{r['order']:>{col['order']}}  "
            f"{r['chain']:>{col['chain']}}  "
            f"{r['b_entropy']:>{col['b_entropy']}.4f}  "
            f"{r['a_entropy']:>{col['a_entropy']}.4f}  "
            f"{r['b_vocab']:>{col['b_vocab']}}  "
            f"{r['a_vocab']:>{col['a_vocab']}}  "
            f"{r['b_diversity']:>{col['b_diversity']}.4f}  "
            f"{r['a_diversity']:>{col['a_diversity']}.4f}  "
            f"{r['js_div']:>{col['js_div']}.4f}"
        )

    print(sep + "\n")


# ------------------------------------------------------------------
# Plots
# ------------------------------------------------------------------

def _save_plots(all_rows: list[dict]) -> None:
    """Save three comparison plots as PNG files."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    orders = sorted({r["order"] for r in all_rows})

    # ---- Plot 1: Mean entropy per chain type, grouped by order ----
    fig, axes = plt.subplots(1, len(orders), figsize=(5 * len(orders), 5), sharey=True)
    if len(orders) == 1:
        axes = [axes]
    for ax, order in zip(axes, orders):
        rows = [r for r in all_rows if r["order"] == order]
        labels = [r["chain"].replace("_", "\n") for r in rows]
        x = list(range(len(labels)))
        w = 0.35
        ax.bar([xi - w / 2 for xi in x], [r["b_entropy"] for r in rows],
               w, label="Baseline", color="steelblue")
        ax.bar([xi + w / 2 for xi in x], [r["a_entropy"] for r in rows],
               w, label="Augmented", color="darkorange")
        ax.set_title(f"Order {order}")
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=8)
        ax.set_ylabel("Mean Entropy (bits)")
        ax.legend(fontsize=8)
    fig.suptitle("Mean Shannon Entropy: Baseline vs Augmented", fontsize=12)
    fig.tight_layout()
    path = OUTPUT_DIR / "entropy_comparison.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  Saved {path}")

    # ---- Plot 2: Vocabulary coverage per chain type ----
    fig, axes = plt.subplots(1, len(orders), figsize=(5 * len(orders), 5), sharey=True)
    if len(orders) == 1:
        axes = [axes]
    for ax, order in zip(axes, orders):
        rows = [r for r in all_rows if r["order"] == order]
        labels = [r["chain"].replace("_", "\n") for r in rows]
        x = list(range(len(labels)))
        w = 0.35
        ax.bar([xi - w / 2 for xi in x], [r["b_vocab"] for r in rows],
               w, label="Baseline", color="steelblue")
        ax.bar([xi + w / 2 for xi in x], [r["a_vocab"] for r in rows],
               w, label="Augmented", color="darkorange")
        ax.set_title(f"Order {order}")
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=8)
        ax.set_ylabel("Unique States (Vocabulary Size)")
        ax.legend(fontsize=8)
    fig.suptitle("Vocabulary Coverage: Baseline vs Augmented", fontsize=12)
    fig.tight_layout()
    path = OUTPUT_DIR / "vocabulary_comparison.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  Saved {path}")

    # ---- Plot 3: N-gram diversity vs Markov order (line chart) ----
    fig, axes = plt.subplots(1, len(CHAIN_TYPES), figsize=(5 * len(CHAIN_TYPES), 5))
    if len(CHAIN_TYPES) == 1:
        axes = [axes]
    for ax, ct in zip(axes, CHAIN_TYPES):
        b_vals = [
            next((r["b_diversity"] for r in all_rows if r["order"] == o and r["chain"] == ct), 0.0)
            for o in orders
        ]
        a_vals = [
            next((r["a_diversity"] for r in all_rows if r["order"] == o and r["chain"] == ct), 0.0)
            for o in orders
        ]
        ax.plot(orders, b_vals, marker="o", label="Baseline", color="steelblue")
        ax.plot(orders, a_vals, marker="s", label="Augmented", color="darkorange")
        ax.set_title(ct.replace("_", " ").title(), fontsize=10)
        ax.set_xlabel("Markov Order")
        ax.set_ylabel("N-gram Diversity")
        ax.set_xticks(orders)
        ax.legend(fontsize=8)
        ax.grid(axis="y", linestyle="--", alpha=0.5)
    fig.suptitle("N-gram Diversity vs Markov Order: Baseline vs Augmented", fontsize=12)
    fig.tight_layout()
    path = OUTPUT_DIR / "diversity_comparison.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  Saved {path}")


# ------------------------------------------------------------------
# Persistence helpers
# ------------------------------------------------------------------

def _save_models(
    baseline: dict[str, NthOrderMarkovChain],
    augmented: dict[str, NthOrderMarkovChain],
    order: int,
) -> None:
    model_dir = OUTPUT_DIR / "models" / f"order_{order}"
    model_dir.mkdir(parents=True, exist_ok=True)
    for ct, chain in baseline.items():
        chain.save(str(model_dir / f"baseline_{ct}.json"))
    for ct, chain in augmented.items():
        chain.save(str(model_dir / f"augmented_{ct}.json"))


def _save_generated(
    baseline_gen: dict[str, list[list[str]]],
    augmented_gen: dict[str, list[list[str]]],
    order: int,
) -> None:
    gen_dir = OUTPUT_DIR / "generated" / f"order_{order}"
    gen_dir.mkdir(parents=True, exist_ok=True)
    for ct, seqs in baseline_gen.items():
        with open(gen_dir / f"baseline_{ct}.json", "w", encoding="utf-8") as f:
            json.dump(seqs, f, indent=2)
    for ct, seqs in augmented_gen.items():
        with open(gen_dir / f"augmented_{ct}.json", "w", encoding="utf-8") as f:
            json.dump(seqs, f, indent=2)


def _export_midi(
    baseline_gen: dict[str, list[list[str]]],
    augmented_gen: dict[str, list[list[str]]],
    order: int,
) -> None:
    """
    Render each generated chord_progression to a MIDI file.

    chord_duration is generated by its own independent Markov chain (same
    as rhythm), with no real timing relationship to chord_progression, so
    a fixed duration is used per chord here instead of pairing it with an
    unrelated generated sequence.
    """
    for label, gen in (("baseline", baseline_gen), ("augmented", augmented_gen)):
        out_dir = MIDI_OUTPUT_DIR / label / f"order_{order}"
        for i, progression in enumerate(gen["chord_progression"]):
            durations_f = [1.0] * len(progression)
            save_chords_as_midi(
                progression, durations_f, str(out_dir / f"{label}_{i + 1}.mid")
            )


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Markov music augmentation research pipeline"
    )
    parser.add_argument(
        "--orders", type=int, nargs="+", default=[1, 2, 3],
        help="Markov orders to evaluate (default: 1 2 3)"
    )
    parser.add_argument(
        "--dataset-path", type=str, default=None,
        help="Path to ABC or MIDI dataset directory"
    )
    parser.add_argument(
        "--length", type=int, default=64,
        help="Generated sequence length (default: 64)"
    )
    parser.add_argument(
        "--n-sequences", type=int, default=20,
        help="Number of sequences to generate per model (default: 20)"
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Random seed for reproducibility (default: 42)"
    )
    args = parser.parse_args()

    random.seed(args.seed)

    banner = "=" * 62
    print(f"\n{banner}")
    print("  MARKOV MUSIC AUGMENTATION — RESEARCH PIPELINE")
    print(f"  Orders: {args.orders}  |  Seq length: {args.length}  |  Seed: {args.seed}")
    print(f"{banner}\n")

    # ---- 1. Load corpus ----
    print("[1/4] Loading corpus...")
    songs = load_corpus(args.dataset_path)
    if not songs:
        print("ERROR: No songs could be loaded. Exiting.")
        return
    print(f"  Baseline corpus: {len(songs)} songs\n")

    # ---- 2. Augment ----
    print("[2/4] Applying transposition augmentation (shifts 1–11)...")
    augmented_songs = transpose_dataset(songs)
    print(f"  Augmented corpus: {len(augmented_songs)} songs "
          f"({len(augmented_songs) // len(songs)}× original)\n")

    baseline_seqs = _sequences_from_corpus(songs)
    augmented_seqs = _sequences_from_corpus(augmented_songs)

    # ---- 3. Train → generate → evaluate (per order) ----
    print("[3/4] Training, generating, and evaluating...")
    all_rows: list[dict] = []

    for order in args.orders:
        print(f"\n  -- Order {order} --")

        print("    Training baseline models...", end="", flush=True)
        baseline_models = _train(baseline_seqs, order)
        print(" done")

        print("    Training augmented models...", end="", flush=True)
        augmented_models = _train(augmented_seqs, order)
        print(" done")

        print("    Generating sequences...", end="", flush=True)
        baseline_gen = _generate(baseline_models, args.n_sequences, args.length)
        augmented_gen = _generate(augmented_models, args.n_sequences, args.length)
        print(" done")

        _save_models(baseline_models, augmented_models, order)
        _save_generated(baseline_gen, augmented_gen, order)

        print("    Rendering MIDI files...", end="", flush=True)
        _export_midi(baseline_gen, augmented_gen, order)
        print(" done")

        rows = _compute_metrics(
            baseline_models, augmented_models,
            baseline_gen, augmented_gen,
            order,
        )
        all_rows.extend(rows)
        print(f"    Metrics computed for order {order}.")

    # ---- 4. Report ----
    print("\n[4/4] Results")
    _print_table(all_rows)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    results_path = OUTPUT_DIR / "results.json"
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(all_rows, f, indent=2)
    print(f"  Metrics saved to {results_path}")

    print("\n  Saving plots...")
    _save_plots(all_rows)
    print(f"\nPipeline complete.  All outputs in {OUTPUT_DIR}/\n")


if __name__ == "__main__":
    main()
