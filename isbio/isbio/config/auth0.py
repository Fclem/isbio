from utilz import get_key

AUTHENTICATION_BACKENDS = (
	'django.contrib.auth.backends.ModelBackend',
	'django_auth0.auth_backend.Auth0Backend',
)

AUTH0_DOMAIN = 'breeze.eu.auth0.com'
AUTH0_TEST_URL = 'https://%s/test' % AUTH0_DOMAIN
AUTH0_ID_FILE_N = 'auth0_id'
AUTH0_CLIENT_ID = get_key(AUTH0_ID_FILE_N)
AUTH0_SECRET_FILE_N = 'auth0'
AUTH0_SECRET = get_key(AUTH0_SECRET_FILE_N)
AUTH0_CALLBACK_URL_BASE = 'https://%s/login/'
AUTH0_CALLBACK_URL = 'https://breeze.fimm.fi/login/'
AUTH0_SUCCESS_URL = '/home/'
AUTH0_LOGOUT_URL = 'https://breeze.eu.auth0.com/v2/logout'
AUTH0_LOGOUT_REDIRECT = 'https://www.fimm.fi'

AUTH0_IP_LIST = ['52.169.124.164', '52.164.211.188', '52.28.56.226', '52.28.45.240', '52.16.224.164', '52.16.193.66']

if MODE_PROD:
	ALLOWED_HOSTS = PROD_DOMAINS + AUTH0_IP_LIST
else:
	ALLOWED_HOSTS = DEV_DOMAINS + AUTH0_IP_LIST
# FIXME : replace with Site.objects.get(pk=0)
AUTH0_CALLBACK_URL = AUTH0_CALLBACK_URL_BASE % ALLOWED_HOSTS[0]

INSTALLED_APPS += ['django_auth0']

TEMPLATES[0]['OPTIONS']['context_processors'] += ['django_auth0.context_processors.auth0',]
