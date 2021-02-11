from setuptools import setup

setup(
    name='photroller',
    author='Jeff Markowitz, Winthrop Gillis',
    description='To boldly go where no mouse has gone before',
    version='0.002a',
    platforms=['mac', 'unix'],
    install_requires=['h5py', 'matplotlib', 'scipy',
                      'numpy', 'click', 'pyserial',
                      'ruamel.yaml'],
    python_requires='>=3.6',
    entry_points={'console_scripts': ['photroller = photroller.cli:cli']}
)
