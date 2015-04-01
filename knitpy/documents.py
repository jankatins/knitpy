from __future__ import absolute_import, unicode_literals

import os
import tempfile
import re
from collections import OrderedDict
from pypandoc import convert as pandoc

# Basic things from IPython
from IPython.config.configurable import LoggingConfigurable
from IPython.utils.traitlets import Bool, Unicode, CaselessStrEnum, List, Instance
from IPython.utils.py3compat import iteritems

from .utils import is_iterable, is_string

TEXT, OUTPUT, CODE, ASIS = "text", "output", "code", "asis"


IMAGE_MIMETYPE_TO_FILEEXTENSION = OrderedDict([("image/png","png"),
                                        ("image/svg+xml","svg"),
                                        ("image/jpeg","jpg"),
                                        ("application/pdf","pdf")])
IMAGE_FILEEXTENSION_TO_MIMETYPE = dict([(v,k) for k,v in iteritems(
                                        IMAGE_MIMETYPE_TO_FILEEXTENSION)])

MARKUP_FORMAT_CONVERTER = OrderedDict([("text/markdown", "markdown"),
                                       ("text/x-markdown", "markdown"),
                                       ("text/html", "html"),
                                       ("text/latex", "latex")])

class KnitpyOutputException(Exception):
    pass

# this is the intersection of what matplotlib supports (eps, pdf, pgf, png, ps, raw, rgba, svg,
# svgz) and what IPython supports ('png', 'png2x', 'retina', 'jpg', 'jpeg', 'svg', 'pdf')...
_possible_image_formats = CaselessStrEnum(values=['pdf', 'png', 'svg'])

DEFAULT_FINAL_OUTPUT_FORMATS = [
    {"name": "html_document", "alias": "html",
     "pandoc_export_format": "html", "file_extension": "html",
     "accepted_image_formats": ["png", "svg"]},
    {"name": "word_document", "alias": "docx",
     "pandoc_export_format": "docx", "file_extension": "docx",
     "accepted_image_formats": ["png", "svg"]},
    {"name": "pdf_document", "alias": "pdf",
     "pandoc_export_format": "latex", "file_extension": "pdf",
     "accepted_image_formats": ["pdf"]},
    ]
VALID_OUTPUT_FORMAT_NAMES = [fmt["name"]  for fmt in DEFAULT_FINAL_OUTPUT_FORMATS] + \
                       [fmt["alias"]  for fmt in DEFAULT_FINAL_OUTPUT_FORMATS]

DEFAULT_OUTPUT_FORMAT_NAME = "html_document"

class FinalOutputConfiguration(LoggingConfigurable):
    """
    This class holds configuration information about the final output document.
    """

    name = Unicode("html_document", help="The name of this type of documents")

    alias = Unicode("html", help="The alias of this type of documents")

    pandoc_export_format = Unicode("html", help="The name of the pandoc export format")

    file_extension = Unicode("html", help="The file extension")

    keep_md = Bool(False, help="Whether to keep the temporary markdown file.")

    accepted_image_formats = List(
        trait=_possible_image_formats,
        default_value=['png', 'svg'], # that's for html, which does not use pdf
        config=False,
        help="""The accepted image formats."""
    )

    # This is atomatically filled from accepted_image_formats
    accepted_image_mimetypes = List(
        config=False,
        default_value=[IMAGE_FILEEXTENSION_TO_MIMETYPE[ifmt] for ifmt in ['png', 'jpg', 'svg']]
    )

    def _accepted_image_formats_changed(self, name, old, new):
        if new != old:
            converted = [IMAGE_FILEEXTENSION_TO_MIMETYPE[ifmt] for ifmt in new]
            self.accepted_image_mimetypes = converted

    def update(self, **config):
        """Update this

        :param config: dict of properties to be updated
        """
        for name, config_value in iteritems(config):
            if hasattr(self, name):
                setattr(self, name, config_value)
            else:
                self.log.error("Unknown config for document '%s': '%s:%s'. Ignored...",
                                      self.name, name, config_value)


    def copy(self):
        """Copy Constructor

        :return: copy of self
        """
        config = {}
        for name in self.trait_names():
            config[name] = getattr(self,name)
        new_fod = type(self)(**config)
        return new_fod



