from PyQt5.QtCore import QThread, pyqtSignal, QObject


class WorkerThread(QThread):
    logger = pyqtSignal(str, bool)
    finished = pyqtSignal(str)

    def __init__(self, dataset, task):
        super().__init__()
        self.dataset = dataset
        self.task = task

    def run(self):
        if self.task == 'analyze':
            self.dataset.generate_markov_model(self.logger)
            self.finished.emit('analyze')
        elif self.task == 'generate':
            self.dataset.generate_music(self.logger)
            self.finished.emit('generate')  # Send the task name signal after generation is complete
