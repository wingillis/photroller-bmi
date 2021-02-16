from setuptools import setup

print('Run this command in your terminal')
print('pip install git+https://github.com/pyqtgraph/pyqtgraph.git@master')

print()
print('make sure your udev rules allow you to write to connect arduinos')

setup(
    name='photroller',
    author='Jeff Markowitz, Winthrop Gillis',
    description='To boldly go where no mouse has gone before',
    version='0.002a',
    platforms=['mac', 'unix'],
    install_requires=['h5py', 'scipy', 'numpy', 'click', 'pyserial',
                      'ruamel.yaml', 'PySide6', 'labjack-ljm',
                      ],
    python_requires='>=3.6',
    entry_points={'console_scripts': ['photroller = photroller.cli:cli']}
)
