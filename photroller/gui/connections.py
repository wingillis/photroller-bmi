from labjack import ljm
from serial.tools import list_ports
from photroller.util import PhotometryController
from PySide6.QtWidgets import QWidget, QPushButton, QGridLayout, QComboBox, QLabel, QVBoxLayout


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
    def __init__(self, gui_info, **kwargs):
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
        analog_in_names = [f'AIN{num}' for num in range(4)] + ['FIO_STATE']
        scan_list = ljm.namesToAddresses(len(analog_in_names), analog_in_names)[0]
        self.gui_info.scan_list = scan_list

        # disable triggered stream
        ljm.eWriteName(handle, 'STREAM_TRIGGER_INDEX', 0)
        # enable internally clocked stream
        ljm.eWriteName(handle, 'STREAM_CLOCK_SOURCE', 0)
        # Configure FIO 0-3
        init_params = {
            'STREAM_TRIGGER_INDEX': 0,
            'STREAM_CLOCK_SOURCE': 0,
            'STREAM_RESOLUTION_INDEX': 4,  # increase this to increase resolution
            'STREAM_SETTLING_US': 0,
            'AIN_ALL_NEGATIVE_CH': ljm.constants.GND,
            'FIO_DIRECTION': 0xF000
        }
        for i in range(4):
            init_params[f'AIN{i}_RANGE'] = 10.0

        ljm.eWriteNames(handle, len(init_params), list(init_params), list(init_params.values()))

        self.gui_info.labjack_init_params = init_params

        self.close()
