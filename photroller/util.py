import click
import serial
import struct
import numpy as np
import time
from serial.tools import list_ports


# from https://stackoverflow.com/questions/46358797/
# python-click-supply-arguments-and-options-from-a-configuration-file
def command_with_config(config_file_param_name):

    class custom_command_class(click.Command):

        def invoke(self, ctx):
            # grab the config file
            config_file = ctx.params[config_file_param_name]
            param_defaults = {p.human_readable_name: p.default for p in self.params
                              if isinstance(p, click.core.Option)}
            param_defaults = {k: tuple(v) if type(v) is list else v for k, v in param_defaults.items()}
            param_cli = {k: tuple(v) if type(v) is list else v for k, v in ctx.params.items()}

            if config_file is not None:
                with open(config_file) as f:
                    config_data = dict(yaml.load(f, yaml.RoundTripLoader))
                config_data = {k: tuple(v) if isinstance(v, yaml.comments.CommentedSeq) else v
                               for k, v in config_data.items() if k in param_defaults.keys()}

                # find differences btw config and param defaults
                diffs = set(param_defaults.items()) ^ set(param_cli.items())

                # combine defaults w/ config data
                combined = {**param_defaults, **config_data}

                # update cli params that are non-default
                keys = [d[0] for d in diffs]
                for k in set(keys):
                    combined[k] = ctx.params[k]

                ctx.params = combined

            return super().invoke(ctx)

    return custom_command_class


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


def init_serial_port(serial_port=None, baudrate=2000000, parity=serial.PARITY_NONE,
                     stopbits=serial.STOPBITS_ONE, bytesize=serial.EIGHTBITS,
                     write_timeout=0):

    if serial_port is None:
        serial_port = select_serial_port()

    serial_device = serial.Serial(serial_port,
                                  baudrate=baudrate,
                                  parity=parity,
                                  stopbits=stopbits,
                                  bytesize=bytesize,
                                  writeTimeout=write_timeout)
    return serial_device


class PhotometryController():

    def __init__(self, photometry_parameters, serial_port=None, **kwargs):
        # initialize serial port, write in the photometry parameters

        self.device = init_serial_port(serial_port, **kwargs)

        self.photometry_parameters = photometry_parameters

        for k, v in self.photometry_parameters.items():
            print('Writing {}: {}'.format(k, v))
            self.write(v)

        self.device.flush()

        while True:
            read_data = self.device.readline()
            if read_data is None:
                break
            else:
                print('{}'.format(read_data))

    def write(self, data):

        if data.dtype == np.int16:
            write_data = struct.pack('<H', data)
        elif data.dtype == np.single:
            write_data = struct.pack('<f', data)

        self.device.write(write_data)

    def read(self):
        return self.device.readline()





    def read(self, data):
        pass
