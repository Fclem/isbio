from __future__ import print_function
from django.shortcuts import render
from django.conf import settings
from django.contrib import auth
from django.core.urlresolvers import reverse
from django.shortcuts import redirect
from django.http import HttpResponse
from django.contrib import messages
from utilz import logger, is_http_client_in_fimm_network # , this_function_name
from breeze.models import BreezeUser # FIXME breaks modularity of the app concept
import json
import requests


UserModel = BreezeUser


def show_login_page(request):
	context = {'from_fimm': is_http_client_in_fimm_network(request)}
	context = {'from_fimm': False}
	return render(request, 'hello_auth/base.html', context=context)


# clem 12/04/2017
def __login_stage_two(request, user_bis):
	user_details = (user_bis.username, user_bis.email)
	# user is authenticated
	if user_bis:
		auth.login(request, user_bis) # persists user
		logger.info('AUTH success for %s (%s)' % user_details)
		# return index(request)
		return success_redirect
	request.session['profile'] = None
	logger.warning('AUTH denied for %s (%s)' % user_details)
	return login_page_redirect()


# clem 30/03/2017
def guest_login(request):
	if not request.user.is_authenticated():
		new_guest = UserModel.new_guest()
		new_guest.backend = settings.AUTH0_CUSTOM_BACKEND_PY_PATH
		if new_guest:
			return __login_stage_two(request, new_guest)
	
	return success_redirect


# clem 10/04/2017
# This is AUTH0 callback endpoint
def process_login(request):
	""" Default handler to login user

	:param request: HttpRequest
	:param user: User
	"""
	
	code = request.GET.get('code', None)
	if code: # Normal AUTH0 login request
		json_header = {'content-type': 'application/json'}
		
		token_payload = {
			'client_id':     settings.AUTH0_CLIENT_ID,
			'client_secret': settings.AUTH0_SECRET,
			'redirect_uri':  settings.AUTH0_CALLBACK_URL,
			'code':          code,
			'grant_type':    'authorization_code'
		}
		
		token_info = requests.post(settings.AUTH0_OAUTH_TOKEN_URL, data=json.dumps(token_payload),
			headers=json_header).json()
		
		if 'error' not in token_info:
			user_url = settings.AUTH0_USER_INFO_URL_BASE % (settings.AUTH0_DOMAIN, token_info['access_token'])
			user_info = requests.get(user_url).json()
			
			user = auth.authenticate(**user_info)
			# We're saving all user information into the session
			request.session['profile'] = user_info
			
			return __login_stage_two(request, user)
		# error from AUTH0
		messages.add_message(request, messages.ERROR, 'AUTH0: %s' % token_info['error'])
		logger.warning('AUTH failure (AUTH0 denied) [%s]' % str(token_info))
	else: # eventual other AUTH0 methods
		# unsupported method
		logger.warning('AUTH invalid GET[%s] POST[%s] content: %s' % (request.GET.__dict__,
		request.POST.__dict__, str(request.body)))
		messages.add_message(request, messages.ERROR, 'Unexpected or unsupported authentication mode')
		print('unsupported auth type :\n', request.GET.__dict__, request.POST.__dict__)
	return login_page_redirect()


# clem 12/04/2017
def logout_login(request):
	trigger_logout(request)
	return HttpResponse(status=200)


# clem 10/04/2017
def trigger_logout(request):
	if request.user.is_authenticated():
		user, url = UserModel.get(request), ''
		auth.logout(request)
		logger.info('LOGOUT %s (%s)' % (user.username, user.email))
		
		try:
			url = user.user_profile.institute_info.url or settings.AUTH0_DEFAULT_LOGOUT_REDIRECT
		except Exception as e:
			logger.exception(str(e))
		
		user.guest_auto_remove()
		return redirect(settings.AUTH0_LOGOUT_URL % url)
	return login_page_redirect()
	

def index(request):
	if not request.user.is_authenticated(): # !! DO NOT REPLACE BY login_required or allow_guest decorator !!
		error = request.GET.get('error', '')
		if error: # get the error sent by Auth0
			error_description = request.GET.get('error_description', '')

			if error and error_description:
				# commit an error message
				logger.info('AUTH FAILED %s, %s' % (error, error_description))
				messages.add_message(request, messages.ERROR, '%s : %s' % (error, error_description))
				# redirect to self, stripping down the QS and sending the message as cookie
				return login_page_redirect()

		return show_login_page(request)

		# return __guest_handler(request) # disabled as this is meant for auto-guest creation
	else:
		return success_redirect


# has to be enclosed otherwise reverse would fail at import time as urls are not resolved
def login_page_redirect(): return redirect(reverse('login_page'))


success_redirect = redirect(settings.AUTH0_SUCCESS_URL)
server_error_response = HttpResponse(status=503)
