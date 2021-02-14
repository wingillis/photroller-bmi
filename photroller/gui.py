import PySide6
import datetime
import numpy as np
from os.path import basename
from labjack import ljm
from serial.tools import list_ports
from dataclasses import dataclass, field
from photroller.util import PhotometryController
from PySide6.QtWidgets import QApplication, QFileDialog, QPlainTextEdit, QVBoxLayout, QWidget, QComboBox, QLabel, QGridLayout, QPushButton, QLineEdit
import pyqtgraph as pg

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


class ConnectArduino(QWidget):
    def __init__(self, gui_info, **kwargs) -> None:
        super().__init__(**kwargs)
        self.gui_info = gui_info
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Connect to Arduino lock-in')
        layout = QGridLayout()
        self.button = QPushButton('Connect')
        refresh_b = QPushButton('Refresh')
        self.combo = QComboBox()

        layout.addWidget(QLabel('Serial ports:'), 0, 0)
        layout.addWidget(self.combo, 0, 1)
        layout.addWidget(self.button, 1, 1)
        layout.addWidget(refresh_b, 1, 0)

        self.button.clicked.connect(self._connect_arduino)
        refresh_b.clicked.connect(self._refresh)

        self._refresh()
        self.setLayout(layout)
        self.show()

    def _connect_arduino(self):
        arduino_path = self.combo.currentText()
        self.gui_info.photometry_controller = PhotometryController(self.gui_info.photometry_parameters,
                                                                   arduino_path)
        self.close()

    def _refresh(self):
        self.combo.clear()
        self.combo.addItems([port.device for port in list_ports.comports()])


class ConnectLabJack(QWidget):
    def __init__(self, gui_info: GUIInfo, **kwargs):
        super().__init__(**kwargs)
        self.gui_info = gui_info
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Connect to LabJack for data stream')
        layout = QVBoxLayout()
        layout.addWidget(QLabel('Connect a LabJack to this computer and click connect'))
        button = QPushButton('Connect')
        button.clicked.connect(self._connect_labjack)
        layout.addWidget(button)
        self.setLayout(layout)

        self.show()

    def _connect_labjack(self):
        handle = ljm.openS('T7', 'ANY', 'ANY')
        self.gui_info.labjack = handle
        info = ljm.getHandleInfo(handle)
        print(f'Labjack device type {info[0]}; connection type {info[1]}')
        print(f'Serial number {info[2]}; IP address {ljm.numberToIP(info[3])}')
        print(f'Port: {info[4]}; Max bytes per MB: {info[5]}')
        # two sinusoids, two pmt signals
        analog_in_names = [f'AIN{num}' for num in range(4)]
        scan_list = ljm.namesToAddresses(len(analog_in_names), analog_in_names)[0]
        self.gui_info.scan_list = scan_list

        # disable triggered stream
        ljm.eWriteName(handle, 'STREAM_TRIGGER_INDEX', 0)
        # enable internally clocked stream
        ljm.eWriteName(handle, 'STREAM_CLOCK_SOURCE', 0)
        init_params = {
            'STREAM_TRIGGER_INDEX': 0,
            'STREAM_CLOCK_SOURCE': 0,
            'STREAM_RESOLUTION_INDEX': 0,
            'STREAM_SETTLING_US': 0,
            'AIN_ALL_NEGATIVE_CH': ljm.constants.GND
        }
        for i in range(4):
            init_params[f'AIN{i}_RANGE'] = 10.0
        self.gui_info.labjack_init_params = init_params

        ljm.eWriteNames(handle, len(init_params), list(init_params), list(init_params.values()))

        self.close()


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

        self.setLayout(layout)

    def _update_params(self):
        converter = {'freq': np.uint16, 'amp': np.single, 'offset': np.single}
        for k, v in self.params.items():
            for c, cv in converter.items():
                if c in k:
                    res = cv(float(v.getText()))
                    self.gui_info.photometry_parameters[k] = res
        self.gui_info.photometry_controller.write_parameters(self.gui_info.photometry_parameters)

    def _set_savefile(self):
        save_path, _ = QFileDialog.getSaveFileName(self, 'Save file...', self.gui_info.save_path, selectedFilter='*.h5')
        self.gui_info.save_path = save_path
        self.filepath.setText(basename(save_path))


class MainWindow(QWidget):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.gui_info = GUIInfo()
        self.initUI()

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

        self.setLayout(layout)
        self.show()

        if self.gui_info.photometry_controller is None:
            # open new window and show
            self.connector = ConnectArduino(self.gui_info)
        if self.gui_info.labjack is None:
            self.labjack_connector = ConnectLabJack(self.gui_info)
    
    def _record_data(self):
        pass


if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    app.exec_()
