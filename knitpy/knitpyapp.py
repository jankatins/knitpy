#!/usr/bin/env python
# encoding: utf-8
"""
knitpy - knitting python flavoured markdown files
"""

# Copyright (c) Jan Schulz <jasc@gmx.net>
# Copyright (c) IPython Development Team.
# Distributed under the terms of the Modified BSD License.

from __future__ import absolute_import, unicode_literals

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------


import codecs
import os
import logging
import glob
import sys

from IPython.core.application import BaseIPythonApplication, base_aliases, base_flags
from IPython.core.crashhandler import CrashHandler
from IPython.core.profiledir import ProfileDir
from IPython.config import catch_config_error
from IPython.utils.traitlets import (
    Unicode, List, Bool, Type, CaselessStrEnum,
)


from .documents import TemporaryOutputDocument
from .utils import get_by_name
from .knitpy import DEFAULT_OUTPUT_FORMAT_NAME, VALID_OUTPUT_FORMAT_NAMES, Knitpy, ParseException


#-----------------------------------------------------------------------------
# Crash handler for this application
#-----------------------------------------------------------------------------

class KnitpyCrashHandler(CrashHandler):
    """sys.excepthook for IPython itself, leaves a detailed report on disk."""

    def __init__(self, app):
        contact_name = "Jan Schulz"
        contact_email = "jasc@gmx.net"
        bug_tracker = 'https://github.com/janschulz/knitpy/issues'
        super(KnitpyCrashHandler,self).__init__(
            app, contact_name, contact_email, bug_tracker
        )

#-----------------------------------------------------------------------------
# Main application
#-----------------------------------------------------------------------------

knitpy_aliases = {}
knitpy_aliases.update(base_aliases)
knitpy_aliases.update({
    'to' : 'KnitpyApp.export_format',
    # TODO: implement log-to-file (form parallel apps)
    'log-to-file' : 'KnitpyApp.log_to_file',
    'keep-md': 'Knitpy.keep_md',
    'kernel-debug': 'Knitpy.kernel_debug',
    'timeout' : 'Knitpy.timeout',
    'output-debug': 'TemporaryOutputDocument.output_debug',
})

knitpy_flags = {}
knitpy_flags.update(base_flags)
knitpy_flags.update({
    'log-to-file' : (
        {'KnitpyApp' : {'log_to_file' : True}},
        "send log output to a file"
    ),
    'keep-md' : (
        {'Knitpy' : {'keep_md' : True}},
        "keep temporary markdown files"
    ),
    'kernel-debug' : (
        {'Knitpy' : {'kernel_debug' : True},
         "KnitpyApp":{"log_level":logging.DEBUG}},
        "send kernel messages to debug log (implies log-level=DEBUG)"
    ),
    'output-debug' : (
        {'TemporaryOutputDocument': {'output_debug': True},
         "KnitpyApp":{"log_level":logging.DEBUG}},
        "send output to debug log (implies log-level=DEBUG)"
    )
})


