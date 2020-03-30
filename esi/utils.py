import os
import re
import sys
from argparse import ArgumentTypeError

from esi.version import __version__

SWAGGER_SPEC_URLS = [
    'legacy',
    'latest',
    'dev',
    '_legacy',
    '_latest',
    '_dev',
]
SWAGGER_META_URL = "https://esi.evetech.net/swagger.json"
SWAGGER_BASE_URL = "https://esi.evetech.net/{spec}/swagger.json"
ASYNC_SUPPORTED = sys.version_info >= (3, 5)
USER_AGENT = "esi-py/%s" % __version__


def try_int(x, default=None):
    """
    Try to convert to an integer
    """
    try:
        return int(x)
    except ValueError:
        return default


FIRST_CAPS = re.compile(r'(.)([A-Z][a-z]+)')
ALL_CAPS = re.compile(r'([a-z0-9])([A-Z])')


def to_camel_case(name: str) -> str:
    name = name.replace('-', '_').replace(' ', '_')
    name = FIRST_CAPS.sub(r'\1_\2', name)
    return ALL_CAPS.sub(r'\1_\2', name).lower().replace('__', '_')


def to_snake_case(name: str) -> str:
    name = name.replace('-', '_').replace(' ', '_')
    first, *others = name.split('_')
    return ''.join([first.lower(), *map(str.title, others)])


def to_pascal_case(name: str, allow_double_under=False) -> str:
    name = name.replace('_', '-')
    if allow_double_under:
        name = name.replace('--', '_-')
    name = name.replace(' ', '-')
    return ''.join(map(str.title, name.split('-')))


class cached_property:
    """
    Decorator that converts a method with a single self argument into a
    property cached on the instance.

    Optional ``name`` argument allows you to make cached properties of other
    methods. (e.g.  url = cached_property(method, name='url') )

    Originally from Django ( https://github.com/django/django/blob/master/django/utils/functional.py )
    """
    def __init__(self, func, name=None):
        self.func = func
        self.__doc__ = getattr(func, '__doc__')
        self.name = name or func.__name__

    def __get__(self, instance, cls=None):
        """
        Call the function and put the return value in instance.__dict__ so that
        subsequent attribute access on the instance returns the cached value
        instead of calling cached_property.__get__().
        """
        if instance is None:
            return self
        res = instance.__dict__[self.name] = self.func(instance)
        return res


class PathType(object):
    def __init__(self, exists=True, type='file', dash_ok=False):
        """
        exists:
            True: a path that does exist
            False: a path that does not exist, in a valid parent directory
            None: don't care
        type: file, dir, symlink, None, or a function returning True for valid paths
            None: don't care
        dash_ok: whether to allow "-" as stdin/stdout

        Originally from https://mail.python.org/pipermail/stdlib-sig/2015-July/000990.html
        """

        assert exists in (True, False, None)
        assert type in ('file', 'dir', 'symlink', None) or hasattr(type, '__call__')

        self._exists = exists
        self._type = type
        self._dash_ok = dash_ok

    def __call__(self, string):
        if string == '-':
            # the special argument "-" means sys.std{in,out}
            if self._type == 'dir':
                raise ArgumentTypeError('standard input/output (-) not allowed as directory path')
            elif self._type == 'symlink':
                raise ArgumentTypeError('standard input/output (-) not allowed as symlink path')
            elif not self._dash_ok:
                raise ArgumentTypeError('standard input/output (-) not allowed')
        else:
            e = os.path.exists(string)
            if self._exists is True:
                if not e:
                    raise ArgumentTypeError("path does not exist: '%s'" % string)

                if self._type is None:
                    pass
                elif self._type == 'file':
                    if not os.path.isfile(string):
                        raise ArgumentTypeError("path is not a file: '%s'" % string)
                elif self._type == 'symlink':
                    if not os.path.symlink(string):
                        raise ArgumentTypeError("path is not a symlink: '%s'" % string)
                elif self._type == 'dir':
                    if not os.path.isdir(string):
                        raise ArgumentTypeError("path is not a directory: '%s'" % string)
                elif not self._type(string):
                    raise ArgumentTypeError("path not valid: '%s'" % string)
            else:
                if self._exists is False and e:
                    raise ArgumentTypeError("path exists: '%s'" % string)

                p = os.path.dirname(os.path.normpath(string)) or '.'
                if not os.path.isdir(p):
                    raise ArgumentTypeError("parent path is not a directory: '%s'" % p)
                elif not os.path.exists(p):
                    raise ArgumentTypeError("parent directory does not exist: '%s'" % p)
        return string
