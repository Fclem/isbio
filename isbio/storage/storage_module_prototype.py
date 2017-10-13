from __future__ import print_function
from types import ModuleType
import time
import logging
import os
import sys
import abc

__version__ = '0.6.1'
__author__ = 'clem'
__date__ = '29/08/2017'

# ## Copy this part in your module ###
__path__ = os.path.realpath(__file__)
__dir_path__ = os.path.dirname(__path__)
__file_name__ = os.path.basename(__file__)
# ## /copy ###

PRINT_LOG = True
LOG_LEVEL = logging.DEBUG

log = logging.getLogger("storage_IF")
log.setLevel(LOG_LEVEL)
if PRINT_LOG:
	ch = logging.StreamHandler()
	ch.setLevel(LOG_LEVEL)
	log.addHandler(ch)

# FIXME : make this module totally generic
# general config # FIXME : get from config and propagate
SECRET_REL_PATH = '/'.join(__dir_path__.split('/')[:-2] + ['configs']) # hack
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
# noinspection PyPep8
FROM_COMMAND_LINE = lambda: __name__ == '__main__' # restrict access
RWX__ = 0o700

if IS_PYTHON2:
	# noinspection PyCompatibility
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

# noinspection PyUnboundLocalVariable
MissingResException = FileNotFoundError


