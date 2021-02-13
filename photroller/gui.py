import pyqtgraph as pg
from serial.tools import list_ports
from dataclasses import dataclass, field
from photroller.util import PhotometryController
from PySide6.QtWidgets import QApplication, QWidget, QComboBox, QLabel, QGridLayout, QPushButton, QLineEdit

@dataclass
class GUIInfo:
    photometry_parameters: dict = field(default_factory=lambda: dict(
                                          freq1=150, freq2=350,
                                          amp1=3, amp2=1,
                                          offset1=0.1, offset2=0.1))
    photometry_controller: PhotometryController = None
    labjack = None


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
        super.__init__(**kwargs)
        self.gui_info = gui_info
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Connect to LabJack for data stream')

        self.show()


class PhotometryParams(QWidget):
    def __init__(self, gui_info: GUIInfo, **kwargs) -> None:
        self.units = ('Hz', 'Hz', 'V', 'V', 'V', 'V')
        super().__init__(**kwargs)
        self.gui_info = gui_info
        self.params = {}
        self.initUI()

    def initUI(self):
        layout = QGridLayout()

        for i, (k, v) in enumerate(self.gui_info.photometry_parameters.items()):
            layout.addWidget(QLabel(f'{k} ({self.units[i]})'), i, 0)
            self.params[k] = QLineEdit()
            self.params[k].setText(str(v))
            layout.addWidget(self.params[k], i, 1)

        # TODO: add button to write parameters to arduino
        self.setLayout(layout)


class MainWindow(QWidget):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.gui_info = GUIInfo()
        self.initUI()

    def initUI(self):
        layout = QGridLayout()
        # populate with graphs and options for graphs
        # place to save file
        # lock-in parameters
        self.setWindowTitle('Photometry BMI')
        self.phot_params = PhotometryParams(self.gui_info)
        layout.addWidget(self.phot_params, 0, 0)

        self.setLayout(layout)
        self.show()

        if self.gui_info.photometry_controller is None:
            # open new window and show
            self.connector = ConnectArduino(self.gui_info)
        if self.gui_info.labjack is None:
            self.labjack_connector = ConnectLabJack(self.gui_info)


if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    app.exec_()
