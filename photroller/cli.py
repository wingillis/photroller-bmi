import click
import numpy as np
from photroller.util import PhotometryController

orig_init = click.core.Option.__init__


def new_init(self, *args, **kwargs):
    orig_init(self, *args, **kwargs)
    self.show_default = True


click.core.Option.__init__ = new_init


@click.group()
def cli():
    pass


@cli.command(name="start-controller")
@click.option("--freq1", "-f1", default=150, type=np.uint16, help="Frequency for LED1")
@click.option("--freq2", "-f2", default=350, type=np.uint16, help="Frequency for LED2")
@click.option("--amp1", "-a1", default=3, type=np.single, help="Amplitude for LED1")
@click.option("--amp2", "-a2", default=1, type=np.single, help="Amplitude for LED2")
@click.option("--offset1", "-o1", default=.1, type=np.single, help="Offset for LED1")
@click.option("--offset2", "-o2", default=.1, type=np.single, help="Offset for LED2")
@click.option("--serial-port", "-s", default=None, help="Serial port of Arduino")
def generate_config(serial_port, **photometry_parameters):

    controller = PhotometryController(photometry_parameters, serial_port)

    converter = {'freq': np.uint16, 'amp': np.single, 'offset': np.single}

    while True:
        new_params = input('Update parameters (format= key: value): ')
        key, val = new_params.split(':')
        for conv_k, conv_v in converter.items():
            if conv_k in key:
                val = conv_v(val)
        photometry_parameters[key] = val
        print(photometry_parameters)
        print()
        controller.write_parameters(photometry_parameters)
        print('-'*30)
