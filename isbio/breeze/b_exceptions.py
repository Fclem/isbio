from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
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


class FileNotFound(ObjectNotFound):
	pass


class ConfigFileNotFound(FileNotFound):
	pass


class ObjectHasNoReadOnlySupport(RuntimeError):
	pass
