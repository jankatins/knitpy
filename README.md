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
* Inline plots
* output format `html`, `pdf` and `docx`
* code chunk arguments `eval`, `results` (apart form "hold", `include` and `echo`
* debugging: ``--debug`, `--kernel-debug=True`

## What does not work (=everything else :-) ):
* YAML headers are currently ignored...
* some advertised command-line options
* chunk names are ignored, no caching system
* probably lots of other stuff...

## Todo
* fix the above...
* refactor the parsing, so that it is line based
  - errors make more sense, because it knows the line ("block starting at line....")
* the final output has to configure the output plot types: 
  - pdf can't use svg, prefers pdf
  - html can handle svg but not pdf...
* the final output has to configure the "includeable" markup docs
  - html in html
  - latex in html?
  - ...
* more arguments for code blocks
* more output formats? -> make output format configurable
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
* sane naming scheme for plots/... -> subdirs, naming-by-chunk-name
* implement more kernel engines (R...) and make it possible to supply/change ones 
  (for installed kernels for python2/3 or coda environments)
* implement a nice default html template
* use metadata in keep_md output (like rmarkdown does...
  - should output `#<title>\n<author>\n<date>` before the rest
  - remove the first yaml block, but keep everything else...
