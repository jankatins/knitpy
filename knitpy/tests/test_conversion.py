#!/usr/bin/env python
# encoding: utf-8

# Copyright (c) Jan Schulz <jasc@gmx.net>
# Distributed under the terms of the Modified BSD License.

import unittest

from knitpy.tests import AbstractOutputTestCase, _add_test_cases
class OutputTestCase(AbstractOutputTestCase):
    pass
_add_test_cases(OutputTestCase, "basics")
_add_test_cases(OutputTestCase, "chunk_options")


if __name__ == "__main__":
    unittest.main()