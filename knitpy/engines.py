from __future__ import absolute_import, unicode_literals

__all__ = ["PythonKnitpyEngine"]

LANGUAGE_ENGINES = []

from IPython.config.configurable import LoggingConfigurable
from IPython.utils.traitlets import Bool, Unicode, CaselessStrEnum, Instance


class BaseKnitpyEngine(LoggingConfigurable):
    name = "<NOT_EXISTANT>"
    kernel_name = "<NOT_EXISTANT>"
    startup_lines = ""

    @property
    def kernel(self):
        return self.parent._get_kernel(self)

    def get_plotting_format_code(self, formats):
        """
        Enables the supplied plotting formats in the backend

        formats : list of strings
             the plotting formats. e.g. `["pdf", "png", "jpeg"]`

        returns string
            The code which should be run on the kernel to set the default plotting formats
        """
        raise NotImplementedError


class PythonKnitpyEngine(BaseKnitpyEngine):

    name = "python"
    kernel_name = "python"
    startup_lines = "# Bad things happen if tracebacks have ansi escape sequences\n" +\
                    "%colors NoColor\n"

    def get_plotting_format_code(self, formats):
        valid_formats = ["png", "jpg", "jpeg", "pdf"]
        code = "%matplotlib inline\n" +\
               "from IPython.display import set_matplotlib_formats\n" +\
               "set_matplotlib_formats({0})\n"
        formats = [fmt for fmt in formats if fmt in valid_formats]
        if not formats:
            raise Exception("No valid output format found! Aborting...")

        fmt_string = "', '".join(formats)
        fmt_string = "'"+fmt_string+"'"
        return code.format(fmt_string)
