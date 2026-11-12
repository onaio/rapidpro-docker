# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# -----------------------------------------------------------------------------------
# RapidPro settings file for the docker setup
# -----------------------------------------------------------------------------------

from getenv import env
import dj_database_url
import django_cache_url
import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.logging import LoggingIntegration, ignore_logger
from django.core.signals import got_request_exception
from sentry_sdk import capture_exception
from django.utils.translation import gettext_lazy as _

from temba.settings_common import *  # noqa

ROOT_URLCONF = env('ROOT_URLCONF', 'temba.urls')

DEBUG = env('DJANGO_DEBUG', 'off') == 'on'
SESSION_COOKIE_AGE = int(
    env('SESSION_COOKIE_AGE', globals().get('SESSION_COOKIE_AGE', 1209600))
)
_session_save_every_request = env(
    'SESSION_SAVE_EVERY_REQUEST',
    globals().get('SESSION_SAVE_EVERY_REQUEST', False),
)
SESSION_SAVE_EVERY_REQUEST = str(
    _session_save_every_request
).lower() in (
    '1',
    'true',
    'yes',
    'on',
)

SENTRY_DSN = os.environ.get("SENTRY_DSN", "")


if SENTRY_DSN:  # pragma: no cover
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration(), CeleryIntegration(), LoggingIntegration()],
        send_default_pii=True,
        traces_sample_rate=0,
    )
    ignore_logger("django.security.DisallowedHost")

    def send_exception_to_sentry(sender, request, **kwargs):
        exception = kwargs.get('exception')
        if exception:
            capture_exception(exception)

    got_request_exception.connect(send_exception_to_sentry)
# Django GIS auto-discovers libgeos_c, libgdal, and libproj via ldconfig
# (ctypes.util.find_library), so no GEOS_LIBRARY_PATH / GDAL_LIBRARY_PATH /
# PROJ_LIBRARY_PATH overrides are needed when the Debian -dev packages are
# installed.

SECRET_KEY = env('SECRET_KEY', required=True)

DATABASE_URL = env('DATABASE_URL', required=True)

_default_database_config = dj_database_url.parse(DATABASE_URL)
_default_database_config['CONN_MAX_AGE'] = 60
_default_database_config['ATOMIC_REQUESTS'] = True
_default_database_config['ENGINE'] = 'django.contrib.gis.db.backends.postgis'

_direct_database_config = _default_database_config.copy()
_default_database_config['DISABLE_SERVER_SIDE_CURSORS'] = True

_readonly_database_config = _default_database_config.copy()

DATABASES = {
    'default': _default_database_config,
    'direct': _direct_database_config,
    'readonly': _readonly_database_config
}

REDIS_URL = env('REDIS_URL', required=True)
CELERY_BROKER_URL = env('BROKER_URL', REDIS_URL)
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND', REDIS_URL)
CACHE_URL = env('CACHE_URL', REDIS_URL)
CACHES = {'default': django_cache_url.parse(CACHE_URL)}
if CACHES['default']['BACKEND'] == 'django_redis.cache.RedisCache':
    if 'OPTIONS' not in CACHES['default']:
        CACHES['default']['OPTIONS'] = {}
    CACHES['default']['OPTIONS']['CLIENT_CLASS'] = 'django_redis.client.DefaultClient'


# -----------------------------------------------------------------------------------
# Used when creating callbacks for Twilio, Nexmo etc..
# -----------------------------------------------------------------------------------
HOSTNAME = env('DOMAIN_NAME', 'rapidpro.ngrok.com')
TEMBA_HOST = env('TEMBA_HOST', HOSTNAME)

INTERNAL_IPS = ('*',)
ALLOWED_HOSTS = env('ALLOWED_HOSTS', HOSTNAME).split(';')

LOGGING['root']['level'] = env('DJANGO_LOG_LEVEL', 'INFO')

STORAGE_URL = env("STORAGE_URL", "http://localhost:8000/media")

AWS_STORAGE_BUCKET_NAME = env('AWS_STORAGE_BUCKET_NAME', '')
AWS_BUCKET_DOMAIN = env('AWS_BUCKET_DOMAIN', AWS_STORAGE_BUCKET_NAME + '.s3.amazonaws.com')
CDN_DOMAIN_NAME = env('CDN_DOMAIN_NAME', '')
AWS_ACCESS_KEY_ID = env('AWS_ACCESS_KEY_ID', '')
AWS_SECRET_ACCESS_KEY = env('AWS_SECRET_ACCESS_KEY', '')
AWS_S3_REGION_NAME = env('AWS_S3_REGION_NAME', '')
AWS_DEFAULT_ACL = env('AWS_DEFAULT_ACL', '')
AWS_LOCATION = env('AWS_LOCATION', '')
AWS_STATIC = env('AWS_STATIC', False)
AWS_MEDIA = env('AWS_MEDIA', False)
AWS_S3_ENDPOINT_URL = env('AWS_S3_ENDPOINT_URL', None)

