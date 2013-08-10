#!/usr/bin/env python
# -*- coding: utf-8 -*-
## @brief Documentation Example
#
#This is the example used in the doxypypy documentation.
#It demonstrates basic docstring usage (including doctests).
#



## @brief     Does nothing more than demonstrate syntax.
#
#    This is an example of how a Pythonic human-readable docstring can
#    get parsed by doxypypy and marked up with Doxygen commands as a
#    regular input filter to Doxygen.
#
#
# @param		arg1	A positional argument.
# @param		arg2	Another positional argument.
#
#
# @param		kwarg	A keyword argument.
#
# @return
#        A string holding the result.
#
#
# @exception		ZeroDivisionError
# @exception		AssertionError
# @exception		ValueError.
#
# @b Examples
# @code
#        >>> myfunction(2, 3)
#        '5 - 0, whatever.'
#        >>> myfunction(5, 0, 'oops.')
#        Traceback (most recent call last):
#            ...
#        ZeroDivisionError: integer division or modulo by zero
#        >>> myfunction(4, 1, 'got it.')
#        '5 - 4, got it.'
#        >>> myfunction(23.5, 23, 'oh well.')
#        Traceback (most recent call last):
#            ...
#        AssertionError
#        >>> myfunction(5, 50, 'too big.')
#        Traceback (most recent call last):
#            ...
#        ValueError
# @endcode
#
# @namespace sample_docexample.myfunction

def myfunction(arg1, arg2, kwarg='whatever.'):
    assert isinstance(arg1, int)
    if arg2 > 23:
        raise ValueError
    return '{0} - {1}, {2}'.format(arg1 + arg2, arg1 / arg2, kwarg)

if __name__ == "__main__":
    import doctest
    doctest.testmod()
