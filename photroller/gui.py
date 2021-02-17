import PySide6
import datetime
import numpy as np
import pyqtgraph as pg
import multiprocess as mp
from os.path import basename
from dataclasses import dataclass, field
from photroller.util import PhotometryController
from PySide6.QtWidgets import QApplication, QFileDialog, QPlainTextEdit, QWidget, QLabel, QGridLayout, QPushButton, QLineEdit
from PySide6.QtCore import QRunnable, QThreadPool, Signal, QObject, Slot
from photroller.bmi_process import Stream
from photroller.gui.connections import ConnectArduino, ConnectLabJack

# TODO:
# - add session length, to automatically stop recording


# class to store global parameters shared across all windows
@dataclass
class GUIInfo:
    photometry_parameters: dict = field(default_factory=lambda: dict(
                                          freq1=150, freq2=350,
                                          amp1=3, amp2=1,
                                          offset1=0.1, offset2=0.1))
    photometry_controller: PhotometryController = None
    labjack = None
    scan_rate: int = 5000  # samples per second
    labjack_init_params = None
    scans_per_read: int = 2500  # samples
    scan_list = None
    save_path: str = field(default_factory=lambda: datetime.datetime.now().strftime('photometry_session_%Y%m%dT%H%M%S-%f.h5'))


class PhotometryUpdateSignal(QObject):
    new_data = Signal(object)
    stop_stream = Signal()


class SessionParams(QWidget):
    def __init__(self, gui_info: GUIInfo, **kwargs) -> None:
        self.units = ('Hz', 'Hz', 'V', 'V', 'V', 'V')
        super().__init__(**kwargs)
        self.gui_info = gui_info
        self.params = {}
        self.initUI()

    def initUI(self):
        layout = QGridLayout()
        self.filepath = QLabel(self.gui_info.save_path)
        layout.addWidget(self.filepath, 0, 0, 1, 2)
        save_file_button = QPushButton('Update save path...')
        save_file_button.clicked.connect(self._set_savefile)
        layout.addWidget(save_file_button, 1, 0, 1, 2)

        for i, (k, v) in enumerate(self.gui_info.photometry_parameters.items(), start=2):
            layout.addWidget(QLabel(f'{k} ({self.units[i - 2]})'), i, 0)
            self.params[k] = QLineEdit()
            self.params[k].setText(str(v))
            layout.addWidget(self.params[k], i, 1)
        i += 1

        button = QPushButton('Update parameters')
        layout.addWidget(button, i, 1)
        button.clicked.connect(self._update_params)

        i += 1
        layout.addWidget(QLabel('Session Name:'), i, 0)
        self.session = QLineEdit()
        self.session.setPlaceholderText('Add session name')
        layout.addWidget(self.session, i, 1)

        i += 1
        layout.addWidget(QLabel('Subject Name:'), i, 0)
        self.subject = QLineEdit()
        self.subject.setPlaceholderText('Add subject name')
        layout.addWidget(self.subject, i, 1)

        i += 1
        self.notes = QPlainTextEdit()
        self.notes.setPlaceholderText('Add notes here...')
        layout.addWidget(self.notes, i, 0, 1, 2)
        self.setMaximumWidth(440)

        self.setLayout(layout)

    def _update_params(self):
        converter = {'freq': np.uint16, 'amp': np.single, 'offset': np.single}
        for k, v in self.params.items():
            for c, cv in converter.items():
                if c in k:
                    res = cv(float(v.text()))
                    self.gui_info.photometry_parameters[k] = res
        self.gui_info.photometry_controller.write_parameters(self.gui_info.photometry_parameters)

    def _set_savefile(self):
        save_path, _ = QFileDialog.getSaveFileName(self, 'Save file...', self.gui_info.save_path,
                                                   selectedFilter='*.h5')
        self.gui_info.save_path = save_path
        self.filepath.setText(basename(save_path))


class PhotometryWorker(QRunnable):

    def __init__(self, gui_info, shutdown_event) -> None:
        super().__init__()
        self.gui_info = gui_info
        self.signals = PhotometryUpdateSignal()
        self.queue = mp.Queue()
        self.shutdown_event = shutdown_event

    @Slot()
    def run(self):
        process = Stream(self.queue, self.shutdown_event, self.gui_info)
        process.start()
        while not self.shutdown_event.is_set():
            data = self.queue.get(block=True, timeout=None)
            self.signals.new_data.emit(data)


class MainWindow(QWidget):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.gui_info = GUIInfo()
        self.initUI()
        self.recording = False
        self.shutdown_event = mp.Event()

    def initUI(self):
        layout = QGridLayout()
        # populate with graphs and options for graphs
        # metadata
        # place to save file
        # lock-in parameters
        self.setWindowTitle('Photometry BMI')
        self.phot_params = SessionParams(self.gui_info)
        layout.addWidget(self.phot_params, 0, 0)
        # add sinusoid plot widget
        w = pg.PlotWidget(title="Sinusoids")
        layout.addWidget(w, 0, 1, 1, 2)
        self.sine_ = w
        w2 = pg.PlotWidget(title="Signal")
        layout.addWidget(w2, 1, 0, 1, 3)
        self.signal_ = w2

        button = QPushButton('Start streaming')
        button.setMaximumHeight(30)
        button.clicked.connect(self._record_data)
        layout.addWidget(button, 2, 2)

        self.setLayout(layout)
        self.show()

        if self.gui_info.photometry_controller is None:
            # open new window and show
            self.connector = ConnectArduino(self.gui_info)
        if self.gui_info.labjack is None:
            self.labjack_connector = ConnectLabJack(self.gui_info)

        self.threadpool = QThreadPool()

    def update_plots(self, data):
        self.sine_.clear()
        self.sine_.plot(y=data[0], pen={'color': 'r'})
        self.sine_.plot(y=data[1], pen={'color': 'c'})

        self.signal_.clear()
        self.signal_.plot(y=data[2], pen={'color': 'r'})
        self.signal_.plot(y=data[3], pen={'color': 'c'})
    
    def _record_data(self):
        if not self.recording:
            worker = PhotometryWorker(self.gui_info, self.shutdown_event)
            worker.signals.new_data.connect(self.update_plots)
            self.threadpool.start(worker)
            self.recording = True

    def closeEvent(self, event: PySide6.QtGui.QCloseEvent) -> None:
        self.shutdown_event.set()
        return super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    app.exec_()
