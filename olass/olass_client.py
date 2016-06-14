"""
Goal: Implement the client which sends
json requests to OLASS server.

@authors:
  Andrei Sura <sura.andrei@gmail.com>

@see:
    http://docs.sqlalchemy.org/en/latest/orm/tutorial.html#querying
    http://docs.sqlalchemy.org/en/latest/orm/contextual.html
    https://github.com/requests/requests-oauthlib/blob/master/requests_oauthlib/oauth2_session.py # NOQA
"""
import os
import sys

import requests
from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session
from oauthlib.oauth2.rfc6749.errors import TokenExpiredError
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from olass import utils
from olass import rules
from olass.models import base
from olass.models.patient import Patient
import logging

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# TODO: move logging config to a helper function
basedir, f = os.path.split(__file__)
log_conf = os.path.join(basedir, 'logging.conf')

if os.path.exists(log_conf):
    logging.config.fileConfig(log_conf)
else:
    lformat = '%(name)s.%(levelname)s ' \
              '- %(filename)s+%(lineno)d: %(message)s'
    logging.basicConfig(format=lformat, level=logging.INFO)

log = logging.getLogger(__package__)
log.debug("logging was configured...")
alog = logging.getLogger('requests_oauthlib')
alog.addHandler(logging.StreamHandler(sys.stdout))
alog.setLevel(logging.INFO)

TOKEN_REQUEST_ATTEMPTS = 3


class OlassClient():

    def __init__(self, config_file, create_tables=False,
                 root_path='.', default_config={}):
        """
        Setup the database connection obtain an access token
        """
        from olass.config import Config
        self.config = Config(
            root_path=root_path,
            defaults=default_config)
        self.config.from_pyfile(config_file)
        self.engine = utils.get_db_engine(self.config)
        self.session = OlassClient.get_db_session(self.engine, create_tables)
        # self.config.from_object(some_module.DefaultConfig)

    @classmethod
    def get_db_session(cls, engine, create_tables=False):
        """
        Connect to the database and return a Session object

        :param create_tables: boolean used to request table creation
        """
        log.info("Call get_db_session()")
        base.init(engine)
        session = base.DBSession()

        if create_tables:
            base.metadata.create_all(engine)

        return session

    def get_access_token(self, attempt=0):
        """
        Connects to the TOKEN_URL endpoint to retrieve a token.
        """
        log.info('Call get_access_token(attempt={})'.format(attempt))
        url = self.config.get('TOKEN_URL')
        client_id = self.config.get('CLIENT_ID')
        client_secret = self.config.get('CLIENT_SECRET')
        log.info('TOKEN_URL: {}'.format(url))
        client = BackendApplicationClient(client_id)
        olass = OAuth2Session(client=client)

        try:
            token = olass.fetch_token(
                token_url=url,
                client_id=client_id,
                client_secret=client_secret,
                verify=self.config.get('VERIFY_SSL_CERT', False))
        except TokenExpiredError as exc:
            if attempt < TOKEN_REQUEST_ATTEMPTS:
                log.warn("Try to get a fresh token: {}".format(exc))
                return self.get_access_token(self, attempt + 1)
            else:
                log.error("Give up after {} attempts to get a token: {}"
                          .format(TOKEN_REQUEST_ATTEMPTS, url))
        return token

    def get_patient_hashes(self):

        # Find patients without `linkage_uuid`
        patients = self.session.query(Patient).filter(
            Patient.pat_birth_date.isnot(None),
            Patient.pat_first_name.isnot(None),
            Patient.pat_last_name.isnot(None),
            Patient.linkage_uuid.is_(None)
        ).limit(10)

        hashes = rules.prepare_patients(patients, rules.RULES_MAP)
        return (hashes, len(hashes))

    def run(self):
        """
        Retrieve the unprocessed patients, compute hashes,
        and send data to the OLASS server.
        """
        access_token = self.get_access_token()
        log.info('Access token: {}'.format(access_token))
        patient_hashes, count = self.get_patient_hashes()
        log.info('Got hashes for [{}] patients'.format(count))

        for id, patient in enumerate(patient_hashes):
            print("{}: {}".format(id, patient))
