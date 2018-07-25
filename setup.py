from setuptools import setup

setup(
    name='photroller',
    author='Jeff Markowitz',
    description='To boldly go where no mouse has gone before',
    version='0.001a',
    platforms=['mac', 'unix'],
    install_requires=['h5py', 'matplotlib', 'scipy>=0.19',
                      'numpy', 'click', 'pyserial',
                      'pyqt5', 'pyqtgraph', 'ruamel.yaml<=0.15.0'],
    python_requires='>=3.6',
    entry_points={'console_scripts': ['photroller = photroller.cli:cli']}
)
