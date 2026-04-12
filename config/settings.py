"""
Django settings for Стильняшки project.

Development uses SQLite; production uses PostgreSQL.
All secrets are read from environment variables (see .env.example).
"""

import os
from pathlib import Path
from dotenv import dotenv_values

env_keys = dotenv_values()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-dev-key-change-in-production')

DEBUG = os.environ.get('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost 127.0.0.1').split()

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
if os.environ.get('DATABASE_URL') or os.environ.get('DB_NAME'):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('DB_NAME', 'stylnyashki'),
            'USER': os.environ.get('DB_USER', 'postgres'),
            'PASSWORD': os.environ.get('DB_PASSWORD', ''),
            'HOST': os.environ.get('DB_HOST', 'localhost'),
            'PORT': os.environ.get('DB_PORT', '5432'),
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

SITE_URL = env_keys.get("SITE_URL", "https://stylnashki.by")

WEBPAY = {
    "MERCHANT_ID": env_keys.get("WEBPAY_MERCHANT_ID", ""),  # из Webpay
    "SECRET_KEY": env_keys.get("WEBPAY_SECRET_KEY", "1"),  # секретный ключ
    "PAYMENT_URL": env_keys.get("WEBPAY_PAYMENT_URL", "https://pay.webpay.by/checkout"),  # пример
    "API_URL": env_keys.get("WEBPAY_API_URL", "https://api.webpay.by"),  # если нужен
    "RETURN_URL": SITE_URL + "/payments/return/",
    "CALLBACK_URL": SITE_URL + "/payments/webhook/",
    "CURRENCY": "BYN",
}
