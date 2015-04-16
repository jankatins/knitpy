# coding: utf-8
"""Compatibility tricks for Python 3.

Stolen from ipython
"""
import os
import sys

if sys.version_info[0] >= 3:
    PY3 = True

    string_types = (str,)
    unicode_type = str

    xrange = range
    def iteritems(d): return iter(d.items())
    def itervalues(d): return iter(d.values())
    getcwd = os.getcwd

else:
    PY3 = False

    string_types = (str, unicode)
    unicode_type = unicode
    
    xrange = xrange
    def iteritems(d): return d.iteritems()
    def itervalues(d): return d.itervalues()
    getcwd = os.getcwdu
