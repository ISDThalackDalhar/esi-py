from functools import total_ordering

from esi.utils import to_camel_case
from esi.spec.describeable import Describeable


class BaseParameter(Describeable):
    _enum = None
    _in = None
    _name = None


@total_ordering
class Parameter(BaseParameter):
    @property
    def name(self):
        return self._name

    @property
    def safe_name(self):
        return to_camel_case(self.name)

    @property
    def part(self):
        return self._in

    @property
    def required(self):
        return self._required

    @property
    def default(self):
        return self._default

    @property
    def has_required(self):
        return self._required

    @property
    def has_default(self):
        return self._default is not None

    def __eq__(self, other):
        return other.name == self.name and other._in == self._in

    def __lt__(self, other):
        if self.has_default != other.has_default:
            return self.has_default < other.has_default
        if self.required != other.required:
            return self.required > other.required
        return self.name < other.name

    @property
    def call_signature(self) -> str:
        """
        Generates a call signature for this parameter.
        Automatically appends typing hints and defaults (or None if no default and not required).
        """
        data = self.data
        data['safe_name'] = self.safe_name
        data['spacer'] = ' ' if data['typing_type'] else ''
        data['type'] = ': {typing_type_name}'.format(**data) if self._type else ''
        has_default = self._default is not None or not self._required
        data['safe_default'] = repr(self._default) if self._default is not None else "None"
        data['default'] = '{spacer}={spacer}{safe_default}'.format(**data) if has_default else ''
        return '{safe_name}{type}{default}'.format(**data)

    @property
    def docstring_line(self) -> str:
        """
        Generates the docstring line for this parameter.
        Automatically appends typing hints.
        """
        data = self.data
        data['safe_name'] = self.safe_name
        data['type_space'] = ' ' if data['typing_type'] else ''
        data['spacer'] = ' ' if (self._default or self._required) else ''
        data['default'] = '[default: {_default!r}]'.format(**data) if self._default else ''
        data['required'] = '[required]' if self._required else ''
        return ":param {typing_type_name}{type_space}{safe_name}: {_description}{spacer}{default}{required}".format(**data)
