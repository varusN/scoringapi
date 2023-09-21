#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import hashlib
import json
import logging
import re
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer
from optparse import OptionParser

from scoring import get_interests, get_score

SALT = "Otus"
ADMIN_LOGIN = "admin"
ADMIN_SALT = "42"
OK = 200
BAD_REQUEST = 400
FORBIDDEN = 403
NOT_FOUND = 404
INVALID_REQUEST = 422
INTERNAL_ERROR = 500
ERRORS = {
    BAD_REQUEST: "Bad Request",
    FORBIDDEN: "Forbidden",
    NOT_FOUND: "Not Found",
    INVALID_REQUEST: "Invalid Request",
    INTERNAL_ERROR: "Internal Server Error",
}
UNKNOWN = 0
MALE = 1
FEMALE = 2
GENDERS = {
    UNKNOWN: "unknown",
    MALE: "male",
    FEMALE: "female",
}


class CustomException(Exception):
    pass


class CharField:
    def __init__(self, required, nullable):
        self.required = required
        self.nullable = nullable

    def __setattr__(self, name, value):
        if name == 'value' and value is not None:
            if not isinstance(value, str):
                raise ValueError
        self.__dict__[name] = value


class ArgumentsField:
    def __init__(self, required, nullable):
        self.required = required
        self.nullable = nullable

    def __setattr__(self, name, value):
        if name == 'value' and value == {}:
            raise ValueError
        self.__dict__[name] = value


class EmailField(CharField):
    def __init__(self, required, nullable):
        super().__init__(required, nullable)

    def __setattr__(self, name, value):
        if name == 'value':
            regex = '^[a-z0-9]+[\._]?[a-z0-9]+[@]\w+[.]\w{2,3}$'
            if not re.match(regex, value):
                raise ValueError
        self.__dict__[name] = value


class PhoneField:
    def __init__(self, required, nullable):
        self.required = required
        self.nullable = nullable

    def __setattr__(self, name, value):
        if name == 'value':
            regex = '^7\d{10}$'
            if re.match(regex, str(value)) or value is None:
                self.__dict__[name] = value
            else:
                raise ValueError
        self.__dict__[name] = value


class DateField:
    def __init__(self, required, nullable):
        self.required = required
        self.nullable = nullable

    def __setattr__(self, name, value):
        if name == 'value' and value is not None:
            date_parts = value.split('.')
            if len(date_parts) != 3 or not all(map(lambda x: x.isdigit(), date_parts)):
                raise ValueError
            try:
                datetime.datetime.strptime(value, '%d.%m.%Y').date()
            except Exception:
                raise ValueError
        self.__dict__[name] = value


class BirthDayField:
    def __init__(self, required, nullable):
        self.required = required
        self.nullable = nullable

    def __setattr__(self, name, value):
        if name == 'value' and value is not None:
            date_parts = value.split('.')
            if len(date_parts) != 3 or not all(map(lambda x: x.isdigit(), date_parts)):
                raise ValueError
            current_date = datetime.date.today()
            try:
                date = datetime.datetime.strptime(value, '%d.%m.%Y').date()
            except Exception:
                raise ValueError
            if int((current_date - date).days / 365.2425) > 70:
                raise ValueError
        self.__dict__[name] = value


class GenderField:
    def __init__(self, required, nullable):
        self.required = required
        self.nullable = nullable

    def __setattr__(self, name, value):
        if name == 'value' and value is not None:
            if value not in [0, 1, 2]:
                raise ValueError

        self.__dict__[name] = value


class ClientIDsField(object):
    def __init__(self, required):
        self.required = required

    def __setattr__(self, name, value):
        if name == 'value':
            if len(value) > 0 and isinstance(value, list):
                for id in value:
                    if not isinstance(id, int):
                        raise ValueError
            else:
                raise ValueError
        self.__dict__[name] = value


class ClientsInterestsRequest:
    client_ids = ClientIDsField(required=True)
    date = DateField(required=False, nullable=True)


class OnlineScoreRequest:
    first_name = CharField(required=False, nullable=True)
    last_name = CharField(required=False, nullable=True)
    email = EmailField(required=False, nullable=True)
    phone = PhoneField(required=False, nullable=True)
    birthday = BirthDayField(required=False, nullable=True)
    gender = GenderField(required=False, nullable=True)


