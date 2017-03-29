# -*- coding: latin-1 -*-
from breeze.watcher import runner
import logging
import os
import datetime
import sys
from breeze.models import UserProfile
from breeze import views
from breeze.utils import TermColoring, context
from django.conf import settings

if settings.DEBUG:
	# quick fix to solve PyCharm Django console environment issue
	# from breeze.process import Process
	from threading import Thread
else:
	# from multiprocessing import Process
	from threading import Thread

logger = logging.getLogger(__name__)
check_file_dt = ''
check_file_state = ''


FILE_TO_CHECK = settings.SOURCE_ROOT + 'breeze'


# experimental site-disabling
# clem 14/09/2015
def modification_date(filename, formatted=False):
	t = os.path.getmtime(filename)
	return datetime.datetime.fromtimestamp(t) if formatted else t


def creation_date(filename, formatted=False):
	t = os.path.getctime(filename)
	return datetime.datetime.fromtimestamp(t) if formatted else t


def get_state():
	try:
		return open(FILE_TO_CHECK).read().lower().replace('\n', '').replace('\r', '').replace('\f', '').replace(' ', '')
	except IOError: # HACK
		return 'on'


def update_state():
	global check_file_dt, check_file_state
	check_file_dt = modification_date(FILE_TO_CHECK)
	check_file_state = get_state()


def is_on():
	global check_file_state
	if check_file_state == '':
		update_state()
	return check_file_state == 'up' or check_file_state == 'enabled' or check_file_state == 'on'


def reload_urlconf(urlconf=None):
	print TermColoring.warning('State changed') + ', ' + TermColoring.ok_blue('Reloading urls...')
	if urlconf is None:
		urlconf = settings.ROOT_URLCONF
	if urlconf in sys.modules:
		reload(sys.modules[urlconf])


def check_state():
	global check_file_dt, check_file_state
	if modification_date(FILE_TO_CHECK) != check_file_dt:
		new_state = get_state()
		old_state = check_file_state
		update_state()
		if new_state != old_state:
			reload_urlconf()
# END


class JobKeeper(object):
	# p = Process(target=runner)
	p = Thread(target=runner)
	log = None

	def __init__(self):
		self.log = logger.getChild('watcher_guard')
		try:
			JobKeeper.p.start()
		except IOError:
			self.log.error('IOError while trying to start watcher... trying again in 5 sec.')
			import time
			time.sleep(5)
			self.__init__()
		except Exception as e:
			self.log.fatal('UNABLE TO START WATCHER : %s' % e)

	def process_request(self, _):
		if not JobKeeper.p.is_alive():
			# JobKeeper.p.terminate()
			JobKeeper.p = Thread(target=runner)
			self.log.warning('watcher was down, restarting...')
			self.__init__()


class BreezeAwake:
	def __init__(self):
		update_state()

	@staticmethod
	def process_request(_):
		check_state()

if settings.ENABLE_DATADOG:
	from datadog import statsd


	class DataDog:
		def __init__(self):
			# Increment a counter.
			statsd.increment('python.breeze.reload')
			statsd.event('Breeze reload', '', 'info', hostname=settings.HOST_NAME)

		@staticmethod
		def process_request(_):
			statsd.increment('python.breeze.request')

		@staticmethod
		def process_view(request, view_func, *_):
			statsd.increment('python.breeze.page.views')
			statsd.increment('python.breeze.page.view.' + str(view_func.__name__))
			if request.user:
				statsd.increment('python.breeze.page.auth_views')

		@staticmethod
		def process_exception(_, e):
			statsd.event('Python Exception', str(e), 'warning', hostname=settings.HOST_NAME)
			statsd.increment('python.breeze.exception')


class CheckUserProfile(object):
	@staticmethod
	def process_exception(request, exception):
		if isinstance(exception, UserProfile.DoesNotExist):
			return views.home(request)
	
	# clem 21/02/2017
	@staticmethod
	def process_response(request, response):
		""" set encrypted session_id cookie for shiny to check authentication
		Warning : shiny_secret must be at least 32 char long.
		"""
		if hasattr(request, 'user') and request.user.is_authenticated() and request.session.session_key:
			from utilz import compute_enc_session_id
			value = compute_enc_session_id(request.session.session_key, settings.SHINY_SECRET)
			if request.COOKIES.get(settings.ENC_SESSION_ID_COOKIE_NAME, '') != value:
				response.set_cookie(settings.ENC_SESSION_ID_COOKIE_NAME, value)
		return response


# clem 28/03/2017
class ContextualRequest(object):
	@staticmethod
	def process_request(request):
		# from utilz import context
		context = {'request': request}
	

class RemoteFW(object):
	@staticmethod
	def process_request(request):
		print type(request), request


class Empty(object):
	pass
