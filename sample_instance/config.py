SECRET_KEY = 'change this value'

SQLALCHEMY_TRACK_MODIFICATIONS = False
SQLALCHEMY_DATABASE_URI = 'sqlite:////{instance}/nptimelapse.sqlite3'

CELERY_RESULT_BACKEND = 'rpc://'
CELERY_BROKER_URL = 'amqp://localhost'
