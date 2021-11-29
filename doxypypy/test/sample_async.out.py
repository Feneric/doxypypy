# -*- coding: utf-8 -*-
## @brief An asynchronous function and an asynchronous method.
#
#Here we're testing out some straightforward Python 3 async
#examples.
#
# @namespace sample_async



## @brief     A sample non-asynchronous function.
#
# @namespace sample_async.non_asynchronous_function

def non_asynchronous_function():
    return "Not async."

## @brief     A sample asynchronous function.
#
# @namespace sample_async.asynchronous_function

async def asynchronous_function():
    return "Async"


## @brief     A sample class with an async method.
#
#    Nothing special, just a basic Python 3 class that has an
#    async method in it.
#
# @namespace sample_async.ClassWithAsyncMethod

class ClassWithAsyncMethod():

    ## @brief         This is a regular, non-async method.
    #
    # @namespace sample_async.ClassWithAsyncMethod.non_asynchronous_method

    def non_asynchronous_method(self):
        return "Not async."

    ## @brief         This is an asynchronous method.
    #
    # @namespace sample_async.ClassWithAsyncMethod.asynchronous_method

    async def asynchronous_method(self):
        return "Async"

