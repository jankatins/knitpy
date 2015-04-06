# encoding: utf-8

# Copyright (c) Jan Schulz <jasc@gmx.net>
# Distributed under the terms of the Modified BSD License.

import codecs
import glob
import os
import tempfile
import inspect
import unittest
import re

from knitpy.knitpy import Knitpy


def _add_test_cases(cls, foldername):
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

    tests_dir = os.path.join(os.path.dirname(inspect.getfile(cls)), foldername)
    test_cases_glob = os.path.join(tests_dir,"*.pymd")
    testcases = glob.glob(test_cases_glob)

    function = cls._output_test

    for input_file in testcases:
        # remove ".pymd" from filename
        basename = os.path.splitext(os.path.basename(input_file))[0]
        output_file = os.path.join(tests_dir, basename+".md")
        # the complicated syntax is needed to get the individual input files into the method...
        # http://math.andrej.com/2009/04/09/pythons-lambda-is-broken/comment-page-1/
        def test_function(self, input_file=input_file, output_file=output_file):
            function(self, input_file, output_file)
        name ="test_%s_%s" % (foldername, basename)
        test_function.__name__ = name
        setattr(cls, name, test_function)


class AbstractOutputTestCase(unittest.TestCase):
    #<ipython-input-2-fb4ced135814>
    _re_ipython_id = re.compile(r"<ipython-input-[0-9]+-[a-z0-9]+>")

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
                output = self._re_ipython_id.sub("<ipython-input>", output)
                output = output.replace(os.linesep, "\n")
                f.write(output)
            self.fail("Output does not exist, created one as %s. Remove '.off' to enable it.")

        with codecs.open(output_file, 'r', 'UTF-8') as f:
            exp = f.read()
        output = self.knitpy._knit(input, tempfile.gettempdir())
        self.assert_equal_output(exp, output, filename=output_file)

    def assert_equal_output(self, expected, received, filename=None):
        # output written to a file does not seem to have os.linesep
        # handle everything here by replacing the os linesep by a simple \n
        expected = expected.replace(os.linesep, "\n").rstrip('\n')
        received = received.replace(os.linesep, "\n").rstrip('\n')
        # in errors, there is a unique id like  <ipython-input-2-fb4ced135814>
        received = self._re_ipython_id.sub("<ipython-input>", received)
        # this is a hardcoded fix for py3, where there are quotes around the module:
        received = received.replace("'NoneExistingModule'", "NoneExistingModule")

        if filename and expected != received:
            _file = filename+".received"
            with codecs.open(_file, 'w', 'UTF-8') as f:
                f.write(received)

        self.assertEqual(expected, received)
