import PySide6
import datetime
import numpy as np
import pyqtgraph as pg
import multiprocess as mp
from os.path import basename, dirname, join
from dataclasses import dataclass, field
from photroller.util import PhotometryController
from PySide6.QtWidgets import QApplication, QFileDialog, QPlainTextEdit, QWidget, QLabel, QGridLayout, QPushButton, QLineEdit
from PySide6.QtCore import QThreadPool
from photroller.gui.workers import PhotometryWorker
from photroller.gui.connections import ConnectArduino, ConnectLabJack

# TODO:
# - add session length, to automatically stop recording
# - add capability to stream without recording
# - add stop recording button
# - add online lock-in filter


def _savepath_generator():
    return datetime.datetime.now().strftime('photometry_session_%Y%m%dT%H%M%S-%f.h5')


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
    saving_parameters: dict = field(default_factory=lambda: dict(
        save_path=_savepath_generator(),
        duration=30  # minutes
    ))


class SessionParams(QWidget):
    def __init__(self, gui_info: GUIInfo, **kwargs) -> None:
        self.units = ('Hz', 'Hz', 'V', 'V', 'V', 'V')
        super().__init__(**kwargs)
        self.gui_info = gui_info
        self.params = {}
        self.initUI()

    def initUI(self):
        layout = QGridLayout()
        self.filepath = QLabel(self.gui_info.saving_parameters['save_path'])
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

        i += 1
        layout.addWidget(QLabel('Session duration (min):'), i, 0)
        self.duration = QLineEdit()
        self.duration.setText(str(self.gui_info.saving_parameters['duration']))
        layout.addWidget(self.duration, i, 1)

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
        save_path, _ = QFileDialog.getSaveFileName(self, 'Save file...',
                                                   self.gui_info.saving_parameters['save_path'],
                                                   selectedFilter='*.h5')
        self.gui_info.saving_parameters['save_path'] = save_path
        self.filepath.setText(basename(save_path))

    def _update_save_parameters(self):
        self.gui_info.saving_parameters['session_name'] = self.session.text()
        self.gui_info.saving_parameters['subject_name'] = self.subject.text()
        self.gui_info.saving_parameters['notes'] = self.notes.toPlainText()
        self.gui_info.saving_parameters['duration'] = float(self.duration.text())

    def reset_filepath(self):
        filepath = _savepath_generator()
        _dir = dirname(self.gui_info.saving_parameters['save_path'])
        self.gui_info.saving_parameters['save_path'] = join(_dir, filepath)
        self.filepath.setText(filepath)


class MainWindow(QWidget):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.gui_info = GUIInfo()
        self.initUI()
        self.recording = False
        self.shutdown_event = mp.Event()

    def initUI(self):
        layout = QGridLayout()
        # TODO: labjack connection status indicator
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
            # self.phot_params._update_params()
            self.phot_params._update_save_parameters()
            worker = PhotometryWorker(self.gui_info, self.shutdown_event)
            worker.signals.new_data.connect(self.update_plots)
            worker.signals.stop_stream.connect(self.stop_stream)
            self.threadpool.start(worker)
            self.recording = True

    def closeEvent(self, event: PySide6.QtGui.QCloseEvent) -> None:
        self.shutdown_event.set()
        return super().closeEvent(event)

    def stop_stream(self):
        self.shutdown_event.set()
        self.phot_params.reset_filepath()


if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    app.exec_()
