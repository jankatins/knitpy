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
import getpass
import datetime
import yaml
try:
    from queue import Empty  # Py 3
except ImportError:
    from Queue import Empty  # Py 2

from pypandoc import convert as pandoc

from IPython.config.configurable import LoggingConfigurable

from IPython.utils.traitlets import (
    Bool, Integer, CaselessStrEnum, CRegExp, Instance, Unicode, List
)
from IPython.utils import py3compat
from IPython.utils.py3compat import unicode_type
from IPython.utils.path import expand_path

# Stuff for the kernels
from IPython.kernel.multikernelmanager import MultiKernelManager
from IPython.kernel.kernelspec import KernelSpecManager

# Our own stuff
from .documents import (TemporaryOutputDocument, FinalOutputConfiguration, KnitpyOutputException,
                        VALID_OUTPUT_FORMAT_NAMES, DEFAULT_OUTPUT_FORMAT_NAME,
                        DEFAULT_FINAL_OUTPUT_FORMATS, IMAGE_FILEEXTENSION_TO_MIMETYPE)
from .engines import BaseKnitpyEngine, PythonKnitpyEngine
from .utils import CRegExpMultiline, _plain_text, _code, is_string
from IPython.utils.py3compat import iteritems

TBLOCK, TINLINE, TTEXT = range(3)

class KnitpyException(Exception):
    pass

class ParseException(KnitpyException):
    pass