class MethodRequest:
    account = CharField(required=False, nullable=True)
    login = CharField(required=True, nullable=True)
    token = CharField(required=True, nullable=True)
    arguments = ArgumentsField(required=True, nullable=True)
    method = CharField(required=True, nullable=False)

    @property
    def is_admin(self):
        return self.login == ADMIN_LOGIN


def check_auth(request):
    try:
        if request.is_admin:
            digest = hashlib.sha512((datetime.datetime.now().strftime("%Y%m%d%H") + ADMIN_SALT).encode()).hexdigest()
        else:
            digest = hashlib.sha512((request.account + request.login + SALT).encode()).hexdigest()
        if digest == request.token:
            return True
    except TypeError:
        return False
    return False


def validation(request, body, argument):
    if argument not in body.keys():
        if request.required:
            logging.info(f'{argument} does not exist, but required')
            raise KeyError
        else:
            logging.info(f'{argument} does not exist')
            raise CustomException('Return empty value')
    request.value = body[argument]
    if hasattr(request, 'nullable'):
        if not request.nullable and request.value is None:
            logging.info(f'{argument} cant be null')
            raise ValueError
    return request.value


def pair_validation(arguments):
    if 'phone' in arguments and 'email' in arguments:
        return
    if 'first_name' in arguments and 'last_name' in arguments:
        return
    if 'gender' in arguments and 'birthday' in arguments:
        return
    logging.info('request does not satisfied validation policy')
    raise ValueError


def method_handler(request, ctx, store):
    response, code = '_', None
    ctx['has'] = []
    invalid = []
    body = request["body"]
    if body == {}:
        logging.info("Invalid request body")
        code = INVALID_REQUEST
        return response, code
    request = MethodRequest()

    try:
        param = request.account
        request.account = validation(param, body, 'account')
    except ValueError:
        code = INVALID_REQUEST
        return response, code
    except KeyError:
        code = BAD_REQUEST
        return response, code
    except CustomException:
        pass

    try:
        param = request.login
        request.login = validation(param, body, 'login')
    except ValueError:
        code = INVALID_REQUEST
        return response, code
    except KeyError:
        code = INVALID_REQUEST
        return response, code
    except CustomException:
        pass

    try:
        param = request.token
        request.token = validation(param, body, 'token')
    except ValueError:
        code = INVALID_REQUEST
        return response, code
    except KeyError:
        code = BAD_REQUEST
        return response, code
    except CustomException:
        pass

    if check_auth(request):
        try:
            param = request.arguments
            request.arguments = validation(param, body, 'arguments')
        except ValueError:
            code = INVALID_REQUEST
            return response, code
        except KeyError:
            code = INVALID_REQUEST
            return response, code
        try:
            param = request.method
            request.method = validation(param, body, 'method')
        except ValueError:
            code = INVALID_REQUEST
            return response, code
        except KeyError:
            code = BAD_REQUEST
            return response, code
        if request.method == 'online_score':
            arguments = request.arguments
            if arguments == {}:
                logging.info("Invalid request arguments")
                code = INVALID_REQUEST
                return response, code
            scoring = OnlineScoreRequest()
            try:
                param = scoring.first_name
                scoring.first_name = validation(param, arguments, 'first_name')
                ctx["has"].append("first_name")
            except ValueError:
                invalid.append('first_name')
            except KeyError:
                code = BAD_REQUEST
                return response, code
            except CustomException:
                pass

            try:
                param = scoring.last_name
                scoring.last_name = validation(param, arguments, 'last_name')
                ctx["has"].append("last_name")
            except ValueError:
                invalid.append('last_name')
            except KeyError:
                code = BAD_REQUEST
                return response, code
            except CustomException:
                pass

            try:
                param = scoring.phone
                scoring.phone = validation(param, arguments, 'phone')
                ctx["has"].append("phone")
            except ValueError:
                invalid.append('phone')
            except KeyError:
                code = BAD_REQUEST
                return response, code
            except CustomException:
                pass

            try:
                param = scoring.email
                scoring.email = validation(param, arguments, 'email')
                ctx["has"].append("email")
            except ValueError:
                invalid.append('email')
            except KeyError:
                code = BAD_REQUEST
                return response, code
            except CustomException:
                pass

            try:
                param = scoring.birthday
                scoring.birthday = validation(param, arguments, 'birthday')
                ctx["has"].append("birthday")
            except ValueError:
                invalid.append('birthday')
            except KeyError:
                code = BAD_REQUEST
                return response, code
            except CustomException:
                pass

            try:
                param = scoring.gender
                scoring.gender = validation(param, arguments, 'gender')
                ctx["has"].append("gender")
            except ValueError:
                invalid.append('gender')
            except KeyError:
                code = BAD_REQUEST
                return response, code
            except CustomException:
                pass

            try:
                pair_validation(ctx["has"])
            except ValueError:
                code = INVALID_REQUEST
                return response, code
            except KeyError:
                code = BAD_REQUEST
                return response, code

            if len(invalid) > 0:
                code = INVALID_REQUEST
                response = f"The following filed(s) are invalid: {','.join(invalid)}"
                return response, code
            else:
                if request.is_admin:
                    score = 42
                else:
                    score = get_score(store, scoring.phone, scoring.email, scoring.birthday, scoring.gender,
                                      scoring.first_name, scoring.last_name)
                response = {"score": score}
                logging.info("Request is succesfuly proceeded.")
                code = OK

        elif request.method == 'clients_interests':
            invalid = []
            ctx["nclients"] = 0
            arguments = request.arguments
            if arguments == {}:
                logging.info("Invalid request arguments")
                code = INVALID_REQUEST
                return response, code
            interests = ClientsInterestsRequest()
            try:
                param = interests.client_ids
                interests.client_ids = validation(param, arguments, 'client_ids')
            except ValueError:
                code = INVALID_REQUEST
                return response, code
            except KeyError:
                code = INVALID_REQUEST
                return response, code

            try:
                param = interests.date
                interests.date = validation(param, arguments, 'date')
            except ValueError:
                invalid.append('date')
            except KeyError:
                code = BAD_REQUEST
                return response, code
            except CustomException:
                pass
            if len(invalid) > 0:
                code = INVALID_REQUEST
                response = f"The following filed(s) are invalid: {','.join(invalid)}"
                return response, code
            else:
                response = dict()
                for cid in interests.client_ids:
                    response[cid] = get_interests(store, cid)
                    ctx["nclients"] += 1
                logging.info("Request is succesfuly proceeded.")
                code = OK

    else:
        logging.info("Authentication failed")
        code = FORBIDDEN

    return response, code


