from esi.utils import to_pascal_case, cached_property
from esi.spec.schema import Schema
from esi.spec.parameter import Parameter


class Path:
    def __init__(self, url, method, data):
        self._parameters = []
        self._responses = {}

        self.url = url
        self.method = method
        self._data = data
        self.load_parameters()
        self.load_responses()

    @property
    def operation_id(self):
        return self._data['operationId']

    @property
    def tags(self):
        return self._data.get('tags', [])

    @property
    def scopes(self):
        security =  self._data.get('security', [])
        if security:
            return security[0].get('evesso', [])
        return []

    @property
    def indent_size(self):
        return len(self.operation_id)

    @cached_property
    def function_name(self):
        return to_pascal_case(self.operation_id, allow_double_under=True)

    @property
    def function_indent_size(self):
        return len(self.function_name)

    @property
    def description(self):
        return self._data.get('description', '').rstrip().rstrip('---').rstrip()

    @property
    def parameters(self):
        return self._parameters

    @property
    def responses(self):
        return self._responses

    @property
    def ordered_parameters(self):
        return list(sorted(self.parameters))

    @property
    def ordered_responses(self):
        return list(sorted(self.responses.items()))

    def load_parameters(self):
        for param in self._data.get('parameters', []):
            if not isinstance(param, Parameter):
                param = Parameter.from_json(param)
            self._parameters.append(param)

    def load_responses(self):
        for code, data in self._data.get('responses', {}).items():
            try:
                code = int(code)
            except:
                continue
            param = data.get('schema', {})
            if not isinstance(param, Schema):
                param = Schema.from_json(param)
            self._responses[code] = param
