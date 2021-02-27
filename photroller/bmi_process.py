import time
import h5py
import numpy as np
import multiprocess as mp
from cmath import rect
from labjack import ljm
from queue import Queue
from threading import Thread
from scipy import signal
from hyphyber.util.sig import is_filter_stable
from functools import reduce
# eventually, add another process to send over raw photometry data
# for saving


def phase_shift(data, shift=np.pi / 2):
    shift = rect(1, shift)
    d2 = np.fft.rfft(data)
    new_data = np.fft.irfft(d2 * shift)
    return new_data + (d2[0].real / len(data))


def demodulate(data, ref_x, bp_filter, lp_filter, lowpass=False):
    ref_y = phase_shift(ref_x)
    out = signal.sosfiltfilt(bp_filter, data)

    out_x = np.square(ref_x * out)
    out_y = np.square(ref_y * out)

    if lowpass:
        out_x = signal.sosfiltfilt(lp_filter, out_x)
        out_y = signal.sosfiltfilt(lp_filter, out_y)

    return np.hypot(np.sqrt(out_x), np.sqrt(out_y))


def _concat(agg, segment):
    for a, s in zip(agg, segment):
        a.extend(s)
    return agg


def concatenate(cache):
    # concat each datastream within the cache
    _in = [list() for _ in range(len(cache[0]))]
    out = reduce(_concat, cache, _in)
    return out


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
            # deciding to save demodulated signal to h5 too
            # OPTION: if computer too slow, change compression from gzip to lzf or nothing
            dset = h5f.create_dataset('raw_photometry', shape=(spr, n_ports + 1),
                                      maxshape=(None, n_ports + 1), dtype=np.float32,
                                      chunks=(spr, n_ports + 1), compression='gzip',
                                      compression_opts=3)
            dio = h5f.create_dataset('digital_io', shape=(spr, ),
                                     maxshape=(None, ), dtype=np.uint16,
                                     chunks=(spr, ), compression='gzip', compression_opts=3)
            offset = 0
            while not self.shutdown_event.is_set() or not self.queue.empty():
                data = self.queue.get(block=True, timeout=None)
                data = data.T
                dset.resize(offset + len(data), axis=0)
                dset[offset:offset + len(data)] = data[:, :-1]
                dio.resize(offset + len(data), axis=0)
                dio[offset:offset + len(data)] = data[:, -1]
                offset += len(data)
        print()
        print('Stream over, closing h5 file')


class Stream(mp.Process):
    def __init__(self, queue, shutdown_event, gui_info, cache_size: int = 3) -> None:
        '''
        Params:
            cache_size: how much data to store in memory in seconds. Used for filtering and visualisation.
                Also used to determine the frequency of dumping data to a file.
        '''
        super().__init__()
        self.cache_size = cache_size
        self.queue = queue
        self.gui_info = gui_info
        self.handle = gui_info.labjack
        self.shutdown_event = shutdown_event

    def run(self):
        # TODO: keep a rolling memory of data (mostly for filtering)
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
        lockin = LockIn(self.gui_info.photometry_parameters['freq1'],
                        self.gui_info.photometry_parameters['freq2'],
                        fs=new_scan_rate, lowpass_cutoff=15)

        n_entries = int(new_scan_rate * self.cache_size / scans_per_read)
        cache = [None] * n_entries
        cache_idx = 0

        while not self.shutdown_event.is_set():
            data = ljm.eStreamRead(self.handle)[0]
            data = [data[i::n_ports] for i in range(n_ports)]
            cache[cache_idx % n_entries] = data
            cache_idx += 1
            if cache_idx < n_entries:
                continue
            # benchmark processing
            start = time.time()
            concat_data = concatenate(cache)
            if cache_idx % n_entries == 0:
                io_queue.put(concat_data)
            rs = lockin(data)
            # re-arrange the data so that digital stream is last
            data = data[:-1] + rs + data[-1:]
            end = time.time()
            print('Time to demodulate', round(end - start, 6), 's')
            data = np.array(data, dtype=np.float32)
            io_queue.put(data)
            self.queue.put(data)
        ljm.eStreamStop(self.handle)
        ljm.close(self.handle)


class LockIn:
    def __init__(self, freq1, freq2, fs=3000, bw=60, lowpass_cutoff=15) -> None:
        # set up filters
        bw = bw // 2
        self.lowpass_sos = signal.butter(2, lowpass_cutoff, fs=fs, output='sos')
        assert is_filter_stable(self.lowpass_sos)
        self.sos1 = signal.ellip(3, 0.1, 40, [freq1 - bw, freq1 + bw],
                                 btype='bandpass', fs=fs, output='sos')
        assert is_filter_stable(self.sos1)
        self.sos2 = signal.ellip(3, 0.1, 40, [freq2 - bw, freq2 + bw],
                                 btype='bandpass', fs=fs, output='sos')
        assert is_filter_stable(self.sos2)

    def __call__(self, data) -> np.array:
        # assume data contains all signals from labjack
        # assume ref1 = blue modulation
        # ref2 = UV modulation
        # signal1 = green channel
        # signal2 = blue channel
        # disregard signal2, both refs onto green shannel
        ref1_x, ref2_x, signal1, _, _ = data

        out1 = demodulate(signal1, ref1_x, self.sos1, self.lowpass_sos, lowpass=True)
        out2 = demodulate(signal1, ref2_x, self.sos2, self.lowpass_sos, lowpass=True)

        return [out1, out2]
