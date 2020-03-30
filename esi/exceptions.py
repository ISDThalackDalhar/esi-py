from esi.utils import try_int


class ESIException(Exception):
    """
    Base class for all ESI exceptions
    """
    pass


class MissingPackageError(ImportError):
    pass


class InvalidSpecError(Exception):
    pass


class ValidationError(Exception):
    """
    Raised when there was an error raising data

    Loosely based on Django's ValidationError, mainly for its chaining purposes
    """
    def __init__(self, message, code=None, params=None):
        super().__init__(message, code, params)

        if isinstance(message, ValidationError):
            if hasattr(message, 'error_dict'):
                message = message.error_dict
            elif not hasattr(message, 'message'):
                message = message.error_list
            else:
                message, code, params = message.message, message.code, message.params
        if isinstance(message, dict):
            self.error_dict = {}
            for field, messages in message.items():
                if not isinstance(messages, ValidationError):
                    messages = ValidationError(messages)
                self.error_dict[field] = messages.error_list
        elif isinstance(message, list):
            self.error_list = []
            for msg in message:
                if not isinstance(msg, ValidationError):
                    msg = ValidationError(msg)
                if hasattr(msg, 'error_dict'):
                    self.error_list.extend(sum(msg.error_dict.values(), []))
                else:
                    self.error_list.extend(msg.error_list)
        else:
            self.message = message
            self.code = code
            self.params = params
            self.error_list = [self]

    @property
    def messages(self):
        if hasattr(self, 'error_dict'):
            return sum(dict(self).values(), [])
        return list(self)

    def update_error_dict(self, error_dict, prefix):
        if hasattr(self, 'error_dict'):
            for field, error_list in self.error_dict.items():
                error_dict.setdefault('%s.%s' % (prefix, field), []).extend(error_list)
        else:
            error_dict.setdefault(prefix, []).extend(self.error_list)
        return error_dict

    def __iter__(self):
        if hasattr(self, 'error_dict'):
            for field, errors in self.error_dict.items():
                yield field, list(ValidationError(errors))
        else:
            for error in self.error_list:
                message = error.message
                if error.params:
                    message %= error.params
                yield str(message)

    def __str__(self):
        if hasattr(self, 'error_dict'):
            return repr(dict(self))
        return repr(list(self))

    def __repr__(self):
        return 'ValidationError(%s)' % self


class ESIScopeRequired(ESIException):
    """
    This exception is raised when the call that is being made requires scopes that have not been enabled.
    """
    def __init__(self, missing_scopes=None):
        self.missing_scopes = missing_scopes or []
        super().__init__(', '.join(self.missing_scopes))


class ESIResponseError(ESIException):
    def __init__(self, status_code, data, headers):
        self.status_code = status_code
        self.data = data
        self.headers = headers

    @property
    def error_limit_remain(self):
        try:
            return int(self.headers['X-Esi-Error-Limit-Remain'])
        except:
            return 1

    @property
    def error_limit_reset(self):
        try:
            return int(self.headers['X-Esi-Error-Limit-Reset'])
        except:
            return 1

    def __getitem__(self, item):
        return self.data[item]

    def __iter__(self):
        return iter(self.data)

    def __len__(self):
        return len(self.data)

    def __repr__(self):
        return "<%s: %d: %r>" % (self.__class__.__name__, self.status_code, self.data)
