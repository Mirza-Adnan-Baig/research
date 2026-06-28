import sys
import argparse
from PyQt5.QtWidgets import QApplication
from features.markov_and_music_gui import MainGUI


def parse_arguments():
    """Function
    for parsing command line arguments"""
    parser = argparse.ArgumentParser(description="Start the GUI with optional debugging.")
    parser.add_argument('--debug', action='store_true', help='Enables debug mode')
    return parser.parse_args()


def main():
    """
    Starting point of the application
    """
    # Parse arguments if necessary
    args = parse_arguments()

    # Erstellen der Anwendung# Creating the application
    app = QApplication(sys.argv)

    # Start the GUI and pass whether debug mode should be used
    gui = MainGUI(debug_mode=args.debug)
    gui.show()

    # Starting the loop
    # Starting the loop
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
