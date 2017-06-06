"""
This module contains a set of utilities functions related to Breeze and Django
	and also some general utilities functions


This modules imports :
	drmaa (if available, set to None otherwise), job_stat_class as an alias to drmaa.JobState or
		a replacement class if drmaa is not available

	from django :
		_  settings

	from python :
		datetime.datetime

		hashlib

		json

		logging (from): getLogger(), getLoggerClass(), LoggerAdapter

		multipledispatch (from): dispatch (enables method overloading)

		os

		os.path (from): isfile, isdir, islink, exists, getsize, join, basename

		os (from): symlink, readlink, listdir, makedirs, access, R_OK, chmod

		socket

		subprocess as sp

		sys (from): stdout

		time

		time (from): time() sleep()

		threading (from): Thread, Lock

	as well as all Breeze specific and customs Exceptions :
		b_exceptions.*

It provides some custom objects :
	_ ObjectCache (an object caching management class)

	_ git (a module that has some git features)

	_ Path (an experimental, unfinished, class to deal with file path)

and also notable custom functions as :
	_ get_logger() (a global log interface for Breeze)

	_ advanced_pretty_print() (a.k.a pp() )

	_ gen_file_from_template() (generates or return a content from a template file and a dict)
"""
from django.conf import settings
from datetime import datetime
from django.utils import timezone
# from django.http import HttpRequest as DjangoHttpRequest
from django.core.handlers.wsgi import WSGIRequest
from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.backends.base import SessionBase
from breeze.b_exceptions import * # DO NOT DELETE : used in sub-modules
from utilz import * # import all the non Breeze / non Django related utilities
from decorators import *

# 01/04/2016 : Moved all non-Django related code to utilities package
# THIS MODULE SHOULD ONLY BE USED FOR DJANGO / BREEZE RELATED CODE, THAT EITHER USE THE DB, OR IMPORTS
# OTHER MODULES FROM BREEZE / DJANGO


# 25/06/2015 Clem
def console_print(text, date_f=None):
	print console_print_sub(text, date_f=date_f)


def console_print_sub(text, date_f=None):
	return "[%s] %s" % (date_t(date_f), text)


# 10/03/2015 Clem / ShinyProxy
def date_t(date_f=None, time_stamp=None):
	if date_f is None:
		date_f = settings.USUAL_DATE_FORMAT
	if not time_stamp:
		date = timezone.now()
	else:
		date = datetime.fromtimestamp(time_stamp)
	return str(date.strftime(date_f))


def safe_rm(path, ignore_errors=False):
	"""
	Delete a folder recursively
	Provide a smart shutil.rmtree wrapper with system folder protection
	Avoid mistake caused by malformed auto generated paths

	:param path: folder to delete
	:type path: str
	:type ignore_errors: bool
	:return:
	:rtype: bool
	"""
	from os import listdir
	from os.path import isdir
	from shutil import rmtree
	if path not in settings.FOLDERS_LST:
		if isdir(path):
			log_txt = 'rmtree %s had %s object(s)' % (path, len(listdir(path)))
			get_logger().debug(log_txt)
			rmtree(path, ignore_errors)
			return True
		else:
			log_txt = 'not a folder : %s' % path
			get_logger().warning(log_txt)
	else:
		log_txt = 'attempting to delete system folder : %s' % path
		get_logger().exception(log_txt)
	return False


# Clem 24/09/2015
def safe_copytree(source, destination, symlinks=True, ignore=None):
	"""
	Copy a folder recursively
	Provide a smart shutil.copytree wrapper with system folder protection
	Avoid mistake caused by malformed auto generated paths
	Avoid non existent source folder, and warn about existent destination folders

	:type source: str
	:type destination: str
	:type symlinks: bool
	:type ignore: callable
	:rtype: bool
	"""
	from os.path import isdir
	if destination not in settings.FOLDERS_LST:
		if isdir(source):
			if isdir(destination):
				log_txt = 'copytree, destination folder %s exists, proceed' % destination
				get_logger().warning(log_txt)
			custom_copytree(source, destination, symlinks, ignore)
			return True
		else:
			log_txt = 'copytree, source folder %s don\'t exists, STOP' % source
			get_logger().warning(log_txt)
	else:
		log_txt = 'attempting to copy to a system folder : %s, STOP' % destination
		get_logger().exception(log_txt)
	return False


# clem 09/10/2015
def saved_fs_state():
	""" Read the saved file system FS_LIST_FILE descriptor and chksums list and return the contained JSON object
	"""
	import json
	with open(settings.FS_LIST_FILE) as f:
		return json.load(f)


# clem 09/10/2015
def fix_file_acl_interface(fid):
	""" Resolves the file designed by <i>fid</i> (for safety) and fix it's access permissions

	:type fid: int
	:rtype: bool
	"""
	saved_state = saved_fs_state()

	if type(fid) != int:
		fid = int(fid)

	for each in saved_state:
		ss = saved_state[each]
		for file_n in ss:
			if ss[file_n][2] == fid:
				path = join(each, file_n)
				return set_file_acl(path)

	return False


