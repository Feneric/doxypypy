#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests the doxypypy filter.

These tests may all be executed by running tox from the
root level of the project.
"""
import unittest
from argparse import Namespace
from os import linesep, sep
from os.path import basename, splitext
from ast import parse
from codecs import open as codecsOpen
from sys import version_info

from pytest import mark

from ..doxypypy import AstWalker


class TestDoxypypy(unittest.TestCase):
    """
    Define our doxypypy tests.
    """
    maxDiff = None

    __Options = Namespace(
        autobrief=True,
        autocode=True,
        debug=False,
        fullPathNamespace='dummy',
        topLevelNamespace='dummy',
        tablength=4,
        filename='dummy.py',
        object_respect=False,
        equalIndent=False,
        keepDecorators=False
    )
    __dummySrc = [
        "print('testing: one, two, three, & four') " + linesep,
        "print('is five.')\t" + linesep
    ]
    __strippedDummySrc = linesep.join([
        "print('testing: one, two, three, & four')",
        "print('is five.')"
    ])
    __sampleBasics = [
        {
            'name': 'onelinefunction',
            'visitor': 'visit_FunctionDef',
            'inputCode': '''def testFunctionOneLine():
                """Here is the brief."""''',
            'expectedOutput': [
                '## @brief Here is the brief.\n# @namespace dummy.testFunctionOneLine',
                'def testFunctionOneLine():'
            ]
        }, {
            'name': 'onelineclass',
            'visitor': 'visit_ClassDef',
            'inputCode': '''class testClassOneLine(object):
                """Here is the brief."""''',
            'expectedOutput': [
                '## @brief Here is the brief.\n# @namespace dummy.testClassOneLine',
                'class testClassOneLine():'
            ]
        }, {
            'name': 'basicfunction',
            'visitor': 'visit_FunctionDef',
            'inputCode': '''def testFunctionBrief():
                """Here is the brief.

                Here is the body. Unlike the brief
                it has multiple lines."""''',
            'expectedOutput': [
                '## @brief Here is the brief.',
                '#',
                '#                Here is the body. Unlike the brief',
                '#                it has multiple lines.\n# @namespace dummy.testFunctionBrief',
                'def testFunctionBrief():'
            ]
        }, {
            'name': 'basicclass',
            'visitor': 'visit_ClassDef',
            'inputCode': '''class testClassBrief(object):
                """Here is the brief.

                Here is the body. Unlike the brief
                it has multiple lines."""''',
            'expectedOutput': [
                '## @brief Here is the brief.',
                '#',
                '#                Here is the body. Unlike the brief',
                '#                it has multiple lines.\n# @namespace dummy.testClassBrief',
                'class testClassBrief():'
            ]
        }, {
            'name': 'basicfunctionnobrief',
            'visitor': 'visit_FunctionDef',
            'inputCode': '''def testFunctionNoBrief():
                """Here is the body. It's not a brief as
                it has multiple lines."""''',
            'expectedOutput': [
                "##Here is the body. It's not a brief as",
                '#                it has multiple lines.\n# @namespace dummy.testFunctionNoBrief',
                'def testFunctionNoBrief():'
            ]
        }, {
            'name': 'basicclassnobrief',
            'visitor': 'visit_ClassDef',
            'inputCode': '''class testClassNoBrief(object):
                """Here is the body. It's not a brief as
                it has multiple lines."""''',
            'expectedOutput': [
                "##Here is the body. It's not a brief as",
                '#                it has multiple lines.\n# @namespace dummy.testClassNoBrief',
                'class testClassNoBrief():'
            ]
        }
    ]
    __sampleArgs = [
        {
            'name': 'onearg',
            'visitor': 'visit_FunctionDef',
            'inputCode': '''def testFunctionArg(arg):
                """Here is the brief.
                Args:
                arg -- a test argument."""''',
            'expectedOutput': [
                '## @brief Here is the brief.',
                '#',
                '# @param\t\targ\ta test argument.\n# @namespace dummy.testFunctionArg',
                'def testFunctionArg(arg):'
            ]
        }, {
            'name': 'multipleargs',
            'visitor': 'visit_FunctionDef',
            'inputCode': '''def testFunctionArgs(arg1, arg2, arg3):
                """Here is the brief.
                Arguments:
                arg1: a test argument.
                arg2: another test argument.
                arg3: yet another test argument."""''',
            'expectedOutput': [
                '## @brief Here is the brief.',
                '#',
                '# @param\t\targ1\ta test argument.',
                '# @param\t\targ2\tanother test argument.',
                '# @param\t\targ3\tyet another test argument.\n# @namespace dummy.testFunctionArgs',
                'def testFunctionArgs(arg1, arg2, arg3):'
            ]
        }, {
            'name': 'multiplelineargs',
            'visitor': 'visit_FunctionDef',
            'inputCode': '''def testFunctionArgsMulti(
                        arg1,
                        arg2,
                        arg3
                    ):
                """Here is the brief.
                Arguments:
                arg1: a test argument.
                arg2: another test argument.
                arg3: yet another test argument."""''',
            'expectedOutput': [
                '## @brief Here is the brief.',
                '#',
                '# @param\t\targ1\ta test argument.',
                '# @param\t\targ2\tanother test argument.',
                '# @param\t\targ3\tyet another test argument.\n# @namespace dummy.testFunctionArgsMulti',
                'def testFunctionArgsMulti(',
                '                        arg1,',
                '                        arg2,',
                '                        arg3',
                '                    ):'
            ]
        }
    ]
    __sampleAttrs = [
        {
            'name': 'oneattr',
            'visitor': 'visit_ClassDef',
            'inputCode': '''class testClassAttr(object):
                """Here is the brief.
                Attributes:
                attr -- a test attribute."""''',
            'expectedOutput': [
                '## @brief Here is the brief.',
                '#\n# @namespace dummy.testClassAttr',
                'class testClassAttr():',
                '\n## @property\t\tattr\n# a test attribute.'
            ]
        }, {
            'name': 'multipleattrs',
            'visitor': 'visit_ClassDef',
            'inputCode': '''class testClassArgs(object):
                """Here is the brief.
                Attributes:
                attr1: a test attribute.
                attr2: another test attribute.
                attr3: yet another test attribute."""''',
            'expectedOutput': [
                '## @brief Here is the brief.',
                '#\n# @namespace dummy.testClassArgs',
                'class testClassArgs():',
                '\n## @property\t\tattr1\n# a test attribute.',
                '\n## @property\t\tattr2\n# another test attribute.',
                '\n## @property\t\tattr3\n# yet another test attribute.'
            ]
        }
    ]
    __sampleReturns = [
        {
            'name': 'returns',
            'visitor': 'visit_FunctionDef',
            'inputCode': '''def testFunctionReturns():
                """Here is the brief.
                Returns:
                Good stuff."""''',
            'expectedOutput': [
                '## @brief Here is the brief.',
                '# @return',
                '#                Good stuff.\n# @namespace dummy.testFunctionReturns',
                'def testFunctionReturns():'
            ]
        }, {
            'name': 'yields',
            'visitor': 'visit_FunctionDef',
            'inputCode': '''def testFunctionYields():
                """Here is the brief.
                Yields:
                Good stuff."""''',
            'expectedOutput': [
                '## @brief Here is the brief.',
                '# @return',
                '#                Good stuff.\n# @namespace dummy.testFunctionYields',
                'def testFunctionYields():'
            ]
        }
    ]
    __sampleRaises = [
        {
            'name': 'oneraises',
            'visitor': 'visit_FunctionDef',
            'inputCode': '''def testFunctionRaisesOne():
                """Here is the brief.
                Raises:
                MyException: bang bang a boom."""''',
            'expectedOutput': [
                '## @brief Here is the brief.',
                '#',
                '# @exception\t\tMyException\tbang bang a boom.\n# @namespace dummy.testFunctionRaisesOne',
                'def testFunctionRaisesOne():'
            ]
        }, {
            'name': 'multipleraises',
            'visitor': 'visit_FunctionDef',
            'inputCode': '''def testFunctionRaisesMultiple():
                """Here is the brief.
                Raises:
                MyException1 -- bang bang a boom.
                MyException2 -- crash.
                MyException3 -- splatter."""''',
            'expectedOutput': [
                '## @brief Here is the brief.',
                '#',
                '# @exception\t\tMyException1\tbang bang a boom.',
                '# @exception\t\tMyException2\tcrash.',
                '# @exception\t\tMyException3\tsplatter.\n# @namespace dummy.testFunctionRaisesMultiple',
                'def testFunctionRaisesMultiple():'
            ]
        }, {
            'name': 'oneraisesclass',
            'visitor': 'visit_ClassDef',
            'inputCode': '''class testClassRaisesOne(object):
                """Here is the brief.
                Raises:
                MyException: bang bang a boom."""''',
            'expectedOutput': [
                '## @brief Here is the brief.',
                '#',
                '# @exception\t\tMyException\tbang bang a boom.\n# @namespace dummy.testClassRaisesOne',
                'class testClassRaisesOne():'
            ]
        }, {
            'name': 'multipleraisesclass',
            'visitor': 'visit_ClassDef',
            'inputCode': '''class testClassRaisesMultiple(object):
                """Here is the brief.
                Raises:
                MyException1 -- bang bang a boom.
                MyException2 -- crash.
                MyException3 -- splatter."""''',
            'expectedOutput': [
                '## @brief Here is the brief.',
                '#',
                '# @exception\t\tMyException1\tbang bang a boom.',
                '# @exception\t\tMyException2\tcrash.',
                '# @exception\t\tMyException3\tsplatter.\n# @namespace dummy.testClassRaisesMultiple',
                'class testClassRaisesMultiple():'
            ]
        }
    ]
    __linesep_for_source = '''
'''
    """
    detect the line ending within test string constants above

     -> as git can check out \n on windows too
     it's git configuration dependent if these line endings are OS specific
     or just \n.
    """

    def setUp(self):
        """
        Sets up a temporary AST for use with our unit tests.
        """
        self.options = TestDoxypypy.__Options
        self.dummyWalker = AstWalker(TestDoxypypy.__dummySrc, self.options)

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

    def test_endCodeIfNeeded(self):
        """
        Test the endCodeIfNeeded method.
        """
        testPairs = {
            ('unu', False): ('unu', False),
            ('du', True): ('# @endcode' + linesep + 'du', False),
            ('tri kvar', True): ('# @endcode' + linesep + 'tri kvar', False),
            ('kvin  \t', True): ('# @endcode' + linesep + 'kvin', False)
        }
        for pair in testPairs.items():
            self.assertEqual(self.dummyWalker._endCodeIfNeeded(*pair[0]),
                             pair[1])

    def test_checkIfCode(self):
        """
        Tests the checkIfCode method on the code side.
        """
        testPairs = [
            (
                [
                    'This is prose, not code.',
                    '...',
                    '>>> print("Now we have code.")'
                ], [
                    'This is prose, not code.',
                    '...{0}# @code{0}'.format(linesep),
                    '>>> print("Now we have code.")'
                ]
            ), (
                [
                    'This is prose, not code.',
                    'Traceback: frobnotz failure',
                    '>>> print("Now we have code.")'
                ], [
                    'This is prose, not code.',
                    'Traceback: frobnotz failure{0}# @code{0}'.format(linesep),
                    '>>> print("Now we have code.")'
                ]
            ), (
                [
                    'This is prose, not code.',
                    '>>> print("Now we have code.")'
                ], [
                    'This is prose, not code.{0}# @code{0}'.format(linesep),
                    '>>> print("Now we have code.")'
                ]
            ), (
                [
                    'This is prose, not code.',
                    'This is still prose, not code.',
                    'Another line of prose to really be sure.',
                    'Ditto again, still prose.',
                    '>>> print("Now we have code.")'
                ], [
                    'This is prose, not code.',
                    'This is still prose, not code.',
                    'Another line of prose to really be sure.',
                    'Ditto again, still prose.{0}# @code{0}'.format(linesep),
                    '>>> print("Now we have code.")'
                ]
            )
        ]
        for testLines, outputLines in testPairs:
            inCodeBlockObj = [False]
            codeChecker = self.dummyWalker._checkIfCode(inCodeBlockObj)
            for lineNum, line in enumerate(testLines):
                codeChecker.send((line, testLines, lineNum))
            self.assertEqual(testLines, outputLines)

    def test_checkIfProse(self):
        """
        Tests the checkIfCode method on the prose side.
        """
        testPairs = [
            (
                [
                    '...',
                    'This is prose, not code.'
                ], [
                    '...{0}# @endcode{0}'.format(linesep),
                    'This is prose, not code.'
                ]
            ), (
                [
                    'Traceback: frobnotz error',
                    'This is prose, not code.'
                ], [
                    'Traceback: frobnotz error{0}# @endcode{0}'.format(linesep),
                    'This is prose, not code.'
                ]
            ), (
                [
                    '>>> print("Code.")',
                    'This is prose, not code.'
                ], [
                    '>>> print("Code."){0}# @endcode{0}'.format(linesep),
                    'This is prose, not code.'
                ]
            ), (
                [
                    '>>> myVar = 23',
                    '>>> print(myVar)',
                    '',
                    'This is prose, not code.'
                ], [
                    '>>> myVar = 23',
                    '>>> print(myVar)',
                    '{0}# @endcode{0}'.format(linesep),
                    'This is prose, not code.'
                ]
            ), (
                [
                    '>>> myVar = 23',
                    '>>> print(myVar)',
                    '>>> myVar += 5',
                    '>>> print(myVar)',
                    '',
                    'This is prose, not code.'
                ], [
                    '>>> myVar = 23',
                    '>>> print(myVar)',
                    '>>> myVar += 5',
                    '>>> print(myVar)',
                    '{0}# @endcode{0}'.format(linesep),
                    'This is prose, not code.'
                ]
            )
        ]
        for testLines, outputLines in testPairs:
            inCodeBlockObj = [True]
            proseChecker = self.dummyWalker._checkIfCode(inCodeBlockObj)
            for lineNum, line in enumerate(testLines):
                proseChecker.send((line, testLines, lineNum))
            self.assertEqual(testLines, outputLines)

    def test_checkMemberName(self):
        """
        Test the checkMemberName method.
        """
        testPairs = {
            'public': None,
            '_protected': 'protected',
            '_stillProtected_': 'protected',
            '__private': 'private',
            '__stillPrivate_': 'private',
            '__notPrivate__': None
        }
        for pair in testPairs.items():
            self.assertEqual(self.dummyWalker._checkMemberName(pair[0]),
                             pair[1])

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

    def snippetComparison(self, sampleSnippets):
        """
        Compare docstring parsing for a list of code snippets.
        """
        options_name = self.options.filename
        for snippetTest in sampleSnippets:
            self.options.filename = snippetTest['name'] + '.py'
            testWalker = AstWalker(snippetTest['inputCode'].split(self.__linesep_for_source),
                                   self.options)
            funcAst = parse(snippetTest['inputCode'])
            getattr(testWalker, snippetTest['visitor'])(funcAst.body[0])
            testWalker.lines[:] = [line.replace(linesep, self.__linesep_for_source)  for line in testWalker.lines]
            self.assertEqual(testWalker.lines, snippetTest['expectedOutput'])
        self.options.filename = options_name

    def test_sampleBasics(self):
        """
        Tests the proper handling of basic docstrings.
        """
        self.snippetComparison(TestDoxypypy.__sampleBasics)

    def test_sampleArgs(self):
        """
        Tests the proper handling of arguments in function docstrings.
        """
        self.snippetComparison(TestDoxypypy.__sampleArgs)

    def test_sampleAttrs(self):
        """
        Tests the proper handling of attributes in class docstrings.
        """
        self.snippetComparison(TestDoxypypy.__sampleAttrs)

    def test_sampleReturns(self):
        """
        Tests the proper handling of returns and yields in function docstrings.
        """
        self.snippetComparison(TestDoxypypy.__sampleReturns)

    def test_sampleRaises(self):
        """
        Tests the proper handling of raises in function and class docstrings.
        """
        self.snippetComparison(TestDoxypypy.__sampleRaises)

    @staticmethod
    def readAndParseFile(options, encoding="ASCII"):
        """
        Helper function to read and parse a given file and create an AST walker.
        """
        inFilename = options.filename
        # Read contents of input file.
        if encoding == 'ASCII':
            inFile = open(inFilename)
        else:
            inFile = codecsOpen(inFilename, encoding=encoding)
        lines = inFile.readlines()
        inFile.close()
        # Create the abstract syntax tree for the input file.
        testWalker = AstWalker(lines, options)
        testWalker.parseLines()
        # Output the modified source.
        return testWalker.getLines()

    def compareAgainstGoldStandard(self, inFilename, encoding="ASCII", equalIndent=False):
        """
        Compare the results against expectations.

        Read and process the input file and compare its output against the gold
        standard.
        """
        inFilenameBase = splitext(basename(inFilename))[0]
        fullPathNamespace = inFilenameBase.replace(sep, '.')
        if not equalIndent:
            trials = (
                ('.out', Namespace(
                    autobrief=True,
                    autocode=True,
                    debug=False,
                    fullPathNamespace=fullPathNamespace,
                    topLevelNamespace=inFilenameBase,
                    tablength=4,
                    filename=inFilename,
                    object_respect=False,
                    equalIndent=equalIndent,
                    keepDecorators=False
                )),
                ('.outnc', Namespace(
                    autobrief=True,
                    autocode=False,
                    debug=False,
                    fullPathNamespace=fullPathNamespace,
                    topLevelNamespace=inFilenameBase,
                    tablength=4,
                    filename=inFilename,
                    object_respect=False,
                    equalIndent=equalIndent,
                    keepDecorators=False
                )),
                ('.outnn', Namespace(
                    autobrief=True,
                    autocode=True,
                    debug=False,
                    fullPathNamespace=fullPathNamespace,
                    topLevelNamespace=None,
                    tablength=4,
                    filename=inFilename,
                    object_respect=False,
                    equalIndent=equalIndent,
                    keepDecorators=False
                )),
                ('.outbare',  Namespace(
                    autobrief=False,
                    autocode=False,
                    debug=False,
                    fullPathNamespace=fullPathNamespace,
                    topLevelNamespace=None,
                    tablength=4,
                    filename=inFilename,
                    object_respect=False,
                    equalIndent=equalIndent,
                    keepDecorators=False
                ))
            )
        else:
            trials = (('.outeq',  Namespace(
                    autobrief=True,
                    autocode=True,
                    debug=False,
                    fullPathNamespace=fullPathNamespace,
                    topLevelNamespace=None,
                    tablength=4,
                    filename=inFilename,
                    object_respect=True,
                    equalIndent=equalIndent,
                    keepDecorators=False
                )),)
                
        for options in trials:
            output = self.readAndParseFile(options[1], encoding=encoding)
            goldFilename = splitext(inFilename)[0] + options[0] + '.py'
            goldFile = open(goldFilename)
            goldContentLines = goldFile.readlines()
            goldFile.close()
            # We have to go through some extra processing to ensure line
            # endings match across platforms.
            goldContent = linesep.join(line.rstrip()
                                       for line in goldContentLines)
            self.assertEqual(output.rstrip(linesep), goldContent.rstrip(linesep))

    def test_pepProcessing(self):
        """
        Test the basic example included in PEP 257.
        """
        sampleName = 'doxypypy/test/sample_pep.py'
        self.compareAgainstGoldStandard(sampleName)

    @mark.skipif(version_info < (3, 0), reason="different behavior for Python 2")
    def test_privacyProcessing(self):
        """
        Test an example with different combinations of public, protected, and private.
        """
        sampleName = 'doxypypy/test/sample_privacy.py'
        self.compareAgainstGoldStandard(sampleName)

    def test_googleProcessing(self):
        """
        Test the examples in the Google Python Style Guide.
        """
        sampleName = 'doxypypy/test/sample_google.py'
        self.compareAgainstGoldStandard(sampleName)

    def test_rawdocstringProcessing(self):
        """
        Test raw docstrings.
        """
        sampleName = 'doxypypy/test/sample_rawdocstring.py'
        self.compareAgainstGoldStandard(sampleName)

    def test_sectionsProcessing(self):
        """
        Test arbitrary sections handling.
        """
        sampleName = 'doxypypy/test/sample_sections.py'
        self.compareAgainstGoldStandard(sampleName)

    def test_docExampleProcessing(self):
        """
        Test the basic example used in the doxypypy docs.
        """
        sampleName = 'doxypypy/test/sample_docexample.py'
        self.compareAgainstGoldStandard(sampleName)

    def test_interfaceProcessing(self):
        """
        Test an example with ZOPE style interfaces.
        """
        sampleName = 'doxypypy/test/sample_interfaces.py'
        self.compareAgainstGoldStandard(sampleName)

    def test_maze(self):
        """
        Test a basic example inspired by the Commodore one-liner.
        """
        sampleName = 'doxypypy/test/sample_maze.py'
        self.compareAgainstGoldStandard(sampleName)

    def test_utf8_bom(self):
        """
        Test a trivial UTF-8 file with a BOM.
        """
        sampleName = 'doxypypy/test/sample_utf8bom.py'
        self.compareAgainstGoldStandard(sampleName, encoding="UTF-8-SIG")

    def test_utf16be_bom(self):
        """
        Test a trivial UTF-16-BE file with a BOM.
        """
        sampleName = 'doxypypy/test/sample_utf16bebom.py'
        self.compareAgainstGoldStandard(sampleName, encoding="UTF-16")

    def test_utf16le_bom(self):
        """
        Test a trivial UTF-16-LE file with a BOM.
        """
        sampleName = 'doxypypy/test/sample_utf16lebom.py'
        self.compareAgainstGoldStandard(sampleName, encoding="UTF-16")

    def test_utf32be_bom(self):
        """
        Test a trivial UTF-32-BE file with a BOM.
        """
        sampleName = 'doxypypy/test/sample_utf32bebom.py'
        self.compareAgainstGoldStandard(sampleName, encoding="UTF-32")

    def test_utf32le_bom(self):
        """
        Test a trivial UTF-32-LE file with a BOM.
        """
        sampleName = 'doxypypy/test/sample_utf32lebom.py'
        self.compareAgainstGoldStandard(sampleName, encoding="UTF-32")

    @mark.skipif(version_info < (3, 0), reason="not supported in Python 2")
    def test_rstProcessing(self):
        """
        Test the examples for rst styles.
        """
        sampleName = 'doxypypy/test/sample_rstexample.py'
        self.compareAgainstGoldStandard(sampleName)

    @mark.skipif(version_info < (3, 0), reason="not supported in Python 2")
    def test_indentProcessing(self):
        """
        Test the examples with rst and indentation reduction.
        """
        sampleName = 'doxypypy/test/sample_rstexample.py'
        self.compareAgainstGoldStandard(sampleName, equalIndent=True)

    @mark.skipif(version_info < (3, 0), reason="not supported in Python 2")
    def test_asyncProcessing(self):
        """
        Test the examples with async functions and methods.
        """
        sampleName = 'doxypypy/test/sample_async.py'
        self.compareAgainstGoldStandard(sampleName)

        
if __name__ == '__main__':
    # When executed from the command line, run all the tests via unittest.
    # e.g. from root of this repository: (this makes relative module import resolving easier ...)
    #   python -m unittest doxypypy.test.test_doxypypy
    #   python -m unittest doxypypy.test.test_doxypypy.TestDoxypypy.test_sampleArgs -v --locals
    # 
    from unittest import main
    main()
