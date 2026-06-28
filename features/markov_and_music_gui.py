import sys
import argparse
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QPushButton, QLabel, QFileDialog,
                             QWidget, QTextEdit, QInputDialog, QCheckBox)
from PyQt5.QtCore import QSize
from features.markov import Dataset
from features.worker_thread import WorkerThread
from features.midi_player_gui import MidiPlayerGUI


class MainGUI(QMainWindow):
    def __init__(self, debug_mode=False):
        super().__init__()

        # Save the debug flag, if present
        self.debug_mode = debug_mode

        # GUI-Setup
        self.setWindowTitle('Markov & Musik - Tool')
        self.setMinimumSize(QSize(500, 300))

        #create the relevant containers
        self.dataset = Dataset(debug_mode)
        self.midi_player_window = None
        self.default_dir = os.path.dirname(os.path.abspath(os.path.join(__file__, os.pardir)))
        self.worker = None

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        # Creating the GUI elements
        # Label for path output
        self.label = QLabel("No folder selected", self)
        self.layout.addWidget(self.label)

        # Button for selecting the dataset
        self.button_select = QPushButton("Select dataset", self)
        self.button_select.clicked.connect(self.open_dataset)
        self.layout.addWidget(self.button_select)

        # Button for loading the results of previous analysis
        #self.button_loadmodels = QPushButton("Load previous Model", self)
        #self.button_loadmodels.clicked.connect(self.prompt_for_model_location)
        #self.layout.addWidget(self.button_loadmodels)

        # Button for starting the analysis
        self.button_analyze = QPushButton("Analyze dataset", self)
        self.button_analyze.clicked.connect(self.prompt_for_inputs)
        self.button_analyze.setEnabled(False)  # Disable the button by default
        self.layout.addWidget(self.button_analyze)


        # Button for the generation function
        self.button_generate = QPushButton("Generate new music", self)
        self.button_generate.clicked.connect(self.generate_music)
        self.button_generate.setEnabled(False)  # Disable the Generate button at the beginning
        self.layout.addWidget(self.button_generate)

        # Button for opening the MIDI player
        self.button_midi_player = QPushButton("Start MIDI Player", self)
        self.button_midi_player.clicked.connect(self.open_midi_player)
        self.layout.addWidget(self.button_midi_player)

        # Checkboxes for selecting the information displayed
        self.show_all_checkbox = QCheckBox("Enable entire log", self)
        self.show_all_checkbox.setChecked(True)  # Enabled by default
        self.show_all_checkbox.stateChanged.connect(self.handle_checkbox_toggle)
        self.layout.addWidget(self.show_all_checkbox)

        self.important_only_checkbox = QCheckBox("Show only important messages", self)
        self.important_only_checkbox.setChecked(False)
        self.important_only_checkbox.stateChanged.connect(self.handle_checkbox_toggle)
        self.layout.addWidget(self.important_only_checkbox)

        # Text field for the logger to display messages
        self.log_area = QTextEdit(self)
        self.log_area.setReadOnly(True)
        self.layout.addWidget(self.log_area)

    def handle_checkbox_toggle(self):
        """
        Method to ensure exclusive behavior between the two checkboxes.
        """
        if self.sender() == self.show_all_checkbox and self.show_all_checkbox.isChecked():
            self.important_only_checkbox.blockSignals(True)
            self.important_only_checkbox.setChecked(False)
            self.important_only_checkbox.blockSignals(False)

        elif self.sender() == self.important_only_checkbox and self.important_only_checkbox.isChecked():
            self.show_all_checkbox.blockSignals(True)
            self.show_all_checkbox.setChecked(False)
            self.show_all_checkbox.blockSignals(False)

    def log_message(self, message, is_important=False):
        """
        Method for displaying messages in the text field
        :param message: Message text
        :param is_important: Flag for the checkboxes to control behavior
        """
        # Determine the logic for the display based on the checkboxes.
        show_important_only = self.important_only_checkbox.isChecked()
        show_all = self.show_all_checkbox.isChecked()

        # Secure checkboxes against each other (either “Important” or “Everything,” never both)
        if show_important_only and show_all:
            self.important_only_checkbox.setChecked(False)


        # Logic for displaying messages
        if show_all:  # When “Show all” is active
            self.log_area.append(message)
        elif show_important_only and is_important:  # If only important information should be displayed
            self.log_area.append(message)

        # Nothing is displayed if no checkbox is active.

        # Automatically scroll to the end of the log to display the most recent message
        self.log_area.verticalScrollBar().setValue(self.log_area.verticalScrollBar().maximum())
        QApplication.processEvents()

    def start_worker(self, task):
        """
        Individual threads are used to prevent GUI elements and functions from blocking each other
        :param task: which task the thread receives (analyze/generate)
        """
        self.set_buttons_enabled(False)
        self.worker = WorkerThread(self.dataset, task)
        self.worker.logger.connect(self.log_message)
        self.worker.finished.connect(self.on_task_finished)
        self.worker.start()

    def set_buttons_enabled(self, enabled):
        """
        Function to enable/disable all buttons in the GUI
        :param enabled: Status of the buttons (true/false)
        """
        self.button_select.setEnabled(enabled)
        self.button_analyze.setEnabled(enabled)
        self.button_generate.setEnabled(enabled)
        self.button_midi_player.setEnabled(enabled)

    def open_dataset(self):
        """
        Function for selecting the data set to be used
        """
        # It will open in file dialog where main.py is located.
        folder_path = QFileDialog.getExistingDirectory(self, 'Select folder', self.default_dir)
        if folder_path:
            self.dataset.load_data(folder_path)  # Set the selected folder path to the dataset
            self.label.setText(f"Selected folder: {folder_path}")
            self.button_analyze.setEnabled(True)  # Activate the Start-Analysis-Button


    #NOTE: This code is broken. Please do not use yet
    def prompt_for_model_location(self):
        """
        Function for selecting a previously generated model
        """
        # It will open in file dialog where main.py is located.
        model_folder_path = QFileDialog.getExistingDirectory(self, 'Select folder', self.default_dir)
        if model_folder_path:
            self.dataset.load_model(model_folder_path)  # Set the selected folder path to the dataset
            self.label.setText(f"Selected folder: {model_folder_path}")
            self.button_generate.setEnabled(True)  # Activate the genarate-Button

    def prompt_for_inputs(self):
        """
        Function for querying the selection of scores and the order of the chain
        """
        text, ok = QInputDialog.getText(self, 'Select voices',
                                'Please enter the indexes of the desired voices (separated by commas '
                                'to be analyzed (blank entry means all):')
        if ok:
            track_indices = list(map(int, text.split(','))) if text else None  #Input saved correctly

            text, ok = QInputDialog.getText(self,'Select chain order',
                                'Please enter the order of the desired chain length as a number '
                                '(an empty entry sets the order to 1):')
            if ok:
                if text.strip():  # Checks whether the text is not empty
                    try:
                        # Convert the input into a single number
                        order = int(text)
                        print("chosen order:", order)

                    except ValueError:
                        if self.debug_mode:
                            print("Invalid input. Please enter a valid number.")
                        return
                else:
                    # Sets the order to 1 if no input has been made
                    order = 1

                # Transferring the values to the dataset
                self.dataset.order = order
                self.dataset.track_indices = track_indices

                # Starting the analysis
                self.analyze_dataset()

    def analyze_dataset(self):
        """
        Logic for the analysis button
        """
        if self.dataset:
            self.log_message("Analyzing data, please wait...", is_important=True)
            if self.dataset.track_indices:
                self.log_message(f"Only the voices {self.dataset.track_indices} are considered.")
            else:
                self.log_message("All voices are considered in the process.")
            if self.dataset.order:
                self.log_message(f"A Markov chain of order {self.dataset.order} will be used.", is_important=True)
            else:
                self.log_message("A first-order Markov chain will be used.")
            self.start_worker(task='analyze')
        else:
            self.log_message("No folder has been selected!", is_important=True)

    def generate_music(self):
        """
        Logic for the the button for generation
        """
        if self.dataset:

            self.log_message("Music generation is starting, please wait...", is_important=True)
            print("Order is ...", self.dataset.order)

            self.start_worker(task='generate')
        else:
            self.log_message("No folder has been selected!", is_important=True)

    def open_midi_player(self):
        """
        Logic of the MIDI player button
        :return:
        """
        self.midi_player_window = MidiPlayerGUI()
        self.midi_player_window.show()

    def on_task_finished(self, task):
        """
        Control what should be executed after each thread has finished
        :param task: which task was executed
        """
        if task == 'analyze':
            self.log_message("Analysis successfully completed!", is_important=True)
        elif task == 'generate':
            self.log_message("Generation successfully completed!", is_important=True)
        self.set_buttons_enabled(True)
        self.worker = None  # Clean up reference for thread


def parse_arguments():
    """
    Function for parsing command line arguments for debug mode
    """
    parser = argparse.ArgumentParser(description="Start the GUI with optional debugging.")
    parser.add_argument('--debug', action='store_true', help='Enables debug mode')
    return parser.parse_args()


if __name__ == '__main__':
    # Parse arguments
    args = parse_arguments()

    # Start the application
    app = QApplication(sys.argv)

    # Create and show the GUI, passing the debug mode
    gui = MainGUI(debug_mode=args.debug)
    gui.show()

    # Start the event loop
    sys.exit(app.exec_())
