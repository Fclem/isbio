from utilz import is_host_online, test_url
from isbio.settings import INSTALLED_APPS, AuthMethods


def check_cas(server_ip, server_url):
	""" Check if CAS server is responding

		imported code from system_check.check_cas
	"""
	if is_host_online(server_ip, 2):
		try:
			return test_url(server_url)
		except Exception:
			pass
	return False

AUTHENTICATION_BACKENDS = (
	'django.contrib.auth.backends.ModelBackend',
	'django_cas_ng.backends.CASBackend',
)

HOME_PAGE = '/jobs/'
ROOT_URLCONF = 'isbio.urls'

CAS_SERVER_IP = 'cas-prot.fimm.fi'
CAS_FRONT_END_URL = 'https://%s/cas/' % CAS_SERVER_IP
CAS_BACK_END_URL = 'https://%s:8443/cas/' % CAS_SERVER_IP
CAS_SERVER_URL = CAS_FRONT_END_URL
# automatic CAS url
if not check_cas(CAS_SERVER_IP, CAS_SERVER_URL):
	CAS_SERVER_URL = CAS_BACK_END_URL
CAS_REDIRECT_URL = '/home/'

INSTALLED_APPS += ['django_cas_ng']

AUTH_BACKEND = AuthMethods.CAS_NG
