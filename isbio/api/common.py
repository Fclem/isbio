from . import settings
from utilz import *
from breeze.decorators import allow_guest, login_required
from django.http import HttpResponse, HttpRequest # , HttpResponseNotModified , HttpResponseBadRequest
from django.core.exceptions import SuspiciousOperation
# from django.views.decorators.csrf import csrf_exempt # !!useful for sub-modules
import time
import json
from json import JSONEncoder

CT_JSON = 'application/json'
CT_TEXT = 'text/plain'
empty_dict = dict()

HTTP_SUCCESS = 200
HTTP_FAILED = 400
HTTP_NOT_FOUND = 404
HTTP_NOT_IMPLEMENTED = 501
HTTP_FORBIDDEN = 403
HTTP_MOVE_PERM = 302
HTTP_MOVED_TEMP = 301
CUSTOM_MSG = {
	HTTP_SUCCESS: 'ok',
	HTTP_FAILED: 'error',
	HTTP_NOT_FOUND: 'NOT FOUND',
	HTTP_NOT_IMPLEMENTED: 'NOT IMPLEMENTED YET',
	HTTP_FORBIDDEN: 'ACCESS DENIED',
	HTTP_MOVE_PERM: 'MOVED PERMANENTLY',
	HTTP_MOVED_TEMP: 'MOVED TEMPORARILY'
}


def _default(_, obj):
	return getattr(obj.__class__, "to_json", _default.default)(obj)


_default.default = JSONEncoder().default  # Save unmodified default.
JSONEncoder.default = _default # replacement


# clem 24/03/2017
def json_convert(an_object):
	""" JSON conversion with error management
	
	:type an_object: object
	:rtype: str
	"""
	
	return json.dumps(an_object)


# clem 18/10/2016
def get_response(result=True, data=empty_dict, version=settings.API_VERSION, raw=False, request=None):
	"""
	
	:param result: optional bool to return HTTP200 or HTTP400
	:type result: bool | None
	:param data: optional dict, containing json-serializable data
	:type data: dict | None
	:param version: optionally specify the version number to return or default
	:type version: str | None
	:param raw: optionally specify if data should be dumped directly as an output
	:type raw: bool
	:type request: HttpRequest
	:rtype: HttpResponse
	"""
	return get_response_opt(data, make_http_code(result), version, make_message(result), request=request) if not raw else \
		get_response_raw(data, make_http_code(result))


# clem 17/10/2016
def get_response_opt(data=empty_dict, http_code=HTTP_SUCCESS, version=settings.API_VERSION, message='', request=None):
	"""
	
	:param data: optional dict, containing json-serializable data
	:type data: dict | None
	:param http_code: optional HTTP code to return (default is 200)
	:type http_code: int | None
	:param version: optionally specify the version number to return or default
	:type version: str | None
	:param message: if no message is provided, one will be generated from the HTTP code
	:type message: str | None
	:type request: HttpRequest
	:rtype: HttpResponse
	"""
	assert isinstance(data, dict)
	if not message:
		message = make_message(http_code=http_code)
	result = {
		'api':     {'version': version, },
		'result':  http_code,
		'message': message,
		'time':    time.time(),
		'data':    data
	}
	if request is not None:
		from breeze.models import UserProfile
		result.update({'auth': UserProfile.objects.get(pk=request.user.id)})
	result.update(data)
	
	return HttpResponse(json_convert(result), content_type=CT_JSON, status=http_code)


# clem 28/02/2016
def get_response_raw(data=empty_dict, http_code=HTTP_SUCCESS):
	"""

	:param data: optional dict, containing json-serializable data
	:type data: dict | None
	:param http_code: optional HTTP code to return (default is 200)
	:type http_code: int | None
	:rtype: HttpResponse
	"""
	assert isinstance(data, dict)
		
	return HttpResponse(json_convert(data), content_type=CT_JSON, status=http_code)


