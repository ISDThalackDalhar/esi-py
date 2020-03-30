import unittest
from datetime import datetime, timezone
from typing import List, Tuple, Any

from esi.spec import Describeable, Item, Parameter, Schema

CONVERSIONS = [
    (Describeable(_type="string"), "test", "test"),
    (Describeable(_type="string", _format="date"), datetime(2003, 5, 6, 0, tzinfo=timezone.utc), "2003-05-06"),
    (Describeable(_type="string", _format="date-time"), datetime(2003, 5, 6, 11, 0, 0, tzinfo=timezone.utc), "2003-05-06T11:00:00+00:00"),
    (Describeable(_type="string", _format="byte"), b'test', 'dGVzdA=='),
    (Describeable(_type="array", _format="int-array", _items=Item(_type="integer")), [1, 2], [1, 2]),
    (Describeable(_type="array", _format="str-array", _items=Item(_type="string")), ["1", "2"], ["1", "2"]),
    (Describeable(_type="object", _properties={'test': Parameter(_type="integer")}), {"test": 1}, {"test": 1}),
    (Describeable(_type="integer"), 10, 10),
    (Describeable(_type="number"), 10.0, 10.0),
    (Describeable(_type="boolean"), True, True),
    (Describeable(_type="schema", _schema=Schema(_type="array", _items=Item(_type="integer"))), [1, 2], [1, 2])
]  # type: List[Tuple[Describeable, Any, Any]]


class TestSimpleConversions(unittest.TestCase):
    """
    Testing simple conversions and validations
    """
    def test_validate(self):
        for desc, _in, _out in CONVERSIONS:
            with self.subTest(msg="Could not properly validate input", _type=desc._type, _format=desc.format):
                desc.validate(_in)

    def test_to_python(self):
        for desc, _in, _out in CONVERSIONS:
            with self.subTest(_type=desc._type, _format=desc.format):
                self.assertEqual(desc.to_python(_out), _in, "Could not properly convert input to python")

    def test_from_python(self):
        for desc, _in, _out in CONVERSIONS:
            with self.subTest(_type=desc._type, _format=desc.format):
                self.assertEqual(desc.from_python(_in), _out, "Could not properly convert from python to output")
