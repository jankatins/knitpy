# knitpy: Elegant, flexible and fast dynamic report generation with python

This is a port of knitr (http://yihui.name/knitr/) and rmarkdown
(http://rmarkdown.rstudio.com/) to python.

To start with, you can run the [example overview document](examples/knitpy_overview.pymd). To 
convert to all defined output formats, run `knitpy --to="all"  -- examples\knitpy_overview.pymd`.
This will produce a `html`, `docx` and `pdf` output (if you have `pdflatex` in path). You can 
view a [markdown rendered](examples/knitpy_overview.html_document.md) and a 
[html rendered](http://htmlpreview.github.io/?https://github.com/JanSchulz/knitpy/blob/master/examples/knitpy_overview.html)
version of this file. It's not yet as pretty as the knitr version...

For a description of the code format see http://rmarkdown.rstudio.com/ and replace
`{r <r style options>}` by `{python <python style options>}` and of course use python 
code blocks...

It uses the IPython kernel infrastructure to execute code, so all kernels for IPython 
are (aem... can potentially be) supported.

## What works:
* code blocks and inline code
* plots are shown inline
* `knitpy filename.pymd` will convert filename `filename.pymd` to the default output format `html`.
* output formats `html`, `pdf` and `docx`. Change with `--to=<format>`
* `--to=all` will convert to all export formats specified in the yaml header
* code chunk arguments `eval`, `results` (apart form "hold"), `include` and `echo`
* errors in code chunks are shown in the document
* uses the IPython display framework, so rich output for objects implementing `_repr_html_()` or 
  `_repr_markdown_()`. Mimetypes not understood by the final output format are automatically 
  converted via pandoc.
* config files: generate an empty one with `knitpy --init --profile-dir=.`
* using it from python (-> your app/ ipython notebook): 
  `import knitpy; knitpy.render(filename.pymd, output="html")` will convert `filename.pymd`
  to `filename.html`. `output=all` will convert to all document types (as specified in the 
  YAML header of the document). The call will return a list of converted documents.
* debugging with ``--debug`, `--kernel-debug=True`, `--output-debug=True`

## What does not work (=everything else :-) ):
* most YAML headers are currently ignored
* some advertised command-line options are ignored
* most code chunk arguments (apart from the ones above) are ignored
* probably lots of other stuff...

## Todo
* fix the above...
* refactor the parsing, so that it is line based
  - errors make more sense, because it knows the line ("block starting at line....")
* add some traits for the default pdflatex/pandoc executeable, so they don't have to be in path
* the final output has to configure the "includeable" markup docs
  - html in html
  - latex in html?
  - ...
* more arguments for code blocks
* more output formats? -> make output format configurable
* more unit-/outputtests...
  - codeblocks + inline
  - yaml
  - errors
  - pandoc caller (via mocks?)
* Documentation
  - what works? what is not supported?
  - differences to rmarkdown / knitr?
* implement more kernel engines (R...) and make it possible to supply/change ones 
  (for installed kernels for python2/3 or coda environments)
* implement a nice default html template
  -  Try https://github.com/timtylin/scholdoc-templates
* implement "code tidying"
  - maybe use https://github.com/google/yapf?
* use metadata in keep_md output (like rmarkdown does...
  - should output `#<title>\n<author>\n<date>` before the rest
  - remove the first yaml block, but keep everything else...
* chunk caching
