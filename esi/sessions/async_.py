import asyncio
from typing import Dict, Any, Union, List

import aiohttp

from esi.sessions.base import BaseAsyncSession


class AsyncSession(BaseAsyncSession):
    def __init__(self, *, esi):
        super().__init__(esi=esi)
        self.session = aiohttp.ClientSession(headers=self.default_headers)

    async def call_single(self, method, ignore_scopes=False, raise_if_error=None):
        url, query, body, headers = self.prepare_call(method, ignore_scopes=ignore_scopes)
        request = getattr(self.session, method.method, self.session.get)
        async with request(url, params=query, json=body, headers=headers) as resp:
            if resp.status == 304:
                data = None
            else:
                data = await resp.json()  # type: Union[Dict[str, Any], List[Any], None]
            return self.process_response(method, resp.status, data, resp.headers, raise_if_error=raise_if_error)

    async def call(self, *methods, ignore_scopes=False, raise_if_error=None, loop=None, timeout=None,
                   return_when=asyncio.ALL_COMPLETED):
        return await asyncio.wait([self.call_single(method, ignore_scopes=ignore_scopes, raise_if_error=raise_if_error)
                                   for method in methods], loop=loop, timeout=timeout, return_when=return_when)

    async def __call__(self, *methods, ignore_scopes=False, raise_if_error=None):
        if not methods:
            return []
        done, pending = await self.call(methods, ignore_scopes=ignore_scopes, raise_if_error=raise_if_error)
        return done if len(methods) > 1 else done[0]

    async def close(self):
        await self.session.close()
