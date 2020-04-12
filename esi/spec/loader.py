import json
from distutils.version import StrictVersion
from urllib.parse import urlunparse

import jsonref
import httpx

from esi.exceptions import InvalidSpecError
from esi.spec.parameter import Parameter
from esi.spec.path import Path
from esi.spec.schema import Schema
from esi.utils import USER_AGENT, SWAGGER_SPEC_URLS, SWAGGER_BASE_URL, SWAGGER_META_URL


class ESISpec:
    def __init__(self, data):
        self.global_definitions = {}
        self.global_parameters = {}
        self.paths = {}
        self.paths_per_method = {}

        self._data = data
        # Load our global stuff before we go through the references
        self.load_globals()
        # Convert it to allow references
        self._data = jsonref.JsonRef.replace_refs(self._data, base_uri="")
        # Build our path list
        self.load_paths()

    def combine_defs(self, other):
        self.global_parameters.update({
            key: val
            for key, val in other.global_parameters.items()
            if key not in self.global_parameters
        })
        self.global_definitions.update({
            key: val
            for key, val in other.global_definitions.items()
            if key not in self.global_definitions
        })

    def combine_functions(self, other):
        paths = {
            key: val
            for key, val in other.paths.items()
            if key not in self.paths
        }
        for key, val in paths.items():
            self.paths[key] = val
            self.paths_per_method.setdefault(val.method, {})[key] = val

    def __iadd__(self, other):
        self.combine_defs(other)
        self.combine_functions(other)
        return self

    def load_globals(self):
        defs = self._data.get('definitions', {})
        for key in list(defs.keys()):
            obj = Schema.from_json(defs[key], is_global=True)
            defs[key] = self.global_definitions[key] = obj

        params = self._data.get('parameters', {})
        for key in list(params.keys()):
            obj = Parameter.from_json(params[key], is_global=True)
            params[key] = self.global_parameters[key] = obj

    def load_paths(self):
        for url, methods in self._data.get('paths', {}).items():
            for method, data in methods.items():
                path = Path(url, method, data)
                self.paths[path.operation_id] = path
                self.paths_per_method.setdefault(path.method, {})[path.operation_id] = path

    @property
    def host(self):
        return self._data.get('host')

    @property
    def _info(self):
        return self._data.get('info', {})

    @property
    def description(self):
        return self._info.get('description', '')

    @property
    def title(self):
        return self._info.get('title', "EVE Swagger Interface")

    @property
    def version(self):
        return StrictVersion(self._info.get('version', '0.0.0'))

    @property
    def base_path(self):
        return self._data.get('basePath', '/')

    @property
    def schemes(self):
        return self._data.get('schemes', ['https'])

    @property
    def sso(self):
        return self._data.get('securityDefinitions', {}).get('evesso', {})

    def iter_valid_urls(self):
        host = self.host
        path = self.base_path
        for scheme in self.schemes:
            yield urlunparse((scheme, host, path, '', '', ''))

    @classmethod
    def from_spec(cls, spec, params=None):
        if spec not in SWAGGER_SPEC_URLS:
            raise InvalidSpecError(spec)
        return cls.from_url(SWAGGER_BASE_URL.format(spec=spec), params=params)

    @classmethod
    def meta_spec(cls, params=None):
        return cls.from_url(SWAGGER_META_URL, params=params)

    @classmethod
    def from_url(cls, url, params=None):
        resp = httpx.get(url, params=params, headers={
            'User-Agent': USER_AGENT,
        })
        return cls(resp.json())

    @classmethod
    def from_file(cls, fname, encoding=None):
        if not hasattr(fname, 'read'):
            with open(fname, mode='r', encoding=encoding) as fh:
                data = json.load(fh)
        else:
            data = json.load(fname)
        return cls(data)

    @classmethod
    def from_document(cls, document):
        return cls(json.loads(document))


