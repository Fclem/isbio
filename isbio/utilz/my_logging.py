# noinspection PyUnresolvedReferences
from logging import getLogger, getLoggerClass, LoggerAdapter, Logger
from time import time
from . import this_function_caller_name
# noinspection PyUnresolvedReferences
import logging

__version__ = '0.1.1'
__author__ = 'clem'
__date__ = '27/05/2016'

logger = getLogger(__name__)


def get_logger(name=None, level=0):
	""" Return a named logger object
	
	:type name: str
	:type level: int
	:return: a named Logger object
	:rtype: Logger
	"""
	if name is None:
		name = this_function_caller_name(level)
	log_obj = logger.getChild(name)
	return log_obj


# clem 29/09/2015
# from [fr] http://saladtomatonion.com/blog/2014/12/16/mesurer-le-temps-dexecution-de-code-en-python/
class Timer(object):
	def __init__(self):
		self.interval = None
		self.start_time = None

	def __enter__(self):
		self.start()
		# __enter__ must return an instance bound with the "as" keyword
		return self

	# There are other arguments to __exit__ but we don't care here
	def __exit__(self, *_):
		self.function_timer()

	def start(self):
		if hasattr(self, 'interval'):
			del self.interval
		self.start_time = time()

	def function_timer(self):
		if hasattr(self, 'start_time'):
			self.interval = time() - self.start_time
			del self.start_time # Force timer reinit


# clem 29/09/2015
# from [fr] http://saladtomatonion.com/blog/2014/12/16/mesurer-le-temps-dexecution-de-code-en-python/
# use as decorator like so : @LoggerTimer('prefix message', logger.debug)
class LoggerTimer(Timer):
	@staticmethod
	def default_logger(msg):
		print(msg)

	def __init__(self, prefix=None, func=None):
		super(LoggerTimer, self).__init__() # not sure about that, TODO check
		# Use func if not None else the default one
		self.f = func or LoggerTimer.default_logger
		# Format the prefix if not None or empty, else use empty string
		self.prefix = prefix or '' # getmembers(func, '__name__')

	def function_timer(self):
		# Call the parent method
		super(LoggerTimer, self).function_timer()
		# Call the logging function with the message
		self.f('{0}{1}{2}'.format(self.prefix, self.interval, ' sec'))

	def __call__(self, func):
		# Use self as context manager in a decorated function
		def decorated_func(*args, **kwargs):
			self.prefix = '{0} : '.format(self.prefix or func.__name__ if func else '')
			with self:
				return func(*args, **kwargs)

		return decorated_func


# clem 29/09/2015 writing shortcut
def logger_timer(func):
	a = LoggerTimer(func=get_logger('timing').debug)
	return a(func)