class KnitpyApp(BaseIPythonApplication):
    """Application used to convert from markdown file type (``*.pymd``)"""

    name = 'knitpy'
    version = Unicode(u'0.1')
    aliases = knitpy_aliases
    flags = knitpy_flags

    crash_handler_class = Type(KnitpyCrashHandler)

    def _log_level_default(self):
        return logging.INFO

    def _classes_default(self):
        classes = [KnitpyApp, Knitpy, TemporaryOutputDocument, ProfileDir]
        # TODO: engines should be added here
        return classes

    description = Unicode(
        u"""This application is used to convert pymd documents (*.pymd)
        to various other formats.

        Codeblocks and inline code are executed via IPython kernels and the results
        are inserted into the document. Documents should follow rmarkdown syntax
        (http://rmarkdown.rstudio.com/), substituting 'python' for 'r' if python
        code should be executed.

        The commandline interface should be compatible to knitr.

        Like these R packages, knitpy uses pandoc to do any file type conversion
        (md -> html|latex|...).

        ONLY SOME FEATURES OF knitr OR rmarkdown ARE YET SUPPORTED...
        """)

    examples = Unicode(u"""
        The simplest way to use knitpy is

        > knitpy mydocument.pymd

        which will convert mydocument.pymd to the default format (probably HTML).
        """)

    # Other configurable variables
    # '--to' ends up here
    export_format = CaselessStrEnum(VALID_OUTPUT_FORMAT_NAMES+["all"],
        default_value=DEFAULT_OUTPUT_FORMAT_NAME,
        config=True,
        help="""The export format to be used."""
    )

    # This is a workaround for https://github.com/ipython/ipython/issues/8025
    # a value of "all" is converted to the function `all` during commandline parsing, which
    # raises if that is set as `export_format`. So on config change, first change it back and
    # then call the original _config_changed(), which puts the config values to the traits
    def _config_changed(self, name, old, new):
        if get_by_name(new, "KnitpyApp.export_format", na=None) is all:
            new.KnitpyApp.export_format = "all"
        super(KnitpyApp, self)._config_changed(name, old, new)


    documents = List([], config=True, help="""List of documents to convert.
                 Wildcards are supported.
                 Filenames passed positionally will be added to the list.
                 """)

    keep_md = Bool(False, config=True,
        help="""Whether to keep the temporary md files""")

    log_to_file = Bool(False, config=True,
        help="""Whether to send the log to a file""")

    @catch_config_error
    def initialize(self, argv=None):
        super(KnitpyApp, self).initialize(argv) # sets the crash handler
        self.init_documents()


    def init_documents(self):
        """Construct the list of documents.
        If documents are passed on the command-line,
        they override documents specified in config files.
        Glob each document to replace document patterns with filenames.
        """

        # Specifying documents on the command-line overrides (rather than adds)
        # the documents list
        if self.extra_args:
            patterns = self.extra_args
        else:
            patterns = self.documents

        # Use glob to replace all the documents patterns with filenames.
        filenames = []
        for pattern in patterns:

            # Use glob to find matching filenames.  Allow the user to convert
            # documents without having to type the extension.
            globbed_files = glob.glob(pattern)
            globbed_files.extend(glob.glob(pattern + '.pymd'))
            if not globbed_files:
                self.log.warn("pattern %r matched no files", pattern)

            for filename in globbed_files:
                if not filename in filenames:
                    filenames.append(filename)
        self.documents = filenames

    def start(self):
        """
        Ran after initialization completed
        """
        super(KnitpyApp, self).start()
        self.convert_documents()

    def convert_documents(self):
        """
        Convert the documents in the self.document traitlet
        """
        # Export each documents
        conversion_success = 0

        kp = Knitpy(log=self.log, parent=self)

        for document_filename in self.documents:

            try:
                outfilenames = kp.render(document_filename, output=self.export_format)
            except ParseException as pe:
                self.log.error(str(pe))
                self.log.error("Error while converting '%s'. Aborting...", document_filename)
                exit(1)

            except Exception as e:
                self.log.error("Error while converting '%s'", document_filename, exc_info=True)
                exit(1)

            #Todo: add a config value... auto-open
            if self.export_format in ["html", "htm"]:
                import webbrowser
                webbrowser.open(outfilenames[0])
            conversion_success += 1

        # If nothing was converted successfully, help the user.
        if conversion_success == 0:
            self.print_help()
            sys.exit(-1)


# redefine the error message on crashes
# The price we pay for reusing the BaseIPythonApplication
_knitpy_lite_message_template = """
If you suspect this is an knitpy bug, please report it at:
    https://github.com/janschulz/knitpy/issues
or send an email to the mailing list at {email}

Extra-detailed tracebacks for bug-reporting purposes can be enabled via:
    {config}Application.verbose_crash=True
"""
import IPython.core.crashhandler as ch
ch._lite_message_template = _knitpy_lite_message_template


#-----------------------------------------------------------------------------
# Main entry point
#-----------------------------------------------------------------------------

launch_new_instance = KnitpyApp.launch_instance

if __name__ == '__main__':
    launch_new_instance()
