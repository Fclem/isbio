from . import settings
from utilz import *
from django.http import HttpResponse
from django.core.handlers.wsgi import WSGIRequest
from django.core.exceptions import SuspiciousOperation
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
import time
import json

CT_JSON = 'application/json'
CT_TEXT = 'text/plain'
empty_dict = dict()

HTTP_SUCCESS = 200
HTTP_FAILED = 400
HTTP_NOT_FOUND = 404
HTTP_NOT_IMPLEMENTED = 501
CUSTOM_MSG = {
	HTTP_SUCCESS: 'ok',
	HTTP_FAILED: 'error',
	HTTP_NOT_FOUND: 'NOT FOUND',
	HTTP_NOT_IMPLEMENTED: 'NOT IMPLEMENTED YET',
}


# clem 18/10/2016
def get_response(result=True, data=empty_dict, version=settings.API_VERSION):
	"""
	
	:param result: optional bool to return HTTP200 or HTTP400
	:type result: bool | None
	:param data: optional dict, containing json-serializable data
	:type data: dict | None
	:param version: optionally specify the version number to return or default
	:type version: str | None
	:rtype: HttpResponse
	"""
	return get_response_opt(data, make_http_code(result), version, make_message(result))
	

# clem 17/10/2016
def get_response_opt(data=empty_dict, http_code=HTTP_SUCCESS, version=settings.API_VERSION, message=''):
	"""
	
	:param data: optional dict, containing json-serializable data
	:type data: dict | None
	:param http_code: optional HTTP code to return (default is 200)
	:type http_code: int | None
	:param version: optionally specify the version number to return or default
	:type version: str | None
	:param message: if no message is provided, one will be generated from the HTTP code
	:type message: str | None
	:rtype: HttpResponse
	"""
	assert isinstance(data, dict)
	if not message:
		make_message(http_code=http_code)
	result = { 'api':
		{'version': version, },
		'result'       : http_code,
		'message'      : message,
		'time'         : time.time()
	}
	result.update(data)
	
	return HttpResponse(json.dumps(result), content_type=CT_JSON, status=http_code)


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
	raise SuspiciousOperation('Invalid request or handling error at %s (payload : %s)' % (request.path,
	len(request.body)))


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
	for key, equal_value in filter_dict.iteritems():
		tail = None
		if '.' in key :
			# if the key is a dotted path
			split = key.split('.')
			# get the first key and rest of path
			key, tail = split[0], '.'.join(split[1:])
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
				if not match_filter(payload_value, {tail: equal_value }, key):
					# if the sub-payload doesn't match
					return False # this cannot be a prime failure source
		elif key in payload.keys() or payload_value != equal_value:
			# the key was not in the payload or the value was different, thus the match fails
			logger.warning('values of %s mismatched (%s!=%s) !' % (org_key or key, payload_value, equal_value))
			return False
	return True

##############
# COMMON VIEWS
##############


# clem 17/10/2016
def root(_):
	return get_response()


# clem 17/10/2016
def handler404(_):
	return get_response_opt(http_code=HTTP_NOT_FOUND)
