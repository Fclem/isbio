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


def show_login_page(request, template='hello_auth/base.html'):
	context = {'from_fimm': is_http_client_in_fimm_network(request)}
	return render(request, template, context=context)


# clem 30/03/2017
def __guest_handler(request):
	from breeze.models import UserProfile
	new_guest = UserProfile.new_guest()
	if new_guest:
		return process_login(request, new_guest)
	return HttpResponse(status=503)


def index(request):
	if not request.user.is_authenticated():
		error = request.GET.get('error', '')
		if error:
			error_description = request.GET.get('error_description', '')
			
			if error and error_description:
				# commit an error message
				logger.info('AUTH FAILED %s, %s' % (error, error_description))
				messages.add_message(request, messages.ERROR, '%s : %s' % (error, error_description))
				return redirect(reverse(this_function_name()))
			
			return show_login_page(request)
		
		return __guest_handler(request)
	else:
		return redirect(settings.AUTH0_SUCCESS_URL)


# TODO : use / extend auth0.auth_helpers instead
def process_login(request, user=None):
	""" Default handler to login user
	
	:param request: HttpRequest
	:param user: User
	"""
	def stage_two(user_bis):
		user_details = (user_bis.username, user_bis.email)
		# check for proper AUTH, and user is active
		if user_bis and user_bis.is_active:
			auth.login(request, user)
			logger.info('AUTH success for %s (%s)' % user_details)
			return index(request)
		request.session['profile'] = None
		logger.warning('AUTH denied for %s (%s)' % user_details)
		return HttpResponse(status=403)
	
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
			url = 'https://%s/userinfo?access_token=%s' # FIXME static url
			user_url = url % (settings.AUTH0_DOMAIN, token_info['access_token'])
			user_info = requests.get(user_url).json()
			
			user = auth.authenticate(**user_info)
			assert isinstance(user, User)
			# We're saving all user information into the session
			request.session['profile'] = user_info
			
			return stage_two(user)
		# error from AUTH0
		print(token_info)
		if token_info['error'] == 'access_denied':
			logger.warning('AUTH failure [%s]' % str(token_info))
			return HttpResponse(status=503)
	# eventual other methods
	else:
		# guest login
		if user: # TODO make a guest user auth backend
			# AUTH0 pass trough
			user.backend = settings.AUTH0_BACKEND_PY_PATH
			return stage_two(user)
		# unsupported method
		logger.warning('AUTH invalid GET[%s] POST[%s] content: %s' % (request.GET.__dict__,
	request.POST.__dict__, str(request.body)))
		print ('unsupported auth type :\n', request.GET.__dict__, request.POST.__dict__)
	
	return index(request)


def trigger_logout(request):
	""" Default handler to login user
	
	
	:param request: HttpRequest
	"""
	if request.user.is_authenticated():
		from breeze.models import OrderedUser
		user = OrderedUser.get(request)
		auth.logout(request)
		logger.info('LOGOUT %s (%s)' % (user.username, user.email))
		url = settings.AUTH0_LOGOUT_URL
		
		try:
			url = user.userprofile.institute_info.url or settings.AUTH0_LOGOUT_REDIRECT
		except Exception as e:
			logger.exception(str(e))
		
		# __scratch_guest_user(user)
		user.guest_auto_remove()
		return redirect('%s?returnTo=%s' % (settings.AUTH0_LOGOUT_URL, url))
		# return redirect('https://www.fimm.fi')
	else:
		return HttpResponse(status=503)
