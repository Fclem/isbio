from .common import *
from webhooks import hooker


# clem 18/10/2016
def _get_abstract(request):
	""" Abstraction with exception management for the two functions bellow
	
	:type request: hooker.HookWSGIReq
	:return: (json, request) | (None, request)
	:rtype: (dict , hooker.HookWSGIReq)
	"""
	assert issubclass(request.__class__, hooker.HookWSGIReq)
	try:
		return request.get_json(), request
	except Exception as e:
		logger.exception(str(e))
	return None, request


# clem 17/10/2016
def get_git_hub_json(request_init):
	""" Get the json object from a GitHub webhook, or None if something is wrong (invalid signature, bad request, etc)
	
	The request should be using POST method, application/json CONTENT_TYPE\n
	the header signature must match the request.body HMAC he PSK loaded from configs/.[name_of_the_calling_func]_secret
	
	:type request_init: WSGIRequest
	:return: (json, request) | (None, request)
	:rtype: (dict , hooker.GitHubWSGIReq)
	"""
	return _get_abstract(hooker.GitHubWSGIReq(request_init, 2, settings.GIT_HUB_IP_NETWORK))


# clem 17/10/2016
def get_json(request_init):
	""" Get the json object from a webhook, or None if something is wrong

	The request should be using POST method, and application/json CONTENT_TYPE \n
	if the request has a signature it must match the request.body HMAC against the PSK loaded from
	configs/.[name_of_the_calling_func]_secret
	
	:type request_init: WSGIRequest
	:return: (json, request) | (None, request)
	"""
	return _get_abstract(hooker.HookWSGIReq(request_init, 2))


# clem 18/10/2016
def do_self_git_pull():
	""" Pulls the code from GIT_REMOTE_NAME GIT_PULL_FROM, if code is updated, django should trigger a restart
	
	Hides and log exceptions
	
	:return: is success
	:rtype: bool
	"""
	try:
		import subprocess
		command = 'sleep 1 && ' + settings.API_PULL_COMMAND
		subprocess.Popen(command, shell=True)
		print (TermColoring.ok_green('$ ') + TermColoring.ok_blue(command))
		return True
	except Exception as e:
		logger.exception(str(e))
	return False


# clem 18/10/2016 # TODO implement
def do_r_source_git_pull():
	""" Pulls the code from R repository for pipeline

	TODO
	Hides and log exceptions

	:return: is success
	:rtype: bool
	"""
	try:
		# logger.warning('NOT_IMPLEMENTED')
		# print (TermColoring.warning('NOT_IMPLEMENTED : R PULL'))
		command = 'FOLDER=`pwd` && cd /projects/breeze/code/ && %s && cd $FOLDER' % settings.GIT_COMMAND
		print(TermColoring.ok_green('$ ') + TermColoring.ok_blue(command))
		return not os.system(command) # FIXME
		# return True
	except Exception as e:
		logger.exception(str(e))
	return False

