from utilz import *
from breeze.models import JobStat, Runnable, ComputeTarget
from storage import StorageModulePrototype, StorageServicePrototype
import abc

__version__ = '0.1.6'
__author__ = 'clem'
__date__ = '04/05/2016'

# TODO improve the architecture of this system : the interface should not carry the runnable object
# TODO 	this should be a "provider" not "interface" and a new interface should be created to link the
# TODO 	provider with the runnable


# clem 15/09/2017
class ComputeInterfaceBasePrototype(object):
	__metaclass__ = abc.ABCMeta
	_not = "Class %s doesn't implement %s()"
	
	# clem 20/10/2016
	@abc.abstractmethod
	def online(self):
		""" Tells if the target is online

		:return:
		:rtype: bool
		:raise: IOError, Exception
		"""
		raise NotImplementedError(self._not % (self.__class__.__name__, this_function_name()))
	
	# clem 21/10/2016
	@abc.abstractmethod
	def can_connect(self):
		raise NotImplementedError(self._not % (self.__class__.__name__, this_function_name()))


# clem 21/10/2016
class ComputeInterfaceBase(ComputeInterfaceBasePrototype):
	__metaclass__ = abc.ABCMeta
	_storage_backend = None
	_missing_exception = None
	_compute_target = None
	_runnable = None
	
	def __init__(self, compute_target, storage_backend=None): # TODO call from child-class, as the first instruction
		"""
		
		:param compute_target: the compute target for this job
		:type compute_target: ComputeTarget
		:param storage_backend: the storage backend python module as defined in the target
		:type storage_backend: StorageModulePrototype
		"""
		assert isinstance(compute_target, ComputeTarget)
		self._compute_target = compute_target
		self._runnable = self._compute_target.runnable
		# assert isinstance(self._runnable, Runnable)
		
		self._storage_backend = storage_backend
		self.__storage_backend_getter()
	
	# clem 06/09/2017
	def __storage_backend_getter(self):
		""" return the storage backend module

		:return:
		:rtype: StorageModulePrototype
		"""
		if not self._storage_backend:
			self._storage_backend = self._compute_target.storage_module
		assert hasattr(self._storage_backend, 'MissingResException')
		
		self._missing_exception = self._storage_backend.MissingResException
		return self._storage_backend
	
	# clem 06/09/2017
	@property
	def storage_backend(self):
		return self.__storage_backend_getter()
	
	# clem 20/10/2016
	@property
	def enabled(self):
		""" Tells if all components are enabled

		:return:
		:rtype: bool
		"""
		return self._compute_target.is_enabled
	
	# clem 20/10/2016
	@property
	def ready(self):
		""" Tells if all components are enabled and if the target is online

		:return:
		:rtype: bool
		:raise: IOError, Exception
		"""
		return self.enabled and self.online and self.can_connect
	
	# clem 17/05/2016
	@property
	def js(self):
		return JobStat
	
	# clem 11/05/2016
	@property
	def log(self):
		log_obj = LoggerAdapter(self._compute_target.runnable.log_custom(1), dict())
		bridge = log_obj.process
		log_obj.process = lambda msg, kwargs: bridge('<%s> %s' % (self._compute_target, str(msg)), kwargs)
		return log_obj
		
	# clem 09/05/2016 from sge_interface
	def apply_config(self):
		""" Applies the proper Django settings, and environement variables for SGE config

		:return: if succeeded
		:rtype: bool
		"""
		if self.target_obj:
			self.engine_obj.set_local_env()
			self.execut_obj.set_local_env()
			self.target_obj.set_local_env(self.target_obj.engine_section)
			self.engine_obj.set_local_env()
			
			# return self.write_config()
			return True
		return False
	
	# clem 14/05/2016
	@property
	def target_obj(self):
		"""

		:return:
		:rtype: ComputeTarget
		"""
		return self._compute_target
	
	# clem 17/05/2016
	@property # writing shortcut
	def engine_obj(self):
		from breeze.non_db_objects import FakeConfigObject
		if self.target_obj and self.target_obj.engine_obj:
			return self.target_obj.engine_obj
		return FakeConfigObject()
	
	# clem 17/05/2016
	@property  # writing shortcut
	def execut_obj(self):
		if self.target_obj and self.target_obj.exec_obj:
			return self.target_obj.exec_obj
		return None


