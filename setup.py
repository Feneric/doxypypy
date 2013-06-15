#!/usr/bin/env python
# -*- coding: utf-8 -*-
from setuptools import setup, find_packages
from os.path import dirname
from os import chdir

chdir(dirname(__file__))


setup(
    name='doxypypy',
    version='0.5',
    description='A Doxygen filter for Python',
    long_description=open('README.md').read(),
    author='Eric W. Brown',
    url='https://github.com/Feneric/doxypypy',
    packages=find_packages(),
    test_suite='doxypypy.test.test_doxypypy',
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
