from typing import Dict, Any, Union, List

import requests

from esi.sessions.base import BaseSyncSession


class SyncSession(BaseSyncSession):
    def __init__(self, *, esi):
        super().__init__(esi=esi)
        self.session = requests.Session()
        self.session.headers.update(self.default_headers)

    def call_single(self, method, ignore_scopes=False, raise_if_error=None):
        url, query, body, headers = self.prepare_call(method, ignore_scopes=ignore_scopes)
        request = getattr(self.session, method.method, self.session.get)
        resp = request(url, params=query, json=body, headers=headers)  # type: requests.Response
        if resp.status_code == 304:
            data = None
        else:
            data = resp.json()  # type: Union[Dict[str, Any], List[Any], None]
        return self.process_response(method, resp.status_code, data, resp.headers, raise_if_error=raise_if_error)

    def call(self, *methods, ignore_scopes=False, raise_if_error=None):
        if not methods:
            return []
        return [self.call_single(method, ignore_scopes=ignore_scopes, raise_if_error=raise_if_error)
                for method in methods]

    def close(self):
        self.session.close()
