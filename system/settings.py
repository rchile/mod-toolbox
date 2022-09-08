import os

from dotenv import load_dotenv
import dj_database_url
from django.contrib.messages import constants as messages

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECRET_KEY = os.getenv('SECRET_KEY', '')
DEBUG = os.getenv('DEBUG', '') == '1'
ALLOWED_HOSTS = [h for h in os.getenv('ALLOWED_HOSTS', '').split(',') if h]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'toolbox'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'system.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# Logging
# https://docs.djangoproject.com/en/3.0/topics/logging/
default_log_format = '%(asctime)s | %(name)-14s | %(levelname)-8s | %(message)s'
default_log_notime = default_log_format[14:]
log_time = os.getenv('LOG_FORMAT_TIME', '1') == '1'
log_format = os.getenv('LOG_FORMAT', default_log_format if log_time else default_log_notime)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'console': {
            'format': log_format,
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'console',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
        },
        'django.utils.autoreload': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'rchilemt': {
            'handlers': ['console'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
        },
    },
}

WSGI_APPLICATION = 'system.wsgi.application'

database_url = os.getenv('DATABASE_URL', 'sqlite:///' + os.path.join(BASE_DIR, 'db.sqlite3'))
DATABASES = {'default': dj_database_url.config(default=database_url)}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': f'django.contrib.auth.password_validation.{x}'} 
    for x in [
        'UserAttributeSimilarityValidator',
        'MinimumLengthValidator',
        'CommonPasswordValidator',
        'NumericPasswordValidator'
    ]
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'America/Santiago'
USE_I18N = True
USE_L10N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'assets')
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]

# Message settings
MESSAGE_TAGS = {
    messages.DEBUG: 'alert-primary',
    messages.INFO: 'alert-light',
    messages.SUCCESS: 'alert-success',
    messages.WARNING: 'alert-warning',
    messages.ERROR: 'alert-danger',
}

# CORS headers
cors_urls_regex_env = os.getenv('CORS_URLS_REGEX')
CORS_URLS_REGEX = r'^/api/.*$' if not cors_urls_regex_env else re.compile(cors_urls_regex_env)
CORS_ORIGIN_WHITELIST = [h for h in os.getenv('CORS_ORIGIN_WHITELIST', 'https://rchile.xyz').split(',') if h]

# Reddit settings
REDDIT_APP_ID = os.getenv('REDDIT_APP_ID', '')
REDDIT_APP_SECRET = os.getenv('REDDIT_APP_SECRET', '')
REDDIT_APP_REFRESH = os.getenv('REDDIT_APP_REFRESH', '')
REDDIT_APP_REDIRECT = os.getenv('REDDIT_APP_REDIRECT', 'http://127.0.0.1:8000/session/return')
REDDIT_APP_UA = os.getenv('REDDIT_APP_UA', 'rchile-mod-toolbox/0.0.0')
REDDIT_DEFAULT_SUB = os.getenv('REDDIT_DEFAULT_SUB', 'chile')

# MongoDB URI
MODLOG_MONGODB_URI = os.getenv('MODLOG_MONGODB_URI', 'mongodb://127.0.0.1:27015/entries')

# Discord Webhook for modlog
DISCORD_MODLOG_WEBHOOK = os.getenv('DISCORD_MODLOG_WEBHOOK')

try:
    from local_settings import *
except ImportError:
    pass

if DEBUG:
    CORS_ORIGIN_WHITELIST += [
        'http://127.0.0.1:5000',
        'http://localhost:5000'
    ]
