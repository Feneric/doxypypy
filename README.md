doxypypy
========

A more Pythonic version of doxypy, a Doxygen filter for Python.

# Intent

[Doxygen](http://www.stack.nl/~dimitri/doxygen/) has limited support for Python.
It recognizes Python comments, but otherwise treats the language as being more
or less like Java.  It doesn't understand basic Python syntax constructs like
docstrings, keyword arguments, generators, nested functions, decorators, or
lambda expressions.  It likewise doesn't understand conventional constructs like
doctests or ZOPE-style interfaces.  It does however support inline filters that
can be used to make input source code a little more like what it's expecting.

The excellent [doxypy](https://github.com/0xCAFEBABE/doxypy) makes it possible
to embed Doxygen commands in Python docstrings, and have those docstrings
converted to Doxygen-recognized comments on the fly per Doxygen's regular
input filtering process.  It however does not address any of the other
previously mentioned areas of difficulty.

This project started off as a fork of doxypy but quickly became quite distinct.
It shares little (if any) of the same code at this point (but maintains the
original license just in case).  It is meant to support all the same command
line options as doxypy, but handle additional Python syntax beyond docstrings.

# Additional Syntax Supported

Python can have functions and classes within both functions and classes.
Doxygen best understands this concept via its notion of namespaces.  This filter
thus can supply Doxygen tags marking namespaces on every function and class.
This addresses the issue of Doxygen merging inner functions' documentation with
the documentation of the parent.

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
in [PEP 257](http://www.python.org/dev/peps/pep-0257/) or that generally follow
the stricter [Google Python Style Guide](http://google-styleguide.googlecode.com/svn/trunk/pyguide.html?showone=Comments#Comments)
will get appropriate Doxygen tags automatically added.
