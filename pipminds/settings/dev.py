from .base import *

from celery.schedules import crontab

DEBUG = True

ALLOWED_HOSTS = []


INSTALLED_APPS += [
    'debug_toolbar'
]

MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware', ]

DEBUG_TOOLBAR_PANELS = [
    'debug_toolbar.panels.versions.VersionsPanel',
    'debug_toolbar.panels.timer.TimerPanel',
    'debug_toolbar.panels.settings.SettingsPanel',
    'debug_toolbar.panels.headers.HeadersPanel',
    'debug_toolbar.panels.request.RequestPanel',
    'debug_toolbar.panels.sql.SQLPanel',
    'debug_toolbar.panels.staticfiles.StaticFilesPanel',
    'debug_toolbar.panels.templates.TemplatesPanel',
    'debug_toolbar.panels.cache.CachePanel',
    'debug_toolbar.panels.signals.SignalsPanel',
    'debug_toolbar.panels.logging.LoggingPanel',
    'debug_toolbar.panels.redirects.RedirectsPanel',
]


def show_toolbar(request):
    return True


DEBUG_TOOLBAR_CONFIG = {
    'INTERCEPT_REDIRECTS': False,
    'SHOW_TOOLBAR_CALLBACK': show_toolbar
}


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}



# DATABASES = {
#     'default': {
       
#         'ENGINE': 'django.db.backends.postgresql_psycopg2',
#         'NAME': 'pipminds_dev',
#         'USER': 'olabanji',
#         'PASSWORD': 'olabanji',
#         'HOST': 'pipminds.cx7ec7mq1fnr.us-east-1.rds.amazonaws.com',
#         'PORT': '5432'
#     }
# }



EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.sendgrid.net'
# EMAIL_HOST = 'smtp.zoho.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True 


DEFAULT_FROM_EMAIL = "Pipminds Invest <hello@pipminds.com>"
# DEFAULT_FROM_EMAIL = "Pipminds Invest <support@pipminds.com>"

# EMAIL_HOST_USER = "support@pipminds.com"
EMAIL_HOST_USER = "apikey"
# EMAIL_HOST_PASSWORD = "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"
EMAIL_HOST_PASSWORD = "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"
# EMAIL_HOST_PASSWORD = "6vs492KNuYUX"

ADMINS = (('Pipminds Support', 'dev@scriptdeskng.com'),)

PAYSTACK_SECRET_KEY = config('PAYSTACK_SECRET_KEY')


MONNIFY_SECRET_KEY = config('MONNIFY_SECRET_KEY')

MONNIFY_API_KEY = config('MONNIFY_API_KEY')

MONNIFY_CONTRACT_CODE = config('MONNIFY_CONTRACT_CODE')

MONNIFY_BASE_URL = config('MONNIFY_BASE_URL')

TEST_MONNIFY_SECRET_KEY = config('TEST_MONNIFY_SECRET_KEY')

TEST_MONNIFY_API_KEY = config('TEST_MONNIFY_API_KEY')

TEST_MONNIFY_CONTRACT_CODE = config('TEST_MONNIFY_CONTRACT_CODE')

TEST_MONNIFY_BASE_URL = config('TEST_MONNIFY_BASE_URL')


FLUTTERWAVE_SECRET_KEY = config('FLUTTERWAVE_SECRET_KEY')

FLUTTERWAVE_ENCRYPTION_KEY = config('FLUTTERWAVE_ENCRYPTION_KEY')

TEST_FLUTTERWAVE_SECRET_KEY = config('TEST_FLUTTERWAVE_SECRET_KEY')

TEST_FLUTTERWAVE_ENCRYPTION_KEY = config('TEST_FLUTTERWAVE_ENCRYPTION_KEY')



# CELERY related settings
BROKER_URL = 'amqp://localhost'
# CELERY_RESULT_BACKEND = 'amqp://'
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Africa/Lagos'


CELERY_BEAT_SCHEDULE = {
    # Executes every Friday at 4pm
    'credit_active_cip_user_investments': { 
         'task': 'investment.tasks.credit_cip_active_investments', 
         'schedule': crontab(minute=0, hour=0),
        },
        'credit_active_hip_user_investments': { 
         'task': 'investment.tasks.credit_hip_active_investments', 
         'schedule': crontab(minute=0, hour=0),
        },         
}



AWS_ACCESS_KEY_ID = config("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = config("AWS_SECRET_ACCESS_KEY")
AWS_STORAGE_BUCKET_NAME = config("AWS_STORAGE_BUCKET_NAME")

AWS_S3_FILE_OVERWRITE = False
AWS_DEFAULT_ACL = None
AWS_S3_REGION_NAME = 'us-east-1'
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'