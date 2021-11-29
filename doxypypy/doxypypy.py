#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Filters Python code for use with Doxygen, using a syntax-aware approach.

Rather than implementing a partial Python parser with regular expressions, this
script uses Python's own abstract syntax tree walker to isolate meaningful
constructs.  It passes along namespace information so Doxygen can construct a
proper tree for nested functions, classes, and methods.  It understands bed lump
variables are by convention private.  It groks Zope-style Python interfaces.
It can automatically turn PEP 257 compliant that follow the more restrictive
Google style guide into appropriate Doxygen tags, and is even aware of
doctests.
"""
from __future__ import print_function

from ast import NodeVisitor, parse, iter_fields, AST, Name, get_docstring
from argparse import ArgumentParser
from re import compile as regexpCompile, IGNORECASE, MULTILINE
from types import GeneratorType
from sys import argv, stderr, exit as sysExit
from os.path import basename, getsize
from os import linesep, sep
from string import whitespace
from codecs import BOM_UTF8, open as codecsOpen
from codeop import compile_command
from chardet import detect


def coroutine(func):
    """Implement the coroutine pattern as a decorator."""
    def __start(*args, **kwargs):
        """Automatically calls next() on the internal generator function."""
        __cr = func(*args, **kwargs)
        next(__cr)
        return __cr
    return __start


class AstWalker(NodeVisitor):
    """
    A walker that'll recursively progress through an AST.

    Given an abstract syntax tree for Python code, walk through all the
    nodes looking for significant types (for our purposes we only care
    about module starts, class definitions, function definitions, variable
    assignments, and function calls, as all the information we want to pass
    to Doxygen is found within these constructs).  If the autobrief option
    is set, it further attempts to parse docstrings to create appropriate
    Doxygen tags.
    """

    # We have a number of regular expressions that we use.  They don't
    # vary across instances and so are compiled directly in the class
    # definition.
    __indentRE = regexpCompile(r'^(\s*)\S')
    __newlineRE = regexpCompile(r'^#', MULTILINE)
    __blanklineRE = regexpCompile(r'^\s*$')
    __docstrMarkerRE = regexpCompile(r"\s*([uUbB]*[rR]?(['\"]{3}))")
    __docstrOneLineRE = regexpCompile(r"\s*[uUbB]*[rR]?(['\"]{3})(.+)\1")

    __implementsRE = regexpCompile(r"^(\s*)(?:zope\.)?(?:interface\.)?"
                                   r"(?:module|class|directly)?"
                                   r"(?:Provides|Implements)\(\s*(.+)\s*\)",
                                   IGNORECASE)
    __classRE = regexpCompile(r"^\s*class\s+(\S+)\s*\((\S+)\):")
    __interfaceRE = regexpCompile(r"^\s*class\s+(\S+)\s*\(\s*(?:zope\.)?"
                                  r"(?:interface\.)?"
                                  r"Interface\s*\)\s*:", IGNORECASE)
    __attributeRE = regexpCompile(r"^(\s*)(\S+)\s*=\s*(?:zope\.)?"
                                  r"(?:interface\.)?"
                                  r"Attribute\s*\(['\"]{1,3}(.*)['\"]{1,3}\)",
                                  IGNORECASE)

    __singleLineREs = {
        ' @author: ': regexpCompile(r"^(\s*Authors?:\s*)(.*)$", IGNORECASE),
        ' @copyright ': regexpCompile(r"^(\s*Copyright:\s*)(.*)$", IGNORECASE),
        ' @date ': regexpCompile(r"^(\s*Date:\s*)(.*)$", IGNORECASE),
        ' @file ': regexpCompile(r"^(\s*File:\s*)(.*)$", IGNORECASE),
        ' @version: ': regexpCompile(r"^(\s*Version:\s*)(.*)$", IGNORECASE),
        ' @note ': regexpCompile(r"^(\s*Note:\s*)(.*)$", IGNORECASE),
        ' @warning ': regexpCompile(r"^(\s*Warning:\s*)(.*)$", IGNORECASE)
    }
    __argsStartRE = regexpCompile(r"^(\s*(?:(?:Keyword\s+)?"
                                  r"(?:A|Kwa)rg(?:ument)?|Attribute)s?"
                                  r"\s*:\s*)$", IGNORECASE)
    __argsRE = regexpCompile(r"^\s*(?P<name>\w+)\s*(?P<type>\(?\S*\)?)?\s*"
                             r"(?:-|:)+\s+(?P<desc>.+)$")
    __returnsStartRE = regexpCompile(r"^\s*(?:Return|Yield)s:\s*$", IGNORECASE)
    __raisesStartRE = regexpCompile(r"^\s*(Raises|Exceptions|See Also):\s*$",
                                    IGNORECASE)
    __listRE = regexpCompile(r"^\s*(([\w\.]+),\s*)+(&|and)?\s*([\w\.]+)$")
    __singleListItemRE = regexpCompile(r'^\s*([\w\.]+)\s*$')
    __listItemRE = regexpCompile(r'([\w\.]+),?\s*')
    __examplesStartRE = regexpCompile(r"^\s*(?:Example|Doctest)s?:\s*$",
                                      IGNORECASE)
    __sectionStartRE = regexpCompile(r"^\s*(([A-Z]\w* ?){1,2}):\s*$")
    # The error line should match traceback lines, error exception lines, and
    # (due to a weird behavior of codeop) single word lines.
    __errorLineRE = regexpCompile(r"^\s*((?:\S+Error|Traceback.*):?\s*(.*)|@?[\w.]+)\s*$",
                                  IGNORECASE)

    # searching for reStructuredText field lists
    # __rst_paramRE = regexpCompile(r"^\s*(?::param(eter)?|:arg(ument)?|:key(word)?)"
    #                               r"\s*(\w*)\s*(\w*)\s*:(.*)") # search for :param, :parameter,
    #                                                              :arg, :argument, :key, :keyword
    # this searches for the keyword and the colons, but returns all in between as one group:
    __rst_paramRE = regexpCompile(r"^\s*(?::param(eter)?|:arg(ument)?|:key(word)?)([^:]*):\s*(.*)")
    __rst_typeRE = regexpCompile(r"^(\s*)(?::type)"
                                 r"\s*(\w*)\s*:(.*)")   # search for :type
    __rst_rtypeRE = regexpCompile(r"^(\s*)(?::rtype)\s*(.*):(.*)")  # search for rtype
    __rst_returnRE = regexpCompile(r"^\s*(?::return)\s*(.*): (.*)$")
    __rst_literal_sectionRE = regexpCompile(r"^(.*)::$")
    __rst_tableRE = regexpCompile(r"^\s*=+\s+(=+\s*)+$")  # end of table is a blank line

    __LITERAL_SECTION_MARK = "~~~~~~"

    def __init__(self, lines, arguments):
        """Initialize a few class variables in preparation for our walk."""
        self.lines = lines
        self.args = arguments
        self.docLines = []

    @staticmethod
    def _stripOutAnds(inStr):
        """Take a string and returns the same without ands or ampersands."""
        assert isinstance(inStr, str)
        return inStr.replace(' and ', ' ').replace(' & ', ' ')

    @staticmethod
    def _endCodeIfNeeded(line, inCodeBlock):
        """Append end code marker if needed."""
        assert isinstance(line, str)
        if inCodeBlock:
            line = '# @endcode{0}{1}'.format(linesep, line.rstrip())
            inCodeBlock = False
        return line, inCodeBlock

    @staticmethod
    @coroutine
    def _checkIfCode(inCodeBlockObj):
        """Check whether or not a given line appears to be Python code."""
        while True:
            line, lines, lineNum = (yield)
            testLineNum = 1
            currentLineNum = 0
            testLine = line.strip()
            lineOfCode = None
            while lineOfCode is None:
                match = AstWalker.__errorLineRE.match(testLine)
                if not testLine or testLine == '...' or match:
                    # These are ambiguous.
                    line, lines, lineNum = (yield)
                    testLine = line.strip()
                    # testLineNum = 1
                elif testLine.startswith('>>>'):
                    # This is definitely code.
                    lineOfCode = True
                elif testLine.startswith('...'):
                    lineOfCode = True
                else:
                    try:
                        compLine = compile_command(testLine)
                        if compLine and lines[currentLineNum].strip().startswith('#'):
                            lineOfCode = True
                        else:
                            line, lines, lineNum = (yield)
                            line = line.strip()
                            if line.startswith('>>>'):
                                # Definitely code, don't compile further.
                                lineOfCode = True
                            else:
                                testLine += linesep + line
                                testLine = testLine.strip()
                                testLineNum += 1
                    except (SyntaxError, RuntimeError):
                        # This is definitely not code.
                        lineOfCode = False
                    except Exception:
                        # Other errors are ambiguous.
                        line, lines, lineNum = (yield)
                        testLine = line.strip()
                        # testLineNum = 1
                currentLineNum = lineNum - testLineNum
            if not inCodeBlockObj[0] and lineOfCode:
                inCodeBlockObj[0] = True
                lines[currentLineNum] = '{0}{1}# @code{1}'.format(
                    lines[currentLineNum],
                    linesep
                )
            elif inCodeBlockObj[0] and lineOfCode is False:
                # None is ambiguous, so strict checking
                # against False is necessary.
                inCodeBlockObj[0] = False
                lines[currentLineNum] = '{0}{1}# @endcode{1}'.format(
                    lines[currentLineNum],
                    linesep
                )

    @coroutine
    def __alterDocstring(self, tail='', writer=None):
        """
        Run eternally, processing docstring lines.

        Parses docstring lines as they get fed in via send, applies appropriate
        Doxygen tags, and passes them along in batches for writing.
        """
        assert isinstance(tail, str) and isinstance(writer, GeneratorType)

        lines = []  # get's filled with changed line data until it is written out again
        timeToSend = False
        inCodeBlock = False       # local CodeBlock state
        inCodeBlockObj = [False]  # codeChecker CodeBlock state
        inSection = False
        in_literal_section = False
        in_rst_table = False
        rst_table_start_line_number = -1
        table_count = 0
        rst_table_middle_column_positions = []  # first and last column are line dependent...
        prefix = ''
        firstLineNum = -1
        sectionHeadingIndent = 0
        codeChecker = self._checkIfCode(inCodeBlockObj)
        while True:
            lineNum, line = (yield)
            if firstLineNum < 0:
                firstLineNum = lineNum
            # Don't bother doing extra work if it's a sentinel.
            if line is not None:
                # Also limit work if we're not parsing the docstring.
                if self.args.autobrief:
                    for doxyTag, tagRE in AstWalker.__singleLineREs.items():
                        match = tagRE.search(line)
                        if match:
                            # We've got a simple one-line Doxygen command
                            if lines:
                                lines[-1], inCodeBlock = self._endCodeIfNeeded(
                                    lines[-1], inCodeBlock)
                            inCodeBlockObj[0] = inCodeBlock
                            writer.send((firstLineNum, lineNum - 1, lines))
                            lines = []
                            firstLineNum = lineNum
                            line = line.replace(match.group(1), doxyTag)
                            timeToSend = True

                    # Special Line Mode handlings:
                    if inSection:
                        # The last line belonged to a section.
                        # Does this one too? (Ignoring empty lines.)
                        match = AstWalker.__blanklineRE.match(line)
                        if not match:
                            indent = len(line.expandtabs(self.args.tablength)) - \
                                len(line.expandtabs(self.args.tablength).lstrip())
                            if indent <= sectionHeadingIndent:
                                inSection = False
                            else:
                                if lines[-1] == '#':
                                    # If the last line was empty, but we're still in a section
                                    # then we need to start a new paragraph.
                                    lines[-1] = '# @par'
                    elif in_literal_section:
                        # currently there's a literal section active
                        match = AstWalker.__blanklineRE.match(line)
                        if not match:
                            # evaluate only non blank lines
                            current_indent = len(line.expandtabs(self.args.tablength)) \
                                - len(line.expandtabs(self.args.tablength).lstrip())
                            if current_indent > sectionHeadingIndent:
                                # just use it unchanged, but ensure it is at least 4 spaces indented
                                # doxygen only evaluates relative indents to former indent level
                                if (current_indent - sectionHeadingIndent) < 4:
                                    extra_indent = " " * (4 - current_indent + sectionHeadingIndent)
                                else:
                                    extra_indent = ''
                                lines.append("#" + extra_indent + line)
                                continue
                            in_literal_section = False
                            # line = line.rstrip() + "Le"
                            # lines.append("#" + AstWalker.__LITERAL_SECTION_MARK)
                            # fencing requires line addition -> which is not yet supported here
                    elif in_rst_table:
                        # end table on a blank line
                        match = AstWalker.__blanklineRE.match(line)
                        if match:
                            in_rst_table = False
                            lines.append("#" + line)
                            continue
                        # check for intermediate border lines -> doxygen only knows them at
                        # second table line as separator line ...
                        match = AstWalker.__rst_tableRE.match(line)
                        if match:
                            if rst_table_start_line_number + 2 == lineNum:
                                line = line.replace("=", "-")
                            else:
                                # line = line.replace("="," ") # white spaces will end the table... so use
                                # replace every starting = with - and all following with ' '
                                line = line.replace(" =", " -")
                                line = line.replace("=", " ")
                        # insert pipes before first text and behind last text ... well not always
                        # needed so skip it for now
                        # insert pipes on all middle positions, check if there's a whitespace there
                        for pos in rst_table_middle_column_positions:
                            if line[pos] == ' ':
                                line = line[:pos] + '|' + line[pos + 1:]
                            # else:
                                # well miss formated simple rst table
                                # -> let the garbage flow... until next blank line...
                                # Note: multiline rst table cells are not translateable to
                                # simple Markdown...
                        lines.append("#" + line)
                        continue  # no further translation needed here
                    match = AstWalker.__returnsStartRE.match(line)
                    if match:
                        # We've got a "returns" section
                        lines[-1], inCodeBlock = self._endCodeIfNeeded(
                            lines[-1], inCodeBlock)
                        inCodeBlockObj[0] = inCodeBlock
                        line = line.replace(match.group(0), ' @return\t').rstrip()
                        prefix = '@return\t'
                    else:
                        match = AstWalker.__argsStartRE.match(line)
                        if match:
                            # We've got an "arguments" section
                            line = line.replace(match.group(0), '').rstrip()
                            if 'attr' in match.group(0).lower():
                                prefix = '@property\t'
                            else:
                                prefix = '@param\t'
                            if lines:
                                lines[-1], inCodeBlock = self._endCodeIfNeeded(lines[-1], inCodeBlock)
                            inCodeBlockObj[0] = inCodeBlock
                            lines.append('#' + line)
                            continue
                        match = AstWalker.__rst_paramRE.match(line)
                        if match:
                            # it's an rst param
                            # last word is the param name
                            param_declarations = match.group(4).rpartition(' ')
                            line = "{} {} {} {}".format(
                                param_declarations[2], param_declarations[0], param_declarations[1], match.group(5)
                            )

                            prefix = '@param\t'
                            if lines:
                                lines[-1], inCodeBlock = self._endCodeIfNeeded(lines[-1], inCodeBlock)
                            lines.append('#@param\t' + line)
                            continue  # line is processed
                        match = AstWalker.__rst_typeRE.match(line)
                        if match:
                            # it's a type description to a former param
                            line = "{}@n type of {}: {}".format(
                                match.group(1), match.group(2), match.group(3)
                            )  # @n = newline
                            if lines:
                                lines[-1], inCodeBlock = self._endCodeIfNeeded(lines[-1], inCodeBlock)
                            lines.append('#' + line)
                            continue  # line is processed
                        match = AstWalker.__rst_returnRE.match(line)
                        if match:
                            # it's a return description line
                            prefix = "@return\t"
                            line = "@return {} {}".format(match.group(1), match.group(2))
                            if lines:
                                lines[-1], inCodeBlock = self._endCodeIfNeeded(lines[-1], inCodeBlock)
                            lines.append('#' + line)
                            continue  # line is processed
                        match = AstWalker.__rst_rtypeRE.match(line)
                        if match:
                            # it's a return type description to a former return
                            line = "{}@n return type of {}: {}".format(
                                match.group(1), match.group(2), match.group(3)
                            )  # @n = newline
                            if lines:
                                lines[-1], inCodeBlock = self._endCodeIfNeeded(lines[-1], inCodeBlock)
                            lines.append('#' + line)
                            continue  # line is processed
                        match = AstWalker.__rst_tableRE.match(line)
                        if match:
                            # found a rst table start
                            in_rst_table = True
                            current_indent = len(line.expandtabs(self.args.tablength)) \
                                - len(line.expandtabs(self.args.tablength).lstrip())
                            rst_table_start_line_number = lineNum
                            # get the positions of middle columns
                            rst_table_middle_column_positions = []
                            pos = line.find("= ")
                            while pos != -1:
                                rst_table_middle_column_positions.append(pos + 1)  # the space is after =
                                pos = line.find("= ", pos + 1)
                            # other code detectors need to be run here to get out of their mode but keep
                            # line indention for not triggering a literal section!
                            table_count += 1
                            # <text> number prevents singleListItem detection later
                            line = " " * current_indent + "Table {}".format(table_count)
                        match = AstWalker.__argsRE.match(line)
                        if match and not inCodeBlock:
                            # We've got something that looks like an item /
                            # description pair.
                            if 'property' in prefix:
                                line = '# {0}\t{1[name]}{2}# {1[desc]}'.format(
                                    prefix, match.groupdict(), linesep)
                            else:
                                line = ' {0}\t{1[name]}\t{1[desc]}'.format(
                                    prefix, match.groupdict())
                        else:
                            match = AstWalker.__raisesStartRE.match(line)
                            if match:
                                line = line.replace(match.group(0), '').rstrip()
                                if 'see' in match.group(1).lower():
                                    # We've got a "see also" section
                                    prefix = '@sa\t'
                                else:
                                    # We've got an "exceptions" section
                                    prefix = '@exception\t'
                                lines[-1], inCodeBlock = self._endCodeIfNeeded(
                                    lines[-1], inCodeBlock)
                                inCodeBlockObj[0] = inCodeBlock
                                lines.append('#' + line)
                                continue
                            match = AstWalker.__listRE.match(line)
                            if match and not inCodeBlock:
                                # We've got a list of something or another
                                itemList = []
                                for itemMatch in AstWalker.__listItemRE.findall(self._stripOutAnds(
                                                                                match.group(0))):
                                    itemList.append('# {0}\t{1}{2}'.format(
                                        prefix, itemMatch, linesep))
                                line = ''.join(itemList)[1:]
                            else:
                                match = AstWalker.__examplesStartRE.match(line)
                                if match and lines[-1].strip() == '#' \
                                   and self.args.autocode:
                                    # We've got an "example" section
                                    inCodeBlock = True
                                    inCodeBlockObj[0] = True
                                    line = line.replace(match.group(0),
                                                        ' @b Examples{0}# @code'.format(linesep))
                                else:
                                    match = AstWalker.__sectionStartRE.match(line)
                                    if match:
                                        # We've got an arbitrary section
                                        prefix = ''
                                        inSection = True
                                        # What's the indentation of the section heading?
                                        sectionHeadingIndent = len(line.expandtabs(self.args.tablength)) \
                                            - len(line.expandtabs(self.args.tablength).lstrip())
                                        line = line.replace(
                                            match.group(0),
                                            ' @par {0}'.format(match.group(1))
                                        )
                                        if lines[-1] == '# @par':
                                            lines[-1] = '#'
                                        lines[-1], inCodeBlock = self._endCodeIfNeeded(
                                            lines[-1], inCodeBlock)
                                        inCodeBlockObj[0] = inCodeBlock
                                        lines.append('#' + line)
                                        continue
                                    if prefix:
                                        match = AstWalker.__singleListItemRE.match(line)
                                        if match and not inCodeBlock:
                                            # Probably a single list item
                                            line = ' {0}\t{1}'.format(
                                                prefix, match.group(0))
                                        elif self.args.autocode:
                                            codeChecker.send(
                                                (
                                                    line, lines,
                                                    lineNum - firstLineNum
                                                )
                                            )
                                            inCodeBlock = inCodeBlockObj[0]
                                    else:
                                        if self.args.autocode:
                                            codeChecker.send(
                                                (
                                                    line, lines,
                                                    lineNum - firstLineNum
                                                )
                                            )
                                            inCodeBlock = inCodeBlockObj[0]

                # If we were passed a tail, append it to the docstring.
                # Note that this means that we need a docstring for this
                # item to get documented.
                if tail and lineNum == len(self.docLines) - 1:
                    line = '{0}{1}# {2}'.format(line.rstrip(), linesep, tail)

                # Add comment marker for every line.
                line = '#{0}'.format(line.rstrip())
                # Ensure the first line has the Doxygen double comment.
                if lineNum == 0:
                    line = '#' + line

                lines.append(line.replace(' ' + linesep, linesep))
            else:
                # If we get our sentinel value, send out what we've got.
                timeToSend = True

            if timeToSend:
                if lines:
                    lines[-1], inCodeBlock = self._endCodeIfNeeded(lines[-1], inCodeBlock)
                inCodeBlockObj[0] = inCodeBlock
                writer.send((firstLineNum, lineNum, lines))
                lines = []
                firstLineNum = -1
                table_count = 0
                timeToSend = False

    @coroutine
    def __writeDocstring(self):
        """
        Run eternally, dumping out docstring line batches as they get fed in.

        Replaces original batches of docstring lines with modified versions
        fed in via send.
        """
        while True:
            firstLineNum, lastLineNum, lines = (yield)
            newDocstringLen = lastLineNum - firstLineNum + 1
            while len(lines) < newDocstringLen:
                lines.append('')
            # Substitute the new block of lines for the original block of lines.
            self.docLines[firstLineNum: lastLineNum + 1] = lines

    def _processDocstring(self, node, tail='', **kwargs):
        """
        Handle a docstring for functions, classes, and modules.

        Basically just figures out the bounds of the docstring and sends it
        off to the parser to do the actual work.

        Return: last line number of this docstring
        """
        typeName = type(node).__name__
        # Modules don't have lineno defined, but it's always 0 for them.
        curLineNum = startLineNum = 0
        if typeName != 'Module':
            startLineNum = curLineNum = node.lineno - 1
        # Figure out where both our enclosing object and our docstring start.
        line = ''
        while curLineNum < len(self.lines):
            line = self.lines[curLineNum]
            match = AstWalker.__docstrMarkerRE.match(line)
            if match:
                break
            curLineNum += 1
        docstringStart = curLineNum
        # Figure out where our docstring ends.
        if not AstWalker.__docstrOneLineRE.match(line):
            # Skip for the special case of a single-line docstring.
            curLineNum += 1
            while curLineNum < len(self.lines):
                line = self.lines[curLineNum]
                if line.find(match.group(2)) >= 0:
                    break
                curLineNum += 1
        endLineNum = curLineNum + 1

        # Isolate our enclosing object's declaration.
        defLines = self.lines[startLineNum: docstringStart]
        # Isolate our docstring.
        self.docLines = self.lines[docstringStart: endLineNum]

        # If we have a docstring, extract information from it.
        if self.docLines:
            # Get rid of the docstring delineators.
            self.docLines[0] = AstWalker.__docstrMarkerRE.sub('',
                                                              self.docLines[0])
            self.docLines[-1] = AstWalker.__docstrMarkerRE.sub('',
                                                               self.docLines[-1])
            # Handle special strings within the docstring.
            docstringConverter = self.__alterDocstring(
                tail, self.__writeDocstring())
            for lineInfo in enumerate(self.docLines):
                docstringConverter.send(lineInfo)
            docstringConverter.send((len(self.docLines) - 1, None))

        # Add a Doxygen @brief tag to any single-line description.
        # but take care not to remove the initial '##' doxygen marker
        if self.args.autobrief:
            safetyCounter = 0
            while self.docLines and self.docLines[0].lstrip('#').strip() == '':
                del self.docLines[0]
                self.docLines.append('')
                safetyCounter += 1
                if safetyCounter >= len(self.docLines):
                    # Escape the effectively empty docstring.
                    break
            if len(self.docLines) == 1 or (len(self.docLines) >= 2 and (
                self.docLines[1].strip(whitespace + '#') == '' or
                    self.docLines[1].strip(whitespace + '#').startswith('@'))):
                self.docLines[0] = "## @brief {0}".format(self.docLines[0].lstrip('#'))
                if len(self.docLines) > 1 and self.docLines[1] == '# @par':
                    self.docLines[1] = '#'
            # safety catch up for starting with doxygen marker even if first DocString Line is empty
            # and has been removed in former processings for autobrief
            if safetyCounter > 0 and not self.docLines[0].lstrip().startswith('##'):
                self.docLines[0] = '##' + self.docLines[0]

        if defLines:
            # make all docstring comments on same indentation as their enclosing object's indention level
            # but remove this added indent within the docstring if needed
            match = AstWalker.__indentRE.match(defLines[0])
            indentStr = match.group(1) if match else ''
            self.docLines = [AstWalker.__newlineRE.sub(indentStr + '#', docLine)
                             for docLine in self.docLines]
            if self.args.equalIndent and indentStr:
                # remove the same amount of indent within the docLine part
                indentPartRE = regexpCompile("{istr}#+({istr})".format(istr=indentStr))
                for (index, docLine) in enumerate(self.docLines):
                    docIndentPart = indentPartRE.match(docLine)
                    if docIndentPart is None:
                        # no match
                        continue
                    # print (f"match line {docstringStart + index} from
                    # {docIndentPart.start(1)} to {docIndentPart.end(1)}")
                    self.docLines[index] = docLine[:docIndentPart.start(1)] + docLine[docIndentPart.end(1):]

        # Taking away a docstring from an interface method definition sometimes
        # leaves broken code as the docstring may be the only code in it.
        # Here we manually insert a pass statement to rectify this problem.
        if typeName != 'Module':
            if docstringStart < len(self.lines):
                match = AstWalker.__indentRE.match(self.lines[docstringStart])
                indentStr = match.group(1) if match else ''
            else:
                indentStr = ''
            containingNodes = kwargs.get('containingNodes', []) or []
            fullPathNamespace = self._getFullPathName(containingNodes)
            parentType = fullPathNamespace[-2][1]
            if parentType == 'interface' and typeName == 'FunctionDef' \
               or fullPathNamespace[-1][1] == 'interface':
                # defLines should always end with some kind of new line -> insert two os correct ones
                defLines[-1] = '{0}{1}{1}{2}pass'.format(defLines[-1].rstrip(),
                                                         linesep, indentStr)
            elif self.args.autobrief and typeName == 'ClassDef':
                # If we're parsing docstrings separate out class attribute
                # definitions to get better Doxygen output.
                for firstVarLineNum, firstVarLine in enumerate(self.docLines):
                    if '@property\t' in firstVarLine:
                        break
                lastVarLineNum = len(self.docLines)
                if lastVarLineNum > 0 and '@property\t' in firstVarLine:
                    while lastVarLineNum > firstVarLineNum:
                        lastVarLineNum -= 1
                        if '@property\t' in self.docLines[lastVarLineNum]:
                            break
                    lastVarLineNum += 1
                    if firstVarLineNum < len(self.docLines):
                        indentLineNum = endLineNum
                        indentStr = ''
                        while not indentStr and indentLineNum < len(self.lines):
                            match = AstWalker.__indentRE.match(self.lines[indentLineNum])
                            indentStr = match.group(1) if match else ''
                            indentLineNum += 1
                        varLines = ['{0}{1}'.format(linesep, docLine).replace(
                                    linesep, linesep + indentStr)
                                    for docLine in self.docLines[
                                        firstVarLineNum: lastVarLineNum]]
                        defLines.extend(varLines)
                        self.docLines[firstVarLineNum: lastVarLineNum] = []
                        # After the property shuffling we will need to relocate
                        # any existing namespace information.
                        namespaceLoc = defLines[-1].find(linesep + '# @namespace')
                        if namespaceLoc >= 0:
                            self.docLines[-1] += defLines[-1][namespaceLoc:]
                            defLines[-1] = defLines[-1][:namespaceLoc]

        # For classes and functions, apply our changes and reverse the
        # order of the declaration and docstring, and for modules just
        # apply our changes.
        if typeName != 'Module':
            self.lines[startLineNum: endLineNum] = self.docLines + defLines
        else:
            self.lines[startLineNum: endLineNum] = defLines + self.docLines
        return endLineNum

    @staticmethod
    def _checkMemberName(name):
        """
        See if a member name indicates that it should be private.

        Private variables in Python (starting with a double underscore but
        not ending in a double underscore) and bed lumps (variables that
        are not really private but are by common convention treated as
        protected because they begin with a single underscore) get Doxygen
        tags labeling them appropriately.
        """
        assert isinstance(name, str)
        restrictionLevel = None
        if not name.endswith('__'):
            if name.startswith('__'):
                restrictionLevel = 'private'
            elif name.startswith('_'):
                restrictionLevel = 'protected'
        return restrictionLevel

    def _processMembers(self, node, contextTag):
        """
        Mark up members if they should be private.

        If the name indicates it should be private or protected, apply
        the appropriate Doxygen tags.
        """
        restrictionLevel = self._checkMemberName(node.name)
        if restrictionLevel:
            workTag = '{0}{1}# @{2}'.format(contextTag,
                                            linesep,
                                            restrictionLevel)
        else:
            workTag = contextTag
        return workTag

    def generic_visit(self, node, **kwargs):
        """
        Extract useful information from relevant nodes including docstrings.

        This is virtually identical to the standard version contained in
        NodeVisitor.  It is only overridden because we're tracking extra
        information (the hierarchy of containing nodes) not preserved in
        the original.
        """
        for field, value in iter_fields(node):
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, AST):
                        self.visit(item, containingNodes=kwargs['containingNodes'])
            elif isinstance(value, AST):
                self.visit(value, containingNodes=kwargs['containingNodes'])

    def visit(self, node, **kwargs):
        """
        Visit a node and extract useful information from it.

        This is virtually identical to the standard version contained in
        NodeVisitor.  It is only overridden because we're tracking extra
        information (the hierarchy of containing nodes) not preserved in
        the original.
        """
        containingNodes = kwargs.get('containingNodes', [])
        method = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        return visitor(node, containingNodes=containingNodes)

    def _getFullPathName(self, containingNodes):
        """
        Return the full node hierarchy rooted at module name.

        The list representing the full path through containing nodes
        (starting with the module itself) is returned.
        """
        assert isinstance(containingNodes, list)
        return [(self.args.fullPathNamespace, 'module')] + containingNodes

    def visit_Module(self, node, **kwargs):
        """
        Handle the module-level docstring.

        Process the module-level docstring and create appropriate Doxygen tags
        if autobrief option is set.
        """
        containingNodes = kwargs.get('containingNodes', [])
        if self.args.debug:
            stderr.write("# Module {0}{1}".format(self.args.fullPathNamespace,
                                                  linesep))
        if get_docstring(node):
            if self.args.topLevelNamespace:
                fullPathNamespace = self._getFullPathName(containingNodes)
                contextTag = '.'.join(pathTuple[0] for pathTuple in fullPathNamespace)
                tail = '@namespace {0}'.format(contextTag)
            else:
                tail = ''
            self._processDocstring(node, tail)
        # Visit any contained nodes (in this case pretty much everything).
        self.generic_visit(node, containingNodes=containingNodes)

    def visit_Assign(self, node, **kwargs):
        """
        Handle assignments within code.

        Variable assignments in Python are used to represent interface
        attributes in addition to basic variables.  If an assignment appears
        to be an attribute, it gets labeled as such for Doxygen.  If a variable
        name uses Python mangling or is just a bed lump, it is labeled as
        private for Doxygen.
        """
        lineNum = node.lineno - 1
        # Assignments have one Doxygen-significant special case:
        # interface attributes.
        match = AstWalker.__attributeRE.match(self.lines[lineNum])
        if match:
            self.lines[lineNum] = '{0}## @property {1}{2}{0}# {3}{2}' \
                '{0}# @hideinitializer{2}{4}{2}'.format(
                    match.group(1),
                    match.group(2),
                    linesep,
                    match.group(3),
                    self.lines[lineNum].rstrip()
            )
            if self.args.debug:
                stderr.write("# Attribute {0.id}{1}".format(node.targets[0],
                                                            linesep))
        if isinstance(node.targets[0], Name):
            match = AstWalker.__indentRE.match(self.lines[lineNum])
            indentStr = match.group(1) if match else ''
            restrictionLevel = self._checkMemberName(node.targets[0].id)
            if restrictionLevel:
                self.lines[lineNum] = '{0}## @var {1}{2}{0}' \
                    '# @hideinitializer{2}{0}# @{3}{2}{4}{2}'.format(
                        indentStr,
                        node.targets[0].id,
                        linesep,
                        restrictionLevel,
                        self.lines[lineNum].rstrip()
                )
        # Visit any contained nodes.
        self.generic_visit(node, containingNodes=kwargs['containingNodes'])

    def visit_Call(self, node, **kwargs):
        """
        Handle function calls within code.

        Function calls in Python are used to represent interface implementations
        in addition to their normal use.  If a call appears to mark an
        implementation, it gets labeled as such for Doxygen.
        """
        lineNum = node.lineno - 1
        # Function calls have one Doxygen-significant special case:  interface
        # implementations.
        match = AstWalker.__implementsRE.match(self.lines[lineNum])
        if match:
            self.lines[lineNum] = '{0}## @implements {1}{2}{0}{3}{2}'.format(
                match.group(1), match.group(2), linesep,
                self.lines[lineNum].rstrip())
            if self.args.debug:
                stderr.write("# Implements {0}{1}".format(match.group(1),
                                                          linesep))
        # Visit any contained nodes.
        self.generic_visit(node, containingNodes=kwargs['containingNodes'])

    def visit_FunctionDef(self, node, **kwargs):
        """
        Handle function definitions within code.

        Process a function's docstring, keeping well aware of the function's
        context and whether or not it's part of an interface definition.
        """
        if self.args.debug:
            stderr.write("# Function {0.name}{1}".format(node, linesep))

        # if it's a property, rewrite the definition to something Doxygen understands
        # (We'll use the getter for the documentation)
        if node.decorator_list:
            match = AstWalker.__indentRE.match(self.lines[node.lineno - 1])
            indentStr = match.group(1) if match else ''
            if getattr(node.decorator_list[0], "id", None) == "property":
                self.lines[node.lineno - 1] = indentStr + "{} = property".format(node.name) + \
                    linesep + indentStr + "## \\private" + linesep + self.lines[node.lineno - 1]
            if getattr(node.decorator_list[0], "attr", None) == "setter":
                self.lines[node.lineno - 1] = indentStr + "## \\private" + linesep + self.lines[node.lineno - 1]

        # Push either 'interface' or 'class' onto our containing nodes
        # hierarchy so we can keep track of context.  This will let us tell
        # if a function is nested within another function or even if a class
        # is nested within a function.
        containingNodes = kwargs.get('containingNodes') or []
        containingNodes.append((node.name, 'function'))
        if self.args.topLevelNamespace:
            fullPathNamespace = self._getFullPathName(containingNodes)
            contextTag = '.'.join(pathTuple[0] for pathTuple in fullPathNamespace)
            modifiedContextTag = self._processMembers(node, contextTag)
            tail = '@namespace {0}'.format(modifiedContextTag)
        else:
            tail = self._processMembers(node, '')
        if get_docstring(node):
            last_doc_line_number = self._processDocstring(
                node, tail, containingNodes=containingNodes)
            if self.args.keepDecorators:
                self._shift_decorators_below_docstring(node, last_doc_line_number)

        # Visit any contained nodes.
        self.generic_visit(node, containingNodes=containingNodes)
        # Remove the item we pushed onto the containing nodes hierarchy.
        containingNodes.pop()
    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node, **kwargs):
        """
        Handle class definitions within code.

        Process the docstring.  Note though that in Python Class definitions
        are used to define interfaces in addition to classes.
        If a class definition appears to be an interface definition tag it as an
        interface definition for Doxygen.  Otherwise tag it as a class
        definition for Doxygen.
        """
        lineNum = node.lineno - 1
        # Push either 'interface' or 'class' onto our containing nodes
        # hierarchy so we can keep track of context.  This will let us tell
        # if a function is a method or an interface method definition or if
        # a class is fully contained within another class.
        containingNodes = kwargs.get('containingNodes') or []

        if not self.args.object_respect:
            # Remove object class of the inherited class list to avoid that all
            # new-style class inherits from object in the hierarchy class
            line = self.lines[lineNum]
            match = AstWalker.__classRE.match(line)
            if match:
                if match.group(2) == 'object':
                    self.lines[lineNum] = line[:match.start(2)] + line[match.end(2):]

        match = AstWalker.__interfaceRE.match(self.lines[lineNum])
        if match:
            if self.args.debug:
                stderr.write("# Interface {0.name}{1}".format(node, linesep))
            containingNodes.append((node.name, 'interface'))
        else:
            if self.args.debug:
                stderr.write("# Class {0.name}{1}".format(node, linesep))
            containingNodes.append((node.name, 'class'))
        if self.args.topLevelNamespace:
            fullPathNamespace = self._getFullPathName(containingNodes)
            contextTag = '.'.join(pathTuple[0] for pathTuple in fullPathNamespace)
            tail = '@namespace {0}'.format(contextTag)
        else:
            tail = ''
        # Class definitions have one Doxygen-significant special case:
        # interface definitions.
        if match:
            contextTag = '{0}{1}# @interface {2}'.format(tail,
                                                         linesep,
                                                         match.group(1))
        else:
            contextTag = tail
        contextTag = self._processMembers(node, contextTag)
        if get_docstring(node):
            last_doc_line_number = self._processDocstring(
                node, contextTag, containingNodes=containingNodes)
            if self.args.keepDecorators:
                self._shift_decorators_below_docstring(node, last_doc_line_number)
        # Visit any contained nodes.
        self.generic_visit(node, containingNodes=containingNodes)
        # Remove the item we pushed onto the containing nodes hierarchy.
        containingNodes.pop()

    # With Python 3.8, a function visit_Constant() was added to ast.NodeVisitor
    # This adds an overload of this function that can take additional
    # arguments, but ignores them and calls the function from NodeVisitor.
    # See also https://github.com/Feneric/doxypypy/issues/70
    def visit_Constant(self, node, **kwargs):
        """Handle constant definitions within code."""
        super(AstWalker, self).visit_Constant(node)

    def _shift_decorators_below_docstring(self, node, last_doc_line_number):
        if node.decorator_list:
            # get the decorators of this function and put them after DocString -> needs doxygen 1.9 or higher
            # as decorators must be one line before function name, restructuring should be possible
            # print (str(node.decorator_list) + str(node.decorator_list[0].id) + str(node.decorator_list[0].lineno))
            for decorator in node.decorator_list:
                # first in list is last decorator called ... -> thus first line with decorator
                org_line_number = decorator.lineno - 1
                new_line_number = last_doc_line_number - 1
                self.lines[org_line_number:new_line_number] = self.lines[org_line_number + 1:new_line_number] \
                    + [self.lines[org_line_number]]

    def parseLines(self):
        """Form an AST for the code and produce a new version of the source."""
        inAst = parse(''.join(self.lines), self.args.filename)
        # Visit all the nodes in our tree and apply Doxygen tags to the source.
        self.visit(inAst)

    def getLines(self):
        """Return the modified file once processing has been completed."""
        # Note: some processing steps insert new lines within one lines.line...
        # so actually all lineseps need to be replaced within one line, even in the middle of a line ...
        return linesep.join(line.rstrip() for line in self.lines)


def main():
    """
    Start it up.

    Starts the parser on the file given by the filename as the first
    argument on the command line.
    """
    def argParse():
        """
        Parse command line options.

        Generally we're supporting all the command line options that doxypy.py
        supports in an analogous way to make it easy to switch back and forth.
        We additionally support a top-level namespace argument that is used
        to trim away excess path information.
        """
        prog = basename(argv[0])
        parser = ArgumentParser(prog=prog,
                                usage="%(prog)s [options] filename")

        parser.add_argument(
            "filename",
            help="Input file name"
        )
        parser.add_argument(
            "-a", "--autobrief",
            action="store_true", dest="autobrief",
            help="parse the docstring for @brief description and other information"
        )
        parser.add_argument(
            "-c", "--autocode",
            action="store_true", dest="autocode",
            help="parse the docstring for code samples"
        )
        parser.add_argument(
            "-n", "--ns",
            action="store", type=str, dest="topLevelNamespace",
            help="specify a top-level namespace that will be used to trim paths"
        )
        parser.add_argument(
            "-t", "--tablength",
            action="store", type=int, dest="tablength", default=4,
            help="specify a tab length in spaces; only needed if tabs are used"
        )
        parser.add_argument(
            "-s", "--stripinit",
            action="store_true", dest="stripinit",
            help="strip __init__ from namespace"
        )
        parser.add_argument(
            "-O", "--object-respect",
            action="store_true", dest="object_respect",
            help="By default, doxypypy hides object class from class dependencies"
                 "even if class inherits explictilty from objects (new-style class),"
                 "this option disable this."
        )
        parser.add_argument(
            "-e", "--equalIndent",
            action="store_true", dest="equalIndent",
            help="Make indention level of docstrings matching with their enclosing"
                 "definitions one."
        )
        parser.add_argument(
            "-k", "--keepDecorators",
            action="store_true", dest="keepDecorators",
            help="Decorators are usually ignored by doxypypy and thus are before the"
                 "doxygen docString output and not before it's definition string."
                 "With this option decorators are kept before it's definition string"
                 "(function or class names). But this requires dogygen 1.9 or higher."
        )
        group = parser.add_argument_group("Debug Options")
        group.add_argument(
            "-d", "--debug",
            action="store_true", dest="debug",
            help="enable debug output on stderr"
        )

        # Parse options based on our definition.
        args = parser.parse_args()

        # Just abort immediately if we are don't have an input file.
        if not args.filename:
            stderr.write("No filename given." + linesep)
            sysExit(-1)

        # Turn the full path filename into a full path module location.
        fullPathNamespace = args.filename.replace(sep, '.')[:-3]
        # Use any provided top-level namespace argument to trim off excess.
        realNamespace = fullPathNamespace
        if args.topLevelNamespace:
            namespaceStart = fullPathNamespace.find(args.topLevelNamespace)
            if namespaceStart >= 0:
                realNamespace = fullPathNamespace[namespaceStart:]
        if args.stripinit:
            realNamespace = realNamespace.replace('.__init__', '')
        args.fullPathNamespace = realNamespace

        return args

    # Figure out what is being requested.
    args = argParse()

    # Figure out encoding of input file.
    numOfSampleBytes = min(getsize(args.filename), 32)
    sampleBytes = open(args.filename, 'rb').read(numOfSampleBytes)
    sampleByteAnalysis = detect(sampleBytes)
    encoding = sampleByteAnalysis['encoding'] or 'ascii'

    # Switch to generic versions to strip the BOM automatically.
    if sampleBytes.startswith(BOM_UTF8):
        encoding = 'UTF-8-SIG'
    if encoding.startswith("UTF-16"):
        encoding = "UTF-16"
    elif encoding.startswith("UTF-32"):
        encoding = "UTF-32"

    # Read contents of input file.
    if encoding == 'ascii':
        inFile = open(args.filename)
    else:
        inFile = codecsOpen(args.filename, encoding=encoding)
    lines = inFile.readlines()
    inFile.close()
    # Create the abstract syntax tree for the input file.
    astWalker = AstWalker(lines, args)
    astWalker.parseLines()
    # Output the modified source.

    # There is a "feature" in print on Windows. If linesep is
    # passed, it will generate 0x0D 0x0D 0x0A each line which
    # screws up Doxygen since it's expected 0x0D 0x0A line endings.
    for line in astWalker.getLines().split(linesep):
        print(line.rstrip())


# See if we're running as a script.
if __name__ == "__main__":
    main()