def norm_proj_p(path, repl=''):
	"""
	:type path: str
	:type repl: str
	:rtype: str
	"""
	return path.replace(settings.PROJECT_FOLDER_PREFIX, repl)


# TODO : test and integrate
def get_r_package(name=''):
	# TEST function for R lib retrieval
	from utilz.cran_old import CranArchiveDownloader
	if name:
		cran = CranArchiveDownloader(name)
		if cran.find() and cran.download():
			return cran.extract_to()
	return False


# clem 20/06/2016
def git_branch():
	return git.get_branch_from_fs(settings.SOURCE_ROOT)


class ContentType(object):
	HTML = 'text/html'
	DEFAULT = HTML
	# TEXT_PLAIN = 'text/plaintext'
	TEXT_PLAIN = 'text/plain'
	PLAIN = TEXT_PLAIN
	JSON = 'application/json'
	ZIP = 'application/zip'
	FORCE_DL = 'application/force-download'
	OCTET_STREAM = 'application/octet-stream'

c_t = ContentType


# clem 22/12/2012 add a verbose level
def verbose_base(self):
	def embd(msg, *args, **kwargs):
		if settings.VERBOSE:
			self.debug(msg, *args, **kwargs)
	return embd


# clem 22/12/2012 override get_logger to add a verbose level
def get_logger(name=None, level=0):
	import utilz
	log_obj = utilz.get_logger(name, level + 1)
	log_obj.verbose = verbose_base(log_obj)
	return log_obj


# clem 22/12/2012 override Logger class to add a verbose level
class MyLogger(Logger):
	def __init__(self, name, level=0):
		super(MyLogger, self).__init__(name, level + 1)
		self.verbose = verbose_base(self)

import logging
logging.setLoggerClass(MyLogger)

# get_logger = get_logger_bis

from importlib import import_module
from django.conf import settings
from django.contrib.auth import SESSION_KEY, BACKEND_SESSION_KEY, load_backend # , get_user


def check_session(session_id):
	engine = import_module(settings.SESSION_ENGINE)
	session = engine.SessionStore(session_id)
	
	try:
		user_id = session[SESSION_KEY]
		backend_path = session[BACKEND_SESSION_KEY]
		backend = load_backend(backend_path)
		user = backend.get_user(user_id) or AnonymousUser()
	except KeyError:
		user = AnonymousUser()
	
	return user.is_authenticated()


# clem 23/05/2017
class HttpRequest(WSGIRequest):
	""" Fake class to use as a prototype for better IDE code evaluation """
	user = AnonymousUser()
	session = SessionBase()


# clem 24/05/2017
class PyPackageLister(object):
	@classmethod
	def get_packages_list(cls, with_summary=True, with_version=True):
		result = dict()
		with open('%srequirements.txt' % settings.SOURCE_ROOT) as requirements_list:
			for each in requirements_list.readlines():
				each = SupStr(each.strip()) - '\n'
				if each[0] != '#':
					module_name = each.split('>=')[0]
					# result.append(PyPackage(module_name).dump(with_summary, with_version))
					package = PyPackage(module_name)
					result.update({package.name: package.dump(with_summary, with_version)})
		return result.values()
		
		
# clem 31/05/2017
class PyPackage(object):
	BASE_URL = 'https://pypi.python.org/pypi/%s'
	JSON_URL = 'https://pypi.python.org/pypi/%s/json'
	import sys
	import importlib
	
	name = ''
	
	def __init__(self, module_name):
		self.name = module_name
	
	@property
	def query_url(self):
		return self.JSON_URL % self.name

	@property
	def page_url(self):
		return self.BASE_URL % self.name
	
	@property
	def summary(self):
		result = json.load(get_http_response(self.query_url))
		return result['info']['summary'] if 'info' in result and 'summary' in result['info'] else ''
	
	@property
	def version(self):
		try:
			a_module = self.sys.modules.get(self.name, None) or self.importlib.import_module(self.name)
			if hasattr(a_module, '__version__'):
				return a_module.__version__
		except ImportError:
			pass
		return ''
	
	def dump(self, with_version=True, with_summary=True):
		return {
			'name':      self.name,
			'version':   self.version if with_version else '',
			'url':       self.page_url,
			'query_url': self.query_url,
			'summary':   self.summary.strip() if with_summary else ''
		}


# clem 06/06/2017
def list_context_functions():
	from breeze import context
	return list_functions_from_module(context)


# clem 06/06/2017
def autogen_context_dict(request, flat=False):
	def filter_functions():
		a_list = list_context_functions()
		b_list = list()
		for each in a_list:
			if not each.__name__.startswith('__') and each.__module__ == 'breeze.context':
				b_list.append(each)
		return b_list
	
	a_dict = dict()
	for each in filter_functions():
		data = each.__call__(request) if each.func_code.co_argcount else each.__call__()
		a_dict.update({each.__name__: data}) if not flat else a_dict.update(data)
	
	return a_dict
