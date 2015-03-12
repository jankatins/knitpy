__author__ = 'jschulz'

from IPython.utils.py3compat import string_types

class _NA_DEFAULT_CLASS(object):
        pass
_NA_DEFAULT = _NA_DEFAULT_CLASS()
def get_by_name(dict_like, name, na="<n/a"):
    res = dict_like
    for part in name.split("."):
        try:
            res = res.get(part, _NA_DEFAULT)
        except:
            return na
        if res is _NA_DEFAULT:
            return na
    return res


def filter_for_debug(msg, names=None):

    if names is None:
        names = ['msg_type', 'content.data']

    # example...
    exl = {'parent_header':
               {u'username': u'username', u'version': u'5.0', u'msg_type':
                u'execute_request', u'msg_id': u'4383f7f6-0b2f-4ad8-80c8-4f790e3bf389',
                u'session': u'6925e9c2-29f1-44a6-9af1-8b375bc996cc',
                u'date': datetime.datetime(2015, 2, 26, 1, 44, 45, 925000)},
           'msg_type': u'execute_reply',
           'msg_id': u'8b22db97-9106-40cb-9e23-eda214bfa499',
           'content': {u'status': u'ok', u'execution_count': 2, u'user_expressions': {},
                      u'payload': []},
           'header': {u'username': u'username', u'version': u'5.0',
                      u'msg_type': u'execute_reply',
                      u'msg_id': u'8b22db97-9106-40cb-9e23-eda214bfa499',
                      u'session': u'45cc1a4f-dd43-4067-838d-412e2e16bb7d',
                      u'date': datetime.datetime(2015, 2, 26, 1, 44, 45, 936000)},
           'buffers': [],
           'metadata': {u'dependencies_met': True,
                        u'engine': u'6364f52f-1366-4e5c-999e-326736541ff1',
                        u'status': u'ok', u'started': u'2015-02-26T01:44:45.926000'}
    }
    ret = {}
    for name in names:
        ret[name] = get_by_name(msg, name)
    return ret

def _plain_text(content):
    data = content.get(u'data')
    if not data is None:
        return data.get(u'text/plain', "")
    else:
        return ""

def _code(content):
    return content.get(u'code',"")

def is_iterable(obj):
    'return true if *obj* is iterable'
    try:
        iter(obj)
    except TypeError:
        return False
    return True

def is_string(obj):
    return isinstance(obj, string_types)

from IPython.utils.traitlets import TraitType
import re
class CRegExpMultiline(TraitType):
    """A casting compiled regular expression trait.

    Accepts both strings and compiled regular expressions. The resulting
    attribute will be a compiled regular expression."""

    info_text = 'a regular expression'

    def validate(self, obj, value):
        try:
            return re.compile(value, re.MULTILINE)
        except:
            self.error(obj, value)
