#!/usr/bin/env python
# -*- coding: utf-8 -*-
##
#Test some restrucutred Text docstrings.
#
#It should process them into valid doxygen tags and formatings.
#

import sys

##
#    ExampleClass just for testing rst docstrings.
#
#    It's meant to be processed as regular text.
#
#        with literal code section
#           which is just        treated as is.
#           by doxygen.
#        until it ends on former paragraph indent.
#
#    Here is a new regular text.
#
#
class ExampleClass:
    ##
    #         Just inits a ExampleClass object.
    #
    def __init__(self):
        self.member = "Value"

    ##
    #        And here is a typical method.
    #
    #        With parameters
    #
    #        :param new: Which holds some random string.
    #        :type new: str
    #        :param other: For random number input
    #        :type other: int
    #        :param yet_another: Yet another number for input.
    #        :type yet_another: int, optional paramter, Default = 0
    #
    #        :return: Just some result as example number
    #        :rtype: int
    #
    def methodExample(self, new : str, other: int, yet_another : int = 0) -> int:
        self.member = "NewValue" + new
        return 2 + other


##
#    This function should work even on module level.
#
#    :param [in] arg: <int> Some thingumabob to this function. with alternative type description.
#    :return: Nothing
#
#    But describe a table of other things.
#
#    ===============  =========    ========
#     With entries       Heads       Cols
#    ===============  =========    ========
#      1. Entry         Big          First
#      2. Entry        Smaller       Third
#      3. Entry        Rare           Even
#    ===============  =========    ========
#
#    And other textes too.
#
def generic_function(arg : int):
    print(arg)
    a = arg
    arg = a


