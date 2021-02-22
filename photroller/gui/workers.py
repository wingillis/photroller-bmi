import h5py
import time
import multiprocess as mp
from toolz import dissoc
from photroller.util import dict_to_h5
from photroller.bmi_process import Stream
from PySide6.QtCore import QRunnable, Signal, QObject, Slot


class PhotometryUpdateSignal(QObject):
    new_data = Signal(object)
    stop_stream = Signal()


class PhotometryWorker(QRunnable):

    def __init__(self, gui_info, shutdown_event) -> None:
        super().__init__()
        self.gui_info = gui_info
        self.signals = PhotometryUpdateSignal()
        self.queue = mp.Queue()
        self.shutdown_event = shutdown_event

    @Slot()
    def run(self):
        duration = self.gui_info.saving_parameters['duration'] * 60  # seconds
        save_path = self.gui_info.saving_parameters['save_path']
        with h5py.File(save_path, 'w') as h5f:
            dict_to_h5(h5f, dissoc(self.gui_info.saving_parameters, 'save_path'), 'metadata')
            dict_to_h5(h5f, self.gui_info.photometry_parameters, 'metadata/photometry')
        process = Stream(self.queue, self.shutdown_event, self.gui_info)
        process.start()
        timer = time.time()
        while not self.shutdown_event.is_set():
            data = self.queue.get(block=True, timeout=None)
            self.signals.new_data.emit(data)
            # stop recording data if we've exceeded the session's duration
            if (time.time() - timer) > duration:
                self.signals.stop_stream.emit()
