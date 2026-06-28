import pygame
from pygame import mixer


class MidiPlayer:
    def __init__(self):
        self.paused = False

    def play(self, file_path, on_music_end=None):
        try:
            # Load the MIDI-File
            mixer.music.load(file_path)
            print("Playing MIDI file:", file_path)

            # Start the playback
            mixer.music.play()

            # Wait until playback has finished or been paused.
            while mixer.music.get_busy() or self.paused:
                pygame.time.Clock().tick(10)

            if on_music_end:
                # Callback function
                on_music_end()

        except pygame.error as e:
            print("Unable to play MIDI file:", e)

    def pause(self):
        if not self.paused:
            mixer.music.pause()
            self.paused = True
            print("Playback paused.")

    def resume(self):
        if self.paused:
            mixer.music.unpause()
            self.paused = False
            print("Playback resumed.")

    def stop(self):
        mixer.music.stop()
        print("Playback stopped.")
        self.paused = False
