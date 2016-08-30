"""
Goal: store application settings
"""
CLIENT_ID = 'client_1'
CLIENT_SECRET = 'secret_1'

# Application endpoints
TOKEN_URL = 'https://localhost'
SAVE_URL = 'https://localhost'

DB_TYPE = 'mysql'
DB_HOST = 'localhost'
DB_PORT = 123
DB_NAME = ''
DB_USER = 'aa'
DB_PASS = 'bb'

# DB_URL_TESTING = 'sqlite:///:memory:'
DB_URL_TESTING = 'sqlite:///db.sqlite'

SALT = '5ce3c76fae7161e7d45a5c96fb6a2b2131134af739fc1c85465e659aded4e431'

# Partners should only add/remove elements to this array
# to activate/deactivate hashing rules
ENABLED_RULES = ['F_L_D_Z', 'L_F_D_Z', 'F_L_D_C', 'L_F_D_C']
