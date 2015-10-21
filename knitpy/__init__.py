# encoding: utf-8
from __future__ import absolute_import

__author__ = 'jschulz'

__all__ = ["knitpy", "render"]

from .knitpy import Knitpy

def render(filename, output=None):
    """ Convert the filename to the given output format(s).

    Returns
    -------
    converted_docs : list
        List of filenames for the converted documents

    """
    kp = Knitpy()
    return kp.render(filename, output=output)

