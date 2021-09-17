import os

# Load the application environment
APP_ENV = os.getenv('APP_ENV')
ES_LOGIN_BSO_BACK = os.getenv('ES_LOGIN_BSO_BACK', '')
ES_PASSWORD_BSO_BACK = os.getenv('ES_PASSWORD_BSO_BACK', '')
ES_URL = os.getenv('ES_URL', 'http://localhost:9200')

# Set default config

# Export config
config = {
    'APP_ENV': APP_ENV
}
