# knitpy: Elegant, flexible and fast dynamic report generation with python

This is a port of knitr (http://yihui.name/knitr/) and rmarkdown
(http://rmarkdown.rstudio.com/) to python.

For a description of the code format see http://rmarkdown.rstudio.com/ and replace
`{r <r style options>}` by `{python <python style options>}` and of course use python 
code blocks...

It uses the IPython kernel infrastructure to execute code, so all kernels for IPython 
are (aem... can potentially be) supported.

## What works:
* `knitpy filename.pymd` will convert filename `filename.pymd` to the defaul output format `html`.
* output formats `html`, `pdf` and `docx`. Change with `--to=<format>`
* code blocks and inline code
* plots are shown inline
* code chunk arguments `eval`, `results` (apart form "hold"), `include` and `echo`
* errors in code chunks are shown in the document
* config files: generate a empty one with `knitpy --init --profile-dir=.`
* using it from python (-> your app/ ipython notebook): 
  `import knitpy; knitpy.render(filename.pymd, output="html")` will convert `filename.pymd`
  to `filename.html`. `output=all` will convert to all document types (as specified in the 
  YAML header of the document). The call will return a list of converted documents.
* debugging with ``--debug`, `--kernel-debug=True`, `--output-debug=True`

## What does not work (=everything else :-) ):
* YAML headers are currently mostly ignored
* some advertised command-line options are ignored
* most code chunk arguments (apart from the ones above) are ignored
* probably lots of other stuff...

## Todo
* fix the above...
* use chunk labels in file names
  - if no chunk label, count up: "unnamed-chunk-1"
  - count up the produced files: <chunkname>-1.png
  - cleanup?
* refactor the parsing, so that it is line based
  - errors make more sense, because it knows the line ("block starting at line....")
* add some traits for the default pdflatex/pandoc executeable, so they don't have to be in path
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
* chunk caching