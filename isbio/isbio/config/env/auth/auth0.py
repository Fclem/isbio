from utilz import get_key
from isbio.settings import INSTALLED_APPS, TEMPLATES, AUTH0_CUSTOM_BACKEND_PY_PATH, DomainList
from isbio.config import ConfigAuthMethods

AUTHENTICATION_BACKENDS = (
	AUTH0_CUSTOM_BACKEND_PY_PATH,
	# AUTH0_BACKEND_PY_PATH,
	
)
# TODO move to custom_auth ?
AUTH0_IP_LIST = ['52.169.124.164', '52.164.211.188', '52.28.56.226', '52.28.45.240', '52.16.224.164', '52.16.193.66']
AUTH0_DOMAIN = 'breeze.eu.auth0.com'
AUTH0_TEST_URL = 'https://%s/test' % AUTH0_DOMAIN
AUTH0_ID_FILE_N = 'auth0_id'
AUTH0_CLIENT_ID = get_key(AUTH0_ID_FILE_N)
AUTH0_SECRET_FILE_N = 'auth0'
AUTH0_SECRET = get_key(AUTH0_SECRET_FILE_N)
AUTH0_CALLBACK_URL_BASE = 'https://%s/login/'
# AUTH0_CALLBACK_URL = 'https://breeze.fimm.fi/login/'
AUTH0_SUCCESS_URL = '/home/'
AUTH0_LOGOUT_URL = 'https://breeze.eu.auth0.com/v2/logout?returnTo=%s'
AUTH0_OAUTH_TOKEN_URL = 'https://%s/oauth/token' % AUTH0_DOMAIN
AUTH0_USER_INFO_URL_BASE = 'https://%s/userinfo?access_token=%s'
AUTH0_DEFAULT_LOGOUT_REDIRECT = 'https://%s' % DomainList.CLOUD_PROD[0]  #  'https://www.fimm.fi'

# INSTALLED_APPS += ['django_auth0']
INSTALLED_APPS += ['custom_auth0']

# add the Auth0 Context Processors tha enabled access to AUTH0 configuration variables from templates
TEMPLATES[0]['OPTIONS']['context_processors'] += ['django_auth0.context_processors.auth0']

AUTH_BACKEND = ConfigAuthMethods.AUTH0
AUTH_BACKEND_CLASS = ConfigAuthMethods.AUTH0
