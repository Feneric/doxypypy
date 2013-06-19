#!/usr/bin/env python
# -*- coding: utf-8 -*-
from setuptools import setup, find_packages
from os.path import dirname
from os import chdir

if dirname(__file__):
    chdir(dirname(__file__))


setup(
    name='doxypypy',
    version='0.5',
    description='A Doxygen filter for Python',
    long_description=open('README.md').read(),
    keywords='Doxygen filter Python documentation',
    author='Eric W. Brown',
    url='https://github.com/Feneric/doxypypy',
    packages=find_packages(),
    test_suite='doxypypy.test.test_doxypypy',
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
