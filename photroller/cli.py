import click
import numpy as np
from photroller.util import PhotometryController, command_with_config

orig_init = click.core.Option.__init__


def new_init(self, *args, **kwargs):
    orig_init(self, *args, **kwargs)
    self.show_default = True


click.core.Option.__init__ = new_init


@click.group()
def cli():
    pass


@cli.command(name="start-controller", cls=command_with_config('config_file'))
@click.option("--freq1", "-f1", default=150, type=np.int16, help="Frequency for LED1")
@click.option("--freq2", "-f2", default=350, type=np.int16, help="Frequency for LED2")
@click.option("--amp1", "-a1", default=3, type=np.single, help="Amplitude for LED1")
@click.option("--amp2", "-a2", default=1, type=np.single, help="Amplitude for LED2")
@click.option("--offset1", "-o1", default=.1, type=np.single, help="Offset for LED1")
@click.option("--offset2", "-o2", default=.1, type=np.single, help="Offset for LED2")
@click.option("--serial-port", "-s", default=None, help="Serial port of Arduino")
@click.option("--config-file", type=click.Path())
def generate_config(freq1, freq2, amp1, amp2, offset1, offset2, serial_port, config_file):

    photometry_parameters = {
        'freq1': freq1,
        'freq2': freq2,
        'amp1': amp1,
        'amp2': amp2,
        'offset1': offset1,
        'offset2': offset2
    }

    controller = PhotometryController(photometry_parameters, serial_port)
