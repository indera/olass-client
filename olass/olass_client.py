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
import json
import requests
import logging

from datetime import datetime
from sqlalchemy import text

from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session
# from oauthlib.oauth2.rfc6749.errors import TokenExpiredError
from requests.packages.urllib3.exceptions import InsecureRequestWarning

from olass import utils
from olass import rules
from olass.config import Config
from olass.models import base
from olass.models.patient import Patient
from olass.version import __version__


requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# TODO: move logging config to a helper function
basedir, f = os.path.split(__file__)
log_conf = os.path.join(basedir, 'logging.conf')

if os.path.exists(log_conf):
    logging.config.fileConfig(log_conf)
else:
    lformat = '%(asctime)s: %(name)s.%(levelname)s ' \
              '- %(filename)s+%(lineno)d: %(message)s'
    logging.basicConfig(format=lformat, level=logging.INFO)

log = logging.getLogger(__package__)
log.debug("logging was configured...")
# alog = logging.getLogger('requests_oauthlib')
# alog.addHandler(logging.StreamHandler(sys.stdout))
# alog.setLevel(logging.INFO)

TOKEN_REQUEST_ATTEMPTS = 3
EXPECTED_SALT_LENGTH = 64


class ConfigErr(Exception):
    pass


class OlassClient():

    def __init__(self,
                 config_file,
                 interactive=True,
                 rows_per_batch=1,
                 create_tables=False,
                 root_path='.',
                 default_config={}):
        """
        Setup the database connection obtain an access token
        """
        self.show_logo()
        self.config = Config(root_path=root_path, defaults=default_config)
        self.config.from_pyfile(config_file)
        log.info("Load config file: {}".format(config_file))
        self.update_config(interactive=interactive,
                           rows_per_batch=rows_per_batch)
        self.validate_config()
        self.engine = utils.get_db_engine(self.config)
        self.session = OlassClient.get_db_session(self.engine, create_tables)
        # self.config.from_object(some_module.DefaultConfig)

    def update_config(self, interactive, rows_per_batch=1):
        """
        Write the command line options to the config object for easy access.

        :param interactive: when `true` ask for confirmation before executing
        :param rows_per_batch: how many rows to process each time we
                               connect to the server

        """
        if rows_per_batch is None or rows_per_batch < 1:
            rows_per_batch = 1

        self.config['INTERACTIVE'] = interactive
        self.config['ROWS_PER_BATCH'] = rows_per_batch

    def validate_config(self):
        """
        Check for required arguments.
        """
        # TODO: perhaps add a generic function for checking and a array
        # of expected variables

        if not self.config.get('CLIENT_ID'):
            raise ConfigErr("Please add config param 'CLIENT_ID'")

        if not self.config.get('CLIENT_SECRET'):
            raise ConfigErr("Please add config param 'CLIENT_SECRET'")

        if not self.config.get('TOKEN_URL'):
            raise ConfigErr("Please add config param 'TOKEN_URL'")

        if not self.config.get('SAVE_URL'):
            raise ConfigErr("Please add config param 'SAVE_URL'")

        if not self.config.get('DB_TYPE'):
            raise ConfigErr("Please add config param 'DB_TYPE'")

        if not self.config.get('DB_HOST'):
            raise ConfigErr("Please add config param 'DB_HOST'")

        if not self.config.get('DB_PORT'):
            raise ConfigErr("Please add config param 'DB_PORT'")

        if not self.config.get('DB_USER'):
            raise ConfigErr("Please add config param 'DB_USER'")

        if not self.config.get('DB_PASS'):
            raise ConfigErr("Please add config param 'DB_PASS'")

        if not self.config.get('SALT'):
            raise ConfigErr("Please add config param 'SALT'")

        if len(self.config.get('SALT')) != EXPECTED_SALT_LENGTH:
            raise ConfigErr("Please add config param 'SALT' ({} characters)"
                            .format(EXPECTED_SALT_LENGTH))

        if not self.config.get('ENABLED_RULES'):
            raise ConfigErr("Please add config array 'ENABLED_RULES'")

        for rule_code in self.config.get('ENABLED_RULES'):
            if rule_code not in rules.AVAILABLE_RULES_MAP:
                raise ConfigErr('Invalid rule code: [{}]! '
                                'Available codes are: {}'
                                .format(rule_code, rules.AVAILABLE_RULES_MAP))

    @classmethod
    def get_db_session(cls, engine, create_tables=False):
        """
        Connect to the database and return a Session object

        :param create_tables: boolean used to request table creation
        """
        log.debug("Call get_db_session()")
        base.init(engine)
        session = base.DBSession()

        if create_tables:
            base.metadata.create_all(engine)

        return session

    def get_access_token(self, attempt=0):
        """
        Connects to the TOKEN_URL endpoint to retrieve a token.
        """
        # TODO: add logic to sleep for X seconds if
        # expires_in < X seconds required to process a batch
        log.debug('Call get_access_token(attempt={})'.format(attempt))
        client_id = self.config.get('CLIENT_ID')
        client_secret = self.config.get('CLIENT_SECRET')

        client = BackendApplicationClient(client_id)
        olass = OAuth2Session(client=client)

        try:
            token = olass.fetch_token(
                token_url=self.config.get('TOKEN_URL'),
                client_id=client_id,
                client_secret=client_secret,
                verify=self.config.get('VERIFY_SSL_CERT', False))

            if token.get('expires_in') == 0:
                if attempt < TOKEN_REQUEST_ATTEMPTS:
                    log.warn("Got an expired token. Re-trying attempt {}..."
                             .format(attempt))
                    return self.get_access_token(attempt + 1)
                else:
                    sys.exit("Give up after {} attempts to get a token"
                             .format(TOKEN_REQUEST_ATTEMPTS))
        except Exception as exc:
            log.error("get_access_token() problem due: {}".format(exc))
            raise exc
        return token

    @staticmethod
    def get_patient_data(session, rows_per_batch, hashing_rules, salt):
        """
        Find patients without `linkage_uuid` and hash their data

        :param session: the database session
        :param rows_per_batch: how many entries to load at one time
            (to avoid overloading the server)
        :param hashing_rules: a list of rule codes
            which should match the constants defined in `olass.rules` module
        :return: two data dictionaries:
            patient_map, hashes
        """
        patients = session.query(Patient).filter(
            Patient.pat_birth_date.isnot(None),
            Patient.pat_first_name.isnot(None),
            Patient.pat_last_name.isnot(None),
            Patient.linkage_uuid.is_(None)
        ).limit(rows_per_batch)
        return rules.prepare_patients(patients, hashing_rules, salt)

    @staticmethod
    def save_response_json(session, patient_map, json_data):
        """
        Called by :meth:`send_hashes_to_server`

        http://docs.sqlalchemy.org/en/latest/orm/query.html

        :param session: the database session
        """
        data = json_data.get('data')
        linkage_added_at = datetime.now()

        for i, pat_id in patient_map.items():
            # log.info("set linkage_uuid = {} WHERE pat_id = {}"
            #          .format(data.get(i).get('uuid'), pat_id))
            linkage_uuid = utils.get_uuid_bin(data.get(i).get('uuid'))

            pat = Patient.get_by_id(pat_id)
            pat.update(linkage_uuid=linkage_uuid,
                       linkage_added_at=linkage_added_at)
        return True

    @staticmethod
    def send_hashes_to_server(config, session, token, patient_map, hashes):
        """
        Send the specified dictionary to the OLASS server.

        :rtype Boolean
        :return True: if all data was sent to the server and response
                    saved to the local database
        """
        success = False
        url = config.get('SAVE_URL')
        log.debug("Sending hashes for [{}] patients to [{}]"
                  .format(len(hashes), url))
        client_id = config.get('CLIENT_ID')
        client = BackendApplicationClient(client_id)

        try:
            olass = OAuth2Session(client=client, token=token)
            json_data = json.dumps({'data': hashes},
                                   indent=2,
                                   sort_keys=True)
            log.debug(json_data)
            headers = {'Content-Type': 'application/json'}
            response = olass.post(url,
                                  data=json_data.encode('utf-8'),
                                  headers=headers,
                                  verify=config.get('VERIFY_SSL_CERT', False),
                                  )
            response_json = response.json()

            log.info("Start updating {} patients with linkage_uuids"
                     .format(len(patient_map)))
            OlassClient.save_response_json(session, patient_map, response_json)
            success = True
        except Exception as exc:
            log.error("Failed due: {}".format(exc))
            # log.error("Response: {}".format(response.text))
        return success

    @staticmethod
    def get_batch_count(session, rows_per_batch):
        """
        Used by :meth:`run`
        """
        sql = text('SELECT COUNT(*) AS rows '
                   'FROM patient WHERE linkage_uuid IS NULL')
        rows = session.execute(sql).scalar()
        return 1 + int(rows / rows_per_batch)

    def _run_batch(self, batch_count, batch):
        """
        Called by :meth:`run`

        :param batch_count: how many are totaly
        :param batch: the current batch number
        :return: tuple(bool, number_of_hashes_computed)
        """
        log.info("Processing batch: {}".format(batch))
        token = self.get_access_token()
        log.debug('Access token: {}'.format(token))

        # After a database update we want to find new rows
        self.session.expire_all()

        patient_map, patient_hashes = OlassClient.get_patient_data(
            self.session,
            self.config.get('ROWS_PER_BATCH'),
            self.config.get('ENABLED_RULES'),
            self.config.get('SALT')
        )
        log.info('Batch [{} out of {}] got hashes for [{}] patients'
                 .format(batch, batch_count, len(patient_hashes)))
        done = OlassClient.send_hashes_to_server(self.config,
                                                 self.session,
                                                 token,
                                                 patient_map,
                                                 patient_hashes)
        return done, len(patient_hashes)

    def run(self):
        """
        Retrieve the unprocessed patients, compute hashes,
        and send data to the OLASS server.

        """
        log.info('TOKEN_URL: {}'.format(self.config.get('TOKEN_URL')))
        rows_per_batch = self.config.get('ROWS_PER_BATCH')
        batch_count = OlassClient.get_batch_count(self.session, rows_per_batch)
        batch_status = {}

        question = "Do you want to continue with " \
            "{} batches ({} rows per batch)?".format(batch_count,
                                                     rows_per_batch)

        if self.config.get('INTERACTIVE') and not utils.ask_yes_no(question):
            sys.exit("Make it so!")

        for i in range(batch_count):
            # Stop to estimate performance
            if False and i == 10:
                sys.exit('Stopped at batch: {}'.format(i))

            status, rows = self._run_batch(batch_count, i)
            batch_status[i] = status

        done = all(status for status in batch_status.values())

        if done:
            log.info("All done!")
        else:
            log.info("Fail!")

    def show_logo(self):
        """ show a figlet... """
        print("""
  ___  _        _    ____ ____
 / _ \| |      / \  / ___/ ___|  __   __
| | | | |     / _ \ \___ \___ \  \ \ / /+======
| |_| | |___ / ___ \ ___) |__) |  \ V / # {}
 \___/|_____/_/   \_\____/____/    \_/  +======

""".format(__version__))
