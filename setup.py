#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Note: To use the 'upload' functionality of this file, you must:
#   $ pip install twine

import io
import os
from Cython.Build import cythonize
from setuptools import find_packages, setup, Extension

# Package meta-data
NAME = 'reolink-api'
DESCRIPTION = 'Reolink API'
URL = 'https://github.com/estasney/reolink-api'
EMAIL = 'estasney@users.noreply.github.com'
AUTHOR = 'Eric Stasney'
REQUIRES_PYTHON = '>=3.9.0'
VERSION = '0.1.0'

REQUIRED = ['aiohttp', 'python-dateutil', 'toolz', 'SQLAlchemy', 'click', 'Pillow', 'Pydantic<2']

EXTRAS = {}

here = os.path.abspath(os.path.dirname(__file__))

# Import the README and use it as the long-description.
# Note: this will only work if 'README.md' is present in your MANIFEST.in file!
try:
    with io.open(os.path.join(here, 'README.md'), encoding='utf-8') as f:
        long_description = '\n' + f.read()
except FileNotFoundError:
    long_description = DESCRIPTION

about = {}
about['__version__'] = VERSION


# Where the magic happens:
setup(
    name=NAME,
    version=about['__version__'],
    description=DESCRIPTION,
    long_description=long_description,
    long_description_content_type='text/markdown',
    author=AUTHOR,
    author_email=EMAIL,
    python_requires=REQUIRES_PYTHON,
    url=URL,
    packages=find_packages(exclude=('tests',)),
    install_requires=REQUIRED,
    entry_points='''
    [console_scripts]
    reolink=reolink.cli:cli
    ''',
    extras_require=EXTRAS,
    include_package_data=False,
    data_files=[],
    license='MIT',
    classifiers=[
        # Trove classifiers
        # Full list: https://pypi.python.org/pypi?%3Aaction=list_classifiers
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.9'
    ],
    ext_modules=cythonize(
            Extension("reolink.interval.c_interval", ["reolink/interval/c_interval.pyx"]),
            annotate=True,
            compiler_directives=dict(language_level=3)
            )

)
