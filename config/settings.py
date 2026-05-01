"""
Django settings for Стильняшки project.

Development uses SQLite; production uses PostgreSQL.
All secrets are read from environment variables (see .env.example).
"""

import os
import logging
from pathlib import Path
from dotenv import dotenv_values
from logging.handlers import RotatingFileHandler

env_keys = dotenv_values()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = env_keys.get('SECRET_KEY', 'django-insecure-dev-key-change-in-production')

DEBUG = env_keys.get('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = env_keys.get('ALLOWED_HOSTS', 'localhost 127.0.0.1').split()

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'mptt',
    'store',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    "config.middleware.request_id.RequestIDMiddleware"
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                "store.context_processors.header_counts",
                "store.context_processors.header_categories",
                'store.context_processors.company_info',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database
# Development: SQLite; Production: PostgreSQL via env vars
if env_keys.get('DATABASE_URL') or env_keys.get('DB_NAME'):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': env_keys.get('DB_NAME', 'stylnyashki'),
            'USER': env_keys.get('DB_USER', 'postgres'),
            'PASSWORD': env_keys.get('DB_PASSWORD', ''),
            'HOST': env_keys.get('DB_HOST', 'localhost'),
            'PORT': env_keys.get('DB_PORT', '5432'),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'ru-ru'
TIME_ZONE = 'Europe/Moscow'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/account/'
LOGOUT_REDIRECT_URL = '/'

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        'rest_framework.authentication.BasicAuthentication',
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_THROTTLE_CLASSES': (
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ),
    'DEFAULT_THROTTLE_RATES': {
        'anon': '30/min',  # статус — 30 req/min для анонимов (polling)
        'user': '60/min',  # авторизованные — 60 req/min
        'retry': '5/min',  # можно использовать кастомный throttle для retry (см. ниже)
    }
}

EMAIL_BACKEND = env_keys.get("EMAIL_BACKEND")
EMAIL_HOST_PASSWORD = env_keys.get("EMAIL_HOST_PASSWORD")
EMAIL_HOST = env_keys.get("EMAIL_HOST")
EMAIL_PORT = env_keys.get("EMAIL_PORT")
EMAIL_HOST_USER = env_keys.get("EMAIL_HOST_USER")
EMAIL_USE_SSL = env_keys.get("EMAIL_USE_SSL")

DEFAULT_FROM_EMAIL = f"Стильняшки <{EMAIL_HOST_USER}>"

RESERVE_TTL_MINUTES = 60

TELEGRAM_BOT_TOKEN = env_keys.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_NEW_ORDER_CHAT_ID = env_keys.get("TELEGRAM_NEW_ORDER_CHAT_ID", "")

SITE_URL = env_keys.get("SITE_URL", "https://still-nashky.by")

WEBPAY = {
    "MERCHANT_ID": env_keys.get("WEBPAY_MERCHANT_ID", ""),  # из Webpay
    "SECRET_KEY": env_keys.get("WEBPAY_SECRET_KEY", "1"),  # секретный ключ
    "PAYMENT_URL": env_keys.get("WEBPAY_PAYMENT_URL", "https://pay.webpay.by/checkout"),  # пример
    "API_URL": env_keys.get("WEBPAY_API_URL", "https://api.webpay.by"),  # если нужен
    "RETURN_URL": SITE_URL + "/payments/return/",
    "CALLBACK_URL": SITE_URL + "/payments/webhook/",
    "CURRENCY": "BYN",
}

LOG_DIR = env_keys.get("LOG_DIR", os.path.join(BASE_DIR, "logs"))
os.makedirs(LOG_DIR, exist_ok=True)

LOG_LEVEL = env_keys.get("LOG_LEVEL", "INFO").upper()
LOG_FILE = env_keys.get("LOG_FILE", os.path.join(LOG_DIR, "app.log"))
ERROR_LOG_FILE = env_keys.get("ERROR_LOG_FILE", os.path.join(LOG_DIR, "error.log"))
LOG_MAX_BYTES = int(env_keys.get("LOG_MAX_BYTES", 10 * 1024 * 1024))  # 10MB
LOG_BACKUP_COUNT = int(env_keys.get("LOG_BACKUP_COUNT", 5))

# logging configuration
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        # чтобы в логах был request_id если middleware установит его
        "request_id": {
            "()": "config.logging_filters.RequestIDFilter",
        },
    },
    "formatters": {
        "verbose": {
            "format": "%(asctime)s [%(levelname)s] [%(name)s] [%(request_id)s] %(message)s (%(pathname)s:%(lineno)d)",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "simple": {"format": "%(levelname)s %(message)s"},
    },
    "handlers": {
        "console": {
            "level": LOG_LEVEL,
            "class": "logging.StreamHandler",
            "formatter": "verbose",
            "filters": ["request_id"],
        },
        "file": {
            "level": LOG_LEVEL,
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOG_FILE,
            "maxBytes": LOG_MAX_BYTES,
            "backupCount": LOG_BACKUP_COUNT,
            "formatter": "verbose",
            "encoding": "utf-8",
            "filters": ["request_id"],
        },
        "error_file": {
            "level": "ERROR",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": ERROR_LOG_FILE,
            "maxBytes": LOG_MAX_BYTES,
            "backupCount": LOG_BACKUP_COUNT,
            "formatter": "verbose",
            "encoding": "utf-8",
            "filters": ["request_id"],
        },
        "mail_admins": {
            "level": "ERROR",
            "class": "django.utils.log.AdminEmailHandler",
            "include_html": True,
        },
    },
    "loggers": {
        # корневой логгер (по умолчанию)
        "": {
            "handlers": ["file", "error_file"],
            "level": LOG_LEVEL,
            "propagate": True,
        },
        "django": {
            "handlers": ["file"],
            "level": "INFO",
            "propagate": False,
        },
        "django.request": {  # 500 errors reporting via mail_admins
            "handlers": ["file", "error_file", "mail_admins"],
            "level": "ERROR",
            "propagate": False,
        },
        # Включи логгер для приложения store (или вашего приложения)
        "store": {
            "handlers": [ "file", "error_file"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
    },
}


CELERY_BROKER_URL = env_keys.get("CELERY_BROKER_URL", "redis://127.0.0.1:6379/0")
CELERY_RESULT_BACKEND = env_keys.get("CELERY_RESULT_BACKEND", "redis://127.0.0.1:6379/1")

# дополнительные опции
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE  # предполагается, что TIME_ZONE задан в settings
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 60 * 5  # 5 минут на задачу (по желанию)

BULK_UPLOAD_TMP_DIR = "bulk_tmp"