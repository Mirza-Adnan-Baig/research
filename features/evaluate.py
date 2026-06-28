"""
Evaluation metrics for comparing NthOrderMarkovChain models.

Four metrics are provided:

    mean_entropy        — average Shannon entropy of transition distributions.
                          Higher entropy → more uniform / diverse transitions.

    vocabulary_coverage — count of unique next-states seen during training.
                          Higher coverage → richer learned vocabulary.

    ngram_diversity     — ratio of unique n-grams to total n-grams in generated
                          output.  Higher ratio → less repetitive output.

    js_divergence       — Jensen-Shannon divergence between the aggregate
                          next-state distributions of two chains.
                          0 = identical distributions, 1 = maximally different.
"""

import math
from collections import Counter

from features.markov import NthOrderMarkovChain


def mean_entropy(chain: NthOrderMarkovChain) -> float:
    """
    Average Shannon entropy (bits) across all contexts seen during training.

    Delegates to NthOrderMarkovChain.mean_entropy() which computes
    H = -∑ p·log₂(p) per context then averages.
    """
    return chain.mean_entropy()


def vocabulary_coverage(chain: NthOrderMarkovChain) -> int:
    """
    Number of unique next-state tokens seen during training across all contexts.

    This measures how broad the learned vocabulary is — the paper's sparseness
    problem manifests as low coverage for higher-order models on small corpora.
    """
    seen: set[str] = set()
    for counter in chain.transitions.values():
        seen.update(counter.keys())
    return len(seen)


def ngram_diversity(sequences: list[list[str]], n: int) -> float:
    """
    Ratio of unique n-grams to total n-grams across a collection of generated
    sequences.

    A ratio of 1.0 means every n-gram is unique (maximally diverse).
    A ratio approaching 0.0 means highly repetitive output.

    Args:
        sequences: Generated token sequences (each a list of strings).
        n:         n-gram size (typically equal to the Markov order).

    Returns:
        Float in [0, 1].  Returns 0.0 if no n-grams can be extracted.
    """
    all_ngrams: list[tuple] = []
    for seq in sequences:
        for i in range(len(seq) - n + 1):
            all_ngrams.append(tuple(seq[i : i + n]))
    if not all_ngrams:
        return 0.0
    return len(set(all_ngrams)) / len(all_ngrams)


def js_divergence(
    chain_a: NthOrderMarkovChain, chain_b: NthOrderMarkovChain
) -> float:
    """
    Jensen-Shannon divergence between the aggregate next-state distributions
    of two Markov chains.

    The aggregate distribution P is computed by summing all transition counts
    across all contexts, then normalising.  This gives a single distribution
    over the vocabulary of next-states, allowing comparison between models
    trained on corpora with different sizes.

    JSD(P || Q) = ½ KL(P || M) + ½ KL(Q || M),  where M = ½(P + Q).

    Returns a value in [0, 1] (base-2 logarithm).
    Returns 0.0 if either chain has no transitions.
    """

    def aggregate(chain: NthOrderMarkovChain) -> dict[str, float]:
        """Sum counts over all contexts and normalise to a probability dist."""
        total_counts: Counter = Counter()
        for counter in chain.transitions.values():
            total_counts.update(counter)
        total = sum(total_counts.values())
        if total == 0:
            return {}
        return {state: count / total for state, count in total_counts.items()}

    p = aggregate(chain_a)
    q = aggregate(chain_b)

    if not p or not q:
        return 0.0

    all_states = set(p) | set(q)
    m = {s: 0.5 * (p.get(s, 0.0) + q.get(s, 0.0)) for s in all_states}

    def kl(dist: dict[str, float]) -> float:
        """KL(dist || m), skipping zero-probability terms."""
        total = 0.0
        for s in all_states:
            pi = dist.get(s, 0.0)
            mi = m[s]
            if pi > 0.0 and mi > 0.0:
                total += pi * math.log2(pi / mi)
        return total

    return 0.5 * kl(p) + 0.5 * kl(q)
