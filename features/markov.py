import json
import math
import random
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path
from typing import Optional, List

from markovify import Chain
from music21 import converter, note, chord, stream
import markovify


class NthOrderMarkovChain:
    """
    N-th order Markov chain trained from frequency counts, as described in
    Van Der Merwe & Schulze (2011).

    Transition probabilities are estimated by maximum likelihood:
        P(q_t | q_{t-1}, ..., q_{t-n}) = count(context → q_t) / count(context)

    Supports configurable order n, probabilistic generation (sampling, never
    argmax), suffix-based backoff for unseen contexts, and Shannon entropy
    computation per context.
    """

    def __init__(self, order: int) -> None:
        """
        Args:
            order: Length of the history window (n in n-th order).
                   1 = standard first-order chain, 2 = bigram context, etc.
        """
        if order < 1:
            raise ValueError(f"Order must be >= 1, got {order}")
        self.order = order
        # Maps n-gram context tuple → Counter of {next_state: frequency}
        self.transitions: dict[tuple, Counter] = defaultdict(Counter)

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def train(self, sequences: list[list[str]]) -> None:
        """
        Learn transition probabilities from a corpus of sequences.

        Each sequence contributes every consecutive (order+1)-gram:
        the first `order` elements form the context, the last element
        is the observed next state.  Short sequences (length <= order)
        are silently skipped.

        Args:
            sequences: List of token sequences (each is a list of strings).
        """
        for seq in sequences:
            if len(seq) <= self.order:
                continue
            for i in range(len(seq) - self.order):
                context: tuple = tuple(seq[i : i + self.order])
                next_state: str = seq[i + self.order]
                self.transitions[context][next_state] += 1

    # ------------------------------------------------------------------
    # Probability lookup with backoff
    # ------------------------------------------------------------------

    def _backoff(self, context: tuple) -> tuple:
        """
        Shorten the context by dropping the oldest token until a known
        context is found, or until the context is empty.

        This is the suffix-based backoff strategy equivalent to PSA
        state resolution in the paper.
        """
        while len(context) > 0 and context not in self.transitions:
            context = context[1:]
        return context  # may be () if nothing found

    def get_probabilities(self, context: tuple) -> dict[str, float]:
        """
        Return the normalised probability distribution over next states
        for the given context (with backoff applied).

        Returns an empty dict when no matching context exists at any order.
        """
        context = self._backoff(context)
        if context not in self.transitions:
            return {}
        counter = self.transitions[context]
        total = sum(counter.values())
        return {state: count / total for state, count in counter.items()}

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------

    def generate(self, length: int, seed: tuple | None = None) -> list[str]:
        """
        Generate a token sequence of the given length by sampling from the
        learned probability distributions (never argmax — paper §Music generation).

        Args:
            length: Desired output sequence length.
            seed:   Optional starting context tuple.  Falls back to a random
                    training context if seed is unknown or None.

        Returns:
            List of generated tokens, exactly `length` elements long
            (or shorter only if the model has zero transitions).
        """
        if not self.transitions:
            return []

        # Resolve starting context
        if seed is not None:
            ctx = self._backoff(seed)
        else:
            ctx = ()

        if ctx not in self.transitions:
            ctx = random.choice(list(self.transitions.keys()))

        output: list[str] = list(ctx)

        while len(output) < length:
            tail = tuple(output[-self.order :])
            probs = self.get_probabilities(tail)
            if not probs:
                # Dead end: jump to a random training context (handles sparse data)
                ctx = random.choice(list(self.transitions.keys()))
                output.extend(ctx)
                continue
            states = list(probs.keys())
            weights = list(probs.values())
            output.append(random.choices(states, weights=weights)[0])

        return output[:length]

    # ------------------------------------------------------------------
    # Entropy
    # ------------------------------------------------------------------

    def entropy(self, context: tuple) -> float:
        """
        Shannon entropy (bits) of the transition distribution for one context.

        H(context) = -∑ p(s) · log₂ p(s)

        Returns 0.0 if the context is unknown.
        """
        probs = self.get_probabilities(context)
        if not probs:
            return 0.0
        return -sum(p * math.log2(p) for p in probs.values() if p > 0)

    def mean_entropy(self) -> float:
        """Average Shannon entropy across all contexts seen during training."""
        if not self.transitions:
            return 0.0
        return sum(self.entropy(ctx) for ctx in self.transitions) / len(self.transitions)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, path: str) -> None:
        """
        Serialize the model to a JSON file.

        Transitions are stored as a list of [context_list, counter_dict]
        pairs to avoid JSON key-type restrictions on tuples.
        """
        data = {
            "order": self.order,
            "transitions": [
                [list(ctx), dict(counter)]
                for ctx, counter in self.transitions.items()
            ],
        }
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, path: str) -> "NthOrderMarkovChain":
        """Load a model previously saved with .save()."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        chain = cls(data["order"])
        for ctx_list, counter_dict in data["transitions"]:
            chain.transitions[tuple(ctx_list)] = Counter(counter_dict)
        return chain


class Dataset:
    """
    A class that contains all the information in the data set and provides the Markov chain methods
    """

    def __init__(self, debug_mode=False):
        # Initializing the required containers
        self.dataset_path = None
        self.model_path = None
        self.order = None
        self.debug_mode = debug_mode
        self.track_indices = None
        self.markov_data = {  # Dictionary to store all relevant data related to Markov
            key: {
                "tokens": Optional[List],
                "tokens_path": Optional[Path],
                "chain": Optional[Chain],
                "model_path": Optional[Path],
            } for key in ["monolithic", "note", "velocity", "duration"]
        }

    def load_data(self, folder_path):
        """
        Saving the path to the data record
        :param folder_path: Path to the data record
        """
        self.dataset_path = Path(folder_path).resolve()

    def load_model(self, model_folder_path):
        """
        Saving the path to the data record
        :param model_folder_path: Path to the data record
        """
        self.model_path = Path(model_folder_path).resolve()


    #NOTE: need to update this to allow reading in previous models
    def generate_markov_model(self, logger):
        """
        Function for creating Markov models
        :param logger: Logger for transmitting messages between threads
        """
        logger.emit(f"Process data from the folder: {self.dataset_path}", False)
        logger.emit(f"Potentially using old model from the folder: {self.model_path}", False)
        logger.emit("Create Markov models!", True)

        # Setting the file paths for the models and tokens depending on their intended use
        for key in self.markov_data:
            # Set the model_path dynamically based on the key
            self.markov_data[key]["model_path"] = Path(f"output/model/markov_model_{key}.json").resolve()
            self.markov_data[key]["tokens_path"] = Path(f"output/tokens/markov_tokens_{key}.json").resolve()

        # Check whether the parent directories of the models and tokens exist
        # and if not, create them
        for path in [Path(f"output/model").resolve(), Path(f"output/tokens").resolve()]:
            if not path.exists():
                path.mkdir(parents=True, exist_ok=True)

        logger.emit(f"Save the generated models in {Path(f'output/model').resolve()}", False)
        logger.emit(f"Store the generated tokens in {Path(f'output/tokens').resolve()}", False)

        # Tokenizing the dataset
        logger.emit("Create Markov chains", False)

        #note: I think there is a problem here with the tokenization of rests. They show up to often.
        #I believe we need to skip this if we have previously decided to load an old model
        #if self.model_path
        self.tokenize_dataset(logger)

        # Debugging: Show the first token elements (if debug mode is enabled)
        if self.debug_mode:
            print("First 5 tokens of each set:")

            # Iterate over all entries in self.markov_data
            for key, data in self.markov_data.items():
                tokens_list = data.get("tokens", [])

                # Display the name of the set and the first 5 tokens for each list in the set
                print(f"Set: {key}")
                for token_set in tokens_list[:5]:  # Show a maximum of 5 lists from the set
                    print([t[:5] for t in token_set])  # Show the first 5 tokens of each list

        # Store Markov chains and their associated paths in a dictionary
        #NOTE: Update here so that the loaded model is used.
        for key in self.markov_data:
            # Set the model_path dynamically based on the key
            self.markov_data[key]["chain"] = markovify.Chain(self.markov_data[key]["tokens"], self.order)

        logger.emit("Data are being saved, please wait....", True)
        for key, data in self.markov_data.items():
            model = data.get("chain")
            model_path = data.get("model_path")
            tokens = data.get("tokens")
            tokens_path = data.get("tokens_path")

            try:
                # Saving Markov models
                if model and model_path:  # Check whether model and model_path exist
                    logger.emit(f"The {key} model has been saved in {model_path}", False)
                    with open(model_path, "w") as f:
                        f.write(model.to_json())  # Save model in JSON format

                # Saving the tokenized data records
                if tokens and tokens_path:  # Check if tokens and path exist
                    logger.emit(f"The created {key} tokens were saved in {path}", False)
                    with open(tokens_path, "w") as f:
                        json.dump(tokens, f, indent=2)  # Save tokens in JSON format
            except (FileNotFoundError, PermissionError, json.JSONDecodeError) as e:
                logger.emit(f"Error while saving: {e}", True)

        # Log the tracks used and the chain order
        if self.track_indices:
            logger.emit(f"Only the audio tracks {self.track_indices} were considered, and a Markov chain of order "
                        f"{self.order} was used.", True)
        else:
            logger.emit(f"All available audio tracks were considered and a Markov chain of {self.order} order was used.",
                        True)

    # function to build string note tokens from all midi files in a folder
    def tokenize_dataset(self, logger):
        # Initialize the lists in self.markov_data
        midi_file_paths = list(self.dataset_path.glob("**/*.mid*"))

        for key in ["monolithic", "note", "velocity", "duration"]:
            self.markov_data[key]["tokens"] = []

        # convert midi to string tokens for each file
        for midi_file_path in midi_file_paths:
            try:
                monolithic_tokens, notes_tokens, volume_tokens, duration_tokens = self.midi_to_string_list(midi_file_path)

                logger.emit(f"Processed Files {midi_file_path.name}", False)

                # Create a dictionary that links the token types with the keys
                token_data = {
                    "monolithic": monolithic_tokens,
                    "note": notes_tokens,
                    "velocity": volume_tokens,
                    "duration": duration_tokens
                }

                # Save the tokens with a loop in self.markov_data
                for key, tokens in token_data.items():
                    self.markov_data[key]["tokens"].append(tokens)

            except Exception as e:
                logger.emit(f"Error processing {midi_file_path}: {e}", True)

    def load_old_Model(self, logger):
        # Initialize the lists in self.markov_data
        for model_file_path in self.model_path:
            try:
                self.markov_data[key]["chain"] = self.model_to_chain(model_file_path)

                logger.emit(f"Processed Files {model_file_path.name}", False)
            except Exception as e:
                logger.emit(f"Error processing {model_file_path}: {e}", True)

    def model_to_chain(self, model_file_path):
        """
        Convert model file to the chain,

        :param model_file_path: Path to the MIDI file
        :return: the transition table (chain)
        """

        try:
            # LOADING Markov models
            if model and model_path:  # Check whether model and model_path exist
                logger.emit(f"The {key} model has been loaded from {model_path}", False)
                with open(model_path, "r") as f:
                    f.read(model.from_json())  # Save model in JSON format

        except (FileNotFoundError, PermissionError, json.JSONDecodeError) as e:
            logger.emit(f"Error while saving: {e}", True)

        #return monolithic_tokens, note_tokens, volume_tokens, duration_tokens


    def midi_to_string_list(self, midi_file_path):
        """
        Convert MIDI file to a list of string tokens, including note volume, duration and rests.

        :param midi_file_path: Path to the MIDI file
        :return: Tuple Lists - (monolithic tokens, notes tokens, volume tokens, duration tokens
        """
        # Parse MIDI file using music21
        midi_stream = converter.parse(midi_file_path)

        monolithic_tokens = []
        note_tokens = []
        volume_tokens = []
        duration_tokens = []

        # Helper function to convert note and chord to token
        def element_to_token(ele):
            if isinstance(ele, note.Note):
                pitch_name = ele.pitch.nameWithOctave
                duration = round(float(Fraction(ele.duration.quarterLength)), 3)  # Convert to float to standardize
                velocity = ele.volume.velocity if ele.volume.velocity else 64  # Default MIDI velocity

                # Monolithic: monolithic tokens (all features in one table)
                monolithic_token = f"NOTE({pitch_name}, {duration}, {velocity})"
                monolithic_tokens.append(monolithic_token)

                # Separate Chains (one chain for each feature)
                note_tokens.append(f"{pitch_name}")
                volume_tokens.append(f"{velocity}")
                duration_tokens.append(f"{duration}")

            elif isinstance(ele, chord.Chord):
                pitches = [pitch.nameWithOctave for pitch in ele.pitches]
                duration = round(float(Fraction(ele.duration.quarterLength)), 3)  # Standardize duration to float
                velocity = ele.volume.velocity if ele.volume.velocity else 64  # Default to 64 if velocity is None

                token_list = [f"({pitch},{duration},{velocity})" for pitch in pitches]
                monolithic_token = f"CHORD({'/'.join(token_list)})"
                monolithic_tokens.append(monolithic_token)

                note_tokens.append("/".join(pitches))  # All pitches separated by /
                volume_tokens.append(f"{velocity}")  # Single velocity for the whole chord
                duration_tokens.append(f"{duration}")  # Standardized duration for the chord

            elif isinstance(ele, note.Rest):
                duration = round(float(Fraction(ele.duration.quarterLength)), 3)  # Convert to float to standardize
                monolithic_tokens.append(f"REST({duration})")
                note_tokens.append("REST")
                volume_tokens.append("0")  # Velocity for the rests is 0
                duration_tokens.append(f"{duration}")

        if self.track_indices is None:
            # Flatten the entire score if no track indices are provided
            elements = midi_stream.flatten().notesAndRests
            for element in elements:
                element_to_token(element)
        else:
            # Process only the specified track indices
            for i, part in enumerate(midi_stream.parts):
                if i in self.track_indices:
                    if self.debug_mode:
                        print(f"Processing track {i} of file {midi_file_path}")
                    elements = part.flatten().notesAndRests
                    for element in elements:
                        element_to_token(element)

        return monolithic_tokens, note_tokens, volume_tokens, duration_tokens

    def generate_music(self, logger):
        # generate new midi from markov_and_musik model
        logger.emit("Start generating MIDI files using the generated Markov models.", False)
        output_dir = Path.cwd() / "output/generated_files"

        if not output_dir.exists():
            output_dir.mkdir(parents=True, exist_ok=True)  # Ensure the directory exists

        for i in range(10):
            monolithic_output_path = output_dir / f"{i + 1}_markov_monolithic_output.midi"
            parallel_output_path = output_dir / f"{i + 1}_markov_parallel_output.midi"

            # convert tokens to midi and save both monolithic and parallel
            #NOTE: WHY is it not sending the order down? How does the walk know the order?
            self.generate_from_markov_chain(monolithic_output_path, parallel_output_path)

            # Debugging: Log generated output file path
            logger.emit(f"Generated file (monolithic): {monolithic_output_path.name}", False)
            logger.emit(f"Generated file  (parallel): {parallel_output_path.name}", False)

        logger.emit(f"Files are saved in {output_dir}", False)

    # Funktion zum Generieren von MIDI aus der Markov-and-Musik-Kette
    def generate_from_markov_chain(self, monolithic_midi_save_path, parallel_midi_save_path):

        # generate tokens from monolithic markov chain
        generated_monolithic_tokens = self.markov_data["monolithic"]["chain"].walk()

        # Create parallel sequences by simultaneously running through the split Markov chains.
        generated_note_sequence = self.markov_data["note"]["chain"].walk()
        generated_velocity_sequence = self.markov_data["velocity"]["chain"].walk()
        generated_duration_sequence = self.markov_data["duration"]["chain"].walk()

        # Initialize an empty list to store the parallel tokens
        parallel_tokens = []

        # Go through the parallel sequences and merge them together.
        for pitch, velocity, duration in zip(generated_note_sequence, generated_velocity_sequence,
                                             generated_duration_sequence):
            # Create the parallel token for each note
            if pitch == "REST":
                parallel_tokens.append(f"REST({duration})")
            elif "/" in pitch:  # Check whether it is a chord
                pitch_tokens = pitch.split("/")

                # Create the chord token from notes, velocity, and duration
                chord_token = "/".join([f"({p},{duration},{velocity})" for p in pitch_tokens])
                parallel_tokens.append(f"CHORD({chord_token})")
            else:
                parallel_tokens.append(f"NOTE({pitch},{duration},{velocity})")

        # Debugging: Log generated tokens
        if self.debug_mode:
            print(f"\n\n\n\n\n"
                  f"Generated monolithic tokens: {generated_monolithic_tokens[:10]}..."
                  f"\n\n\n\n\n"
                  f"Generated parallel tokens: {parallel_tokens[:10]}..."
                  f"\n\n\n\n\n")

        # generate midi stream for both cases
        generated_monolithic_stream = self.string_list_to_midi(generated_monolithic_tokens)
        generated_parallel_stream = self.string_list_to_midi(parallel_tokens)

        # save midi stream to file if path provided
        if monolithic_midi_save_path:
            monolithic_midi_save_path = Path(monolithic_midi_save_path).resolve()
            generated_monolithic_stream.write("midi", monolithic_midi_save_path)

        if parallel_midi_save_path:
            parallel_midi_save_path = Path(parallel_midi_save_path).resolve()
            generated_parallel_stream.write("midi", parallel_midi_save_path)

    def string_list_to_midi(self, generated_midi_data):
        # create new midi stream
        generated_stream = stream.Stream()

        # convert string representations to midi
        for line in generated_midi_data:
            line = line.strip()
            next_element = None

            # Debug output to check the current line
            if self.debug_mode:
                print(f"Processing token: {line}")

            # Handle rest tokens
            if line.startswith("REST"):
                try:
                    rest_duration = float(line.strip("REST()"))
                    next_element = note.Rest()
                    next_element.duration.quarterLength = rest_duration
                except ValueError:
                    if self.debug_mode:
                        print(f"{line} is not correct formatted as REST!")

            # Handle chord tokens
            elif line.startswith("CHORD"):
                token_list = line.replace("CHORD", "").replace("(", "").replace(")", "").split("/")
                chord_notes = []

                for token in token_list:
                    try:
                        # Split the token into pitch, duration, and velocity
                        pitch_name, duration, velocity = token.split(",")

                        if pitch_name:  # Make sure there's a valid pitch
                            # Create a Note object
                            chord_note = note.Note(pitch_name)

                            # Set the duration
                            chord_note.duration.quarterLength = float(duration)

                            # Set the velocity (volume)
                            chord_note.volume.velocity = int(velocity)

                            # Add the note to the chord list
                            chord_notes.append(chord_note)
                    except ValueError as e:
                        print(f"Invalid token '{token}': {e}")

                # Create a Chord object from the list of notes
                next_element = chord.Chord(chord_notes)

            # Handle note tokens
            elif line.startswith("NOTE"):
                try:
                    # Replace "NOTE(" and remove the closing parenthesis
                    token = line.replace("NOTE(", "").replace(")", "")
                    pitch_name, duration, velocity = token.split(",")
                    # Debug output to see parsed components
                    if self.debug_mode:
                        print(f"Pitch name: {pitch_name}, Duration: {duration}, Velocity: {velocity}")

                    if pitch_name:  # Check if pitch_name is valid
                        next_element = note.Note(pitch_name)
                        next_element.duration.quarterLength = float(duration)
                        next_element.volume.velocity = int(velocity)
                    else:
                        if self.debug_mode:
                            print(f"Warning: Empty pitch name in token: {line}")
                except Exception as e:
                    if self.debug_mode:
                        print(f"Error parsing token {line}: {e}")

            # Append the element to the stream if valid
            if next_element:
                generated_stream.append(next_element)

        return generated_stream
