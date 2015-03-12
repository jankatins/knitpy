from __future__ import absolute_import, unicode_literals

import os
import tempfile
import re
from collections import OrderedDict
from pypandoc import convert as pandoc

# Basic things from IPython
from IPython.config.configurable import LoggingConfigurable
from IPython.utils.traitlets import Bool, Unicode, CaselessStrEnum, List, Instance

from .utils import is_iterable, is_string

TEXT, OUTPUT, CODE, ASIS = "text", "output", "code", "asis"

OUTPUT_FORMATS = {
    #name: (pandoc_to_format, fileending)
    "html": ("html", "html"),
    "pdf": ("latex", "pdf"),
    "docx": ("docx", "docx")
}

VALID_OUTPUT_FORMATS = OUTPUT_FORMATS.keys()
DEFAULT_OUTPUT_FORMAT = "html"

IMAGE_FORMAT_FILEENDINGS = OrderedDict([("image/png","png"), ("image/svg","svg")])
MARKUP_FORMAT_CONVERTER = OrderedDict([("text/markdown", "markdown"),
                                       ("text/x-markdown", "markdown"),
                                       ("text/html", "html"),
                                       ("text/latex", "latex")])

class KnitpyOutputException(Exception):
    pass

class MarkdownOutputDocument(LoggingConfigurable):

    output_debug = Bool(False, config=True,
        help="""Whether to print outputs to the (debug) log""")
    # TODO: put loglevel to debug of this is True...

    code_startmarker = Unicode("``` {}", config=True,
                               help="Start of a code block, with language placeholder and "
                                    "without linefeed")
    code_endmarker = Unicode("```", config=True, help="end of a code block, without linefeed")
    output_startmarker = Unicode("```", config=True,
                                 help="Start of a output block, without linefeed")
    output_endmarker = Unicode("```", config=True, help="End of a output block, without linefeed")

    export_format = CaselessStrEnum(VALID_OUTPUT_FORMATS,
        default_value=DEFAULT_OUTPUT_FORMAT,
        config=False,
        help="""The export format to be used."""
    )


    plot_mimetypes = List(default_value=IMAGE_FORMAT_FILEENDINGS.keys(), allow_none=False,
                          config=True,
                          help="Mimetypes, which should be handled as plots.")

    markup_mimetypes = List(default_value=MARKUP_FORMAT_CONVERTER.keys(), allow_none=False,
                          config=True,
                          help="Mimetypes, which should be handled as markeduped text")

    context = Instance(klass="knitpy.knitpy.ExecutionContext", config=False, allow_none=True)

    def __init__(self, fileoutputs, export_format="html", **kwargs):
        super(MarkdownOutputDocument,self).__init__(**kwargs)
        self._fileoutputs = fileoutputs
        if export_format.endswith("_document"):
            export_format = export_format[:-9]
        self.export_format = export_format
        self._output = []

    @property
    def outputdir(self):
        if not os.path.isdir(self._fileoutputs):
            os.mkdir(self._fileoutputs)
            self.log.info("Support files will be in %s", os.path.join(self._fileoutputs, ''))

        return self._fileoutputs

    @property
    def plotdir(self):
        plotdir_name = "figure-%s" % self.export_format
        plotdir = os.path.join(self.outputdir, plotdir_name)
        if not os.path.isdir(plotdir):
            os.mkdir(plotdir)
        return plotdir

    @property
    def content(self):
        self.flush()
        return "".join(self._output)

    # The caching system is needed to make fusing together same "type" of content possible
    # -> code inputs without output should go to the same block
    _last_content = None
    _cache_text = []
    _cache_code = []
    _cache_code_language = None
    _cache_output = []

    def flush(self):
        if self.output_debug:
            self.log.debug("Flushing caches in output.")
        if self._cache_text:
            self._output.extend(self._cache_text)
            self._cache_text = []
        if self._cache_code:
            self._output.append(self.code_startmarker.format(self._cache_code_language))
            self._output.append("\n")
            self._output.extend(self._cache_code)
            self._output.append(self.code_endmarker)
            self._output.append("\n")
            self._cache_code = []
            self._cache_code_language = None
        if self._cache_output:
            self._output.append(self.output_startmarker)
            self._output.append("\n")
            self._output.extend(self._cache_output)
            self._output.append(self.output_endmarker)
            self._output.append("\n")
            self._cache_output = []

    def _add_to_cache(self, content, content_type):

        if is_string(content):
            content = [content]
        elif is_iterable(content):
            pass
        else:
            content = [u"%s" % content]

        if self.output_debug:
            self.log.debug("Adding '%s': %s", content_type, content)

        if content_type != self._last_content:
            self.flush()
            # make sure there is a newline after befor ethe next differently formatted part,
            # so that pandoc doesn't get confused...
            self._output.append("\n")
        if content_type == CODE:
            cache = self._cache_code
            self._last_content = CODE
        elif content_type == OUTPUT:
            cache = self._cache_output
            self._last_content = OUTPUT
        elif content_type == ASIS:
            # just add it as normal text
            cache = self._cache_text
            self._last_content = TEXT
        else:
            cache = self._cache_text
            self._last_content = TEXT

        cache.extend(content)

    def add_code(self, code, language="python"):
        if language != self._cache_code_language:
            self.flush()
        self._cache_code_language = language
        self._add_to_cache(code, CODE)

    def add_output(self, output):
        self._add_to_cache(output, OUTPUT)

    def add_text(self, text):
        self._add_to_cache(text, TEXT)

    def add_asis(self, content):
        self._add_to_cache(content, ASIS)

    def add_image(self, mimetype, mimedata, title=""):
        try:
            import base64
            mimedata = base64.decodestring(mimedata)
            # save as a file
            if not self.context is None:
                filename = u"%s-%s.%s" % (self.context.chunk_label,
                                          self.context.chunk_plot_number,
                                          IMAGE_FORMAT_FILEENDINGS[mimetype])
                f = open(os.path.join(self.plotdir, filename), mode='w+b')
            else:
                self.log.info("Context no specified: using random filename for image")
                f = tempfile.NamedTemporaryFile(suffix="."+IMAGE_FORMAT_FILEENDINGS[mimetype],
                                                prefix='plot', dir=self.plotdir, mode='w+b',
                                                delete=False)
            f.write(mimedata)
            f.close()
            relative_name= "%s/%s/%s" % (self.outputdir, os.path.basename(self.plotdir),
                                         os.path.basename(f.name))
            self.log.info("Written file of type %s to %s", mimetype, relative_name)
            template = "![%s](%s)"
            self.add_asis("\n")
            self.add_asis(template % (title, relative_name))
            self.add_asis("\n")
        except Exception as e:
            self.log.exception("Could not save a image")
            raise KnitpyOutputException(str(e))


    def add_markup_text(self, mimetype, mimedata):
        # workaround for some pandoc weirdness:
        # pandoc interprets html with indention as code and formats it with pre
        # So remove all linefeeds/whitespace...
        if mimetype == "text/html":
            res= []
            for line in mimedata.split("\n"):
                res.append(line.strip())
            mimedata = "".join(res)
            # pandas adds multiple spaces if one element in a column is long, but the rest is
            # short. Remove these spaces, as pandoc doesn't like them...
            mimedata = re.sub(' +',' ', mimedata)

        to_format = "markdown"
        # try to convert to the current format so that it can be included "asis"
        if not MARKUP_FORMAT_CONVERTER[mimetype] in [to_format, self.export_format]:
            if "<table" in mimedata:
                raise KnitpyOutputException("pandoc can't convert html tables to markdown, "
                                            "skipping...")
            try:
                self.log.debug("Converting markup of type '%s' to '%s' via pandoc...",
                               mimetype, to_format)
                mimedata = pandoc(mimedata, to=to_format, format=MARKUP_FORMAT_CONVERTER[mimetype])
            except RuntimeError as e:
                # these are pypandoc errors
                msg = "Could not convert mime data of type '%s' to output format '%s'."
                self.log.debug(msg, mimetype, to_format)
                raise KnitpyOutputException(str(e))
            except Exception as e:
                msg = "Could not convert mime data of type '%s' to output format '%s'."
                self.log.exception(msg, mimetype, to_format)
                raise KnitpyOutputException(str(e))

        self.add_asis("\n")
        self.add_asis(mimedata)
        self.add_asis("\n")


    def add_execution_error(self, error, details=""):
        msg = "\n**ERROR**: %s\n\n" % error
        if details:
            msg += "```\n%s\n```\n" % details
        self.add_asis(msg)
