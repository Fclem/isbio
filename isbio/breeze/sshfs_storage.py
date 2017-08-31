from storage_stub import *

__version__ = '0.0.1'
__author__ = 'clem'
__date__ = '29/08/2016'


__DEV__ = True
__path__ = os.path.realpath(__file__)
__dir_path__ = os.path.dirname(__path__)
__file_name__ = os.path.basename(__file__)


# clem 14/04/2016
class SSHFSModule(object):
	__metaclass__ = abc.ABCMeta
	_not = "Class %s doesn't implement %s()"
	_blob_service = None
	container = None
	old_md5 = ''
	_interface = None # as to be defined as a BlobStorageObject that support argument list : (account_name=self
	# .ACCOUNT_LOGIN, account_key=self.ACCOUNT_KEY). OR you can override the 'blob_service' property
	missing_res_exception = FileNotFound

	def __init__(self, base_path):
		assert isinstance(base_path, basestring)
		self.container = base_path # TODO

	@property
	def blob_service(self):
		""" the * storage interface to self.ACCOUNT_LOGIN\n
		if not connected yet, establish the link and save it

		:return: * storage interface
		:rtype: BlockBlobService
		:raise: Exception
		"""
		if not self._blob_service:
			self._blob_service = self._interface(account_name=self.ACCOUNT_LOGIN, account_key=self.ACCOUNT_KEY)
		return self._blob_service

	def container_url(self):
		""" The public url to self.container\n
		(the container might not be public, thus this url would be useless)

		:return: the url to access self.container
		:rtype: str
		"""
		return self._container_url(self.container)

	def list_blobs(self, do_print=False):
		""" The list of blob in self.container

		:param do_print: print the resulting list ? (default to False)
		:type do_print: bool
		:return: generator of the list of blob in self.container
		"""
		return self._list_blobs(self.container, do_print)

	def blob_info(self, blob_name):
		"""
		:param blob_name: a blob existing in self.container to get info about
		:type blob_name: str
		:return: info object of specified blob
		:rtype: Blob
		"""
		return self._blob_info(self.container, blob_name)

	# clem 20/04/2016
	def _print_call(self, fun_name, args):
		arg_list = ''
		if isinstance(args, basestring):
			args = [args]
		for each in args:
			arg_list += "'%s', " % Bcolors.warning(each)
		print Bcolors.bold(fun_name) + "(%s)" % arg_list[:-2]

	# clem 29/04/2016
	def _upload_self_sub(self, blob_name, file_name, container=None):
		if not container:
			container = MNGT_CONTAINER
		blob_name = blob_name.replace('.pyc', '.py')
		file_name = file_name.replace('.pyc', '.py')
		self.erase(blob_name, container, no_fail=True)
		return self.upload(blob_name, file_name, container)

	# clem 20/04/2016
	def upload_self(self, container=None):
		""" Upload this script to * blob storage

		:param container: target container (default to MNGT_CONTAINER)
		:type container: str|None
		:return: Info on the created blob as a Blob object
		:rtype: Blob
		"""
		return self._upload_self_sub(__file_name__, __file__, container)

	# clem 29/04/2016
	def _update_self_sub(self, blob_name, file_name, container=None):
		if not container:
			container = MNGT_CONTAINER
		# try:
		blob_name = blob_name.replace('.pyc', '.py')
		file_name = file_name.replace('.pyc', '.py')
		return self.download(blob_name, file_name, container)
		#except Exception: # blob was not found
		#	return False

	# clem 20/04/2016
	def update_self(self, container=None):
		""" Download a possibly updated version of this script from * blob storage
		Will only work from command line for the implementation.
		You must override this method, use _update_self_sub, and call it using super, like so :
		return super(__class_name__, self).update_self() and self._update_self_sub(__file_name__, __file__, container)

		:param container: target container (default to MNGT_CONTAINER)
		:type container: str|None
		:return: success ?
		:rtype: bool
		:raise: AssertionError
		"""
		return self._update_self_sub(__file_name__, __file__, container)

	# clem 28/04/201
	@abc.abstractmethod
	def _container_url(self, container):
		raise NotImplementedError(self._not % (self.__class__.__name__, function_name()))

	# clem 28/04/201
	@abc.abstractmethod
	def list_containers(self, do_print=False):
		""" The list of container in the current * storage account

		:param do_print: print the resulting list ? (default to False)
		:type do_print: bool
		:return: generator of the list of containers in self.ACCOUNT_LOGIN storage account
		"""
		raise NotImplementedError(self._not % (self.__class__.__name__, function_name()))

	# clem 28/04/201
	@abc.abstractmethod
	def _list_blobs(self, container, do_print=False):
		"""
		:param container: name of the container to list content from
		:type container: str
		:param do_print: print the resulting list ? (default to False)
		:type do_print: bool
		"""
		raise NotImplementedError(self._not % (self.__class__.__name__, function_name()))

	# clem 28/04/201
	@abc.abstractmethod
	def _blob_info(self, cont_name, blob_name):
		raise NotImplementedError(self._not % (self.__class__.__name__, function_name()))

	# clem 28/04/201
	@abc.abstractmethod
	def upload(self, blob_name, file_path, container=None, verbose=True):
		""" Upload wrapper (around BlockBlobService().blob_service.get_blob_properties) for * block blob storage :\n
		upload a local file to the default container or a specified one on * storage
		if the container does not exists, it will be created using BlockBlobService().blob_service.create_container

		:param blob_name: Name of the blob as to be stored in * storage
		:type blob_name: str
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
	def download(self, blob_name, file_path, container=None, verbose=True):
		""" Download wrapper (around BlockBlobService().blob_service.get_blob_to_path) for * block blob storage :\n
		download a blob from the default container (or a specified one) from * storage and save it as a local file
		if the container does not exists, the operation will fail

		:param blob_name: Name of the blob to retrieve from * storage
		:type blob_name: str
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
	def erase(self, blob_name, container=None, verbose=True, no_fail=False):
		""" Delete the specified blob in self.container or in the specified container if said blob exists

		:param blob_name: Name of the blob to delete from * storage
		:type blob_name: str
		:param container: Name of the container where the blob is stored (default to self.container)
		:type container: str or None
		:param verbose: Print actions (default to True)
		:type verbose: bool or None
		:return: success?
		:rtype: bool
		:raise: self.missing_res_error
		"""
		raise NotImplementedError(self._not % (self.__class__.__name__, function_name()))


# TODO : in your concrete class, simply add those four line at the end
if __name__ == '__main__':
	a, b, c = input_pre_handling()
	# TODO : replace StorageModule with your implemented class
	storage_inst = SSHFSModule('account', 'key', ACT_CONT_MAPPING[a])
	command_line_interface(storage_inst, a, b, c)
