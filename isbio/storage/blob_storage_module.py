from storage_stub import *

__version__ = '0.4.3'
__author__ = 'clem'
__date__ = '28/04/2016'


# TODO set this configs :
SERVICE_BLOB_BASE_URL = '' # format 'proto://%s.domain/%s/' % (container_name, url)
__DEV__ = True
__path__ = os.path.realpath(__file__)
__dir_path__ = os.path.dirname(__path__)
__file_name__ = os.path.basename(__file__)


# TODO throw an error if key is invalid, otherwise azure keeps on returning "resource not found" error
# clem 22/09/2016 duplicated from utilities/__init__
def get_key_bis(name=''):
	if name.endswith('_secret'):
		name = name[:-7]
	if name.startswith('.'):
		name = name[1:]
	try:
		full_path = '%s/.%s_secret' % (__dir_path__, name)
		print 'accessing key at %s' % full_path
		with open(full_path) as f:
			return str(f.read())[:-1]
	except Exception:
		pass
	return ''


# clem 14/04/2016
class StorageModule(StorageModuleAbstract):
	__metaclass__ = abc.ABCMeta
	_not = "Class %s doesn't implement %s()"
	_blob_service = None
	container = None
	ACCOUNT_LOGIN = ''
	ACCOUNT_KEY = ''
	old_md5 = ''
	# TODO : populate these values accordingly in concrete class
	_interface = None # as to be defined as a BlobStorageObject that support argument list : (account_name=self
	# .ACCOUNT_LOGIN, account_key=self.ACCOUNT_KEY). OR you can override the 'blob_service' property
	missing_res_exception = None # AzureMissingResourceHttpError

	def __init__(self, login, key, container):
		assert isinstance(login, basestring)
		assert isinstance(key, basestring)
		assert isinstance(container, basestring)
		self.ACCOUNT_LOGIN = login
		self.ACCOUNT_KEY = key
		self.container = container

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
		:param no_fail: suppress error messages (default to False)
		:type no_fail: bool or None
		:return: success?
		:rtype: bool
		:raise: self.missing_res_error
		"""
		raise NotImplementedError(self._not % (self.__class__.__name__, function_name()))
	

# TODO : in your concrete class, simply add those four line at the end
if __name__ == '__main__':
	a, b, c = input_pre_handling()
	# TODO : replace StorageModule with your implemented class
	storage_inst = StorageModule('account', 'key', ACT_CONT_MAPPING[a])
	command_line_interface(storage_inst, a, b, c)
