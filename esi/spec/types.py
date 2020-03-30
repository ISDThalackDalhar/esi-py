import base64
import decimal
from datetime import date, datetime
from typing import Any, Dict, List, Tuple

import iso8601
import rfc3339
from esi.exceptions import ValidationError
from esi.spec.describeable import Describeable, Property


class Type:
    python_type = None
    typing_type = None

    def get_valid_types(self, described: Describeable) -> Tuple[type]:
        return (self.python_type,)

    def to_python(self, described: Describeable, value):
        """
        Encode the data to its python variant

        :param described: The described object
        :param value: The value to convert
        :return: The converted value
        """
        if not isinstance(value, self.python_type):
            value = self.python_type(value)
        return value

    def from_python(self, described: Describeable, value):
        """
        Encode the python data to the output format

        :param described: The described object
        :param value: The value to convert
        :return: The converted value
        """
        if not isinstance(value, self.python_type):
            value = self.python_type(value)
        return value

    def validate(self, described: Describeable, value):
        if not isinstance(value, self.get_valid_types(described)):
            _type = described._type
            fmt = described.format
            if fmt:
                _type = '%s.%s' % (_type, fmt)
            raise ValidationError(
                "Invalid type: %(type)s",
                code='typeerror',
                params={
                    'type': _type,
                }
            )

    def get_typing_type(self, described: Describeable):
        return self.typing_type


class StringType(Type):
    python_type = str
    typing_type = str

    def to_python(self, described: Describeable, value):
        """
        Encode the data to its python variant

        Since OpenAPI allows for certain formats, we have to be specific for certain ones.

        :param described: The described object
        :param value: The value to convert
        :return: The converted value
        """
        fmt = described.format
        if fmt in ("date", "date-time"):
            value = iso8601.parse_date(value)
        elif fmt == "byte":
            if not isinstance(value, bytes):
                value = value.encode()
            value = base64.b64decode(value)
        elif fmt == "binary":
            # We do not support binary format since the docs are too vague on what it requires
            value = super().to_python(described, value)
        else:
            value = super().to_python(described, value)
        return value

    def from_python(self, described: Describeable, value):
        """
        Encode the python data to the output format

        Since OpenAPI allows for certain formats, we have to be specific for certain ones.

        :param described: The described object
        :param value: The value to convert
        :return: The converted value
        """
        fmt = described.format
        if fmt == "date":
            if isinstance(value, datetime):
                value = value.date()
            elif isinstance(value, int):
                value = datetime.fromtimestamp(value).date()
            if isinstance(value, date):
                value = value.isoformat()
        elif fmt == "date-time":
            if isinstance(value, datetime):
                value = rfc3339.rfc3339(value)
            elif isinstance(value, int):
                value = datetime.fromtimestamp(value)
                value = rfc3339.rfc3339(value)
        elif fmt == "byte":
            if not isinstance(value, bytes):
                value = value.encode()
            value = base64.b64encode(value).strip().decode()
        elif fmt == "binary":
            # We do not support binary format since the docs are too vague on what it requires
            value = super().to_python(described, value)
        else:
            value = super().to_python(described, value)
        return value

    def get_valid_types(self, described: Describeable) -> Tuple[type]:
        fmt = described.format
        types = (self.python_type,)
        if fmt == "date":
            types = (self.python_type, int, datetime, date)
        elif fmt == "date-time":
            types = (self.python_type, int, datetime)
        elif fmt == "byte":
            types = (self.python_type, bytes)
        return types


class IntegerType(Type):
    python_type = int
    typing_type = int

    def validate(self, described: Describeable, value):
        super().validate(described, value)

        _min = described.minimum
        _max = described.maximum
        fmt = described.format
        boundary = {
            "int32": 0x7FFFFFFF,
            "int64": 0x7FFFFFFFFFFFFFFF,
        }.get(fmt, None)
        if boundary:
            _max = min(_max or boundary, boundary)
            _min = max(_min or -boundary, -boundary)
        if any([
                _min and value < _min,
                _max and value > _max,
               ]):
            raise ValidationError(
                "Value not within allowed range: %(min)s - %(max)s",
                code='value',
                params={
                    'min': _min,
                    'max': _max,
                }
            )


class NumberType(IntegerType):
    python_type = float
    typing_type = float

    def get_valid_types(self, described: Describeable) -> Tuple[type]:
        return (float, decimal.Decimal)


class BooleanType(Type):
    python_type = bool
    typing_type = bool

    def validate(self, described: Describeable, value):
        if value not in (True, False):
            raise ValidationError(
                "Value not within expected options",
                code='value',
            )


class ArrayType(Type):
    python_type = list
    typing_type = List[Any]

    def to_python(self, described: Describeable, value):
        subitem = described.items
        return [subitem.to_python(x) for x in value]

    def from_python(self, described: Describeable, value):
        subitem = described.items
        return [subitem.from_python(x) for x in value]

    def validate(self, described: Describeable, value):
        super().validate(described, value)

        _min = described.min_items or described.minimum
        _max = described.max_items
        _len = len(value)
        if any([
                _min and _len < _min,
                _max and _len > _max,
            ]):
            raise ValidationError(
                "Value length not within allowed range: %(min)s - %(max)s",
                code='value',
                params={
                    'min': _min,
                    'max': _max,
                }
            )
        if described.unique_items and len(set(value)) != _len:
            raise ValidationError(
                "Values are not unique",
                code='value',
            )
        subitem = described.items
        suberrors = []
        for item in value:
            try:
                subitem.validate(item)
            except ValidationError as e:
                suberrors.append(e)
        if suberrors:
            raise ValidationError({'[]': suberrors})

    def get_typing_type(self, described: Describeable):
        return List[described.items.typing_type]


class ObjectType(Type):
    python_type = dict
    typing_type = Dict[str, Any]

    def to_python(self, described: Describeable, value):
        props = described.properties  # type: Dict[str, Property]
        return {
            name: prop.to_python(value.get(name, prop.default))
            for name, prop in props.items()
            if name in value or prop.default
        }

    def from_python(self, described: Describeable, value):
        props = described.properties  # type: Dict[str, Property]
        return {
            name: prop.from_python(value[name])
            for name, prop in props.items()
            if name in value
        }

    def validate(self, described: Describeable, value):
        props = described.properties  # type: Dict[str, Property]
        suberrors = {}
        for name, prop in props.items():
            if name in value:
                subval = value[name]
                try:
                    prop.validate(subval)
                except ValidationError as e:
                    e.update_error_dict(suberrors, name)
            elif name in described.required:
                suberrors.setdefault(name, []).append(ValidationError(
                    "Value is required",
                    code='required',
                ))
        if suberrors:
            raise ValidationError(suberrors)


class SchemaType(Type):
    python_type = object
    typing_type = Any

    def to_python(self, described: Describeable, value):
        schema = described.schema
        return schema.to_python(value)

    def from_python(self, described: Describeable, value):
        schema = described.schema
        return schema.from_python(value)

    def validate(self, described: Describeable, value):
        schema = described.schema
        return schema.validate(value)

    def get_typing_type(self, described: Describeable):
        return described.schema.typing_type


TYPELIST = {
    "string": StringType(),
    "integer": IntegerType(),
    "number": NumberType(),
    "boolean": BooleanType(),
    "array": ArrayType(),
    "object": ObjectType(),
    "schema": SchemaType(),
}
DEFAULT_TYPE = ObjectType()
