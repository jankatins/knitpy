#!/usr/bin/env python
# encoding: utf-8

## Running all output tests in the debugger is a pain, so use this to run only one

# Copyright (c) Jan Schulz <jasc@gmx.net>
# Distributed under the terms of the Modified BSD License.

import os

from knitpy.tests import AbstractOutputTestCase

class SingleOutputTestCase(AbstractOutputTestCase):
    def test_single_output(self):
        testname =  "knitpy/tests/chunk_options/comment.pymd"

        input_file = os.path.join(testname)
        output_file = input_file[:-4]+"md"
        self._output_test(input_file, output_file)


if __name__ == "__main__":
    import nose
    nose.runmodule(argv=[__file__, '-vvs', '-x', '--pdb', '--pdb-failure'],
                   # '--with-coverage', '--cover-package=pandas.core']
                    exit=False)