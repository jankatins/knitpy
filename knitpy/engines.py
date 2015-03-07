from __future__ import absolute_import, unicode_literals

__all__ = ["PythonKnitpyEngine"]

LANGUAGE_ENGINES = []

from IPython.config.configurable import LoggingConfigurable
from IPython.utils.traitlets import Bool, Unicode, CaselessStrEnum, Instance


class BaseKnitpyEngine(LoggingConfigurable):

    kernel_name = "<NOT_EXISTANT>"
    startup_lines = ""

    @property
    def kernel(self):
        return self.parent._get_kernel(self)


class PythonKnitpyEngine(BaseKnitpyEngine):

    kernel_name = "python"
    startup_lines = "%matplotlib inline\print('Loaded matplotlib')"

    def wrap_code(self, text):
        begin = "\n```python\n"
        end = "\n```\n"
        return begin + text + end