if AWS_STORAGE_BUCKET_NAME:
    if CDN_DOMAIN_NAME:
        AWS_S3_DOMAIN = CDN_DOMAIN_NAME
    else:
        AWS_S3_DOMAIN = '%s.s3.amazonaws.com' % AWS_STORAGE_BUCKET_NAME

    _s3_storage_options = {
        'bucket_name': AWS_STORAGE_BUCKET_NAME,
        'region_name': AWS_S3_REGION_NAME or None,
        'endpoint_url': AWS_S3_ENDPOINT_URL,
        'default_acl': AWS_DEFAULT_ACL or None,
    }
    _s3_storage_options = {k: v for k, v in _s3_storage_options.items() if v is not None}

    if AWS_STATIC:
        STATIC_URL = "https://%s/" % AWS_S3_DOMAIN
        STORAGES['staticfiles'] = {
            'BACKEND': 'storages.backends.s3boto3.S3Boto3Storage',
            'OPTIONS': _s3_storage_options,
        }

    if AWS_MEDIA:
        MEDIA_URL = "https://%s/" % AWS_S3_DOMAIN
        STORAGES['default'] = {
            'BACKEND': 'storages.backends.s3boto3.S3Boto3Storage',
            'OPTIONS': _s3_storage_options,
        }
        STORAGES['public'] = {
            'BACKEND': 'storages.backends.s3boto3.S3Boto3Storage',
            'OPTIONS': _s3_storage_options,
        }

    STORAGES['archives'] = {
        'BACKEND': 'storages.backends.s3boto3.S3Boto3Storage',
        'OPTIONS': _s3_storage_options,
    }

if not AWS_STATIC:
    STATIC_URL = '/sitestatic/'
    MIDDLEWARE = list(MIDDLEWARE) + ['whitenoise.middleware.WhiteNoiseMiddleware']

COMPRESS_ENABLED = env('DJANGO_COMPRESSOR', 'on') == 'on'
COMPRESS_OFFLINE = False

COMPRESS_URL = STATIC_URL
# Use MEDIA_ROOT rather than STATIC_ROOT because it already exists and is
# writable on the server. It's also the directory where other cached files
# (e.g., translations) are stored
COMPRESS_ROOT = STATIC_ROOT
COMPRESS_CSS_HASHING_METHOD = 'content'
COMPRESS_OFFLINE_MANIFEST = 'manifest-%s.json' % env('RAPIDPRO_VERSION', required=True)

MAGE_AUTH_TOKEN = env('MAGE_AUTH_TOKEN', None)
MAGE_API_URL = env('MAGE_API_URL', 'http://localhost:8026/api/v1')
SEND_MESSAGES = env('SEND_MESSAGES', 'off') == 'on'
SEND_WEBHOOKS = env('SEND_WEBHOOKS', 'off') == 'on'
SEND_EMAILS = env('SEND_EMAILS', 'off') == 'on'
SEND_AIRTIME = env('SEND_AIRTIME', 'off') == 'on'
SEND_CALLS = env('SEND_CALLS', 'off') == 'on'
IP_ADDRESSES = tuple(filter(None, env('IP_ADDRESSES', '').split(',')))

EMAIL_HOST = env('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_HOST_USER = env('EMAIL_HOST_USER', 'server@temba.io')
EMAIL_PORT = int(env('EMAIL_PORT', 25))
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', 'server@temba.io')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', 'mypassword')
EMAIL_USE_TLS = env('EMAIL_USE_TLS', 'on') == 'on'
SECURE_PROXY_SSL_HEADER = (
    env('SECURE_PROXY_SSL_HEADER', 'HTTP_X_FORWARDED_PROTO'), 'https')
IS_PROD = env('IS_PROD', 'off') == 'on'
DEFAULT_BRAND = env('DEFAULT_BRAND', HOSTNAME)

BRAND = {
    'name': env('BRANDING_NAME', 'RapidPro'),
    'description': _("Visually build nationally scalable mobile applications from anywhere in the world."),
    'hosts': ALLOWED_HOSTS,
    'domain': HOSTNAME,
    'emails': {
        'notifications': env('BRANDING_EMAIL', DEFAULT_FROM_EMAIL),
        'support': env('BRANDING_SUPPORT_EMAIL', DEFAULT_FROM_EMAIL),
    },
    'logos': {
        'primary': env('BRANDING_LOGO', 'images/logo-dark.svg').lstrip('/'),
        'favico': env('BRANDING_FAVICO', 'brands/rapidpro/rapidpro.ico').lstrip('/'),
    },
    'landing': {
        'hero': env('BRANDING_SPLASH', 'brands/rapidpro/splash.jpg').lstrip('/'),
    },
    'docs_link': env('BRANDING_DOCS_LINK', 'http://docs.rapidpro.io'),
    'ticket_domain': env('BRANDING_TICKET_DOMAIN', HOSTNAME),
    'features': [],
}
if env('BRANDING_ALLOW_SIGNUPS', 'on') == 'on':
    BRAND['features'].append('signups')

