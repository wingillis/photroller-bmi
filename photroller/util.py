import h5py
import click
import serial
import struct
import time
import numpy as np
from serial.tools import list_ports


def select_serial_port():

    all_ports = list_ports.comports()

    for idx, port in enumerate(all_ports):
        print('[{}] {}'.format(idx, port.device))

    selection = None

    while selection is None:
        selection = click.prompt('Enter a selection', type=int)
        if selection > len(all_ports) or selection < 0:
            selection = None

    return all_ports[selection].device


def init_serial_port(serial_port=None, baudrate=115200, parity=serial.PARITY_NONE,
                     stopbits=serial.STOPBITS_ONE, bytesize=serial.EIGHTBITS,
                     write_timeout=0):

    if serial_port is None:
        serial_port = select_serial_port()

    serial_device = serial.Serial(serial_port,
                                  baudrate=baudrate,
                                #   parity=parity,
                                #   stopbits=stopbits,
                                  bytesize=bytesize,
                                #   writeTimeout=write_timeout
                                  )
    return serial_device


class PhotometryController:

    def __init__(self, photometry_parameters, serial_port=None, **kwargs):
        # initialize serial port, write in the photometry parameters
        if serial_port is not None:
            self.serial_port = serial_port

        self.device = init_serial_port(serial_port, **kwargs)
        self.photometry_parameters = photometry_parameters
        self.write_order = ('freq1', 'freq2', 'amp1', 'amp2', 'offset1', 'offset2')
        time.sleep(0.4)
        self.write_parameters(self.photometry_parameters)

    def write_parameters(self, phot_params):
        self.photometry_parameters = phot_params
        for k in self.write_order:
            v = self.photometry_parameters[k]
            self.write(v)
        for k in self.write_order:
            v = self.photometry_parameters[k]
            print(f'Writing {k}: {v}')
        # self.device.flush()

    def write(self, data):

        if isinstance(data, float):
            write_data = struct.pack('<f', np.single(data))
        elif isinstance(data, int):
            write_data = struct.pack('<H', np.uint16(data))
        elif data.dtype == np.uint16:
            write_data = struct.pack('<H', data)
        elif data.dtype == np.single:
            write_data = struct.pack('<f', data)

        self.device.write(write_data)

    def read(self):
        return self.device.readline()


def dict_to_h5(h5, dic, root='/'):
    '''
    Save an dict to an h5 file, mounting at root.
    Keys are mapped to group names recursively.
    Parameters
    ----------
    h5 (h5py.File instance): h5py.file object to operate on
    dic (dict): dictionary of data to write
    root (string): group on which to add additional groups and datasets
    Returns
    -------
    None
    '''

    if not root.endswith('/'):
        root = root + '/'

    for key, item in dic.items():
        dest = root + key
        try:
            if isinstance(item, (np.ndarray, np.int64, np.float64, str, bytes)):
                h5[dest] = item
            elif isinstance(item, (tuple, list)):
                h5[dest] = np.asarray(item)
            elif isinstance(item, (int, float)):
                h5[dest] = np.asarray([item])[0]
            elif item is None:
                h5.create_dataset(dest, data=h5py.Empty(dtype=h5py.special_dtype(vlen=str)))
            elif isinstance(item, dict):
                dict_to_h5(h5, item, dest)
            else:
                raise ValueError('Cannot save {} type to key {}'.format(type(item), dest))
        except Exception as e:
            print(e)
            if key != 'inputs':
                print('h5py could not encode key:', key)
