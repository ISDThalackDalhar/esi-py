import unittest
from operator import itemgetter

from esi.spec.describeable import Item, Property
from esi.spec.parameter import Parameter
from esi.spec.schema import Schema

SCHEMA_OUTPUT = """Schema(
    _items=Item(
        _title='test'
    )
)"""

SCHEMAS = {
    'raw': Schema(_items=Item(_title='test')),
    'partially': Schema(_items={'title': 'test'}),
    'json': Schema.from_json({'items': {'title': 'test'}}),
}

TEST_PARAM_OUTPUT = "Parameter(_name='test', _type='test')"

TEST_PARAM = Parameter(
    _type="test",
    _name="test",
)

REPRS = {
    Parameter: "Parameter()",
    Schema: "Schema()",
    Item: "Item()",
    Property: "Property()",
}

CALL_SIGNATURES = [
    (Parameter(_type="string", _name="req", _required=True), "req: str"),
    (Parameter(_type="integer", _name="optional"), "optional: int = None"),
    (Parameter(_type="array", _name="array", _items=Item(_type="integer")), "array: typing.List[int] = None"),
    (Parameter(_type="object", _name="object"), "object: typing.Dict[str, typing.Any] = None"),
    (Parameter(_type="integer", _name="_default", _default=1), "_default: int = 1"),
]


class TestComponents(unittest.TestCase):
    def test_0001_repr(self):
        for klass, out in sorted(REPRS.items(), key=itemgetter(1)):
            with self.subTest(klass=klass.__name__):
                self.assertEqual(repr(klass()), out, "repr() does not produce expected output")
        with self.subTest(type="no-indent"):
            self.assertEqual(TEST_PARAM.__do_repr__(None), TEST_PARAM_OUTPUT, "repr() does not produce expected output")

    def test_0002_repr_subitems(self):
        for key, val in sorted(SCHEMAS.items()):
            with self.subTest(key=key):
                self.assertEqual(repr(val), SCHEMA_OUTPUT, "Schema does not repr() properly")

    def test_0003_re_eval(self):
        evaled = eval(repr(TEST_PARAM), globals(), locals())
        self.assertEqual(repr(TEST_PARAM), repr(evaled), "Re-evalled Parameter does not repr properly")

    def test_0004_signatures(self):
        for param, expected in CALL_SIGNATURES:
            with self.subTest(key=param.name):
                self.assertEqual(param.call_signature, expected, "Could not create expected call signature")
