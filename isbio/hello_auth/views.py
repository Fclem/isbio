from django.shortcuts import render
from django.conf import settings
from django.contrib import auth
from django.core.urlresolvers import reverse
from django.shortcuts import redirect
from django.http import HttpResponse
from django.contrib.auth.models import User
from django.contrib import messages
from utilz import logger, is_http_client_in_fimm_network, this_function_name
import json
import requests
# from django.contrib.auth.decorators import login_required
# import os


# FIXME move elsewhere
def __make_guest_user(request, force=False):
	# create a unique guest user, and proceed to login him in
	if force or settings.AUTH_ALLOW_GUEST:
		from django.contrib.auth import get_user_model
		from breeze.models import UserProfile, Institute, OrderedUser
		from utilz import get_sha2
		import binascii
		import os
		import time
		
		kwargs = {
			'first_name': 'guest',
			'last_name': binascii.hexlify(os.urandom(3)).decode(),
		}
		username = '%s_%s' % (kwargs['first_name'], kwargs['last_name'])
		email = '%s@%s' % (username, request.META['HTTP_HOST'])
		kwargs.update({
			'username': username,
			'email': email,
			'password': get_sha2([username, email, str(time.time()), str(os.urandom(1000))])
		})

		user = get_user_model().objects.create(**kwargs)
		user = OrderedUser.objects.get(id=user.id)
		
		user_details = UserProfile()
		user_details.user = user
		user_details.institute_info = Institute.objects.get(pk=settings.GUEST_INSTITUTE_ID)
		user_details.save()
		
		logger.info('AUTH created guest user %s' % user.username)
		
		return process_login(request, user)
	else:
		return HttpResponse(status=503)


def show_login_page(request, template='hello_auth/base.html'):
	context = {'from_fimm': is_http_client_in_fimm_network(request)}
	return render(request, template, context=context)


def index(request):
	if not request.user.is_authenticated():
		error = request.GET.get('error', '')
		if error:
			error_description = request.GET.get('error_description', '')
			
			if error and error_description:
				# commit an error message
				messages.add_message(request, messages.ERROR, '%s : %s' % (error, error_description))
				return redirect(reverse(this_function_name()))
			
			return show_login_page(request)
		
		return __make_guest_user(request)
	else:
		return redirect(settings.AUTH0_SUCCESS_URL)


# TODO : use / extend auth0.auth_helpers instead
def process_login(request, user=None):
	""" Default handler to login user
	
	
	:param request: HttpRequest
	"""
	
	code = request.GET.get('code', '')
	# Normal AUTH0 login request
	if code:
		json_header = {'content-type': 'application/json'}
		token_url = 'https://%s/oauth/token' % settings.AUTH0_DOMAIN
		
		token_payload = {
			'client_id'    : settings.AUTH0_CLIENT_ID,
			'client_secret': settings.AUTH0_SECRET,
			'redirect_uri' : settings.AUTH0_CALLBACK_URL,
			'code'         : code,
			'grant_type'   : 'authorization_code'
		}
		
		token_info = requests.post(token_url,
			data=json.dumps(token_payload),
			headers=json_header).json()
		
		if 'error' not in token_info:
			url = 'https://%s/userinfo?access_token=%s'
			user_url = url % (settings.AUTH0_DOMAIN, token_info['access_token'])
			user_info = requests.get(user_url).json()
			
			user = auth.authenticate(**user_info)
			assert isinstance(user, User)
			# We're saving all user information into the session
			request.session['profile'] = user_info
			
			if user and user.is_active:
				auth.login(request, user)
				logger.info('AUTH success for %s (%s)' % (user.username, user.email))
			else: # error from django auth (i.e. inactive user, or id mismatch)
				request.session['profile'] = None
				logger.warning('AUTH denied for %s (%s)' % (user.username, user.email))
				return HttpResponse(status=403)
		else: # error from AUTH0
			print(token_info)
			if token_info['error'] == 'access_denied':
				logger.warning('AUTH failure [%s]' % str(token_info))
				return HttpResponse(status=503)
	# eventual other methods
	else:
		# guest login
		if user:
			print('before: ', user)
			# AUTH0 pass trough TODO make a guest user auth backend
			# user = auth.authenticate(nickname=user.username, email=user.email, user_id=user.password, picture='')
			# FIXME should not be statically linked
			user.backend = 'django_auth0.auth_backend.Auth0Backend'
			print('after: ', user)
			if user and user.is_active:
				auth.login(request, user)
				logger.info('AUTH guest success for %s (%s)' % (user.username, user.email))
			else: # error from django auth (i.e. inactive user, or id mismatch)
				request.session['profile'] = None
				logger.warning('AUTH guest denied for %s (%s)' % (user.username, user.email))
				return HttpResponse(status=403)
		# unsupported method
		else:
			logger.warning('AUTH invalid GET[%s] POST[%s] content: %s' % (request.GET.__dict__,
		request.POST.__dict__, str(request.body)))
			print ('unsupported auth type :\n', request.GET.__dict__, request.POST.__dict__)
	
	return index(request)


def trigger_logout(request):
	""" Default handler to login user
	
	
	:param request: HttpRequest
	"""
	if request.user.is_authenticated():
		from breeze.models import OrderedUser, UserProfile
		user = OrderedUser.getter(request)
		auth.logout(request)
		logger.info('LOGOUT %s (%s)' % (user.username, user.email))
		url = settings.AUTH0_LOGOUT_URL
		
		try:
			url = user.userprofile.institute_info.url or settings.AUTH0_LOGOUT_REDIRECT
		except Exception as e:
			logger.exception(str(e))
		
		if user.is_guest:
			username = user.username
			try:
				if UserProfile.getter(request).delete():
					logger.info('AUTH deleted guest user %s' % username)
			except Exception as e:
				logger.error('while deleting %s : %s' % (username, e))
		return redirect('%s?returnTo=%s' % (settings.AUTH0_LOGOUT_URL, url))
		# return redirect('https://www.fimm.fi')
	else:
		return HttpResponse(status=503)