class TemporaryOutputDocument(LoggingConfigurable):

    output_debug = Bool(False, config=True,
        help="""Whether to print outputs to the (debug) log""")
    # TODO: put loglevel to debug of this is True...

    code_startmarker = Unicode("```{}", config=True,
                               help="Start of a code block, with language placeholder and "
                                    "without linefeed")
    code_endmarker = Unicode("```", config=True, help="end of a code block, without linefeed")
    output_startmarker = Unicode("```", config=True,
                                 help="Start of a output block, without linefeed")
    output_endmarker = Unicode("```", config=True, help="End of a output block, without linefeed")

    export_config = Instance(klass=FinalOutputConfiguration, help="Final output document configuration")


    plot_mimetypes = List(default_value=list(IMAGE_MIMETYPE_TO_FILEEXTENSION.keys()),
                          allow_none=False, config=True,
                          help="Mimetypes, which should be handled as plots.")

    markup_mimetypes = List(default_value=list(MARKUP_FORMAT_CONVERTER.keys()),
                            allow_none=False, config=True,
                            help="Mimetypes, which should be handled as markeduped text")

    context = Instance(klass="knitpy.knitpy.ExecutionContext", config=False, allow_none=True)

    def __init__(self, fileoutputs, export_config, **kwargs):
        super(TemporaryOutputDocument,self).__init__(**kwargs)
        self._fileoutputs = fileoutputs
        self.export_config = export_config
        self._output = []
        # Init the caching system (class variables cache the first output of a former conversion
        # in future runs)
        self._last_content = None
        self._cache_text = []
        self._cache_code = []
        self._cache_code_language = None
        self._cache_output = []


    @property
    def outputdir(self):
        if not os.path.isdir(self._fileoutputs):
            os.mkdir(self._fileoutputs)
            self.log.info("Support files will be in %s", os.path.join(self._fileoutputs, ''))

        return self._fileoutputs

    @property
    def plotdir(self):
        plotdir_name = "figure-%s" % self.export_config.file_extension
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
            if content_type == CODE:
                _type = "%s (%s)" % (content_type, self._cache_code_language)
            else:
                _type = content_type
            self.log.debug("Adding '%s': %s", _type, content)

        if content_type != self._last_content:
            self.flush()
            # make sure there is a newline after before the next differently formatted part,
            # so that pandoc doesn't get confused...
            if self._output:
                # only add such a line if we are between our own generated content, i.e. between
                # code and output or output and new code
                if ((content_type, self._last_content) == (CODE, OUTPUT) or
                    (content_type, self._last_content) == (OUTPUT, CODE)):
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
                                          IMAGE_MIMETYPE_TO_FILEEXTENSION[mimetype])
                f = open(os.path.join(self.plotdir, filename), mode='w+b')
            else:
                self.log.info("Context no specified: using random filename for image")
                f = tempfile.NamedTemporaryFile(suffix="."+IMAGE_MIMETYPE_TO_FILEEXTENSION[mimetype],
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
        if not MARKUP_FORMAT_CONVERTER[mimetype] in [to_format,
                                                     self.export_config.pandoc_export_format]:
            if "<table" in mimedata:
                # There is a bug in pandoc <=1.13.2, where th in normal tr is triggers "only
                # text" conversion.
                msg = "Trying to fix tables for conversion with pandoc (bug in pandoc <=1.13.2)."
                self.log.debug(msg)
                mimedata = self._fix_html_tables_old_pandoc(mimedata)

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

    def _fix_html_tables_old_pandoc(self, htmlstring):
        """
        Fix html tables, so that they are recognized by pandoc

        pandoc in <=1.13.2 converts tables with '<th>' and <td> to plain text (each cell one
        paragraph. Remove all <th> in later rows (tbody) by replacing it with <td>. This is
        close to the same solution as taken by pandoc in 1.13.3 and later.

        See also: https://github.com/jgm/pandoc/issues/2015
        """
        result = []
        pos = 0
        re_tables = re.compile(r"<table.*</table>", re.DOTALL)
        re_tbody = re.compile(r"<tbody.*</tbody>", re.DOTALL)
        tables = re_tables.finditer(htmlstring)
        for table in tables:
            # process the html before the match
            result.append(htmlstring[pos:table.start()])
            # now the table itself
            table_html = htmlstring[table.start():table.end()]
            tbody = re_tbody.search(table_html)
            if not tbody is None:
                result.append(table_html[0:tbody.start()])
                tbody_html = table_html[tbody.start():tbody.end()]
                tbody_html = tbody_html.replace("<th","<td")
                tbody_html = tbody_html.replace("</th>", "</td>")
                result.append(tbody_html)
                result.append(table_html[tbody.end():])
            else:
                result.append(table_html)
            pos = table.end()
        result.append(htmlstring[pos:])

        return "".join(result)



    def add_execution_error(self, error, details=""):
        msg = "\n**ERROR**: %s\n\n" % error
        if details:
            msg += "```\n%s\n```\n" % details
        self.add_asis(msg)
