# Graph Report - .  (2026-07-06)

## Corpus Check
- Corpus is ~34,497 words - fits in a single context window. You may not need a graph.

## Summary
- 198 nodes · 300 edges · 11 communities
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 14 edges (avg confidence: 0.7)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Pipeline & Markov Core|Pipeline & Markov Core]]
- [[_COMMUNITY_Main GUI Application|Main GUI Application]]
- [[_COMMUNITY_ABC Corpus Parsing|ABC Corpus Parsing]]
- [[_COMMUNITY_Dataset Model Layer|Dataset Model Layer]]
- [[_COMMUNITY_Transposition Augmentation|Transposition Augmentation]]
- [[_COMMUNITY_MIDI Playback|MIDI Playback]]
- [[_COMMUNITY_Reference Paper Concepts|Reference Paper Concepts]]
- [[_COMMUNITY_Smoothing & Generation Theory|Smoothing & Generation Theory]]
- [[_COMMUNITY_MIDI Export|MIDI Export]]
- [[_COMMUNITY_Project Documentation|Project Documentation]]

## God Nodes (most connected - your core abstractions)
1. `NthOrderMarkovChain` - 22 edges
2. `MainGUI` - 19 edges
3. `Dataset` - 17 edges
4. `MidiPlayerGUI` - 13 edges
5. `main()` - 11 edges
6. `Music Generation with Markov Models (Van Der Merwe & Schulze, 2011)` - 10 edges
7. `transpose_dataset()` - 9 edges
8. `MidiPlayer` - 9 edges
9. `load_corpus()` - 8 edges
10. `js_divergence()` - 8 edges

## Surprising Connections (you probably didn't know these)
- `js_divergence()` --semantically_similar_to--> `Partial Turing Test evaluation (263 respondents)`  [INFERRED] [semantically similar]
  features/evaluate.py → Van Der Merwe and Schulze - 2011 - Music Generation with Markov Models.pdf
- `NthOrderMarkovChain` --semantically_similar_to--> `Markov Chain (MC) — models chord duration/progression/rhythm`  [INFERRED] [semantically similar]
  features/markov.py → Van Der Merwe and Schulze - 2011 - Music Generation with Markov Models.pdf
- `NthOrderMarkovChain._backoff()` --semantically_similar_to--> `Prediction Suffix Automaton (PSA)`  [INFERRED] [semantically similar]
  project_explanation.html → Van Der Merwe and Schulze - 2011 - Music Generation with Markov Models.pdf
- `Transposition Augmentation (concept)` --conceptually_related_to--> `transpose_dataset()`  [EXTRACTED]
  explanation_augmentation.html → features/augmentation.py
- `Data Sparseness Problem` --rationale_for--> `transpose_dataset()`  [EXTRACTED]
  project_explanation.html → features/augmentation.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Shared self.transitions dict across NthOrderMarkovChain methods** — features_markov_nthordermarkovchain_train, features_markov_nthordermarkovchain_get_probabilities, features_markov_nthordermarkovchain_entropy, features_markov_nthordermarkovchain_mean_entropy, features_evaluate_vocabulary_coverage [EXTRACTED 1.00]
- **pipeline.py orchestrates load -> augment -> train -> evaluate -> export flow** — pipeline, features_abc_parser_load_corpus, features_augmentation_transpose_dataset, features_markov_nthordermarkovchain, features_evaluate, features_midi_export_save_chords_as_midi [EXTRACTED 1.00]
- **Four evaluate.py metrics jointly answer the augmentation research question** — features_evaluate_mean_entropy, features_evaluate_vocabulary_coverage, features_evaluate_ngram_diversity, features_evaluate_js_divergence [EXTRACTED 1.00]

## Communities (11 total, 0 thin omitted)

### Community 0 - "Pipeline & Markov Core"
Cohesion: 0.08
Nodes (35): js_divergence(), mean_entropy(), ngram_diversity(), Evaluation metrics for comparing NthOrderMarkovChain models.  Four metrics are p, Average Shannon entropy (bits) across all contexts seen during training.      De, Number of unique next-state tokens seen during training across all contexts., Ratio of unique n-grams to total n-grams across a collection of generated     se, Jensen-Shannon divergence between the aggregate next-state distributions     of (+27 more)

### Community 1 - "Main GUI Application"
Cohesion: 0.08
Nodes (20): MainGUI, parse_arguments(), Individual threads are used to prevent GUI elements and functions from blocking, Function to enable/disable all buttons in the GUI         :param enabled: Status, Function for selecting the data set to be used, Function for selecting a previously generated model, Function for querying the selection of scores and the order of the chain, Logic for the analysis button (+12 more)

