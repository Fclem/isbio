from __future__ import print_function
import time
import os
import sys
import abc

__version__ = '0.5'
__author__ = 'clem'
__date__ = '29/08/2017'


__path__ = os.path.realpath(__file__)
__dir_path__ = os.path.dirname(__path__)
__file_name__ = os.path.basename(__file__)

# general config
ENV_OUT_FILE = ('OUT_FILE', 'out.tar.xz')
ENV_IN_FILE = ('IN_FILE', 'in.tar.xz')
ENV_DOCK_HOME = ('DOCK_HOME', '/breeze')
ENV_HOME = ('HOME', '/root')
ENV_JOB_ID = ('JOB_ID', '')
ENV_HOSTNAME = ('HOSTNAME', '')
CONTAINERS_NAME = ['breeze-queue', 'breeze-results', 'docker-config']
JOBS_CONTAINER = CONTAINERS_NAME[0] # container where jobs to be run are stored
DATA_CONTAINER = CONTAINERS_NAME[1] # container where jobs' results data are stored
MNGT_CONTAINER = CONTAINERS_NAME[2] # container where some configuration and code is stored

# command line CONSTs
OUT_FILE = os.environ.get(*ENV_OUT_FILE)
IN_FILE = os.environ.get(*ENV_IN_FILE)
DOCK_HOME = os.environ.get(*ENV_DOCK_HOME)
HOME = os.environ.get(*ENV_HOME)
ACTION_LIST = ('load', 'save', 'upload', 'upgrade') # DO NOT change item order
ACT_CONT_MAPPING = {
	ACTION_LIST[0]: JOBS_CONTAINER,
	ACTION_LIST[1]: DATA_CONTAINER,
	ACTION_LIST[2]: MNGT_CONTAINER,
	ACTION_LIST[3]: MNGT_CONTAINER,
}
# clem 05/09/2017
PYTHON_VERSION = sys.version_info.major
IS_PYTHON2 = PYTHON_VERSION == 2
IS_PYTHON3 = PYTHON_VERSION == 3
FROM_COMMAND_LINE = __name__ == '__main__' # restrict access


if IS_PYTHON2:
	basestring_t = basestring
	
	# clem 05/09/2017
	class FileExistsError(OSError):
		pass
	
	
	class TimeoutError(OSError):
		pass


	class FileNotFoundError(OSError):
		pass
elif IS_PYTHON3:
	basestring_t = str


# clem 08/04/2016 (from utilities)
def function_name(delta=0):
	return sys._getframe(1 + delta).f_code.co_name


# clem on 21/08/2015 (from utilities)
def get_md5(content):
	""" compute the md5 checksum of the content argument

	:param content: the content to be hashed
	:type content: list or str
	:return: md5 checksum of the provided content
	:rtype: str
	"""
	import hashlib
	m = hashlib.md5()
	if type(content) == list:
		for eachLine in content:
			m.update(eachLine)
	else:
		m.update(content)
	return m.hexdigest()


# clem on 21/08/2015 (from utilities)
def get_file_md5(file_path):
	""" compute the md5 checksum of a file

	:param file_path: path of the local file to hash
	:type file_path: str
	:return: md5 checksum of file
	:rtype: str
	"""
	try:
		fd = open(file_path, "rb")
		content = fd.readlines()
		fd.close()
		return get_md5(content)
	except IOError:
		return ''


# from utilities
class Bcolors(object):
	HEADER = '\033[95m'
	OKBLUE = '\033[94m'
	OKGREEN = '\033[92m'
	WARNING = '\033[33m'
	FAIL = '\033[91m'
	ENDC = '\033[0m'
	BOLD = '\033[1m'
	UNDERLINE = '\033[4m'

	@staticmethod
	def ok_blue(text):
		return Bcolors.OKBLUE + text + Bcolors.ENDC

	@staticmethod
	def ok_green(text):
		return Bcolors.OKGREEN + text + Bcolors.ENDC

	@staticmethod
	def fail(text):
		return Bcolors.FAIL + text + Bcolors.ENDC + ' (%s)' % __name__

	@staticmethod
	def warning(text):
		return Bcolors.WARNING + text + Bcolors.ENDC

	@staticmethod
	def header(text):
		return Bcolors.HEADER + text + Bcolors.ENDC

	@staticmethod
	def bold(text):
		return Bcolors.BOLD + text + Bcolors.ENDC

	@staticmethod
	def underlined(text):
		return Bcolors.UNDERLINE + text + Bcolors.ENDC


