import serial
from serial.tools import list_ports
from dataclasses import dataclass
from PyQt5.QtWidgets import QApplication, QComboBox, QWidget, QLabel, QGridLayout, QPushButton

@dataclass
class GUIInfo:
    serial_device: serial.Serial = None

gui_info = GUIInfo()

app = QApplication([])

window = QWidget()

layout = QGridLayout()
layout.addWidget(QLabel('Serial ports:'), 0, 0)

combo = QComboBox()
all_ports = list_ports.comports()
combo.addItems([port.device for port in all_ports])
layout.addWidget(combo, 0, 1)

button = QPushButton('Connect')
layout.addWidget(button, 1, 1)

window.setLayout(layout)
window.show()

def connect_arduino():
    arduino_path = combo.currentText()
    serial_device = serial.Serial(arduino_path,
                                  baudrate=115200,
                                  bytesize=serial.EIGHTBITS)
    gui_info.serial_device = serial_device
    
button.clicked.connect(connect_arduino)

app.exec()