COMPRESS_OFFLINE_CONTEXT = dict(
    STATIC_URL=STATIC_URL,
    base_template='frame.html',
    brand=BRAND,
    debug=False,
    testing=False,
)

REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {
    'v2': env('API_THROTTLE_V2', '2500/hour'),
    'v2.contacts': env('API_THROTTLE_V2_CONTACTS', '2500/hour'),
    'v2.messages': env('API_THROTTLE_V2_MESSAGES', '2500/hour'),
    'v2.runs': env('API_THROTTLE_V2_RUNS', '2500/hour'),
    'v2.api': env('API_THROTTLE_V2_API', '2500/hour'),
    'v2.broadcasts': env('API_THROTTLE_V2_BROADCASTS', '2500/hour'),
}

# DRF page size — overridable via PAGE_SIZE env var. Default matches
# upstream rapidpro/rapidpro (250) so unset deployments keep prior behaviour.
REST_FRAMEWORK['PAGE_SIZE'] = int(env('PAGE_SIZE', 250))

# Trust the X-Forwarded-Host header from the ingress when constructing
# request.get_host(). Only enable when every ingress in front of the app
# is trusted to strip/rewrite this header from clients.
USE_X_FORWARDED_HOST = env('USE_X_FORWARDED_HOST', 'off') == 'on'

MAILROOM_URL = env('MAILROOM_URL', '')
MAILROOM_AUTH_TOKEN = env('MAILROOM_AUTH_TOKEN', '')

FLOW_SESSION_TRIM_DAYS = env('FLOW_SESSION_TRIM_DAYS', 7)
MAX_ACTIVE_CONTACTFIELDS_PER_ORG = env('MAX_ACTIVE_CONTACTFIELDS_PER_ORG', 250)

# set of ISO-639-3 codes of languages to allow in addition to all ISO-639-1 languages
iso_3_languages = env('NON_ISO6391_LANGUAGES', '')
NON_ISO6391_LANGUAGES = {}
if iso_3_languages:
    NON_ISO6391_LANGUAGES = set(iso_3_languages.split(','))

ENABLE_OIDC = env('ENABLE_OIDC', 'off')
if ENABLE_OIDC == 'on':
    INSTALLED_APPS = INSTALLED_APPS + (
        'storages',
        'oidc',
    )

    APP_URLS += [
        "oidc.urls",
    ]
    # ona-oidc expects these settings to be dicts. django-getenv's env()
    # auto-parses dict-shaped env-var values via ast.literal_eval, so
    # deployment values can use Python literals (True/False/None,
    # trailing commas) in addition to strict JSON.
    # Preserve RapidPro admin behavior; OIDC 2.6 enables its import admin by default.
    OPENID_IMPORT_USER = {'ENABLED': False}
    OPENID_CONNECT_VIEWSET_CONFIG = env('OPENID_CONNECT_VIEWSET_CONFIG', {})
    OPENID_CONNECT_AUTH_SERVERS = env('OPENID_CONNECT_AUTH_SERVERS', {})
    OPENID_CONNECT_DEFAULT_AUTH_SERVER = env('OPENID_CONNECT_DEFAULT_AUTH_SERVER', 'default')
    LOGIN_URL = "/oidc/" + OPENID_CONNECT_DEFAULT_AUTH_SERVER + "/login/"
    LOGOUT_URL = "/oidc/" + OPENID_CONNECT_DEFAULT_AUTH_SERVER + "/logout/"
    # Send id_token_hint during RP-initiated logout to identify the session.
    # Register this post-logout redirect URI with the OIDC provider for
    # the RapidPro client.
    OPENID_CONNECT_POST_LOGOUT_REDIRECT_URI = env(
        'OPENID_CONNECT_POST_LOGOUT_REDIRECT_URI', 'https://%s/users/login' % HOSTNAME)

# CSRF trusted origins — comma-separated list provided by the deployment.
# Example: CSRF_TRUSTED_ORIGINS="https://app.example.org/*,https://api.example.org/*"
_csrf_origins = env('CSRF_TRUSTED_ORIGINS', '')
if _csrf_origins:
    CSRF_TRUSTED_ORIGINS = [o.strip() for o in _csrf_origins.split(',') if o.strip()]
