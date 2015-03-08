# knitpy: Elegant, flexible and fast dynamic report generation with python

This is a port of knitr (http://yihui.name/knitr/) and rmarkdown 
(http://rmarkdown.rstudio.com/) to python.

For a description of the code format see http://rmarkdown.rstudio.com/ and replace
`{r...}` by `{python ...}` and of course use python code blocks...

It uses the IPython kernel infrastructure to execute code, so all kernels for IPython 
are (aem... can potentially be) supported.

## What works:
* converting a simple pymd file via `knitpy document.pymd`. Both code blocks and 
  inline code are supported
* output format `html` and `docx`
* debugging: ``--debug`, `--kernel-debug=True`

## What does not work (=everything else :-) ):
* other output format than html and docx
* YAML headers are currently ignored...
* arguments for code blocks (`{python block_name, arg=val}` -> currently, everything 
  after `python` will be ignored...
* messages to stderr will not show up...
* most advertised command-line options
* probably lots of other stuff...

## Todo
* fix the above...
* fix output format: what should be exported in knitpyapp, knitpy and how should the return 
  from knitpy.render look like
* refactor the parsing, so that it is line based
  - errors make more sense, because it knows the line ("block starting at line....")
* make output format configurable
* unittests...
  - should probably be done by a simple dir + textfiles ala test_input.pymd, test_output.md
  - codeblocks + inline
  - yaml
  - errors
  - pandoc caller (via mocks?)
* travis...
* Documentation
  - what works? what is not supported?
  - differences to rmarkdown / knitr?
* put the mimetype handling into the output document (next to `add_code`, etc)
* sane naming scheme for plots/... -> subdirs, naming-by-chunk-name
* implement more kernel engines (R...) and make it possible to supply/change ones 
  (for installed kernels for python2/3 or coda environments)
* implement a nice default html template
* use metadata in keep_md output (like rmarkdown does...
  - should output `#<title>\n<author>\n<date>` before the rest
  - remove the first yaml block, but keep everything else...