# clem 14/04/2016
class StorageServicePrototype(object):
	__metaclass__ = abc.ABCMeta
	_not = "Class %s doesn't implement %s()"
	missing_res_exception = None
	
	# clem 20/04/2016
	@staticmethod
	def _print_call(fun_name, args):
		""" Nicely print a function call
		
		:param fun_name: the name of the function
		:type fun_name: basestring_t
		:param args: an arg, or a list of arg supplied to the function
		:type args: list | tuple | basestring_t
		:return:
		:rtype:
		"""
		arg_list = ''
		if isinstance(args, basestring_t):
			args = [args]
		for each in args:
			arg_list += "'%s', " % Bcolors.warning(str(each))
		print(Bcolors.bold(fun_name) + "(%s)" % arg_list[:-2])
	
	# clem 07/09/2017
	def _verbose_print_and_call(self, verbose, fun_object, *args):
		""" Print the function call if verbose, and call the function with args
		
		:param verbose: wether to print or not the call
		:type verbose: bool
		:param fun_object: function to call
		:type fun_object: function
		:param args: argument list
		:type args: *list
		:return: the function result
		"""
		assert callable(fun_object)
		if verbose:
			# noinspection PyUnresolvedReferences
			self._print_call(str(fun_object.func_name), args)
		return fun_object(*args)
	
	# clem 29/04/2016
	def _update_self_do(self, blob_name, file_name, container=None):
		""" TBD
		
		:type blob_name: basestring_t
		:type file_name: basestring_t
		:type container: basestring_t | None
		"""
		if not container:
			container = MNGT_CONTAINER
		# try:
		blob_name = blob_name.replace('.pyc', '.py')
		file_name = file_name.replace('.pyc', '.py')
		if os.path.exists(file_name):
			os.chmod(file_name, RWX__) # make the target file writeable for overwrite
		# TODO check against md5 and download only if different
		return self.download(blob_name, file_name, container)
	
	# clem 20/04/2016
	@abc.abstractmethod
	def update_self(self, container=None):
		""" Download a possibly updated version of this script from *
		
		Will only work from command line for the implementation.
		
		YOU MUST COPY THE FOLLOWING IN YOUR MODULE :
				def update_self(self, container=None):
					assert FROM_COMMAND_LINE
					
					super(YourClassName, self).update_self(container)
					
					return self._update_self_do(__file_name__, __file__, container)

		:param container: target container (default to MNGT_CONTAINER)
		:type container: basestring_t | None
		:return: success ?
		:rtype: bool
		:raise: AssertionError
		"""
		assert FROM_COMMAND_LINE
		return self._update_self_do(__file_name__, __file__, container)

	# clem 29/04/2016
	def _upload_self_do(self, blob_name, file_name, container=None):
		""" TBD
		
		:type blob_name: basestring_t
		:type file_name: basestring_t
		:type container: basestring_t | None
		"""
		if not container:
			container = MNGT_CONTAINER
		blob_name = blob_name.replace('.pyc', '.py')
		file_name = file_name.replace('.pyc', '.py')
		# TODO check against md5 and upload/overwrite only if different
		self.erase(blob_name, container, no_fail=True)
		return self.upload(blob_name, file_name, container)
	
	###
	#   docker_interface access methods
	###
	
	# clem 20/04/2016 @override
	@abc.abstractmethod
	def upload_self(self, container=None):
		""" Upload this script to target storage system, provides auto-updating feature for the other end
		
		YOU MUST COPY THE FOLLOWING IN YOUR MODULE :
			def upload_self(self, container=None):
				super(YourClassName, self).upload_self(container)
				
				return self._upload_self_do(__file_name__, __file__, container)
		
		:param container: target container (default to MNGT_CONTAINER)
		:type container: basestring_t | None
		:return: Info on the created blob as a Blob object
		:rtype: Blob
		"""
		return self._upload_self_do(__file_name__, __file__, container)
	
	# clem 06/09/2017
	@abc.abstractproperty
	def load_environement(self):
		""" define here ENV vars you want to be set on the target execution environement in
		relation with storage, like storage account credentials.

		:return: ENV vars to be set on target
		:rtype: dict[str, str]
		"""
		raise NotImplementedError(self._not % (self.__class__.__name__, function_name()))

	# clem 28/04/201
	@abc.abstractmethod
	def upload(self, target_path, file_path, container=None, verbose=True):
		""" Upload wrapper for * storage :\n
		upload a local file to the default container or a specified one on * storage
		if the container does not exists, it will be created using *

		:param target_path: Name/path of the object as to be stored in * storage
		:type target_path: basestring_t
		:param file_path: Path of the local file to upload
		:type file_path: basestring_t
		:param container: Name of the container to use to store the blob (default to self.container)
		:type container: basestring_t | None
		:param verbose: Print actions (default to True)
		:type verbose: bool | None
		:return: object corresponding to the created blob
		:rtype: Blob # FIXME
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
		:type target_path: basestring_t
		:param file_path: Path of the local file to save the downloaded blob
		:type file_path: basestring_t
		:param container: Name of the container to use to store the blob (default to self.container)
		:type container: basestring_t | None
		:param verbose: Print actions (default to True)
		:type verbose: bool | None
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
		:type target_path: basestring_t
		:param container: Name of the container where the blob is stored (default to self.container)
		:type container: basestring_t or None
		:param verbose: Print actions (default to True)
		:type verbose: bool | None
		:param no_fail: suppress error messages (default to False)
		:type no_fail: bool | None
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
	""" Parse arguments from command line
	
	:return: (action, object_id, file_name)
	:rtype: tuple[basestring, basestring, basestring]
	"""
	assert len(sys.argv) >= 2, '%s : %s' % (len(sys.argv), str(sys.argv))

	aa = str(sys.argv[1])
	bb = '' if len(sys.argv) <= 2 else str(sys.argv[2])
	cc = '' if len(sys.argv) <= 3 else str(sys.argv[3])

	assert isinstance(aa, basestring_t) and aa in ACTION_LIST
	return aa, bb, cc


# clem 22/09/2017
def download_cli(storage, remote_path, local_path, erase):
	""" downloads an arbitrary remote_path file to an arbitrary local_path location
	
	:param storage: the storage instance class
	:type storage: StorageServicePrototype
	:param remote_path: the name/path of the file to download from storage
	:type remote_path: basestring_t
	:param local_path: the local file path to store the downloaded file to
	:type local_path: basestring_t
	:param erase: erase the file from storage after successful download
	:type erase: bool
	:return: is success
	:rtype: bool
	"""
	if storage.download(remote_path, local_path):
		if erase:  # if the download was successful we delete the job file
			storage.erase(remote_path)
		return True
	return False


# clem 22/09/2017
def download_job_cli(storage, obj_id='', erase=True):
	""" downloads the job obj_id from storage and stores it at location HOME + '/' + IN_FILE
	
	
	:param storage: the storage instance class
	:type storage: StorageServicePrototype
	:param obj_id: the name/path of the file to download from storage
	:type obj_id: basestring_t | None
	:param erase: erase the file from storage after successful download
	:type erase: bool | None
	:return: is success
	:rtype: bool
	"""
	return download_cli(storage, obj_id if obj_id else os.environ.get(*ENV_JOB_ID), HOME + '/' + IN_FILE, erase)


# clem 22/09/2017
def upload_cli(storage, remote_path, local_path):
	""" uploads an arbitrary obj_id file to an arbitrary file_n location
	
	:param storage: the storage instance class
	:type storage: StorageServicePrototype
	:param remote_path: the name/path of the file to upload local file to
	:type remote_path: basestring_t
	:param local_path: the local file path of the file to upload
	:type local_path: basestring_t
	:return: is success
	:rtype: bool
	"""
	return storage.upload(remote_path, local_path)


# clem 22/09/2017
def upload_job_cli(storage, remote_path=''):
	""" uploads the job from HOME + '/' + OUT_FILE to storage and stores it at location remote_path
	
	:param storage: the storage instance class
	:type storage: StorageServicePrototype
	:param remote_path: the name/path of the file to upload job to
	:type remote_path: basestring_t | None
	:return: is success
	:rtype: bool
	"""
	local_path = HOME + '/' + OUT_FILE
	if not remote_path:  # the job id must be in env(ENV_JOB_ID[0]) if not we use either the hostname or the md5
		remote_path = os.environ.get(ENV_JOB_ID[0], os.environ.get(ENV_HOSTNAME[0], get_file_md5(local_path)))
	return upload_cli(storage, remote_path, local_path)


# clem 22/09/2017
def self_update_cli(storage):
	""" update itself from storage and its parent/child modules
	
	:param storage: the storage instance class
	:type storage: StorageServicePrototype
	:return: is success
	:rtype: bool
	"""
	old_md5 = get_file_md5(__file__)
	if storage.update_self():
		new_md5 = get_file_md5(__file__)
		if new_md5 != old_md5:
			log.info('%s, %s' %
				(Bcolors.ok_green('successfully'), 'updated from %s to %s' %
					(Bcolors.bold(old_md5), Bcolors.bold(new_md5))))
		else:
			log.info('%s, %s' %
				(Bcolors.ok_green('not updated'), Bcolors.ok_blue('this is already the latest version.')))
		return True
	else:
		log.error(Bcolors.fail('Upgrade failure'))
	return False


# clem on 28/04/2016
def command_line_interface(storage_implementation_instance, action, obj_id='', file_n=''):
	"""	Command line interface of the module, it's the interface the docker container will use.
	
	original base code by clem 14/04/2016

	:type storage_implementation_instance: BlobStorageService
	:type action: basestring_t
	:type obj_id: basestring_t | None
	:type file_n: basestring_t | None
	"""
	global __DEV__
	assert isinstance(storage_implementation_instance, StorageServicePrototype)
	__DEV__ = False # not unused, overrides child's module one
	try: # TODO make functions
		storage = storage_implementation_instance
		if action == ACTION_LIST[0]: # download the job archive from * storage
			exit(int(not download_job_cli(storage, obj_id)))
		elif action == ACTION_LIST[1]: # uploads the job resulting data's archive to * storage
			exit(int(not upload_job_cli(storage, obj_id)))
		elif action == ACTION_LIST[2]: # uploads an arbitrary file to * storage
			assert file_n and len(file_n) > 3
			assert obj_id and len(obj_id) > 4
			exit(int(not upload_cli(storage, obj_id, HOME + '/' + file_n)))
		elif action == ACTION_LIST[3]: # self update
			exit(int(not self_update_cli(storage)))
	except Exception as e:
		import traceback
		tb = traceback.format_exc()
		log.error(Bcolors.fail('FAILURE :'))
		code = 2425
		if hasattr(e, 'msg') and e.msg:
			log.error(e.msg)
		elif hasattr(e, 'message') and e.message:
			log.error(e.message)
		else:
			raise
		if hasattr(e, 'status_code'):
			code = e.status_code
		elif hasattr(e, 'code'):
			code = e.code
		log.exception(tb)
		exit(code)
	

#
# Only utilities after this point
#

# TODO : in your concrete class, simply add those four line at the end
if __name__ == '__main__':
	a, b, c = input_pre_handling()
	# storage_inst = StorageServicePrototype()
	# usually :
	# noinspection PyUnresolvedReferences
	storage_inst = back_end_initiator(ACT_CONT_MAPPING[a])
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
		:param verbose: if to print progress
		:type verbose: bool | None
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


# module prototype to be used as a type abstract for the dynamic import of storage modules
# the imported module is type annotated as this class, while it is really in fact a module that have at least
# clem 06/09/2017
class StorageModulePrototype(ModuleType):
	__metaclass__ = abc.ABCMeta
	_not = "Class %s doesn't implement %s()"
	
	@abc.abstractmethod # FIXME un-used
	def command_line_interface(self, storage_implementation_instance, action, obj_id='', file_n=''):
		"""	Command line interface of the module, it's the interface the docker container will use.
		
		original base code by clem 14/04/2016

		:type storage_implementation_instance: BlobStorageService
		:type action: basestring_t
		:type obj_id: basestring_t | None
		:type file_n: basestring_t | None
		:return: exit code
		:rtype: int
		"""
		raise NotImplementedError(self._not % (self.__class__.__name__, function_name()))
	
	@abc.abstractmethod
	def back_end_initiator(self, container):
		""" Provide a way to override storage instance initialization
		
		:param container: the name of the storage container in the storage service
		:type container: basestring
		:return: an instance of an implementation of StorageServicePrototype
		:rtype: StorageServicePrototype
		"""
		raise NotImplementedError(self._not % (self.__class__.__name__, function_name()))
	
	@abc.abstractmethod
	def input_pre_handling(self): # FIXME un-used
		""" Parse arguments from command line

		:return: (action, object_id, file_name)
		:rtype: tuple[basestring, basestring, basestring]
		"""
		raise NotImplementedError(self._not % (self.__class__.__name__, function_name()))
	
	@abc.abstractmethod
	def management_container(self):
		""" give the name of the management container (where this script will be stored for auto-updates)
		
		:return: The name of the management container
		:rtype: basestring
		"""
		raise NotImplementedError(self._not % (self.__class__.__name__, function_name()))
	
	@abc.abstractmethod
	def data_container(self):
		""" give the name of the data container (the one used to store results)

		:return: The name of the management container
		:rtype: basestring
		"""
		raise NotImplementedError(self._not % (self.__class__.__name__, function_name()))
	
	@abc.abstractmethod
	def jobs_container(self):
		""" give the name of the job container (the one in charge of workloads)

		:return: The name of the job container
		:rtype: basestring
		"""
		raise NotImplementedError(self._not % (self.__class__.__name__, function_name()))
	
	# clem 22/09/2017
	@abc.abstractmethod
	def download_cli(self, storage, remote_path, local_path, erase):
		""" downloads an arbitrary remote_path file to an arbitrary local_path location

		:param storage: the storage instance class
		:type storage: StorageServicePrototype
		:param remote_path: the name/path of the file to download from storage
		:type remote_path: basestring_t
		:param local_path: the local file path to store the downloaded file to
		:type local_path: basestring_t
		:param erase: erase the file from storage after successful download
		:type erase: bool
		:return: is success
		:rtype: bool
		"""
		raise NotImplementedError(self._not % (self.__class__.__name__, function_name()))
	
	# clem 22/09/2017
	@abc.abstractmethod
	def download_job_cli(self, storage, obj_id='', erase=True):
		""" downloads the job obj_id from storage and stores it at location HOME + '/' + IN_FILE

		:param storage: the storage instance class
		:type storage: StorageServicePrototype
		:param obj_id: the name/path of the file to download from storage
		:type obj_id: basestring_t | None
		:param erase: erase the file from storage after successful download
		:type erase: bool | None
		:return: is success
		:rtype: bool
		"""
		raise NotImplementedError(self._not % (self.__class__.__name__, function_name()))
	
	# clem 22/09/2017
	@abc.abstractmethod
	def upload_cli(self, storage, remote_path, local_path):
		""" uploads an arbitrary obj_id file to an arbitrary file_n location

		:param storage: the storage instance class
		:type storage: StorageServicePrototype
		:param remote_path: the name/path of the file to upload local file to
		:type remote_path: basestring_t
		:param local_path: the local file path of the file to upload
		:type local_path: basestring_t
		:return: is success
		:rtype: bool
		"""
		raise NotImplementedError(self._not % (self.__class__.__name__, function_name()))
	
	# clem 22/09/2017
	@abc.abstractmethod
	def upload_job_cli(self, storage, remote_path=''):
		""" uploads the job from HOME + '/' + OUT_FILE to storage and stores it at location remote_path

		:param storage: the storage instance class
		:type storage: StorageServicePrototype
		:param remote_path: the name/path of the file to upload job to
		:type remote_path: basestring_t | None
		:return: is success
		:rtype: bool
		"""
		raise NotImplementedError(self._not % (self.__class__.__name__, function_name()))
	
	# clem 22/09/2017
	@abc.abstractmethod
	def self_update_cli(self, storage):
		""" update itself from storage and its parent/child modules

		:param storage: the storage instance class
		:type storage: StorageServicePrototype
		:return: is success
		:rtype: bool
		"""
		raise NotImplementedError(self._not % (self.__class__.__name__, function_name()))
	
	# utils for prototyping, do not implement
	FileExistsError = FileExistsError
	TimeoutError = TimeoutError
	FileNotFoundError = FileNotFoundError
	StorageServicePrototype = StorageServicePrototype
	MissingResException = FileNotFoundError


# TODO throw an error if key is invalid, otherwise azure keeps on returning "resource not found" error
# clem 22/09/2016 duplicated from utilities/__init__
def get_key_bis(name=''):
	if name.endswith('_secret'):
		name = name[:-7]
	if name.startswith('.'):
		name = name[1:]
	try:
		full_path = '%s/.%s_secret' % (__dir_path__, name)
		if not os.path.isfile(full_path):
			full_path = '%s/.%s_secret' % (SECRET_REL_PATH, name)
		print('accessing key at %s from %s' % (full_path, this_function_caller_name()))
		with open(full_path) as f:
			return str(f.read()).replace('\n', '').replace('\r', '')
	except IOError:
		log.warning('could not read key %s' % name)
	return ''


# clem 08/04/2016 (from utilities)
def function_name(delta=0):
	""" Return the name of the calling function (at delta=0) (provided sys implements _getframe)

	:param delta: change the depth of the call stack inspection
	:type delta: int

	:rtype: str
	"""
	try:
		# noinspection PyProtectedMember
		return sys._getframe(1 + delta).f_code.co_name if hasattr(sys, "_getframe") else ''
	except Exception as e:
		log.error(str(e))
	return ''


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
	OK_BLUE = '\033[94m'
	OK_GREEN = '\033[92m'
	WARNING = '\033[33m'
	FAIL = '\033[91m'
	END_C = '\033[0m'
	BOLD = '\033[1m'
	UNDERLINE = '\033[4m'
	
	@staticmethod
	def ok_blue(text):
		return Bcolors.OK_BLUE + text + Bcolors.END_C
	
	@staticmethod
	def ok_green(text):
		return Bcolors.OK_GREEN + text + Bcolors.END_C
	
	@staticmethod
	def fail(text):
		return Bcolors.FAIL + text + Bcolors.END_C + ' (%s)' % __name__
	
	@staticmethod
	def warning(text):
		return Bcolors.WARNING + text + Bcolors.END_C
	
	@staticmethod
	def header(text):
		return Bcolors.HEADER + text + Bcolors.END_C
	
	@staticmethod
	def bold(text):
		return Bcolors.BOLD + text + Bcolors.END_C
	
	@staticmethod
	def underlined(text):
		return Bcolors.UNDERLINE + text + Bcolors.END_C


# clem 30/08/2017
def timed(fun, *args):
	s = time.time()
	r = fun(*args)
	total_time = time.time() - s
	return r, total_time


# clem 30/08/2017
def waiter(message, wait_sec):
	message += '      \r'
	while wait_sec > 0:
		print(message % wait_sec, end='')
		wait_sec -= 1
		time.sleep(1)
	print()


# clem 30/08/2017 from line 6 @ https://goo.gl/BLuUFD 03/02/2016
def human_readable_byte_size(num, suffix='B'):
	if type(num) is not int:
		if os.path.isfile(num):
			num = os.path.getsize(num)
		else:
			raise TypeError('num should either be a integer file size, or a valid file path')
	for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
		if abs(num) < 1024.0:
			return "%3.1f%s%s" % (num, unit, suffix)
		num /= 1024.0
	return "%.1f%s%s" % (num, 'Yi', suffix)


# clem 30/08/2017
def compute_speed(file_path, transfer_time):
	if not transfer_time:
		return ''
	try:
		size = os.path.getsize(file_path)
		return human_readable_byte_size(int(size / transfer_time)) + '/s'
	except (IOError, FileNotFoundError):
		return ''


# clem 30/08/2017 form line 203 @ https://goo.gl/Wquh6Z clem 08/04/2016 + 10/10/2016
def this_function_caller_name(delta=0):
	""" Return the name of the calling function's caller (for delta=0)

	:param delta: change the depth of the call stack inspection
	:type delta: int

	:rtype: str
	"""
	return function_name(2 + delta)


# clem 30/08/2017 from line 154 @ https://goo.gl/PeiZDk 19/05/2016
def get_key(name=''):
	secrets_root = '.secret/'
	if name.endswith('_secret'):
		name = name[:-7]
	if name.startswith('.'):
		name = name[1:]
	full_path = '%s.%s_secret' % (secrets_root, name)
	
	def read_key():
		with open(full_path) as f:
			log.debug('Read key %s from %s' % (full_path, this_function_caller_name(1)))
			return str(f.read()).replace('\n', '').replace('\r', '')
	
	try:
		return read_key()
	except Exception as e:
		log.warning('could not read key %s from %s (%s)' % (name, secrets_root, str(e)))
	return ''