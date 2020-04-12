from asyncio import wait, ALL_COMPLETED, create_task

from httpx import Client as _Client, AsyncClient as _AsyncClient, URL

from esi.exceptions import ESIScopeRequired
from esi.utils import USER_AGENT


class ESIClientBase:
    def __init__(self, esi, **kwargs):
        self.esi = esi
        hdrs = {
            'user-agent': esi.user_agent or USER_AGENT,
        }
        if esi.auth_token:
            token = esi.auth_token() if callable(esi.auth_token) else esi.auth_token
            if token:
                hdrs['Authorization'] = 'Bearer %s' % token
        hdrs.update(kwargs.get("headers", {}))
        kwargs["headers"] = hdrs
        super().__init__(**kwargs)

    def __call__(self, request, **kwargs):
        return self.send(request **kwargs)

    def validate_esi_request(self, request):
        from esi.spec import Function
        if not isinstance(request, Function):
            return
        # If scope validation is requested, we do this before we send.
        if not request.validate_scopes(self.esi.enabled_scopes or []):
            raise ESIScopeRequired(request.scopes)

    def prepare_esi_request(self, request):
        from esi.spec import Function
        if not isinstance(request, Function):
            return
        # Prepare the request for sending.
        # Since we don't include the host/base url in the requests, we join it here
        if request.url.scheme not in ("http", "https") or not request.url.host:
            new_path = '/'.join([self.esi.base_path.rstrip('/'), request.url.path.lstrip('/')])
            request.url = url = request.url.copy_with(scheme=self.esi.get_scheme(), host=self.esi.host, path=new_path)
            # Make sure to update the Host header to the proper value as well
            if url.userinfo:
                # Ensure we don't include any form of credentials in the host header.
                url = url.copy_with(username=None, password=None)
            request.headers["host"] = url.authority

        # Ensure our headers are all set
        for key, val in self.headers.items():
            request.headers.setdefault(key, val)

    def process_esi_repsonse(self, request, response, raise_if_error=None):
        status_code = response.status_code
        schema = request.responses.get(status_code)
        headers = response.headers

        if response.status_code == 304:
            data = None
        else:
            data = response.json()
            if schema:
                data = schema.to_python(data)
        
        return status_code, data, headers


class Client(ESIClientBase, _Client):
    def send(self, request, **kwargs):
        # `validate_esi_request` is a noop if the request is not a Function subclass
        if kwargs.pop("validate_scopes", True):
            self.validate_esi_request(request)
        # `prepare_esi_request` is a noop if the request is not a Function subclass
        self.prepare_esi_request(request)                            
        return super().send(request, **kwargs)

    def send_esi_request(self, request, *, raise_if_error=None, validate_scopes=True, **kwargs):
        resp = self.send(request, **kwargs)
        return self.process_esi_repsonse(request, resp, raise_if_error=raise_if_error)

    def __call__(self, *requests, raise_if_error=None, validate_scopes=True, **kwargs):
        return [
            self.send_esi_request(request, raise_if_error=raise_if_error, validate_scopes=validate_scopes, **kwargs)
            for request in requests
        ]


class AsyncClient(ESIClientBase, _AsyncClient):
    async def send(self, request, **kwargs):
        # `validate_esi_request` is a noop if the request is not a Function subclass
        if kwargs.pop("validate_scopes", True):
            self.validate_esi_request(request)
        # `prepare_esi_request` is a noop if the request is not a Function subclass
        self.prepare_esi_request(request)                            
        return await super().send(request, **kwargs)

    async def send_esi_request(self, request, *, raise_if_error=None, **kwargs):
        resp = await self.send(request, **kwargs)
        return self.process_esi_repsonse(request, resp, raise_if_error=raise_if_error)

    async def __call__(self, *requests, raise_if_error=None, validate_scopes=True, return_when=ALL_COMPLETED, **kwargs):
        done, pending = await wait([
            create_task(self.send_esi_request(request, raise_if_error=raise_if_error, validate_scopes=validate_scopes, **kwargs))
            for request in requests
        ], return_when=return_when)
        done = [x.result() for x in done]
        return done if len(requests) > 1 else done[0]