class Knitpy(LoggingConfigurable):
    """Engine used to convert from python markdown (``*.pymd``) to html/latex/..."""
    keep_md = Bool(False, config=True,
        help="""Whether to keep the temporary md files""")

    log_to_file = Bool(False, config=True,
        help="""Whether to send the log to a file""")

    extra_document_configs = List(default_value=[], config=True,
                           help="Additional configurations for FinalOutputDocuments")

    default_export_format = CaselessStrEnum(VALID_OUTPUT_FORMAT_NAMES,
        default_value=DEFAULT_OUTPUT_FORMAT_NAME,
        config=True,
        help="""The export format to be used (can't by from extra_document_configs!)."""
    )

    kernel_debug = Bool(False, config=True,
        help="""Whether to output kernel messages to the (debug) log""")

    timeout = Integer(10, config=True, help="timeout for individual code executions")

    # Things for the parser...
    chunk_begin = CRegExpMultiline(r'^\s*```+\s*{[.]?(?P<engine>[a-z]+)\s*(?P<args>.*)}\s*$',
                                   config=True, help="chunk begin regex (must include the named "
                                                     "group 'engine' and 'args'")
    chunk_end = CRegExpMultiline(r'^\s*```+\s*$', config=True, help="chunk end regex")
    inline_code = CRegExpMultiline(r'`(?P<engine>[a-z]+) +([^`]+)\s*`', config=True,
                                   help="inline code regex (must include a named group 'engine')")
    comment_line = CRegExp(r'^\s*#',config=True, help="comment line regex")
    yaml_separator = CRegExpMultiline(r"^---\s*$", config=True,
                                      help="separator for the yaml metadata")

    def __init__(self, **kwargs):
        super(Knitpy,self).__init__(**kwargs)
        self.init_kernel_manager()
        self.init_engines()
        self.init_output_configurations()


    def init_kernel_manager(self):
        self._km = MultiKernelManager(log=self.log, parent=self)
        self._ksm = KernelSpecManager(log=self.log, parent=self)
        self._kernels = {}
        #ksm.find_kernel_specs()

    def init_engines(self):
        self._engines = {}
        self._engines["python"] = PythonKnitpyEngine(parent=self)
        # TODO: check that every kernel_name is in ksm.find_kernel_specs()

    def init_output_configurations(self):
        self._outputs = {}
        for config in DEFAULT_FINAL_OUTPUT_FORMATS:
            fod = FinalOutputConfiguration(parent=self, **config)
            self._outputs[config["name"]] = fod
            self._outputs[config["alias"]] = fod
        for config in self.extra_document_configs:
            fod = FinalOutputConfiguration(parent=self, **config)
            self._outputs[config["name"]] = fod
            self._outputs[config["alias"]] = fod

    def parse_document(self,input):
        if os.path.exists(input):
            filename = input
            f = codecs.open(filename, 'r', 'UTF-8')
            doc = f.read()
        else:
            doc = input
            filename = "anonymous_input"

        # the yaml can stay in the doc, pandoc will remove '---' blocks
        # pandoc will also do it's own interpretation and use title/author and so on...
        # ToDo: not sure of that should stay or if we should start with clean metadata
        # title, author, date
        # title: "A first try"
        # author: "Jan Schulz"
        # date: "Monday, February 23, 2015"
        # default values
        metadata = {"title":filename,
                         "author":getpass.getuser(),
                         "date": datetime.datetime.now().strftime("%A, %B %d, %Y")}

        pos = 0
        start = self.yaml_separator.search(doc, pos)
        if not start is None:
            end = self.yaml_separator.search(doc, start.end())
            if end is None:
                raise ParseException("Found no metadata end separator.")
            try:
                res = yaml.load(doc[start.end():end.start()])
                self.log.debug("Metadata: %s", res)
                metadata.update(res)
            except Exception as e:
                raise ParseException("Malformed metadata: %s" % str(e))

        parsed_doc = self._parse_blocks(doc)
        return parsed_doc, metadata

    def _parse_blocks(self, doc):
        result = []
        doc_pos = 0
        blocks = self.chunk_begin.finditer(doc)
        for block_start in blocks:
            # process the text before the match
            text = doc[doc_pos:block_start.start()]
            self._parse_inline(text, result)
            # TODO: somehow a empty line before a codeblock vanishes, so add one here
            result.append((TTEXT,"\n"))
            # now the block itself
            # find the end of the block
            block_end = self.chunk_end.search(doc, block_start.end())
            if block_end is None:
                raise ParseException("Found no end for the block starting at pos %s" % block_start.end())
            result.append((TBLOCK,(doc[block_start.end():block_end.start()], block_start.groupdict())))
            doc_pos = block_end.end()
        # text after the last block
        self._parse_inline(doc[doc_pos:], result)
        return result

    def _parse_inline(self, text, result):
        text_pos = 0
        for inline in self.inline_code.finditer(text):
            # text before inline code
            result.append((TTEXT,text[text_pos: inline.start()]))
            # inline code
            engine_offset = len(inline.group('engine'))+1
            result.append((TINLINE,(text[inline.start()+engine_offset+1:inline.end()-1], inline.groupdict())))
            text_pos = inline.end()
        # text after the last inline code
        result.append((TTEXT,text[text_pos:]))

    def _all_lines_comments(self, lines):
        for line in lines.split("\n"):
            if not self.comment_line.match(line):
                return False
        return True

    def convert(self, parsed, output):

        context = ExecutionContext(output=output)

        for entry in parsed:
            if entry[0] == TBLOCK:
                context.mode="block"
                self._process_code(entry[1], context=context)
            elif entry[0] == TINLINE:
                context.mode="inline"
                self._process_code(entry[1], context=context)
            elif entry[0] == TTEXT:
                output.add_text(entry[1])
            else:
                raise ParseException("Found something unexpected: %s" % entry)
        # process_code opened kernels, so close them here
        self._km.shutdown_all()
        # workaround for https://github.com/ipython/ipython/issues/8007
        # FIXME: remove if IPython >3.0 is in require
        self._km._kernels.clear()
        self._kernels = {}
        return output

    def _process_code(self, input, context):

        context.execution_started()

        # setup the execution context
        code = input[0]
        intro = input[1]
        engine_name =  intro["engine"]
        raw_args = intro.get("args","")


        args = self._parse_args(raw_args)

        # eval=False means that we don't execute the block at all
        if "eval" in args:
            _eval =  args.pop("eval")
            if _eval is False:
                return

        # for compatibility with knitr, where python is specified via "{r engine='python'}"
        if "engine" in args:
            engine_name = args.pop("engine")
            self.log.debug("Running on engine: %s", engine_name)

        try:
            engine = self._engines[engine_name]
        except:
            raise ParseException("Unknown codeblock type: %s" % engine_name)
        assert not engine is None, "Engine is None"
        context.engine = engine
        if not engine.name in context.enabled_documents:
            plotting_formats = context.output.export_config.accepted_image_formats
            plot_code = engine.get_plotting_format_code(plotting_formats)
            self._run_silently(context.engine.kernel, plot_code)
            context.enabled_documents.append(engine.name)
            self.log.info("Enabled image formats '%s' in engine '%s'.",
                          plotting_formats,
                          engine.name)

        # configure the context
        if "echo" in args:
            context.echo = args.pop("echo")

        if "results" in args:
            context.results = args.pop("results")

        if "include" in args:
            context.include = args.pop("include")

        if "chunk_label" in args:
            context.chunk_label = args.pop("chunk_label")
        else:
            context.chunk_label = u"unnamed-chunk-%s" % context.chunk_number

        if args:
            self.log.debug("Found unhandled args: %s", args)

        lines = ''
        for line in code.split('\n'):
            lines = lines + line
            msg = engine.kernel.is_complete(lines+"\n\n")
            reply = engine.kernel.get_shell_msg(timeout=self.timeout)
            assert reply['msg_type'] == 'is_complete_reply', str(reply)
            if self.kernel_debug:
                self.log.debug("completion_request: %s", msg)
            if reply['content']['status'] == 'complete':
                if lines.strip() == "":
                    # No requests for "no code"
                    lines = ""
                    continue
                elif self._all_lines_comments(lines):
                    # comments should go to to the next code block
                    lines += "\n"
                    continue
                self._run_lines(lines+"\n", context)
                lines = ""
            elif reply['content']['status'] == 'invalid':
                # TODO: not sure how this should be handled
                # Either abort execution of the whole file or just retry with the next line?
                # However this should be handled via a user message
                self.log.info("Code invalid:\n%s",  lines)
                context.output.add_execution_error("Code invalid",  lines)
                lines = ""
            else:
                lines += "\n"

        # This can only happen if the last line is incomplete
        # This will always result in an error!
        if lines.strip() != "":
            self._run_lines(lines, context)

        context.execution_finished()


    def _parse_args(self, raw_args):
        # Todo: knitr interprets all values, so code references are possible
        # This also means that we have to do args parsing at interpretation time, so that
        # variable from other code can be taken into account..

        args = {}
        if raw_args.strip() == "":
            return args
        # The first is special as that can be the name of the chunk
        first = True
        converter = {
            "True":True,
            "False":False,
            "T":True, # Rs True/False
            "F":False,
            "TRUE":True,
            "FALSE":False,
        }
        for arg in raw_args.split(","):
            arg = arg.strip()
            if not "=" in arg:
                if not first:
                    raise ParseException("Malformed options for code chunk: '%s' in '%s'" % (
                        arg,raw_args))
                args["chunk_label"] = arg
                continue
            first = False
            label, value = arg.split("=")
            v = value.strip()
            # convert to real types.
            # TODO: Should be done by submitting the whole thing to the kernel, like knitr does
            # -> variables form one codecell can be used in the args of the next one ...
            if (v[0] == '"' and v[-1] == '"'):
                v = v[1:-1]
            elif (v[0] == "'" and v[-1] == "'"):
                v = v[1:-1]
            elif v in converter:
                v = converter[v]
            else:
                try:
                    v = int(v)
                except:
                    self.log.error("Could not decode option value: '%s=%s'. Discarded...", label, v)
                    continue

            args[label.strip()] = v

        return args



    def _run_lines(self, lines, context):
        kernel = context.engine.kernel
        msg_id = kernel.execute(lines)
        if self.kernel_debug:
            self.log.debug("Executing lines (msg_id=%s):\n%s", msg_id, lines)
        # wait for finish, with timeout
        # At first we have to wait until the kernel tells us it is finished with running the code
        while True:
            try:
                msg = kernel.shell_channel.get_msg(timeout=self.timeout)
                if self.kernel_debug:
                    self.log.debug("shell msg: %s", msg)
            except Empty:
                # This indicates that something bad happened, as AFAIK this should return...
                self.log.error("Timeout waiting for execute reply")
                raise KnitpyException("Timeout waiting for execute reply.")
            if msg['parent_header'].get('msg_id') == msg_id:
                # It's finished, and we got our reply, so next look at the results
                break
            else:
                # not our reply
                self.log.debug("Discarding message from a different client: %s" % msg)
                continue

        # Now look at the results of our code execution and earlier completion requests
        # We handle messages until the kernel indicates it's ide again
        status_idle_again = False
        while True:
            try:
                msg = kernel.get_iopub_msg(timeout=self.timeout)
            except Empty:
                # There should be at least some messages: we just executed code!
                # The only valid time could be when the timeout happened too early (aka long
                # running code in the document) -> we handle that below
                self.log.warn("Timeout waiting for expected IOPub output")
                break

            if msg['parent_header'].get('msg_id') != msg_id:
                if msg['parent_header'].get(u'msg_type') != u'is_complete_request':
                    # not an output from our execution and not one of the complete_requests
                    self.log.debug("Discarding output from a different client: %s" % msg)
                else:
                    # complete_requests are ok
                    pass
                continue

            # Here we have some message which corresponds to our code execution
            msg_type = msg['msg_type']
            content = msg['content']

            # The kernel indicates some status: executing -> idle
            if msg_type == 'status':
                if content['execution_state'] == 'idle':
                    # When idle, the kernel has executed all input
                    status_idle_again = True
                    break
                else:
                    # the "starting execution" messages
                    continue
            elif msg_type == 'clear_output':
                # we don't handle that!?
                self.log.debug("Discarding unexpected 'clear_output' message: %s" % msg)
                continue
            ## So, from here on we have a messages with real content
            if self.kernel_debug:
                self.log.debug("iopub msg (%s): %s",msg_type, msg)
            if context.include:
                self._handle_return_message(msg, context)

        if not status_idle_again:
            self.log.error("Code lines didn't execute in time. Don't use long-running code in "
                           "documents or increase the timeout!")
            self.log.error("line(s): %s" % lines)

    def _handle_return_message(self, msg, context):
        if context.mode == "inline":
            #self.log.debug("inline: %s" % msg)
            if msg["msg_type"] == "execute_result":
                context.output.add_text(_plain_text(msg["content"]))
        elif context.mode == "block":
            #self.log.debug("block: %s" % msg)
            type = msg["msg_type"]
            if type == "execute_input":
                if context.echo:
                    context.output.add_code(_code(msg[u'content']))
            elif type == "stream":
                # {u'text': u'a\nb\nc\n', u'name': u'stdout'}
                # TODO: format stdout and stderr differently?
                txt = msg["content"].get("text","")
                if txt.strip() == "":
                    return
                if context.results == 'markup':
                    context.output.add_output(txt)
                elif context.results == 'asis':
                    context.output.add_asis(txt)
                elif context.results == 'hide':
                    return
                else:
                    # TODO: implement a caching system... again...
                    self.log.warn("Can't handle results='hold' yet, falling back to 'markup'.")
                    context.output.add_output(txt)
            elif (type == "execute_result") or (type == "display_data"):
                if context.results == 'hide':
                    return
                if context.results == 'hold':
                    self.log.warn("Can't handle results='hold' yet, falling back to 'markup'.")

                # Here we handle the output from the IPython display framework.
                # 1. If a object has a _display_ipython(), that will be called. This method should
                #    publish (one) display_data message and return -> the content ends up in
                #    "display_data" msg and the "executive_result" has no data
                # 2. else try different IPython.core.formatters for the object, which basically
                #    call the right _repr_<whatever>_ method to get a formated string in that
                #    mimetype. This is added as alternatives under content.data of the
                #    "executive_result".

                # data has/can have multiple types of the same message
                data = msg[u"content"][u'data']
                #self.log.debug(str(data))

                # handle plots
                #self.log.debug("Accepted image mimetypes: %s", context.output.export_config.accepted_image_mimetypes)
                for mime_type in context.output.export_config.accepted_image_mimetypes:
                    mime_data = data.get(mime_type, None)
                    if mime_data is None:
                        self.log.debug("No image found: %s", mime_type)
                        continue
                    try:
                        self.log.debug("Trying to include image...")
                        context.output.add_image(mime_type, mime_data, title="")
                    except KnitpyOutputException as e:
                        self.log.info("Couldn't include image: %s", e)
                        continue
                    return

                # now try some marked up text formats
                for mime_type in context.output.markup_mimetypes:
                    mime_data = data.get(mime_type, None)
                    if mime_data is None:
                        continue
                    try:
                        self.log.debug("Trying to include markup text...")
                        context.output.add_markup_text(mime_type, mime_data)
                    except KnitpyOutputException as e:
                        self.log.info("Couldn't include markup text: %s", e)
                        continue
                    return

                # as a last resort, try plain text...
                if u'text/plain' in data:
                    txt = data.get(u"text/plain", "")
                    if txt != "":
                        if context.results == 'markup':
                            context.output.add_output(txt)
                            if txt[-1] != "\n":
                                context.output.add_output("\n")
                        elif context.results == 'asis':
                            context.output.add_asis(txt)
                            if txt[-1] != "\n":
                                context.output.add_asis("\n")

                        return

                # If we are here,  we couldn't handle any of the more specific data types
                # and didn't find any output text
                excuse = "\n(Found data of type '{}', but couldn't handle it)\n"
                context.output.add_output(excuse.format(data.keys()))
            elif (type == "error"):
                ename = msg["content"].get("ename","unknown exception")
                evalue = msg["content"].get("evalue","unknown exception value")
                tb = msg["content"].get("traceback","<not available>")
                if not is_string(tb):
                    # remove the first line...
                    tb = "\n".join(tb[1:])
                self.log.info(tb)
                #there are ansi escape sequences in the traceback, which kills pandoc :-(
                if u"\x1b[1;32m" in tb:
                    tb = "!! traceback unavailable due to included color sequences;\n" \
                         "!! execute `%colors NoColor` once before this line to remove them!"
                context.output.add_execution_error("%s: %s" % (ename, evalue), tb)
            else:
                self.log.debug("Ignored msg of type %s" % type)


    def _run_silently(self, kc, lines):
        try:
            msg_id = kc.execute(lines + "\n\n", silent=self.kernel_debug, store_history=False)
            self.log.debug("Executed silent code: %s", lines)
            reply = kc.get_shell_msg(timeout=self.timeout)
            assert reply['parent_header'].get('msg_id') == msg_id, "Wrong reply! " + str(reply)
            if self.kernel_debug:
                self.log.debug("Silent code shell reply: %s", reply)
        except Empty:
            self.log.error("Code took too long:\n %s", lines)

        # now empty the iopub channel (there is at least a "starting" message)
        while True:
            try:
                msg = kc.get_iopub_msg(timeout=0.1)
                if self.kernel_debug:
                    self.log.debug("Silent code iopub msg: %s", msg)
            except Empty:
                break

    def _get_kernel(self, engine):
        kernel_name = engine.kernel_name
        kernel_startup_lines = engine.startup_lines

        if not kernel_name in self._kernels:
            self.log.info("Starting a new kernel: %s" % kernel_name)
            kernelid = self._km.start_kernel(kernel_name=kernel_name)
            #km.list_kernel_ids()
            kn = self._km.get_kernel(kernelid)
            kc = kn.client()
            self._kernels[kernel_name] = kc
            # now initalize the channels
            kc.start_channels()
            kc.wait_for_ready()
            self._run_silently(kc, kernel_startup_lines)
            self.log.info("Executed kernel startup lines for engine '%s'.", engine.name)

        return self._kernels[kernel_name]


    def get_output_format(self, fmt_name, config=None):
        self._ensure_valid_output(fmt_name)
        fod = self._outputs.get(fmt_name).copy()
        # self.log.info("%s: %s", fmt_name, config)
        if not config:
            pass
        elif isinstance(config, dict):
            fod.update(**config)
        elif config == "default":
            # html_document: default
            pass
        else:
            self.log.error("Unknown config for document '%s': '%s'. Ignored...",
                           fmt_name, config)
        return fod

    def _knit(self, input, outputdir_name, final_format="html", config=None):
        """Internal function to aid testing"""


        parsed, metadata = self.parse_document(input) # sets kpydoc.parsed and
        final_format = self.get_output_format(final_format, config=config)

        md_temp = TemporaryOutputDocument(fileoutputs=outputdir_name,
                                          export_config=final_format,
                                          log=self.log, parent=self)

        # get the temporary md file
        self.convert(parsed, md_temp)

        return md_temp.content


    def render(self, filename, output=None):
        """
        Convert the filename to the given output format(s)
        """
        # Export each documents
        conversion_success = 0
        converted_docs = []

        # save here to change back after the conversation.
        orig_cwd = os.getcwd()
        needs_chdir = False

        # expand $HOME and so on...
        filename = expand_path(filename)
        self.log.info("Converting %s..." % filename)

        basedir = os.path.dirname(filename)
        basename = os.path.splitext(os.path.basename(filename))[0]

        # It's easier if we just change wd to the dir of the file
        if unicode_type(basedir) != py3compat.getcwd():
            os.chdir(basedir)
            needs_chdir = True
            self.log.info("Changing to working dir: %s" % basedir)
            filename = os.path.basename(filename)


        outputdir_name = os.path.splitext(basename)[0] + "_files"

        # parse the input document
        parsed, metadata = self.parse_document(filename)

        # get the output formats
        # order: kwarg overwrites default overwrites document
        output_formats = [self._outputs[self.default_export_format]]
        if output is None:
            self.log.debug("Converting to default output format [%s]!" % self.default_export_format)
        elif output == "all":
            outputs = metadata.get("output", None)
            # if nothing is specified, we keep the default
            if outputs is None:
                self.log.debug("Did not find any specified output formats: using only default!")
            else:
                output_formats = []
                for fmt_name, config in iteritems(outputs):
                    fod = self.get_output_format(fmt_name, config)
                    output_formats.append(fod)
                self.log.debug("Converting to all specified output formats: %s" %
                               [fmt.name for fmt in output_formats])
        else:
            self._ensure_valid_output(output)
            output_formats = [self._outputs[output]]

        for final_format in output_formats:
            self.log.info("Converting document %s to %s", filename, final_format.name)
            # TODO: build a proper way to specify final output...

            md_temp = TemporaryOutputDocument(fileoutputs=outputdir_name,
                                              export_config=final_format,
                                              log=self.log, parent=self)

            # get the temporary md file
            self.convert(parsed, md_temp)
            if final_format.keep_md or self.keep_md:
                mdfilename = basename+"."+final_format.name+".md"
                self.log.info("Saving the temporary markdown as '%s'." % mdfilename)
                # TODO: remove the first yaml metadata block and
                # put "#<title>\n<author>\n<date>" before the rest
                with codecs.open(mdfilename, 'w+b','UTF-8') as f:
                    f.write(md_temp.content)

            # convert the md file to the final filetype
            input_format = "markdown" \
                           "+autolink_bare_uris" \
                           "+ascii_identifiers" \
                           "+tex_math_single_backslash-implicit_figures" \
                           "+fenced_code_attributes"

            extra = ["--smart", # typographically correct output (curly quotes, etc)
                     "--email-obfuscation", "none", #do not obfuscation email names with javascript
                     "--self-contained", # include img/scripts as data urls
                     "--standalone", # html with header + footer
                     "--section-divs",
                     ]

            outfilename = basename+"." +final_format.file_extension

            # exported is irrelevant, as we pass in a filename
            exported = pandoc(source=md_temp.content,
                              to=final_format.pandoc_export_format,
                              format=input_format,
                              extra_args=extra,
                              outputfile=outfilename)
            self.log.info("Written final output: %s" % outfilename)
            converted_docs.append(os.path.join(basedir, outfilename))
        if needs_chdir:
            os.chdir(orig_cwd)
        return converted_docs


    def _ensure_valid_output(self, fmt_name):
        if fmt_name in self._outputs:
            return
        raise KnitpyException("Format '%s' is not a valid output format!" % fmt_name)

