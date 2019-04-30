doxypypy
========

*A more Pythonic version of doxypy, a Doxygen filter for Python.*

Intent
------

For now Doxygen_ has limited support for Python.  It recognizes Python comments,
but otherwise treats the language as being more or less like Java.  It doesn't
understand basic Python syntax constructs like docstrings, keyword arguments,
generators, nested functions, decorators, or lambda expressions.  It likewise
doesn't understand conventional constructs like doctests or ZOPE-style
interfaces.  It does however support inline filters that can be used to make
input source code a little more like what it's expecting.

The excellent doxypy_ makes it possible to embed Doxygen commands in Python
docstrings, and have those docstrings converted to Doxygen-recognized comments
on the fly per Doxygen's regular input filtering process.  It however does not
address any of the other previously mentioned areas of difficulty.

This project started off as a fork of doxypy but quickly became quite distinct.
It shares little (if any) of the same code at this point (but maintains the
original license just in case).  It is meant to support all the same command
line options as doxypy, but handle additional Python syntax beyond docstrings.

Additional Syntax Supported
---------------------------

Python can have functions and classes within both functions and classes.
Doxygen best understands this concept via its notion of namespaces.  This filter
thus can supply Doxygen tags marking namespaces on every function and class.
This addresses the issue of Doxygen merging inner functions' documentation with
the documentation of the parent.

Python class members whose names begin with a double-underscore are mangled
and kept private by the language.  Doxygen does not understand this natively
yet, so this filter additionally provides Doxygen tags to label such variables
as private.

Python frequently embeds doctests within docstrings.  This filter makes it
trivial to mark off such sections of the docstring so they get displayed as
code.

ZOPE-style interfaces overload class definitions to be interface definitions,
use embedded variable assignments to identify attributes, and use specific
function calls to indicate interface adherence.  Furthermore, they frequently
don't have any code beyond their docstrings, so naively removing docstrings
would result in broken Python.  This filter has basic understanding of these
interfaces and treats them accordingly, supplying Doxygen tags as appropriate.

Fundamentally Python docstrings are meant for humans and not machines, and ought
not to have special mark-up beyond conventional structured text.  This filter
heuristically examines Python docstrings, and ones like the sample for complex
in `PEP 257`_ or that generally follow the stricter `Google Python Style Guide`_
will get appropriate Doxygen tags automatically added.

How It Works
------------

This project takes a radically different approach than doxypy.  Rather than use
regular expressions tied to a state machine to figure out syntax, Python's own
Abstract Syntax Tree module is used to extract items of interest.  If the
`autobrief` option is enabled, docstrings are parsed via a set of regular
expressions and a producer / consumer pair of coroutines.

Example
-------

This filter will correctly process code like the following working (albeit
contrived) example:

.. code-block:: python

    def myfunction(arg1, arg2, kwarg='whatever.'):
        """
        Does nothing more than demonstrate syntax.

        This is an example of how a Pythonic human-readable docstring can
        get parsed by doxypypy and marked up with Doxygen commands as a
        regular input filter to Doxygen.

        Args:
            arg1:   A positional argument.
            arg2:   Another positional argument.

        Kwargs:
            kwarg:  A keyword argument.

        Returns:
            A string holding the result.

        Raises:
            ZeroDivisionError, AssertionError, & ValueError.

        Examples:
            >>> myfunction(2, 3)
            '5 - 0, whatever.'
            >>> myfunction(5, 0, 'oops.')
            Traceback (most recent call last):
                ...
            ZeroDivisionError: integer division or modulo by zero
            >>> myfunction(4, 1, 'got it.')
            '5 - 4, got it.'
            >>> myfunction(23.5, 23, 'oh well.')
            Traceback (most recent call last):
                ...
            AssertionError
            >>> myfunction(5, 50, 'too big.')
            Traceback (most recent call last):
                ...
            ValueError
        """
        assert isinstance(arg1, int)
        if arg2 > 23:
            raise ValueError
        return '{0} - {1}, {2}'.format(arg1 + arg2, arg1 / arg2, kwarg)

There are a few points to note:

1.  No special tags are used.  Best practice human-readable section headers
are enough.

2.  Some flexibility is allowed.  Most common names for sections are accepted,
and items and descriptions may be separated by either colons or dashes.

3.  The brief must be the first item and be no longer than one line.

4.  Everything thrown into an examples section will be treated as code, so it's
the perfect place for doctests.

Additional more comprehensive examples can be found in the test area.

Installing doxypypy
-------------------

One can use either :code:`pip` or :code:`easy_install` for installation.
Running either:

.. code-block:: shell

    pip install doxypypy

or:

.. code-block:: shell

    easy_install doxypypy

with administrator privileges should do the trick.

Previewing doxypypy Output
--------------------------

After successful installation, doxypypy can be run from the command line to
preview the filtered results with:

.. code-block:: shell

    doxypypy -a -c file.py

Typically you'll want to redirect output to a file for viewing in a text editor:

.. code-block:: shell

    doxypypy -a -c file.py > file.py.out

Invoking doxypypy from Doxygen
------------------------------

To make Doxygen run your Python code through doxypypy, set the FILTER\_PATTERNS
tag in your Doxyfile as follows:

.. code-block:: shell

    FILTER_PATTERNS        = *.py="doxypypy -a -c"

Running Doxygen as usual should now run all Python code through doxypypy.  Be
sure to carefully browse the Doxygen output the first time to make sure that
Doxygen properly found and executed doxypypy.

.. _Doxygen: http://www.stack.nl/~dimitri/doxygen/
.. _doxypy: https://github.com/Feneric/doxypy
.. _PEP 257: http://www.python.org/dev/peps/pep-0257/
.. _Google Python Style Guide: https://google.github.io/styleguide/pyguide.html?showone=Comments#Comments