class MainHTTPHandler(BaseHTTPRequestHandler):
    router = {
        "method": method_handler
    }
    store = None

    def get_request_id(self, headers):
        return headers.get('HTTP_X_REQUEST_ID', uuid.uuid4().hex)

    def do_POST(self):
        response, code = {}, OK
        context = {"request_id": self.get_request_id(self.headers)}
        request = None
        try:
            data_string = self.rfile.read(int(self.headers['Content-Length']))
            request = json.loads(data_string)
        except Exception as e:
            logging.exception(f"Unexpected error: {e}")
            code = BAD_REQUEST
        if request:
            path = self.path.strip("/")
            logging.info(f"{self.path} {data_string}")
            if path in self.router:
                try:
                    response, code = self.router[path]({"body": request, "headers": self.headers}, context, self.store)
                except Exception as e:
                    logging.exception(f"{context['request_id']} | Unexpected error: {e}")
                    code = INTERNAL_ERROR
            else:
                code = NOT_FOUND
        else:
            logging.info(f"{context['request_id']} | Empty request")
            code = INVALID_REQUEST
            response = '_'

        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        if code not in ERRORS:
            r = {"response": response, "code": code}
        else:
            r = {"error": response or ERRORS.get(code, "Unknown Error"), "code": code}
        context.update(r)
        logging.info(context)
        self.wfile.write(json.dumps(r).encode())
        return


if __name__ == "__main__":
    op = OptionParser()
    op.add_option("-p", "--port", action="store", type=int, default=8080)
    op.add_option("-l", "--log", action="store", default=None)
    (opts, args) = op.parse_args()
    logging.basicConfig(filename=None, level=logging.INFO,
                        format='[%(asctime)s] %(levelname).1s %(message)s', datefmt='%Y.%m.%d %H:%M:%S')
    server = HTTPServer(("0.0.0.0", opts.port), MainHTTPHandler)
    logging.info("Starting server at %s" % opts.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()
