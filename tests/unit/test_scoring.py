import datetime
import functools
import random
import unittest
from unittest import mock

from scoring import get_interests, get_score


def cases(cases):
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args):
            for c in cases:
                new_args = args + (c if isinstance(c, tuple) else (c,))
                f(*new_args)
        return wrapper
    return decorator


class TestScoring(unittest.TestCase):
    @cases([
        ({}, 0),
        ({"phone": "1234657890"}, 1.5),
        ({"phone": "1234657890", "email": "example@otus.ru"}, 3),
        ({"phone": "1234657890", "email": "example@otus.ru", "gender": "1"}, 3),
        ({"phone": "1234657890", "email": "example@otus.ru", "gender": 1, "birthday": "01.01.1922"}, 4.5),
        ({"phone": "1234657890", "email": "example@otus.ru", "gender": 1, "birthday": "01.01.2000",
          "first_name": "first"}, 4.5),
        ({"phone": "123", "email": "example@otus.ru", "gender": 1, "birthday": "01.01.2000",
          "first_name": "first", "last_name": "last"}, 5),
        ({"phone": "645", "birthday": "01.01.2000", "first_name": "first"}, 1.5),
        ({"email": "example@otus.ru", "gender": 1, "last_name": "last"}, 1.5),
    ])
    def test_get_score(self, tests, expectation):
        with (
                mock.patch("logging.info") as logging,
                mock.patch("api.Store") as mocked_store,
                mock.patch.object(mocked_store, 'cache_get', return_value='')
        ):

            phone = tests.get('phone', None)
            email = tests.get('email', None)
            birthday = tests.get('birthday', None)
            if birthday is not None:
                birthday = datetime.datetime.strptime(birthday, '%d.%m.%Y').date(),
                birthday = birthday[0]
            gender = tests.get('gender', None)
            first_name = tests.get('first_name', None)
            last_name = tests.get('last_name', None)
            result = get_score(logging, mocked_store, phone, email, birthday, gender, first_name, last_name)
            self.assertEqual(expectation, result, tests)

    def test_get_interests(self):
        with (
                mock.patch("logging.info") as logging,
                mock.patch("api.Store") as mocked_store,
                mock.patch.object(mocked_store, 'get', return_value=["cars", "pets"])
        ):
            cid = random.randint(0, 10)
            result = get_interests(logging, mocked_store, cid)
            self.assertEqual(["cars", "pets"], result)