# clem 14/04/2016
class StorageModuleAbstract(object):
	__metaclass__ = abc.ABCMeta
	_not = "Class %s doesn't implement %s()"
	missing_res_exception = None

	# clem 20/04/2016
	def _print_call(self, fun_name, args):
		arg_list = ''
		if isinstance(args, basestring_t):
			args = [args]
		for each in args:
			arg_list += "'%s', " % Bcolors.warning(each)
		print(Bcolors.bold(fun_name) + "(%s)" % arg_list[:-2])
	
	# clem 29/04/2016
	def _update_self_do(self, blob_name, file_name, container=None):
		if not container:
			container = MNGT_CONTAINER
		# try:
		blob_name = blob_name.replace('.pyc', '.py')
		file_name = file_name.replace('.pyc', '.py')
		return self.download(blob_name, file_name, container)
	
	# clem 20/04/2016
	def update_self(self, container=None):
		""" Download a possibly updated version of this script from *
		Will only work from command line for the implementation.
		You must override this method, use _update_self_sub, and call it using super, like so :
		return super(__class_name__, self).update_self() and self._update_self_sub(__file_name__, __file__, container)

		:param container: target container (default to MNGT_CONTAINER)
		:type container: str|None
		:return: success ?
		:rtype: bool
		:raise: AssertionError
		"""
		assert FROM_COMMAND_LINE
		return self._update_self_do(__file_name__, __file__, container)
		
	# clem 29/04/2016
	def _upload_self_do(self, blob_name, file_name, container=None):
		if not container:
			container = MNGT_CONTAINER
		blob_name = blob_name.replace('.pyc', '.py')
		file_name = file_name.replace('.pyc', '.py')
		self.erase(blob_name, container, no_fail=True)
		return self.upload(blob_name, file_name, container)
	
	###
	#   docker_interface access methods
	###
	
	# clem 20/04/2016 @override
	def upload_self(self, container=None):
		""" Upload this script to target storage system, provides auto-updating feature for the other end

		:param container: target container (default to MNGT_CONTAINER)
		:type container: str|None
		:return: Info on the created blob as a Blob object
		:rtype: Blob
		"""
		self._upload_self_do(__file_name__, __file__, container)

	# clem 28/04/201
	@abc.abstractmethod
	def upload(self, target_path, file_path, container=None, verbose=True):
		""" Upload wrapper for * storage :\n
		upload a local file to the default container or a specified one on * storage
		if the container does not exists, it will be created using *

		:param target_path: Name/path of the object as to be stored in * storage
		:type target_path: str
		:param file_path: Path of the local file to upload
		:type file_path: str
		:param container: Name of the container to use to store the blob (default to self.container)
		:type container: str or None
		:param verbose: Print actions (default to True)
		:type verbose: bool or None
		:return: object corresponding to the created blob
		:rtype: Blob
		:raise: IOError or FileNotFoundError
		"""
		raise NotImplementedError(self._not % (self.__class__.__name__, function_name()))

	# clem 28/04/201
	@abc.abstractmethod
	def download(self, target_path, file_path, container=None, verbose=True):
		""" Download wrapper for * storage :\n
		download a blob from the default container (or a specified one) from * storage and save it as a local file
		if the container does not exists, the operation will fail

		:param target_path: Name/path of the object to retrieve from * storage
		:type target_path: str
		:param file_path: Path of the local file to save the downloaded blob
		:type file_path: str
		:param container: Name of the container to use to store the blob (default to self.container)
		:type container: str or None
		:param verbose: Print actions (default to True)
		:type verbose: bool or None
		:return: success?
		:rtype: bool
		:raise: self.missing_res_error
		"""
		raise NotImplementedError(self._not % (self.__class__.__name__, function_name()))

	# clem 28/04/201
	@abc.abstractmethod
	def erase(self, target_path, container=None, verbose=True, no_fail=False):
		""" Delete the specified blob in self.container or in the specified container if said blob exists

		:param target_path: Name/path of the object to delete from * storage
		:type target_path: str
		:param container: Name of the container where the blob is stored (default to self.container)
		:type container: str or None
		:param verbose: Print actions (default to True)
		:type verbose: bool or None
		:param no_fail: suppress error messages (default to False)
		:type no_fail: bool or None
		:return: success?
		:rtype: bool
		:raise: self.missing_res_error
		"""
		raise NotImplementedError(self._not % (self.__class__.__name__, function_name()))


def jobs_container():
	return JOBS_CONTAINER


def data_container():
	return DATA_CONTAINER


def management_container():
	return MNGT_CONTAINER


# clem on 28/04/2016
def input_pre_handling():
	assert len(sys.argv) >= 2

	aa = str(sys.argv[1])
	bb = '' if len(sys.argv) <= 2 else str(sys.argv[2])
	cc = '' if len(sys.argv) <= 3 else str(sys.argv[3])

	assert isinstance(aa, basestring_t) and aa in ACTION_LIST
	return aa, bb, cc


