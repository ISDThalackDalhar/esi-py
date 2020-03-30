import unittest

from esi.spec import Describeable, Item, Parameter, Schema, Function


class SingleParam(Function):
    path = '/test/'
    name = 'single param'
    method = 'get'
    params = [
        Parameter(
            _format='int32',
            _in='query',
            _name='test',
            _type='integer',
            _required=True,
        ),
    ]


class SchemaArrayFunc(Function):
    path = '/test/'
    name = 'schema array'
    method = 'get'
    params = [
        Parameter(
            _in='body',
            _name='test',
            _required=True,
            _schema=Schema(
                _items=Item(
                    _format='int32',
                    _type='integer'
                ),
                _max_items=1000,
                _min_items=1,
                _type='array',
                _unique_items=True
            ),
            _type='schema'
        ),
    ]


TESTS = [
    (SingleParam, {'test': 1}, {'query': {'test': 1}}),
]


class TestSimpleConversions(unittest.TestCase):
    """
    Testing simple conversions and validations
    """

    def test_validate(self):
        for klass,  kwargs, data in TESTS:
            with self.subTest(name=klass.name):
                expected = {x: {} for x in ['body', 'query', 'path', 'headers']}
                expected.update(data)
                obj = klass(None, **kwargs)
                self.assertEqual(obj.data, expected)
