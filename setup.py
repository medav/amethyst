from setuptools import setup

setup(
    name = 'amethyst',
    packages = [
        'amethyst',
        'amethyst.backend',
        'amethyst.cache',
        'amethyst.frontend',
        'amethyst.management',
        'amethyst.support'
    ],
    scripts = [
        'bin/amethyst-build'
    ],
    version = '0.1',
    description = '5-stage processor implemented in Atlas HDL',
    author = 'Michael Davies',
    author_email = 'michaelstoby@gmail.com',
    url = 'https://github.com/medav/amethyst',
    download_url = '',
    keywords = ['verilog', 'hdl', 'fpga', 'hardware'],
    classifiers = [],
)
