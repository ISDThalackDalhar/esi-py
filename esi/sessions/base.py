from typing import Union, Dict, Any, List
from urllib.parse import urlunparse

from esi import ESIScopeRequired
from esi.exceptions import ESIResponseError
from esi.utils import USER_AGENT
from esi.spec import Function

if False:  # typing
    from esi.core import ESIBase


class BaseSession:
    def __init__(self, *, esi, raise_if_error=True):
        self.esi = esi  # type: ESIBase
        self.raise_if_error = raise_if_error

    @property
    def default_headers(self):
        hdrs = {
            'User-Agent': self.esi.user_agent or USER_AGENT,
        }
        if self.esi.auth_token:
            token = self.esi.auth_token
            if callable(token):
                token = token()
            if token:
                hdrs['Authorization'] = 'Bearer %s' % token
        return hdrs

    def prepare_call(self, method: Function, ignore_scopes=False):
        if self.esi.enabled_scopes and not ignore_scopes:
            if not method.validate_scopes(self.esi.enabled_scopes):
                raise ESIScopeRequired(method.scopes)
        url = self.prepare_url(method)
        query = self.prepare_query(method)
        body = self.prepare_body(method)
        headers = self.prepare_headers(method)
        return url, query, body, headers

    def prepare_query(self, method):
        query = method.data.get('query', None)
        if query is None:
            return None
        ret = []
        for k, v in query.items():
            if isinstance(v, (list, set, tuple)):
                ret.append((k, ','.join(map(str, v))))
            else:
                ret.append((k, str(v)))
        return ret

    def prepare_body(self, method):
        body = method.data.get('body', None)
        if body:
            body = list(body.values())[0]
        return body

    def prepare_headers(self, method):
        return method.data.get('headers', {})

    def prepare_url(self, method):
        base = self.esi.base_path or ''
        url = method.path.lstrip('/')
        url = url.format(**method.data.get('path', {}))
        url = '/'.join([base.rstrip('/'), url])
        return urlunparse((self.esi.get_scheme(), self.esi.host, url, '', '', ''))

    def process_response(self, method, status_code: int, data: Union[Dict[str, Any], List[Any], None],
                         headers, raise_if_error=None) -> Any:
        schema = method.responses.get(status_code)
        if not schema:
            return data
        do_raise = self.raise_if_error
        if raise_if_error is not None:
            do_raise = raise_if_error
        if data:
            data = schema.to_python(data)
        if not (200 <= status_code < 400) and do_raise:
            raise ESIResponseError(status_code, data, headers)
        return status_code, data, headers


class BaseSyncSession(BaseSession):
    def call(self, method, ignore_scopes=False, raise_if_error=None):
        pass

    def __call__(self, *methods, ignore_scopes=False, raise_if_error=None):
        if not methods:
            return []
        ret = self.call(*methods, ignore_scopes=ignore_scopes, raise_if_error=raise_if_error)
        return ret if len(methods) > 1 else ret[0]

    def close(self):
        pass


class BaseAsyncSession(BaseSession):
    async def call(self, method, ignore_scopes=False, raise_if_error=None):
        pass

    async def __call__(self, *methods, ignore_scopes=False, raise_if_error=None):
        if not methods:
            return []
        ret = await self.call(*methods, ignore_scopes=ignore_scopes, raise_if_error=raise_if_error)
        return ret if len(methods) > 1 else ret[0]

    async def close(self):
        pass
