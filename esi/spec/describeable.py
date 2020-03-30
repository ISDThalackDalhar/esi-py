from typing import Any, Dict

from esi.utils import cached_property, to_camel_case


class PropDict(dict):
    def __do_repr__(self, indent_base=0, short=False):
        indent = (indent_base + 4) if indent_base is not None else 0

        data = [
            '%r: %s' % (key, val.__do_repr__(indent, short) if hasattr(val, '__do_repr__') else repr(val))
            for key, val in sorted(self.items())
        ]

        indent_str = ''  # Indent amount for parameters
        newline = ''  # Newline marker for parameters
        indent_base = ' ' * (indent_base or 0)  # Base indent level for the last line

        if data and indent:
            indent_str = ' ' * indent
            newline = '\n'
        if not data:
            return '{}'

        return "{{{newline}{indent}{data}{newline}{indent_base}}}".format(
            newline=newline,
            indent=indent_str,
            indent_base=indent_base,
            data=(',%s%s' % (newline, indent_str or ' ')).join(data)
        )

    def __repr__(self):
        return super().__repr__()


class Describeable:
    """
    All properties when passed are prefixed with a _ as some might be identical to python keywords, or shadow
    python types/functions.
    """
    _title = None  # type: str
    _type = None  # type: str
    _format = None  # type: str
    _description = None  # type: str
    _is_global = False  # type: bool
    _required = False  # type: bool
    _properties = None
    _items = None
    _required = False  # type: bool
    _schema = None
    _default = None  # type: Any

    _min_items = None  # type: int
    _max_items = None  # type: int
    _unique_items = False  # type: bool
    _minimum = None  # type: int
    _maximum = None  # type: int

    _skippable_keys = [
        'title',
        'description',
    ]

    @classmethod
    def from_json(cls, data : Dict[str, Any], is_global=False):
        return cls(_is_global=is_global, **{
            '_%s' % to_camel_case(key): value
            for key, value in data.items()
        })

    def __init__(self, **kwargs):
        from esi.spec.schema import Schema
        for k, v in kwargs.items():
            if hasattr(self, k):
                setattr(self, k, v)

        if self._items and not isinstance(self._items, Describeable):
            # noinspection PyTypeChecker
            self._items = Item.from_json(self._items)
        elif self._properties:
            self._properties = PropDict({
                key: Property.from_json(value) if not isinstance(value, Describeable) else value
                for key, value in self._properties.items()
            })
        if not self._type and self._schema:
            self._schema = Schema.from_json(self._schema)\
                if not isinstance(self._schema, Describeable) else self._schema
            self._type = "schema"

    @cached_property
    def internal_type(self):
        from esi.spec.types import TYPELIST, DEFAULT_TYPE
        return TYPELIST.get(self._type, DEFAULT_TYPE)  # type: Type

    @property
    def python_type(self):
        return self.internal_type.python_type

    @cached_property
    def typing_type(self) -> str:
        return self.internal_type.get_typing_type(self)

    @property
    def typing_type_name(self):
        tt = self.typing_type
        if tt is None:
            return None
        return getattr(tt, '__name__', str(tt))

    def validate(self, value):
        return self.internal_type.validate(self, value)

    def from_python(self, value):
        return self.internal_type.from_python(self, value)

    def to_python(self, value):
        return self.internal_type.to_python(self, value)

    @property
    def data(self):
        items = sorted([x for x in dir(self) if x.startswith('_') and not x.startswith('__') and hasattr(self, x)])
        items = [x for x in items if getattr(self, x) != getattr(self.__class__, x)]
        return {
            key: getattr(self, key)
            for key in items + ['python_type', 'typing_type', 'typing_type_name']
        }

    def __do_repr__(self, indent_base=0, short=False):
        """
        Think __repr__, only with stacking indent levels.

        :param indent_base: The base indent level to continue from
        :return: The representation for this object
        """
        klass = self.__class__.__name__
        indent = (indent_base + 4) if indent_base is not None else 0
        skip = self._skippable_keys if short else []
        params = [
            '%s=%s' % (key, val.__do_repr__(indent, short) if hasattr(val, '__do_repr__') else repr(val))
            for key, val in sorted(self.data.items())
            if key.startswith('_') and key[1:] not in skip
        ]

        indent_str = ''  # Indent amount for parameters
        newline = ''  # Newline marker for parameters
        indent_base = ' ' * (indent_base or 0)  # Base indent level for the last line

        if params and indent:
            indent_str = ' ' * indent
            newline = '\n'

        # Depending on parameters, output either one of the following:
        #  Describeable()  # no parameters
        #  Describeable(
        #               _var = value
        #               [...]
        #  )  # with parameters
        if not params:
            return '{name}()'.format(name=self.__class__.__name__)
        return "{name}({newline}{indent}{params}{newline}{indent_base})".format(
            name=self.__class__.__name__,
            newline=newline,
            indent=indent_str,  # Do not indent if we stay on one line
            indent_base=indent_base,  # Do not indent if we stay on one line
            params=(',%s%s' % (newline, indent_str or ' ')).join(params)
        )

    def __repr__(self):
        return self.__do_repr__(0)

    @property
    def is_global(self) -> bool:
        return self._is_global

    @property
    def format(self) -> str:
        return self._format

    @property
    def minimum(self) -> int:
        return self._minimum

    @property
    def maximum(self) -> int:
        return self._maximum

    @property
    def items(self):
        return self._items

    @property
    def min_items(self) -> int:
        return self._min_items

    @property
    def max_items(self) -> int:
        return self._max_items

    @property
    def unique_items(self) -> bool:
        return self._unique_items

    @property
    def schema(self):
        return self._schema

    @property
    def properties(self):
        return self._properties

    @property
    def default(self):
        return self._default

    @property
    def title(self):
        return self._title

    @property
    def required(self):
        return self._required


class Property(Describeable):
    pass


class Item(Describeable):
    pass
