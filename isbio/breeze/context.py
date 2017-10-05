from django.contrib.auth.models import User
from django.contrib.sites.shortcuts import get_current_site
from django.utils.functional import SimpleLazyObject
from breeze.utils import autogen_context_dict
from django.conf import settings


def site(request):
	a_site = SimpleLazyObject(lambda: get_current_site(request))
	protocol = 'https' if request.is_secure() else 'http'
	
	return {
		'site'     : a_site,
		'site_root': SimpleLazyObject(lambda: "{0}://{1}".format(protocol, a_site.domain)),
		'site_title': settings.BREEZE_TITLE,
		'site_title_long': settings.BREEZE_TITLE_LONG
	}


def user_context(request):
	is_auth = request.user.is_authenticated()
	is_admin = False
	try:
		is_admin = is_auth and (request.user.is_staff or request.user.is_superuser)
	except Exception as e:
		from utilz import logger
		logger.critical('while forming is_admin context: %s' % e)
	
	return {
		'is_local_admin': is_admin,
		'is_authenticated': is_auth,
		'guest_expiry': '%s hours' % (settings.GUEST_EXPIRATION_TIME / 60)
	}


def date_context(_):
	import datetime
	return {'now': datetime.datetime.now()}


def run_mode_context(_):
	return {
		'run_mode_text': '-DEV' if settings.DEV_MODE else '',
		'run_mode': settings.RUN_MODE,
		'run_env': settings.RUN_ENV
	}


# clem 06/06/2017
def __context_var_list(request):
	all_context = autogen_context_dict(request, True)
	return {'context_vars_list': all_context.keys(),
			'context_vars_values': all_context }
