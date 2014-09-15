import os
from setuptools import setup, find_packages

def read(*paths):
    """Build a file path from *paths* and return the contents."""
    with open(os.path.join(*paths), 'r') as f:
        return f.read()

setup(
    name = "airypi-rpi",
    version = "0.0.1",
    description = "The airypi client for Raspberry Pi",
    long_description=(read('README.md')),
    url = "https://www.airypi.com/docs/",
    license = "GPL v3",
    author = "airypi",
    author_email = "dev@airypi.com",
    packages=find_packages(exclude=['tests*']),
    keywords = ["raspberry", "pi", 'client', 'server', 'cloud', 'library', 'airypi', 'control', 'io', 'gpio', 'serial', 'smbus', 'spi', 'i2c'],
    include_package_data=True,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Programming Language :: Python :: 2.7",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
    ],
    install_requires = ['gevent', 'requests', 'RPi.GPIO', 'pyserial', 'backports.ssl_match_hostname'],
    entry_points = {
        'console_scripts': ['airypi = airypi_rpi.commandline:cmd_run']
    }
)