# clem 18/10/2016
def make_http_code(a_bool):
	return HTTP_SUCCESS if a_bool else HTTP_FAILED


# clem 18/10/2016
def make_message(a_bool=True, http_code=None):
	if not http_code:
		http_code = make_http_code(a_bool)
	return CUSTOM_MSG[http_code]


# clem 18/10/2016
def default_suspicious(request):
	import traceback
	exc_type, exc_value, exc_traceback = sys.exc_info()
	stack = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
	raise SuspiciousOperation('Invalid request or handling error at %s (payload : %s)\n%s' % (request.path,
	len(request.body), stack)) # FIXME len doesnt work !


# clem 18/10/2016 + 19/10/2016 # TODO description
def match_filter(payload, filter_dict, org_key=''):
	""" TODO
	
	:type payload: dict
	:type filter_dict:  dict
	:type org_key:  str
	:rtype: bool
	"""
	check_type = (type(payload), type(filter_dict))
	if check_type not in [(dict, dict)]:
		logger.error('cannot match with %s, %s' % check_type)
		return False
	for key, equal_value in filter_dict.items():
		tail = None
		if '.' in key:
			# if the key is a dotted path
			split = key.split('.')
			# get the first key and rest of path
			org_key, key, tail = key, split[0], '.'.join(split[1:])
		# value for this key, wether the key was a name or a path
		payload_value = payload.get(key, '')
		if tail:
			# the path was dotted and has at least one other component (i.e path was not "something.")
			if not (payload_value and type(payload_value) is dict):
				# there was no such key in payload, or the payload_value was not a dict
				# (i.e. there is no sub-path to go to for this key) thus the match fails
				logger.warning('incorrect key path, or key not found')
				return False
			else:
				# payload_value is a dict and tail as some more path component
				if not match_filter(payload_value, {tail: equal_value}, org_key):
					# if the sub-payload doesn't match
					return False # this cannot be a prime failure source
		else:
			if key not in payload.keys():
				# the key was not in the payload
				logger.warning('no key %s in payload' % org_key or key)
				return False
			if str(payload_value) != str(equal_value): # FIXME possible unicode issue
				# the values were different, thus the match fails
				logger.warning('key "%s" values mismatched "%s" != "%s"' % (org_key or key, payload_value, equal_value))
				return False
	return True


# clem 20/02/2017
def _is_authenticated(request):
	return request.user.is_authenticated() if request and hasattr(request, 'user') else False

##############
# COMMON VIEWS
##############


# clem 17/10/2016
def root(_=None):
	return get_response()


# clem 17/10/2016
def handler404(request):
	data = {'request': {'url': request.path, 'get': request.GET, 'post': request.POST}}
	return get_response_opt(data=data, http_code=HTTP_NOT_FOUND)


# clem 20/02/2017
def is_authenticated(request):
	auth = _is_authenticated(request)
	data = {'auth': auth}
	return get_response_opt(data=data, http_code=HTTP_SUCCESS if auth else HTTP_FORBIDDEN)


# clem 20/02/2017
@allow_guest
def has_auth(request):
	return who(request)


# clem 31/03/2017
@login_required
def no_guest(request):
	return who(request)


# clem 28/03/2017
def who(request):
	from breeze.models import UserProfile
	UserProfile.add_keys(('user.email', 'email'))
	data = {'auth': UserProfile.rq_getter(request)}
	return get_response(data={'data': data})


# clem 21/02/2017
def shiny_auth(request):
	from breeze.utils import check_session
	auth = False
	try:
		enc_session_id = request.GET.get(settings.settings.ENC_SESSION_ID_COOKIE_NAME, '')
		session_id = compute_dec_session_id(enc_session_id, settings.settings.SHINY_SECRET)
		auth = check_session(session_id)
	except Exception as e:
		logger.warning(str(e))
	data = {'auth': auth}
	return get_response_opt(data=data, http_code=HTTP_SUCCESS if auth else HTTP_FORBIDDEN)
