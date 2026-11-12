"""Exercise the installed OIDC package and the image's logout patches."""
import sys
from importlib.metadata import version
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from django.conf import settings

SERVER = {
    'CLIENT_ID': 'test-client', 'CLIENT_SECRET': 'test-secret',
    'TOKEN_ENDPOINT': 'https://identity.example.org/oauth2/token',
    'AUTHORIZATION_ENDPOINT': 'https://identity.example.org/oauth2/authorize',
    'JWKS_ENDPOINT': 'https://identity.example.org/jwks',
    'END_SESSION_ENDPOINT': 'https://identity.example.org/logout',
    'REDIRECT_URI': 'https://rapidpro.example.org/oidc/default/callback/',
    'RESPONSE_TYPE': 'code', 'RESPONSE_MODE': 'form_post',
    'REQUEST_MODE': 'form_post', 'USE_NONCES': False,
}
settings.configure(
    SECRET_KEY='test-only', ROOT_URLCONF=__name__,
    INSTALLED_APPS=['django.contrib.auth', 'django.contrib.contenttypes',
                    'django.contrib.sessions', 'rest_framework', 'oidc'],
    DATABASES={'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}},
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}},
    MIDDLEWARE=['django.contrib.sessions.middleware.SessionMiddleware',
                'django.contrib.auth.middleware.AuthenticationMiddleware'],
    TEMPLATES=[{'BACKEND': 'django.template.backends.django.DjangoTemplates', 'APP_DIRS': True}],
    ALLOWED_HOSTS=['testserver'],
    OPENID_CONNECT_AUTH_SERVERS={'default': SERVER},
    OPENID_CONNECT_POST_LOGOUT_REDIRECT_URI='',
    OPENID_CONNECT_VIEWSET_CONFIG={
        'USE_RAPIDPRO_VIEWSET': True, 'USE_AUTH_BACKEND': True,
        'USE_SSO_COOKIE': False, 'AUTO_CREATE_USER': False,
        'REDIRECT_AFTER_AUTH': '/org/choose/',
        'MAP_CLAIM_TO_MODEL': {'sub': 'email'},
    },
)
import django

django.setup()
from django.urls import include, path

urlpatterns = [path("", include("oidc.urls"))]
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.test.runner import DiscoverRunner
from oidc.client import OpenIDClient, TokenVerificationFailed


class OIDCCompatibilityTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='existing', email='existing@example.org')

    def test_runtime(self):
        self.assertEqual(sys.version_info[:2], (3, 10))
        self.assertEqual(django.VERSION[:2], (4, 2))
        self.assertEqual(version('ona-oidc'), '2.6.0')

    @patch('oidc.client.requests.post')
    def test_token_exchange_uses_body(self, post):
        post.return_value.json.return_value = {'id_token': 'test-token'}
        result = OpenIDClient('default').retrieve_tokens_using_auth_code('test-code')
        self.assertEqual(result['id_token'], 'test-token')
        args, kwargs = post.call_args
        self.assertEqual(args, (SERVER['TOKEN_ENDPOINT'],))
        self.assertIsNone(kwargs['params'])
        self.assertEqual(kwargs['data'], {
            'grant_type': 'authorization_code', 'code': 'test-code',
            'client_id': 'test-client', 'client_secret': 'test-secret',
            'redirect_uri': SERVER['REDIRECT_URI'],
        })
        self.assertEqual(kwargs['headers']['Content-Type'], 'application/x-www-form-urlencoded')

    def login(self):
        session = self.client.session
        session['before_login'] = True
        session.save()
        old_key = session.session_key
        with patch.object(OpenIDClient, 'retrieve_tokens_using_auth_code',
                          return_value={'id_token': 'test-token'}), \
             patch.object(OpenIDClient, 'verify_and_decode_id_token',
                          return_value={'sub': self.user.email}), \
             patch.object(OpenIDClient, 'retrieve_user_info') as user_info:
            response = self.client.post('/oidc/default/callback', {'code': 'test-code'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/org/choose/')
        self.assertEqual(self.client.session['_auth_user_id'], str(self.user.pk))
        self.assertEqual(self.client.session['oidc_id_token'], 'test-token')
        self.assertNotEqual(self.client.session.session_key, old_key)
        user_info.assert_not_called()
        self.user.refresh_from_db()
        self.assertIsNotNone(self.user.last_login)

    def test_existing_user_callback(self):
        self.login()

    def test_post_logout_clears_session(self):
        self.login()
        response = self.client.post('/oidc/default/logout')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(parse_qs(urlsplit(response.url).query), {'id_token_hint': ['test-token']})
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertNotIn('oidc_id_token', self.client.session)
        self.assertEqual(response.cookies['sessionid']['max-age'], 0)
        self.assertIn('no-store', response['Cache-Control'])
        self.assertEqual(response['Pragma'], 'no-cache')

    @override_settings(OPENID_CONNECT_POST_LOGOUT_REDIRECT_URI='https://rapidpro.example.org/users/login')
    def test_logout_redirect_and_existing_query(self):
        client = OpenIDClient('default')
        client.end_session_endpoint += '?client_id=test-client'
        query = parse_qs(urlsplit(client.logout(id_token_hint='a+b').url).query)
        self.assertEqual(query, {'client_id': ['test-client'], 'id_token_hint': ['a+b'],
                                'post_logout_redirect_uri': ['https://rapidpro.example.org/users/login']})

    def test_logout_without_token(self):
        self.assertEqual(self.client.get('/oidc/default/logout').url, SERVER['END_SESSION_ENDPOINT'])

    def test_missing_code_does_not_authenticate(self):
        response = self.client.post('/oidc/default/callback', {})
        self.assertEqual(response.status_code, 400)
        self.assertNotIn('_auth_user_id', self.client.session)

    @patch.object(OpenIDClient, 'retrieve_tokens_using_auth_code',
                  side_effect=TokenVerificationFailed('Rejected test code'))
    def test_rejected_code_does_not_authenticate(self, exchange):
        response = self.client.post('/oidc/default/callback', {'code': 'bad-code'})
        self.assertEqual(response.status_code, 401)
        self.assertNotIn('_auth_user_id', self.client.session)


if __name__ == '__main__':
    # Imported as a standalone script inside the image, independent of RapidPro's PostGIS database.
    sys.exit(bool(DiscoverRunner(verbosity=2).run_tests(['__main__'])))
