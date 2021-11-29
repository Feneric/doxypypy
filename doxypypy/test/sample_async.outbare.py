# -*- coding: utf-8 -*-
##
#An asynchronous function and an asynchronous method.
#
#Here we're testing out some straightforward Python 3 async
#examples.
#


##
#    A sample non-asynchronous function.
#
def non_asynchronous_function():
    return "Not async."

##
#    A sample asynchronous function.
#
async def asynchronous_function():
    return "Async"


##
#    A sample class with an async method.
#
#    Nothing special, just a basic Python 3 class that has an
#    async method in it.
#
class ClassWithAsyncMethod():

    ##
    #        This is a regular, non-async method.
    #
    def non_asynchronous_method(self):
        return "Not async."

    ##
    #        This is an asynchronous method.
    #
    async def asynchronous_method(self):
        return "Async"

