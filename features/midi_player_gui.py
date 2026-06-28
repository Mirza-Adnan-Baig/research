import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QPushButton, QLabel, QFileDialog, QWidget, QTextEdit
from PyQt5.QtCore import QSize
from music21 import converter, note, chord, tempo, meter
from features.midiplayer import MidiPlayer
from threading import Thread
import pygame


class MidiPlayerGUI(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setMinimumSize(QSize(250, 100))
        self.setWindowTitle("MIDI Player")
        self.midi_player = MidiPlayer()
        self.paused = False
        self.file_loaded = False
        self.play_thread = None  # Store the play thread
        pygame.mixer.init()
        self.default_path = os.path.dirname(os.path.abspath(os.path.join(__file__, os.pardir)))

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        self.file_label = QLabel("Aktuelle Datei:")
        self.layout.addWidget(self.file_label)

        self.play_button = QPushButton("Play")
        self.play_button.clicked.connect(self.play_pause)
        self.layout.addWidget(self.play_button)

        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.stop)
        self.layout.addWidget(self.stop_button)

        self.show_area = QTextEdit(self)
        self.show_area.setReadOnly(True)
        self.layout.addWidget(self.show_area)

        self.update_button_state()

    def display_midi_events(self, midi_file_path):
        # Parse the MIDI file
        midi = converter.parse(midi_file_path)

        # Iterate through all elements in the score
        for element in midi.flatten().notesAndRests:
            if isinstance(element, note.Note):
                self.show_area.append(f"Note: {element.pitch}, Duration: {element.duration.quarterLength}, "
                                      f"Offset: {element.offset}")
            elif isinstance(element, chord.Chord):
                pitches = [pitch.nameWithOctave for pitch in element.pitches]
                self.show_area.append(f"Chord: {pitches}, Duration: {element.duration.quarterLength}, "
                                      f"Offset: {element.offset}")
            elif isinstance(element, note.Rest):
                self.show_area.append(f"Rest: Duration: {element.duration.quarterLength}, "
                                      f"Offset: {element.offset}")

        # Iterate through tempo changes
        for element in midi.flatten().getElementsByClass(tempo.MetronomeMark):
            self.show_area.append(f"Tempo: {element.number} BPM, Offset: {element.offset}")

        # Iterate through time signature changes
        for element in midi.flatten().getElementsByClass(meter.TimeSignature):
            self.show_area.append(f"Time Signature: {element.ratioString}, Offset: {element.offset}")

    def play_pause(self):
        if not self.file_loaded:
            file_path, _ = QFileDialog.getOpenFileName(self, "Open MIDI file", self.default_path,
                                                       "MIDI Files (*.midi *.mid)")
            if file_path:
                self.file_loaded = True
                self.display_midi_events(file_path)
                self.play_button.setText("Pause")
                self.file_label.setText(f"Aktuelle Datei: {os.path.basename(file_path)}")
                self.update_button_state()
                self.play_thread = Thread(target=self.midi_player.play, args=(file_path,))
                self.play_thread.start()
        else:
            if self.paused:
                self.paused = False
                self.play_button.setText("Pause")
                self.midi_player.resume()
            else:
                self.paused = True
                self.play_button.setText("Resume")
                self.midi_player.pause()

    def on_music_end(self):
        self.file_loaded = False
        self.play_button.setText("Play")
        self.update_button_state()

    def stop(self):
        if self.play_thread and self.play_thread.is_alive():
            self.midi_player.stop()
            self.play_thread.join()  # Ensure the play thread terminates properly
        self.file_loaded = False
        self.play_button.setText("Play")
        self.show_area.clear()
        self.update_button_state()

    def update_button_state(self):
        self.play_button.setEnabled(not self.paused or not self.file_loaded)
        self.stop_button.setEnabled(self.file_loaded)

    def closeEvent(self, event):
        self.stop()
        event.accept()


if __name__ == "__main__":
    app = QApplication([])
    window = MidiPlayerGUI()
    window.show()
    app.exec_()