# clem on 28/04/2016
def command_line_interface(storage_implementation_instance, action, obj_id='', file_n=''):
	"""	Command line interface of the module, it's the interface the docker container will use.
	original base code by clem 14/04/2016

	:type storage_implementation_instance: StorageModule
	:type action: basestring_t
	:type obj_id: basestring_t
	:type file_n: basestring_t
	:return: exit code
	:rtype: int
	"""
	assert isinstance(storage_implementation_instance, StorageModuleAbstract)
	__DEV__ = False
	try:
		storage = storage_implementation_instance
		if action == ACTION_LIST[0]: # download the job archive from * storage
			if not obj_id:
				obj_id = os.environ.get(*ENV_JOB_ID)
			path = HOME + '/' + IN_FILE
			if not storage.download(obj_id, path):
				exit(1)
			else: # if the download was successful we delete the job file
				storage.erase(obj_id)
		elif action == ACTION_LIST[1]: # uploads the job resulting data's archive to * storage
			path = HOME + '/' + OUT_FILE
			if not obj_id: # the job id must be in env(ENV_JOB_ID[0]) if not we use either the hostname or the md5
				obj_id = os.environ.get(ENV_JOB_ID[0], os.environ.get(ENV_HOSTNAME[0], get_file_md5(path)))
			storage.upload(obj_id, path)
		elif action == ACTION_LIST[2]: # uploads an arbitrary file to * storage
			assert file_n and len(file_n) > 3
			assert obj_id and len(obj_id) > 4
			path = HOME + '/' + file_n
			storage.upload(obj_id, path)
		elif action == ACTION_LIST[3]: # self update
			old_md5 = get_file_md5(__file__)
			if storage.update_self():
				new_md5 = get_file_md5(__file__)
				if new_md5 != old_md5:
					print(Bcolors.ok_green('successfully'), 'updated from %s to %s' % (Bcolors.bold(old_md5),
					Bcolors.bold(new_md5)))
				else:
					print(Bcolors.ok_green('not updated') + ',', Bcolors.ok_blue('this is already the latest version.'))
			else:
				print(Bcolors.fail('Upgrade failure'))
				exit(1)
	except Exception as e:
		print(Bcolors.fail('FAILURE :'))
		code = 1
		if hasattr(e, 'msg') and e.msg:
			print(e.msg)
		elif hasattr(e, 'message') and e.message:
			print(e.message)
		else:
			raise
		if hasattr(e, 'status_code'):
			code = e.status_code
		elif hasattr(e, 'code'):
			code = e.code
		exit(code)


# TODO : in your concrete class, simply add those four line at the end
if __name__ == '__main__':
	a, b, c = input_pre_handling()
	# TODO : replace StorageModule with your implemented class
	# storage_inst = StorageModuleAbstract('account', 'key', ACT_CONT_MAPPING[a])
	storage_inst = StorageModuleAbstract()
	command_line_interface(storage_inst, a, b, c)


class BlockingTransfer(object): # TODO move elsewhere
	_completed = False
	_per100 = 0.
	_last_progress = 0.
	_started = False
	_start_time = 0
	_transfer_func = None
	_waiting = False
	_failed = False
	_verbose = False
	
	def __init__(self, transfer_func, verbose=True):
		"""

		:param transfer_func: The actual transfer function, that takes as first and only parameter the
			progress_func(current, total)
		:type transfer_func: callable
		"""
		assert callable(transfer_func)
		self._verbose = verbose
		self._transfer_func = transfer_func
	
	def do_blocking_transfer(self):
		if not self._started:
			try:
				self._start_time = time.time()
				self._transfer_func(self._progress_func)
				self._started = True
				self._wait()
				return True
			except Exception:
				self._failed = True
				self._waiting = False
				raise
		return False
	
	def _wait(self):
		if self._started and not self._waiting:
			self._waiting = True
			while not self.is_complete:
				time.sleep(0.005)
				if (time.time() - self._start_time) % 2 == 0:
					# check every two seconds if some progress was made
					if self._per100 == self._last_progress:
						print('TimeoutError')
						raise TimeoutError
	
	def _progress_func(self, current, total):
		self._last_progress = self._per100
		self._per100 = (current // total) * 100
		if self._verbose:
			print('transfer: %.2f%%   \r' % self._per100, end='')
		if current == total:
			self._completed = True
			if self._verbose:
				print('transfer complete')
	
	@property
	def is_complete(self):
		return self._completed and not self._failed
	
	@property
	def progress(self):
		return self._per100
