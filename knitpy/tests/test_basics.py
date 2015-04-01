#!/usr/bin/env python
# encoding: utf-8
"""
knitpy - knitting python flavoured markdown files
"""

# Copyright (c) Jan Schulz <jasc@gmx.net>
# Copyright (c) IPython Development Team.
# Distributed under the terms of the Modified BSD License.

import unittest
import os
import glob
import codecs
import inspect
import tempfile

from knitpy.knitpy import Knitpy

def _add_test_cases(cls):
    """ Adds one testcase for each input file in the 'test_dir'

    You have to build a TestCase class, with a _output_test(self, input_file, output_file)
    method and a tests_dir property, which is simply the name of the dir, where the test cases
    are in.

    The inputs for the test cases have to have a file ending "*_input.pymd" and the outputs have
    to end in "*_output.md".

    The `_output_test` method has to convert input and then test for equality with the output.

    The generated test methods will be called `test_something` for `something_input.pymd`.
    """
    # Put them together to make a list of new test functions.
    # One test function for each input file

    tests_dir = os.path.join(os.path.dirname(inspect.getfile(cls)), cls.tests_dir)
    test_cases_glob = os.path.join(tests_dir,"*_input.pymd")
    testcases = glob.glob(test_cases_glob)

    function = cls._output_test

    for input_file in testcases:
        # remove "_input.pymd" from filename
        basename = os.path.splitext(os.path.basename(input_file))[0][:-6]
        output_file = os.path.join(tests_dir, basename+"_output.md")
        # the complicated syntax is needed to get the individual input files into the method...
        # http://math.andrej.com/2009/04/09/pythons-lambda-is-broken/comment-page-1/
        def test_function(self, input_file=input_file, output_file=output_file):
            function(self, input_file, output_file)
        name ="test_%s" % (basename)
        test_function.__name__ = name
        setattr(cls, name, test_function)


class BasicsTestCase(unittest.TestCase):

    tests_dir = "basics"

    def setUp(self):
        self.maxDiff = None
        self.knitpy = Knitpy()

    def _output_test(self, input_file, output_file):

        with codecs.open(input_file, 'r', 'UTF-8') as f:
            input = f.read()

        if not os.path.exists(output_file):
            _file = output_file+".off"
            with codecs.open(_file, 'w', 'UTF-8') as f:
                output = self.knitpy._knit(input, tempfile.gettempdir())
                f.write(output)
            self.fail("Output does not exist, created one as %s. Remove '.off' to enable it.")

        with codecs.open(output_file, 'r', 'UTF-8') as f:
            exp = f.read()
        output = self.knitpy._knit(input, tempfile.gettempdir())
        self.assertEqualExceptForNewlineEnd(exp, output)

    def assertEqualExceptForNewlineEnd(self, expected, received):
        # output written to a file does not seem to have os.linesep
        # handle everything here by replacing the os linesep by a simple \n
        expected = expected.replace(os.linesep, "\n")
        received = received.replace(os.linesep, "\n")
        self.assertEqual(expected.rstrip('\n'), received.rstrip('\n'))

_add_test_cases(BasicsTestCase)

if __name__ == "__main__":
    unittest.main()