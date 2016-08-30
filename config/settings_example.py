"""
Goal: store application settings.

Notes:
-   This file serves as an example only and should be changed
    for production deployments.
-   The *SALT* value will be provided over the phone.
"""

# Set to False if the a target server has a self-signed certificate
VERIFY_SSL_CERT = False

CLIENT_ID = 'client_1'
CLIENT_SECRET = 'secret_1'

# Application endpoints
TOKEN_URL = 'https://localhost:5000/oauth/token'
SAVE_URL = 'https://localhost:5000/api/save'

DB_TYPE = 'mysql'  # or 'mssql'
DB_HOST = 'localhost'
DB_PORT = 3306
DB_NAME = 'olassc'
DB_USER = 'olassc'
DB_PASS = 'insecurepassword'

# Expected length: 64 characters
# Derived from 'himalayan_salt'
SALT = '5ce3c76fae7161e7d45a5c96fb6a2b2131134af739fc1c85465e659aded4e431'

# Partners should only add/remove elements to this array
# to activate/deactivate hashing rules
ENABLED_RULES = ['F_L_D_Z', 'L_F_D_Z', 'F_L_D_C', 'L_F_D_C']
