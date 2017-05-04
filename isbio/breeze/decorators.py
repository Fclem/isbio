from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import PermissionDenied
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.conf import settings


login_required_original = login_required


def decorator_tester(function=None, redirect_field_name=REDIRECT_FIELD_NAME, login_url=None, condition=None):
	assert callable(condition)
	
	login_url = login_url or settings.DEFAULT_LOGIN_URL
	if settings.FORCE_DEFAULT_LOGIN_URL:
		login_url = settings.DEFAULT_LOGIN_URL
	
	actual_decorator = user_passes_test(
		condition,
		login_url=login_url,
		redirect_field_name=redirect_field_name
	)
	if function:
		return actual_decorator(function)
	return actual_decorator


def __users_all_authenticated(user):
	return user.is_authenticated() # and not user.is_anonymous


def __users_authenticated_not_guest(user):
	if user.is_guest:
		raise PermissionDenied
	return user.is_authenticated()


def login_required(function=None, redirect_field_name=REDIRECT_FIELD_NAME, login_url=None):
	"""
	Decorator for views that checks that the user is logged in, redirecting
	to the log-in page if necessary.
	"""
	predicate = __users_authenticated_not_guest if settings.RESTRICT_GUEST_TO_SPECIFIC_VIEWS else __users_all_authenticated
	return decorator_tester(function, redirect_field_name, login_url, predicate)


from django.contrib.auth import decorators as base_decorators

base_decorators.login_required = login_required


# clem 31/03/2017
def allow_guest(function=None, redirect_field_name=REDIRECT_FIELD_NAME, login_url=None):
	"""
	Decorator for views that checks that the user is logged in, redirecting
	to the log-in page if necessary.
	"""
	return decorator_tester(function, redirect_field_name, login_url,
		__users_all_authenticated)


base_decorators.allow_guest = allow_guest
