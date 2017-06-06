from django.contrib.auth.models import User
from django.contrib.sites.shortcuts import get_current_site
from django.utils.functional import SimpleLazyObject
from breeze.utils import list_context_functions
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
		'run_mode': settings.RUN_MODE
	}


def __autogen_context_dict(request, flat=False):
	def filter_functions():
		a_list = list_context_functions()
		b_list = list()
		for each in a_list:
			if not each.__name__.startswith('__') and each.__module__ == 'breeze.context':
				b_list.append(each)
		return b_list
	a_dict = dict()
	for each in filter_functions():
		data = each.__call__(request) if each.func_code.co_argcount else each.__call__()
		a_dict.update({each.__name__: data}) if not flat else a_dict.update(data)
	
	return a_dict


def __context_var_list(request):
	return {'context_vars_list': __autogen_context_dict(request, True).keys()}