class ExecutionContext(LoggingConfigurable):

    # These first are valid for the time of the existance of this contex
    output = Instance(klass=TemporaryOutputDocument, allow_none=True, config=False,
                            help="current output document")

    chunk_number = Integer(0, config=False, allow_none=False, help="current chunk number")
    def _chunk_number_changed(self, name, old, new):
        if old != new:
            self.chunk_label= None

    enabled_documents = List([], config=False, help="Names for enabled documents.")

    # the following are valid for the time of one code execution
    chunk_label = Unicode(None, config=False, allow_none=True, help="current chunk label")
    chunk_plot_number = Integer(0, config=False, allow_none=False,
                                help="current plot number in this chunk")
    def _chunk_label_changed(self, name, old, new):
        if old != new:
            self.chunk_plot_number = 0

    echo = Bool(True, config=False, help="If False, knitpy will not display the code in the code "
                                        "chunk above it's results in the final document.")

    results = CaselessStrEnum(default_value="markup", values=["markup", "hide", "hold", "asis"],
                              allow_none=False, config=False,
                              help="If 'hide', knitpy will not display the code’s results in the "
                                   "final document. If 'hold', knitpy will delay displaying all  "
                                   "output pieces until the end of the chunk. If 'asis', "
                                   "knitpy will pass through results without reformatting them "
                                   "(useful if results return raw HTML, etc.)")

    include = Bool(True, config=False, help="If False, knitpy will will run the chunk but not "
                                          "include the chunk in the final document.")

    mode = CaselessStrEnum(default_value=None, values=["inline", "block"],
                                 allow_none=True, config=False, help="current mode: inline or "
                                                                     "block")

    engine = Instance(klass=BaseKnitpyEngine, allow_none=True, config=False,
                            help="current engine")


    def __init__(self, output, **kwargs):
        super(ExecutionContext,self).__init__(**kwargs)
        self.output = output
        output.context = self

    def execution_started(self):
        self.chunk_number += 1

    def execution_finished(self):
        reset_needed = ["engine", "mode"
                        "chunk_label",
                        "include", "echo",  "include", "results"]
        for name in self.trait_names():
            if name in reset_needed:
                self.traits()[name].set_default_value(self)
