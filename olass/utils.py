"""
Goal: store utility functions

@authors:
  Andrei Sura <sura.andrei@gmail.com>

"""
import sys
import uuid
import logging
import unicodedata

from binascii import unhexlify
from itertools import zip_longest, islice, chain
from hashlib import sha256
from datetime import datetime
from datetime import date

import sqlalchemy as db

log = logging.getLogger(__package__)
# FORMAT_US_DATE = "%x"
# FORMAT_US_DATE_TIME = '%x %X'
FORMAT_DATABASE_DATE = "%Y-%m-%d"
# FORMAT_DATABASE_DATE_TIME = "%Y-%m-%d %H:%M:%S"

DB_TYPE_MYSQL = 'MYSQL'
DB_TYPE_MSSQL = 'MSSQL'


# table of punctuation characters + space
CHARS_TO_DELETE = dict.fromkeys(
    i for i in range(sys.maxunicode)
    if unicodedata.category(chr(i)).startswith('P') or
    not chr(i).isalnum())


def prepare_for_hashing(text):
    """
    Given a string with punctuation characters
    """
    if not text:
        return ''
    return text.translate(CHARS_TO_DELETE).lower()


def get_uuid_bin(uuid_text=None):
    """
    Note: the returned value needs to be hexlified to be human readable
    """
    if not uuid_text:
        uuid_text = uuid.uuid1()

    lower = str(uuid_text).replace('-', '').lower()
    return unhexlify(lower.encode())


def get_db_url_sqlserver(config):
    """
    Helper function for creating the "pyodbc" connection string.

    @see http://docs.sqlalchemy.org/en/latest/dialects/mssql.html
    @see https://code.google.com/p/pyodbc/wiki/ConnectionStrings
    """
    from urllib import parse
    params = parse.quote(
        "Driver={{FreeTDS}};Server={};Port={};"
        "Database={};UID={};PWD={};"
        .format(config['DB_HOST'], config['DB_PORT'], config['DB_NAME'],
                config['DB_USER,'], config['DB_PASS']))
    return 'mssql+pyodbc:///?odbc_connect={}'.format(params)


def get_db_url_mysql(config):
    """
    Format the configuration parameters to build the connection string
    """
    if 'DB_URL_TESTING' in config:
        return config['DB_URL_TESTING']

    return 'mysql+mysqlconnector://{}:{}@{}/{}' \
           .format(config['DB_USER'],
                   config['DB_PASS'],
                   config['DB_HOST'],
                   config['DB_NAME'])


def get_db_url(config):
    db_type = config.get('DB_TYPE').upper()

    if DB_TYPE_MYSQL == db_type:
        url = get_db_url_mysql(config)
    elif DB_TYPE_MSSQL == db_type:
        url = get_db_url_sqlserver(config)
    else:
        raise Exception("Incorrect DB_TYPE: {}".format(db_type))

    return url


def get_db_engine(config):
    """
    @see http://docs.sqlalchemy.org/en/latest/core/connections.html
    """
    url = get_db_url(config)

    try:
        engine = db.create_engine(url,
                                  pool_size=10,
                                  max_overflow=5,
                                  pool_recycle=3600,
                                  echo=False)
    except TypeError as exc:
        log.warning("Got exc from db.create_engine(): {}".format(exc))
        engine = db.create_engine(url, echo=False)

    return engine


def apply_sha256(val):
    """ Compute sha256 sum
    :param val: the input string
    :rtype string: the sha256 hexdigest
    """
    m = sha256()
    m.update(val.encode('utf-8'))
    return m.hexdigest()


def format_date_as_string(val, fmt='%m-%d-%Y'):
    """
    :rtype str:
    :return the input value formatted as '%Y-%m-%d'

    :param val: datetime or string
    :param fmt: the input format for the date
    """
    if isinstance(val, date):
        return val.strftime(fmt)

    da = format_date(val, fmt)

    if not da:
        return ''

    return da.strftime(FORMAT_DATABASE_DATE)


def format_date(val, fmt='%m-%d-%Y'):
    """
    Transform the input string to a datetime object

    :param val: the input string for date
    :param fmt: the input format for the date
    """
    date_obj = None

    try:
        date_obj = datetime.strptime(val, fmt)
    except Exception as exc:
        log.warning("Problem formatting date: {} - {} due: {}"
                    .format(val, fmt, exc))

    return date_obj


def list_grouper(iterable, n, fillvalue=None):
    """
    Collect data into fixed-length chunks or blocks.
    From: https://docs.python.org/2.7/library/itertools.html#recipes
    Example: grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx

    zip_longest: Make an iterator that aggregates elements from each of the
    iterables. If the iterables are of uneven length, missing values are
    filled-in with fillvalue. Iteration continues until the longest iterable
    is exhausted.
    """
    args = [iter(iterable)] * n
    return zip_longest(*args, fillvalue=fillvalue)


# def dict_grouper_memory(iterable, n):
#     chunks = [iter(iterable.items())] * n
#     generators = (dict(filter(None, v)) for v in zip_longest(*chunks))
#     return generators


def dict_grouper(iterable, n):
    """
    TODO: investigate why not always returning same results
    Stream the elements of the the dictionary in groups of "n".
    @see http://programeveryday.com/post/using-python-itertools-to-save-memory/
    The chain function can take any number of iterables and will return a new
    iterable which combines the passed in iterables.

    : rtype itertools.chain:
    """
    sourceiter = iter(iterable.items())

    while True:
        group_iter = islice(sourceiter, n)
        yield chain([next(group_iter)], group_iter)

# def prin_trace():
#     import traceback
#     exc_type, exc_value, exc_traceback = sys.exc_info()
#     print("*** print_tb:")
#     traceback.print_tb(exc_traceback, limit=1, file=sys.stdout)
#     print("*** print_exception:")
#     traceback.print_exception(exc_type, exc_value, exc_traceback,
#                               limit=2, file=sys.stdout)
#     print("*** print_exc:")
#     traceback.print_exc()


def ask_yes_no(question, default="y"):
    """Ask a yes/no question via raw_input() and return the answer
    as a boolean.

    :param question: the question displayed to the user
    :param default: the default answer if the user hits <Enter>

    """
    valid = {"y": True, "n": False}

    if default is None:
        prompt = " [y/n] "
    elif default == "y":
        prompt = " [Y/n] "
    elif default == "n":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while True:
        sys.stdout.write(question + prompt)
        choice = input().lower()

        if default is not None and choice == '':
            return valid[default]

        choice_letter = choice[0]

        if choice_letter in valid:
            return valid[choice_letter]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' "
                             "(or 'y' or 'n').\n")
