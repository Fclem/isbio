from django.core.exceptions import PermissionDenied as PermissionDenied_org, ObjectDoesNotExist
from utilz import logger, this_function_caller_name
__author__ = 'clem'
__date__ = '25/05/2015'
#
# System checks
#


class SystemCheckFailed(RuntimeWarning):
	pass


class UrlFileHasMalformedPatterns(SystemCheckFailed):
	pass


class FileSystemNotMounted(SystemCheckFailed):
	pass


class MysqlDbUnreachable(BaseException):
	pass


class FileServerUnreachable(BaseException):
	pass


class NetworkUnreachable(SystemCheckFailed):
	pass


class InternetUnreachable(SystemCheckFailed):
	pass


class RORAUnreachable(SystemCheckFailed):
	pass


class RORAFailure(SystemCheckFailed):
	pass


class SGEImproperlyConfigured(SystemCheckFailed):
	pass


class DOTMUnreachable(SystemCheckFailed):
	pass


class ShinyUnreachable(SystemCheckFailed):
	pass


class NoSshTunnel(SystemCheckFailed):
	pass


class TargetNotResponding(SystemCheckFailed):
	pass


class DockerNotResponding(TargetNotResponding):
	pass


class ShinyNotResponding(TargetNotResponding):
	pass


class WatcherIsNotRunning(SystemCheckFailed):
	pass


class SGEUnreachable(SystemCheckFailed):
	pass


class CASUnreachable(SystemCheckFailed):
	pass


class GlobalSystemChecksFailed(SystemError):
	pass
#
# END
#


class SGEError(RuntimeWarning):
	pass


class NoSuchJob(RuntimeWarning):
	pass


class InvalidArgument(BaseException):
	pass


class InvalidArguments(BaseException):
	pass


class ReadOnlyAttribute(RuntimeWarning):
	pass


class NotDefined(BaseException):
	pass


class ObjectNotFound(BaseException):
	pass


class FileNotFound(ObjectNotFound, IOError):
	pass


class ConfigFileNotFound(FileNotFound):
	pass


class ObjectHasNoReadOnlySupport(RuntimeError):
	pass


class PermissionDenied(PermissionDenied_org):
	def __init__(self, *args, **kwargs):
		
		# print 'kwargs.keys() : %s' % kwargs.keys()
		# print kwargs.get('user')
		
		def is_user_obj(obj):
			from django.contrib.auth.models import User
			print 'is_user_obj ? %s or (%s and %s) %s' % (isinstance(obj, User), hasattr(obj, '__class__'), issubclass(obj.__class__, User))
			return isinstance(obj, User) or (hasattr(obj, '__class__') and issubclass(obj.__class__, User))
		
		def is_request_obj(obj):
			from django.core.handlers.wsgi import WSGIRequest
			return isinstance(obj, WSGIRequest) or (hasattr(obj, '__class__') and issubclass(obj.__class__, WSGIRequest))
		
		def _extract_user_obj():
			if 'user' in kwargs.keys():
				result = kwargs.get('user', None)
				# return result if is_user_obj(result) else None
				return result
			elif len(args) >= 1:
				for each in args:
					if each and is_user_obj(each):
						return each
			return None
		
		def _extract_request_obj():
			if 'request' in kwargs.keys():
				result = kwargs.get('request', None)
				return result if is_request_obj(result) else None
			elif len(args) >= 1:
				for each in args:
					if each and is_request_obj(each):
						return each
			return None
		
		def get_message():
			if 'message' in kwargs.keys():
				result = kwargs.get('message', None)
				return result if isinstance(result, basestring) else ''
			elif len(args) >= 1:
				for each in args:
					if each and isinstance(each, basestring):
						return each
			return ''
		
		def get_user():
			rq = _extract_request_obj()
			print 'rq : %s' % rq
			return _extract_user_obj() or rq.user if rq else None
		
		def get_username():
			user = get_user()
			return user.username if user else ''
		
		# clem 11/05/2017
		def get_function_name():
			if 'func_name' in kwargs.keys():
				result = kwargs.get('func_name', None)
				return result if result else this_function_caller_name(1)
		
		super(PermissionDenied, self).__init__()
		user_name = get_user() # FIXME broken # get_username()
		message = get_message()
		function_name = get_function_name()
		final_text = 'Access denied to %s for %s' % (user_name or '?', function_name or '?')
		if message:
			if final_text:
				message = ' (%s)' % message
			final_text += message
		logger.warning(final_text)


# clem 30/03/2017
class DisabledByCurrentSettings(PermissionDenied):
	pass
