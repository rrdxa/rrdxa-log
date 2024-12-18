"""
Django settings for rrdxa project.

Generated by 'django-admin startproject' using Django 3.2.13.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.2/ref/settings/
"""

from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-v%%kw28nw6d6z&v%s$6e^*)6^e*x*wfb5e85-9es*dq+-f83x$'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = ['logbook.rrdxa.org', 'localhost', '127.0.0.1']


# Application definition

INSTALLED_APPS = [
    'daphne',
    #'channels',
    #'channels_postgres',
    'django.contrib.humanize',
    'api',
    'cluster',
    'contestchallenge',
    'dxchallenge',
    'rrlog',
    'rrmember',
]

MIDDLEWARE = [
]

ROOT_URLCONF = 'rrdxa.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
            ],
        },
    },
]

WSGI_APPLICATION = 'rrdxa.wsgi.application'
ASGI_APPLICATION = "rrdxa.asgi.application"

# Database
# https://docs.djangoproject.com/en/3.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'rrdxa',
    },
    #'channels_postgres': {
    #    'ENGINE': 'django.db.backends.postgresql',
    #    'NAME': 'rrdxa',
    #},
}

CHANNEL_LAYERS = {
    'default': {
        #'BACKEND': 'channels_postgres.core.PostgresChannelLayer',
        #'CONFIG': {
        #    'ENGINE': 'django.db.backends.postgresql',
        #    'NAME': 'rrdxa',
        #    'config': {
        #    }
        #},
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [("127.0.0.1", 6379)],
        },
    },
}

# Internationalization
# https://docs.djangoproject.com/en/3.2/topics/i18n/
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.2/howto/static-files/
STATIC_URL = 'static/'

# Default primary key field type
# https://docs.djangoproject.com/en/3.2/ref/settings/#default-auto-field
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# people who can edit other people's uploads
RRDXA_ADMINS = [
        'DF7CB',
        'DF7EE',
        'DK2DQ',
        'DL9DAN',
        ]