### Community 2 - "ABC Corpus Parsing"
Cohesion: 0.18
Nodes (17): Chord, _chord_label(), _extract_from_abc(), _extract_from_score(), _load_abc_files(), _load_bach_corpus(), load_corpus(), _load_score_files() (+9 more)

### Community 3 - "Dataset Model Layer"
Cohesion: 0.13
Nodes (7): Dataset, A class that contains all the information in the data set and provides the Marko, Saving the path to the data record         :param folder_path: Path to the data, Saving the path to the data record         :param model_folder_path: Path to the, Function for creating Markov models         :param logger: Logger for transmitti, Convert model file to the chain,          :param model_file_path: Path to the MI, Convert MIDI file to a list of string tokens, including note volume, duration an

### Community 4 - "Transposition Augmentation"
Cohesion: 0.14
Nodes (17): Enharmonic Equivalent, Transposition Augmentation (concept), _FLAT_TO_SHARP dict, _parse_chord(), _transpose_chord(), CHROMATIC scale list, _parse_chord(), Transposition-based data augmentation for chord-progression corpora.  For every (+9 more)

### Community 5 - "MIDI Playback"
Cohesion: 0.18
Nodes (3): Logic of the MIDI player button         :return:, MidiPlayerGUI, MidiPlayer

### Community 6 - "Reference Paper Concepts"
Cohesion: 0.12
Nodes (17): Brink van der Merwe (author), Carmel (finite-state transducer toolkit), Hidden Markov Model (HMM) — models melody/harmonization, Högberg — Wind in the Willows (tech report UMINF 05.13), Markov Chain (MC) — models chord duration/progression/rhythm, Moray & Williams — Harmonising Chorales by Probabilistic Inference (2005), MusicXML representation, Pachet — The Continuator (2003) (+9 more)

### Community 7 - "Smoothing & Generation Theory"
Cohesion: 0.13
Nodes (12): NthOrderMarkovChain._backoff(), Shannon entropy (bits) of the transition distribution for one context., Shorten the context by dropping the oldest token until a known         context i, Return the normalised probability distribution over next states         for the, Generate a token sequence of the given length by sampling from the         learn, Finding: augmentation entropy gain largest at order 3 (+61%), Shannon Entropy, LearnPSA algorithm (+4 more)

### Community 8 - "MIDI Export"
Cohesion: 0.33
Nodes (6): chords_to_midi_stream(), MIDI export for the research pipeline's generated chord sequences.  Renders a ch, Render a chord-progression/chord-duration pair as a block-chord stream., Render a chord sequence and write it to `path` as a MIDI file., save_chords_as_midi(), Stream

### Community 9 - "Project Documentation"
Cohesion: 0.33
Nodes (6): output/ folder map (GUI vs pipeline artifacts), Research Question: does transposition augmentation improve Markov chain output quality?, System 1 — the GUI App, System 2 — the Research Pipeline, Research Question: does transposition augmentation improve Markov chain output quality?, Multidimensional Markov Music (README)

## Ambiguous Edges - Review These
- `Multidimensional Markov Music (README)` → `System 1 — the GUI App`  [AMBIGUOUS]
  README.md · relation: conceptually_related_to

## Knowledge Gaps
- **22 isolated node(s):** `Multidimensional Markov Music (README)`, `Enharmonic Equivalent`, `CHROMATIC scale list`, `_FLAT_TO_SHARP dict`, `music21 bundled Bach chorale corpus (433 files)` (+17 more)
  These have ≤1 connection - possible missing edges or undocumented components.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `Multidimensional Markov Music (README)` and `System 1 — the GUI App`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `NthOrderMarkovChain` connect `Pipeline & Markov Core` to `Project Documentation`, `ABC Corpus Parsing`, `Reference Paper Concepts`, `Smoothing & Generation Theory`?**
  _High betweenness centrality (0.350) - this node is a cross-community bridge._
- **Why does `Dataset` connect `Dataset Model Layer` to `Pipeline & Markov Core`, `Main GUI Application`, `Project Documentation`?**
  _High betweenness centrality (0.247) - this node is a cross-community bridge._
- **Why does `MainGUI` connect `Main GUI Application` to `Dataset Model Layer`, `MIDI Playback`?**
  _High betweenness centrality (0.233) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `MainGUI` (e.g. with `Dataset` and `MidiPlayerGUI`) actually correct?**
  _`MainGUI` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `MidiPlayerGUI` (e.g. with `MainGUI` and `MidiPlayer`) actually correct?**
  _`MidiPlayerGUI` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Corpus loader for the research pipeline.  Returns a list of song dicts, each wit`, `Convert a music21 root name (may contain '-' for flat) to sharp notation.`, `Derive a simplified chord label ('C', 'Am', 'Gm', etc.) from a     music21 Chord` to the rest of the system?**
  _78 weakly-connected nodes found - possible documentation gaps or missing edges._