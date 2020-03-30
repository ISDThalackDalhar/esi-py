from esi.utils import ASYNC_SUPPORTED
from esi.version import __version__
from esi.exceptions import ESIException, ESIScopeRequired, MissingPackageError, InvalidSpecError, ValidationError,\
    ESIResponseError

__all__ = [
    '__version__',

    'ESIException',
    'ESIScopeRequired',
    'MissingPackageError',
    'InvalidSpecError',
    'ValidationError',
    'ESIResponseError',

    'ASYNC_SUPPORTED',
]

if __name__ == '__main__':
    from esi.commands import generate
    generate()
