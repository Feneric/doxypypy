## @brief Code Indentation Example
#
# @namespace sample_code_indent



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
# @par Examples
#        for a in range(2):
#            print(a)
#
# @namespace sample_code_indent.myfunction

def myfunction(arg1, arg2, kwarg='whatever.'):
    pass