# clem 15/09/2017
class ComputeInterfacePrototype(ComputeInterfaceBasePrototype):
	# clem 06/10/2016
	@abc.abstractmethod
	def name(self):
		""" This method should return the name of the engine/version executing the workload
		"""
		raise NotImplementedError(self._not % (self.__class__.__name__, this_function_name()))
	
	# clem 23/05/2016
	@abc.abstractmethod
	def assemble_job(self):
		""" This function should implement whatever assembling of the source / files / dependencies are necessary
		for the job to be ready for submission and run

		It is advised to return a bool indicating success or failure
		"""
		raise NotImplementedError(self._not % (self.__class__.__name__, this_function_name()))
	
	@abc.abstractmethod
	def send_job(self):
		""" This function should implement the submission and triggering of the job's run

		It is advised to return a bool indicating success or failure
		"""
		raise NotImplementedError(self._not % (self.__class__.__name__, this_function_name()))
	
	@abc.abstractmethod
	def get_results(self):
		""" This function should implement the transfer and extraction of the results files from the storage backend
		to the local report folder in Breeze tree structure

		It is advised to return a bool indicating success or failure
		"""
		raise NotImplementedError(self._not % (self.__class__.__name__, this_function_name()))
	
	# clem 06/05/2016
	@abc.abstractmethod
	def abort(self):
		""" This function should implement the abortion of the job

		It is advised to return a bool indicating success or failure
		"""
		raise NotImplementedError(self._not % (self.__class__.__name__, this_function_name()))
	
	# clem 06/05/2016
	@abc.abstractmethod
	def status(self):
		""" This function should implement a status interface for the job.

		:rtype: str
		"""
		raise NotImplementedError(self._not % (self.__class__.__name__, this_function_name()))
	
	# clem 06/05/2016
	@abc.abstractmethod
	def busy_waiting(self, *args):
		""" This function should implement an active busy waiting system, that waits until job competition.

		This method will be run on another Thread, so you do not need to worry about blocking execution.
		However it is advised to use time.sleep() with increments of 1 second, to reduce CPU usage of the server.
		Also you are not required to use busy waiting, and can simply return True early on, this will not affect the
		job status, and implement instead a event driven status system.

		It is advised to return a bool indicating success or failure
		"""
		raise NotImplementedError(self._not % (self.__class__.__name__, this_function_name()))
	
	# clem 06/05/2016
	@abc.abstractmethod
	def job_is_done(self):
		""" This function should implement the necessary action to take upon job completion.

		It will not be called from Breeze, it is for you to trigger it.
		This function should also access the final status of the job, and call the appropriated method from runnable
		Runnable.manage_run_*()

		It is advised to return a bool indicating success or failure
		"""
		raise NotImplementedError(self._not % (self.__class__.__name__, this_function_name()))


# clem 04/05/2016
class ComputeInterface(ComputeInterfaceBase, ComputeInterfacePrototype):
	__metaclass__ = abc.ABCMeta
	__docker_storage = None
	_data_storage = None
	_jobs_storage = None
	
	# clem 21/10/2016
	def __init__(self, compute_target, storage_backend=None):
		super(ComputeInterface, self).__init__(compute_target, storage_backend)
		assert isinstance(self._runnable, Runnable)

	def _get_storage(self, container=None):
		return self.storage_backend.back_end_initiator(container)

	# clem 20/04/2016
	def make_tarfile(self, output_filename, source_dir):
		""" makes a tar.bz2 archive from source_dir, and stores it in output_filename

		:param output_filename: the name/path of the resulting archive
		:type output_filename: basestring
		:param source_dir: the path of the source folder
		:type source_dir: basestring
		:return: if success
		:rtype: bool
		"""
		try:
			return make_tarfile(output_filename, source_dir)
		except Exception as e:
			self.log.exception('Error creating %s : %s' % (output_filename, str(e)))
		return False

	# clem 23/05/2016
	def extract_tarfile(self, input_filename, destination_dir):
		""" extract an tar.* to a destination folder

		:param input_filename: the name/path of the source archive
		:type input_filename: basestring
		:param destination_dir: the path of the destination folder
		:type destination_dir: basestring
		:return: if success
		:rtype: bool
		"""
		try:
			return extract_tarfile(input_filename, destination_dir)
		except Exception as e:
			self.log.exception('Error extracting %s : %s' % (input_filename, str(e)))
		return False
	
	#######################
	#  STORAGE INTERFACE  #
	#######################
	
	# clem 20/04/2016
	@property
	def _job_storage(self):
		""" The storage backend to use to store the jobs-to-run archives

		:return: an implementation of
		:rtype: StorageServicePrototype
		"""
		if not self._jobs_storage:
			self._jobs_storage = self._get_storage(self.storage_backend.jobs_container())
		return self._jobs_storage
	
	# clem 21/04/2016
	@property
	def _result_storage(self):
		""" The storage backend to use to store the results archives

		:return: an implementation of
		:rtype: StorageServicePrototype
		"""
		if not self._data_storage:
			self._data_storage = self._get_storage(self.storage_backend.data_container())
		return self._data_storage
	
	# clem 21/04/2016
	@property
	def _docker_storage(self):
		""" The storage backend to use to store the storage backend files

		:return: an implementation of
		:rtype: StorageServicePrototype
		"""
		if not self.__docker_storage:
			self.__docker_storage = self._get_storage(self.storage_backend.management_container())
		return self.__docker_storage
	
	@property
	def remote_env_conf(self):
		""" Make a dict with the remote environement vars to be configured on the target
		
		:rtype: dict[str, str]
		"""
		env = self._job_storage.load_environement
		env.update(self.execut_obj.remote_env_config)
		env.update(self.engine_obj.remote_env_config)
		env.update(self.target_obj.remote_env_config)
		return env
	
	# clem 16/05/2016
	def __repr__(self):
		return '<%s@%s>' % (self.__class__.__name__, hex(id(self)))


# clem 04/05/2016 EXAMPLE function
# TODO override in implementation
def initiator(compute_target, *_):
	# It is probably a good idea to cache the object you are going to create here.
	# Also a good idea is to use module-wide Thread.Lock() to avoid cache-miss due to concurrency
	assert isinstance(compute_target, ComputeTarget)
	# Replace compute_target.storage_module with another module.
	# Note : compute_target.storage_module is also the default
	return ComputeInterface(compute_target, compute_target.storage_module)


# clem 21/10/2016
# TODO override in implementation
def is_ready(compute_target, *_):
	assert isinstance(compute_target, ComputeTarget)
	raise NotImplementedError("The module %s doesn't implement %s()" % (__file__, this_function_name()))
