# -*- coding: utf-8 -*-
"""
An asynchronous function and an asynchronous method.

Here we're testing out some straightforward Python 3 async
examples.
"""


def non_asynchronous_function():
    """
    A sample non-asynchronous function.
    """
    return "Not async."

async def asynchronous_function():
    """
    A sample asynchronous function.
    """
    return "Async"


class ClassWithAsyncMethod():
    """
    A sample class with an async method.

    Nothing special, just a basic Python 3 class that has an
    async method in it.
    """

    def non_asynchronous_method(self):
        """
        This is a regular, non-async method.
        """
        return "Not async."

    async def asynchronous_method(self):
        """
        This is an asynchronous method.
        """
        return "Async"

