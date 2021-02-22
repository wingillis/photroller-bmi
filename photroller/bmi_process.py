import time
import h5py
import numpy as np
import multiprocess as mp
from labjack import ljm
from threading import Thread
from queue import Queue
# eventually, add another process to send over raw photometry data
# for saving


class IO(Thread):
    def __init__(self, gui_info, queue, shutdown_event):
        super().__init__()
        self.queue = queue
        self.gui_info = gui_info
        self.shutdown_event = shutdown_event

    def run(self):
        spr = self.gui_info.scans_per_read
        n_ports = len(self.gui_info.scan_list)
        with h5py.File(self.gui_info.saving_parameters['save_path'], 'a') as h5f:
            # OPTION: if computer too slow, change compression from gzip to lzf or nothing
            dset = h5f.create_dataset('raw_photometry', shape=(spr, n_ports),
                                      maxshape=(None, n_ports), dtype=np.float32,
                                      chunks=(spr, n_ports), compression='gzip',
                                      compression_opts=3)
            offset = 0
            while not self.shutdown_event.is_set():
                data = self.queue.get(block=True, timeout=None)
                start = time.time()
                data = data.T
                dset.resize(offset + len(data), axis=0)
                dset[offset:offset + len(data)] = data
                stop = time.time()
                offset += len(data)
                print('h5 write time:', round(stop - start, 5), 's')


class Stream(mp.Process):
    def __init__(self, queue, shutdown_event, gui_info) -> None:
        super().__init__()
        self.queue = queue
        self.gui_info = gui_info
        self.handle = gui_info.labjack
        self.shutdown_event = shutdown_event

    def run(self):
        scan_list = self.gui_info.scan_list
        scans_per_read = self.gui_info.scans_per_read
        scan_rate = self.gui_info.scan_rate
        n_ports = len(scan_list)
        io_queue = Queue()
        io_thread = IO(self.gui_info, io_queue, self.shutdown_event)
        io_thread.start()

        new_scan_rate = ljm.eStreamStart(self.handle, scans_per_read, n_ports,
                                         scan_list, scan_rate)
        print('New scanning rate is:', new_scan_rate)

        while not self.shutdown_event.is_set():
            data = ljm.eStreamRead(self.handle)[0]
            data = [data[i::n_ports] for i in range(n_ports)]
            data = np.array(data, dtype=np.float32)
            self.queue.put(data)
            io_queue.put(data)
        ljm.eStreamStop(self.handle)
        ljm.close(self.handle)
