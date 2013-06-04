# -*- coding: utf-8 -*-
"""
Tests the doxypypy filter.
"""
import unittest
from collections import namedtuple
from src.doxypypy import AstWalker
from os.path import basename, splitext
from os import linesep


class TestDoxypypy(unittest.TestCase):
    """
    Define our doxypypy tests.
    """

    __Options = namedtuple('Options', 'autobrief debug fullPathNamespace')
    __dummySrc = [
        "print 'testing: one, two, three, & four' " + linesep,
        "print 'is five.'\t" + linesep
    ]
    __strippedDummySrc = linesep.join([
        "print 'testing: one, two, three, & four'",
        "print 'is five.'"
    ])

    def setUp(self):
        """
        Sets up a temporary AST for use with our unit tests.
        """
        options = TestDoxypypy.__Options(True, False, 'dummy')
        self.dummyWalker = AstWalker(TestDoxypypy.__dummySrc,
                                     options, 'dummy.py')

    def test_stripOutAnds(self):
        """
        Test the stripOutAnds method.
        """
        testPairs = {
            'This and that.': 'This that.',
            'This & that.': 'This that.',
            'This, that, & more.': 'This, that, more.',
            'This and that & etc.': 'This that etc.',
            'Handy.': 'Handy.',
            'This, that, &c.': 'This, that, &c.'
        }
        for pair in testPairs.items():
            self.assertEqual(self.dummyWalker._stripOutAnds(pair[0]), pair[1])

    def test_getFullPathName(self):
        """
        Test the getFullPathName method.
        """
        self.assertEqual(self.dummyWalker._getFullPathName([('one', 'class')]),
                         [('dummy', 'module'), ('one', 'class')])

    def test_getLines(self):
        """
        Test the getLines method.
        """
        self.assertEqual(self.dummyWalker.getLines(),
                         TestDoxypypy.__strippedDummySrc)

    def test_parseLines(self):
        """
        Test the parseLines method.
        """
        # For our sample data parseLines doesn't change anything.
        self.dummyWalker.parseLines()
        self.assertEqual(self.dummyWalker.getLines(),
                         TestDoxypypy.__strippedDummySrc)

    @staticmethod
    def readAndParseFile(inFilename, options):
        """
        Helper function to read and parse a given file and create an AST walker.
        """
        # Read contents of input file.
        inFile = open(inFilename)
        lines = inFile.readlines()
        inFile.close()
        # Create the abstract syntax tree for the input file.
        testWalker = AstWalker(lines, options, inFilename)
        testWalker.parseLines()
        # Output the modified source.
        return testWalker.getLines()

    def compareAgainstGoldStandard(self, inFilename, options):
        """
        Read and process the input file and compare its output against the gold
        standard.
        """
        output = self.readAndParseFile(inFilename, options)
        goldFilename = splitext(inFilename)[0] + '.out.py'
        goldFile = open(goldFilename)
        goldContentLines = goldFile.readlines()
        goldFile.close()
        # We have to go through some extra processing to ensure line endings
        # match across platforms.
        goldContent = linesep.join(line.rstrip() for line in goldContentLines)
        self.assertEqual(output, goldContent)

    def test_pep(self):
        """
        Test the basic example included in PEP 257.
        """
        sampleName = 'test/sample_complex.py'
        sampleNameBase = splitext(basename(sampleName))[0]
        options = TestDoxypypy.__Options(True, False, sampleNameBase)
        self.compareAgainstGoldStandard(sampleName, options)


if __name__ == '__main__':
    # When executed from the command line, run all the tests via unittest.
    from unittest import main
    main()
