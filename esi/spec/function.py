from typing import List

from esi.exceptions import ValidationError
from esi.spec.schema import Schema
from esi.spec.parameter import Parameter


class Function:
    path = None  # type: str
    name = None  # type: str
    method = None  # type: str
    tags = []  # type: List[str]
    scopes = []  # type: List[str]
    params = []  # type: List[Parameter]
    responses = {}  # type: Dict[int, Schema]

    def __init__(self, **kwargs):
        self.data = data = {
            'body': {},
            'headers': {},
            'path': {},
            'query': {},
        }
        data['header'] = data['headers']
        skip_validation = kwargs.pop('esi_skip_validation', False)
        errors = {}
        for param in self.params:
            value = kwargs.pop(param.safe_name)
            if value == param.default:
                continue
            try:
                param.validate(value)
            except ValidationError as e:
                e.update_error_dict(errors, param.safe_name)
            data[param.part][param.name] = value
        if errors and not skip_validation:
            raise ValidationError(errors)

    @classmethod
    def decorate(cls, func):
        func.handler = cls
        func.name = cls.name
        func.method = cls.method
        func.path = cls.path
        func.scopes = cls.scopes
        func.validate_scopes = cls.validate_scopes
        return func

    @classmethod
    def validate_scopes(cls, active_scopes):
        if not cls.scopes:
            return True
        if active_scopes is None:
            return False
        return all(x in active_scopes for x in cls.scopes)
