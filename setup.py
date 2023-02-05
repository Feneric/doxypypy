#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Setup file for the doxypypy package."""

from setuptools import setup, find_packages
from os.path import dirname, join
from os import chdir

if dirname(__file__):
    chdir(dirname(__file__))

setup(
    name='doxypypy',
    version='0.8.8.7',
    description='A Doxygen filter for Python',
    long_description=open(join(dirname(__file__), 'README.rst')).read(),
    keywords='Doxygen filter Python documentation',
    author='Eric W. Brown',
    url='https://github.com/Feneric/doxypypy',
    packages=find_packages(),
    install_requires=[
        'chardet'
    ],
    test_suite='doxypypy.test.test_doxypypy',
    extras_require={
        'testing': ['pytest', 'tox'],
    },
    entry_points={
        'console_scripts': [
            'doxypypy = doxypypy.doxypypy:main'
        ]
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Environment :: Plugins',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
        'Natural Language :: English',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: POSIX',
        'Operating System :: Unix',
        'Programming Language :: Python',
        'Topic :: Software Development :: Documentation'
    ]
)
