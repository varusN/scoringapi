import functools
import unittest

import api


def cases(cases):
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args):
            for c in cases:
                new_args = args + (c if isinstance(c, tuple) else (c,))
                f(*new_args)
        return wrapper
    return decorator


class TestValidation(unittest.TestCase):
    class TestArgument(object):
        def __init__(self, request):
            self.value = request['value']
            self.required = request['required']
            self.nullable = request['nullable']

    def test_validation_required__not_nullable(self):
        request = TestValidation.TestArgument({'value': None, 'required': True, 'nullable': True})
        body = {'One': 'First', 'Two': 'Second'}
        argument = 'One'
        expectation = 'First'
        result = api.validation(request, body, argument)
        self.assertEqual(expectation, result)

    def test_validation_not_required__not_nullable(self):
        request = TestValidation.TestArgument({'value': None, 'required': False, 'nullable': True})
        body = {'One': 'First', 'Two': 'Second'}
        argument = 'One'
        expectation = 'First'
        result = api.validation(request, body, argument)
        self.assertEqual(expectation, result)

    def test_validation_required__nullable(self):
        request = TestValidation.TestArgument({'value': None, 'required': True, 'nullable': False})
        body = {'One': 'First', 'Two': 'Second'}
        argument = 'One'
        expectation = 'First'
        result = api.validation(request, body, argument)
        self.assertEqual(expectation, result)

    def test_validation_not_required__nullable(self):
        request = TestValidation.TestArgument({'value': None, 'required': False, 'nullable': False})
        body = {'One': 'First', 'Two': 'Second'}
        argument = 'One'
        expectation = 'First'
        result = api.validation(request, body, argument)
        self.assertEqual(expectation, result)

    def test_validation_not_required__nullable_null(self):
        request = TestValidation.TestArgument({'value': None, 'required': False, 'nullable': False})
        body = {'One': None, 'Two': 'Second'}
        argument = 'One'
        self.assertRaises(ValueError, api.validation, request, body, argument)

    def test_validation_required__not_nullable_null(self):
        request = TestValidation.TestArgument({'value': None, 'required': True, 'nullable': True})
        body = {'One': None, 'Two': 'Second'}
        argument = 'One'
        expectation = None
        result = api.validation(request, body, argument)
        self.assertEqual(expectation, result)

    def test_validation_required_missed__nullable(self):
        request = TestValidation.TestArgument({'value': None, 'required': True, 'nullable': False})
        body = {'Two': 'Second'}
        argument = 'One'
        self.assertRaises(KeyError, api.validation, request, body, argument)

    def test_validation_not_required_missed__nullable(self):
        request = TestValidation.TestArgument({'value': None, 'required': False, 'nullable': False})
        body = {'Two': 'Second'}
        argument = 'One'
        self.assertRaises(api.CustomException, api.validation, request, body, argument)


class TestPairValidation(unittest.TestCase):

    @cases([
        (['phone', 'email']),
        (['first_name', 'last_name']),
        (['gender', 'birthday']),
    ])
    def test_pair_valid_success(self, arguments):
        self.assertIsNone(api.pair_validation(arguments))

    @cases([
        ([]),
        (['first_name', 1]),
        (['gender', 'first_name']),
    ])
    def test_pair_valid_empty(self, arguments):
        self.assertRaises(ValueError, api.pair_validation, arguments)
