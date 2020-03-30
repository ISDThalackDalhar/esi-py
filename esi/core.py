from typing import List

from esi.sessions import BaseSession, BaseSyncSession, BaseAsyncSession, SyncSession, AsyncSession
from esi.utils import USER_AGENT


class ESIBaseMetaClass(type):
    __anon_session = None

    @property
    def anonymous(self):
        """
        A simple trick to create a class property with a singleton instance for unauthenticated requests.
        """
        if self.__anon_session is None:
            self.__anon_session = self(auth_token=None, enabled_scopes=[])
        return self.__anon_session


class ESIBase(metaclass=ESIBaseMetaClass):
    version = None  # type: str
    host = None  # type: str
    base_path = None  # type: str
    schemes = ['https']  # type: List[str]

    session_class = SyncSession
    async_session_class = AsyncSession

    user_agent = USER_AGENT

    def __hash__(self):
        return hash((
            self.auth_token,
            ','.join(self.enabled_scopes or []),
            self.user_agent,
            self.get_scheme(),
            self.host,
            self.base_path,
            self.version,
        ))

    def __init__(self, *, auth_token=None, enabled_scopes=None, user_agent=None):
        self.auth_token = auth_token
        self.enabled_scopes = enabled_scopes
        self.active_session = None  # type: BaseSession
        if user_agent:
            self.user_agent = user_agent

    def __repr__(self):
        from urllib.parse import urlunparse
        return '<{name}: {auth} for {host} version {version}>'.format(
            name=self.__class__.__name__,
            auth='Authenticated' if self.auth_token else 'Anonymous',
            host=urlunparse((self.get_scheme(), self.host, self.base_path, '', '', '')),
            path=self.base_path,
            version=self.version,
        )

    def get_session_class(self):
        klass = self.session_class
        if not issubclass(klass, BaseSyncSession):
            raise TypeError("session_class does not subclass BaseSyncSession")
        return klass

    def get_async_session_class(self):
        klass = self.async_session_class
        if not issubclass(klass, BaseAsyncSession):
            raise TypeError("async_session_class does not subclass BaseAsyncSession")
        return klass

    def get_scheme(self):
        return (self.schemes + ['https'])[0]

    @classmethod
    def session(cls, *, auth_token, enabled_scopes=None):
        obj = cls(auth_token=auth_token, enabled_scopes=enabled_scopes)
        return obj.get_session_class()(esi=obj)

    @classmethod
    async def async_session(cls, *, auth_token, enabled_scopes=None):
        obj = cls(auth_token=auth_token, enabled_scopes=enabled_scopes)
        return obj.get_async_session_class()(esi=obj)

    def __enter__(self):
        self.active_session = self.get_session_class()(esi=self)
        return self.active_session

    def __aenter__(self):
        self.active_session = self.get_async_session_class()(esi=self)
        return self.active_session

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.active_session:
            self.active_session.close()
            self.active_session = None

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.active_session:
            self.active_session.close()
            self.active_session = None
