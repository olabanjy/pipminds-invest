from .base import *

from celery.schedules import crontab

DEBUG = False
ALLOWED_HOSTS = ['18.235.234.56','portal.pipminds.com']
# ALLOWED_HOSTS = ['*']



DATABASES = {
    'default': {
        # 'ENGINE': 'django.db.backends.postgresql',
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'pipminds_dev',
        'USER': 'olabanji',
        'PASSWORD': 'olabanji',
        'HOST': 'pipminds.cx7ec7mq1fnr.us-east-1.rds.amazonaws.com',
        'PORT': '5432'
    }
}
 
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
#EMAIL_HOST = 'smtp.zoho.com'
EMAIL_HOST = 'smtp.sendgrid.net'
EMAIL_PORT = 587
EMAIL_USE_TLS = True 

DEFAULT_FROM_EMAIL = "Pipminds Invest <hello@pipminds.com>"
#EMAIL_HOST_USER = config("EMAIL_HOST_USER")
#EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD")

EMAIL_HOST_USER = "apikey"
EMAIL_HOST_PASSWORD = "SG....Pk50GCM3Qs6fEBD6rQJIIw.zqJKbTkR3ttO1qPT1m57MW7_zVJn0bAH8XpCK9pARv4"

ADMINS = (('Pipminds Support', 'hello@pipminds.com'),)

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




SESSION_COOKIE_AGE = 1209600

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
        'send_inv_mature_reminder': { 
         'task': 'investment.tasks.send_inv_mature_reminder', 
         'schedule': crontab(minute=0, hour=0),
        },
        'generate_payment_for_completed_inv': { 
         'task': 'investment.tasks.generate_payment_for_completed_inv', 
         'schedule': crontab(minute=0, hour=0),
        },
        'end_ppp_pioneers_subs': { 
         'task': 'users.tasks.end_ppp_pioneers_subs', 
         'schedule': crontab(minute=0, hour=0),
        }, 
        'end_ppp_subs': { 
         'task': 'users.tasks.end_ppp_subs', 
         'schedule': crontab(minute=0, hour=0),
        }, 
        'send_ppp_sub_reminder': { 
         'task': 'users.tasks.send_ppp_sub_reminder', 
         'schedule': crontab(minute=0, hour=0),
        },
        'start_running_pool': { 
         'task': 'pools.tasks.start_running_pool', 
         'schedule': crontab(minute=0, hour=0),
        }, 
        'end_completed_pools': { 
         'task': 'pools.tasks.end_completed_pools', 
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
