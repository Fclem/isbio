# from docker.api import container
from __future__ import print_function
from storage_module_prototype import *

__version__ = '0.5'
__author__ = 'clem'
__date__ = '28/04/2016'


# TODO set this configs :
SERVICE_BLOB_BASE_URL = '' # format 'proto://%s.domain/%s/' % (container_name, url)
__DEV__ = True
__path__ = os.path.realpath(__file__)
__dir_path__ = os.path.dirname(__path__)
__file_name__ = os.path.basename(__file__)


# clem 14/04/2016
# this is an extension to StorageServicePrototype that describes an abstract BlobStorageService
# this abstract was derived from BlockBlobService in order to be able to use it as a potential prototype
# for other object storage
class BlobStorageService(StorageServicePrototype):
	__metaclass__ = abc.ABCMeta
	_blob_service = None
	container = None
	ACCOUNT_LOGIN = ''
	ACCOUNT_KEY = ''
	old_md5 = ''
	# TODO : populate these values accordingly in concrete class
	_interface = None # as to be defined as a BaseBlobServicePrototype implementation
	# OR you can override the 'blob_service' property

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
		:rtype: BaseBlobServicePrototype
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
	def update_self(self, container=None):
		""" Download a possibly updated version of this script from *
		Will only work from command line for the implementation.
		You must override this method, use _update_self_sub, and call it using super, like so :
		return super(__class_name__, self).update_self() and self._update_self_sub(__file_name__, __file__,
		container)

		:param container: target container (default to MNGT_CONTAINER)
		:type container: str|None
		:return: success ?
		:rtype: bool
		:raise: AssertionError
		"""
		assert FROM_COMMAND_LINE
		return super(BlobStorageService, self).update_self(container) and \
			self._update_self_do(__file_name__, __file__, container)

	# clem 20/04/2016
	def upload_self(self, container=None):
		""" Upload this script to * blob storage

		:param container: target container (default to MNGT_CONTAINER)
		:type container: str|None
		:return: Info on the created blob as a Blob object
		:rtype: Blob
		"""
		return super(BlobStorageService, self).upload_self(container) and \
			self._upload_self_do(__file_name__, __file__, container)

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
	# TODO : replace BlobStorageService with your implemented class
	storage_inst = BlobStorageService('account', 'key', ACT_CONT_MAPPING[a])
	command_line_interface(storage_inst, a, b, c)

SERVICE_HOST_BASE = 'core.windows.net'
DEFAULT_PROTOCOL = 'https'


# clem 05/09/2017
# This metaclass was copied from azure.storage.blob.baseblobservice.BaseBlobService for the sole purpose of
# providing a prototype of the BaseBlobService object for code completion, and to expose a list of method used
# by this module. Commented out definitions are the one not in use in this module
class BaseBlobServicePrototype(object):
	"""
	This is the main class managing Blob resources.

	The Blob service stores text and binary data as blobs in the cloud.
	The Blob service offers the following three resources: the storage account,
	containers, and blobs. Within your storage account, containers provide a
	way to organize sets of blobs. For more information please see:
	https://msdn.microsoft.com/en-us/library/azure/ee691964.aspx
	"""
	_not = "Class %s doesn't implement %s()"
	__metaclass__ = abc.ABCMeta
	MAX_SINGLE_GET_SIZE = 64 * 1024 * 1024
	MAX_CHUNK_GET_SIZE = 4 * 1024 * 1024
	
	@abc.abstractmethod
	def __init__(self, account_name=None, account_key=None, sas_token=None,
		is_emulated=False, protocol=DEFAULT_PROTOCOL, endpoint_suffix=SERVICE_HOST_BASE,
		custom_domain=None, request_session=None, connection_string=None):
		"""
		:param str account_name:
			The storage account name. This is used to authenticate requests
			signed with an account key and to construct the storage endpoint. It
			is required unless a connection string is given, or if a custom
			domain is used with anonymous authentication.
		:param str account_key:
			The storage account key. This is used for shared key authentication.
			If neither account key or sas token is specified, anonymous access
			will be used.
		:param str sas_token:
			A shared access signature token to use to authenticate requests
			instead of the account key. If account key and sas token are both
			specified, account key will be used to sign. If neither are
			specified, anonymous access will be used.
		:param bool is_emulated:
			Whether to use the emulator. Defaults to False. If specified, will
			override all other parameters besides connection string and request
			session.
		:param str protocol:
			The protocol to use for requests. Defaults to https.
		:param str endpoint_suffix:
			The host base component of the url, minus the account name. Defaults
			to Azure (core.windows.net). Override this to use the China cloud
			(core.chinacloudapi.cn).
		:param str custom_domain:
			The custom domain to use. This can be set in the Azure Portal. For
			example, 'www.mydomain.com'.
		:param requests.Session request_session:
			The session object to use for http requests.
		:param str connection_string:
			If specified, this will override all other parameters besides
			request session. See
			http://azure.microsoft.com/en-us/documentation/articles/storage-configure-connection-string/
			for the connection string format.
		"""
		raise NotImplementedError(self._not % (self.__class__.__name__, function_name()))
	
	# def make_blob_url
	# def generate_account_shared_access_signature
	# def generate_container_shared_access_signature
	# def generate_blob_shared_access_signature
	
	@abc.abstractmethod
	def list_containers(self, prefix=None, num_results=None, include_metadata=False,
		marker=None, timeout=None):
		"""
		Returns a generator to list the containers under the specified account.
		The generator will lazily follow the continuation tokens returned by
		the service and stop when all containers have been returned or num_results is reached.

		If num_results is specified and the account has more than that number of
		containers, the generator will have a populated next_marker field once it
		finishes. This marker can be used to create a new generator if more
		results are desired.

		:param str prefix:
			Filters the results to return only containers whose names
			begin with the specified prefix.
		:param int num_results:
			Specifies the maximum number of containers to return. A single list
			request may return up to 1000 contianers and potentially a continuation
			token which should be followed to get additional resutls.
		:param bool include_metadata:
			Specifies that container metadata be returned in the response.
		:param str marker:
			An opaque continuation token. This value can be retrieved from the
			next_marker field of a previous generator object if num_results was
			specified and that generator has finished enumerating results. If
			specified, this generator will begin returning results from the point
			where the previous generator stopped.
		:param int timeout:
			The timeout parameter is expressed in seconds.
		"""
		raise NotImplementedError(self._not % (self.__class__.__name__, function_name()))
	
	@abc.abstractmethod
	def create_container(self, container_name, metadata=None,
		public_access=None, fail_on_exist=False, timeout=None):
		"""
		Creates a new container under the specified account. If the container
		with the same name already exists, the operation fails if
		fail_on_exist is True.

		:param str container_name:
			Name of container to create.
		:param metadata:
			A dict with name_value pairs to associate with the
			container as metadata. Example:{'Category':'test'}
		:type metadata: a dict mapping str to str
		:param public_access:
			Possible values include: container, blob.
		:type public_access:
			One of the values listed in the :class:`~azure.storage.blob.models.PublicAccess` enum.
		:param bool fail_on_exist:
			Specify whether to throw an exception when the container exists.
		:param int timeout:
			The timeout parameter is expressed in seconds.
		:return: True if container is created, False if container already exists.
		:rtype: bool
		"""
		raise NotImplementedError(self._not % (self.__class__.__name__, function_name()))
	
	# def get_container_properties
	# def get_container_metadata
	# def set_container_metadata
	# def get_container_acl
	# def set_container_acl
	# def delete_container
	# def acquire_container_lease
	# def renew_container_lease
	# def release_container_lease
	# def break_container_lease
	# def change_container_lease
	
	@abc.abstractmethod
	def list_blobs(self, container_name, prefix=None, num_results=None, include=None,
		delimiter=None, marker=None, timeout=None):
		"""
		Returns a generator to list the blobs under the specified container.
		The generator will lazily follow the continuation tokens returned by
		the service and stop when all blobs have been returned or num_results is reached.

		If num_results is specified and the account has more than that number of
		blobs, the generator will have a populated next_marker field once it
		finishes. This marker can be used to create a new generator if more
		results are desired.

		:param str container_name:
			Name of existing container.
		:param str prefix:
			Filters the results to return only blobs whose names
			begin with the specified prefix.
		:param int num_results:
			Specifies the maximum number of blobs to return,
			including all :class:`BlobPrefix` elements. If the request does not specify
			num_results or specifies a value greater than 5,000, the server will
			return up to 5,000 items. Setting num_results to a value less than
			or equal to zero results in error response code 400 (Bad Request).
		:param ~azure.storage.blob.models.Include include:
			Specifies one or more additional datasets to include in the response.
		:param str delimiter:
			When the request includes this parameter, the operation
			returns a :class:`~azure.storage.blob.models.BlobPrefix` element in the
			result list that acts as a placeholder for all blobs whose names begin
			with the same substring up to the appearance of the delimiter character.
			The delimiter may be a single character or a string.
		:param str marker:
			An opaque continuation token. This value can be retrieved from the
			next_marker field of a previous generator object if num_results was
			specified and that generator has finished enumerating results. If
			specified, this generator will begin returning results from the point
			where the previous generator stopped.
		:param int timeout:
			The timeout parameter is expressed in seconds.
		"""
		raise NotImplementedError(self._not % (self.__class__.__name__, function_name()))
	
	# def _list_blobs
	# def get_blob_service_stats
	# def set_blob_service_properties
	# def get_blob_service_properties
	
	@abc.abstractmethod
	def get_blob_properties(
		self, container_name, blob_name, snapshot=None, lease_id=None,
		if_modified_since=None, if_unmodified_since=None, if_match=None,
		if_none_match=None, timeout=None):
		"""
		Returns all user-defined metadata, standard HTTP properties, and
		system properties for the blob. It does not return the content of the blob.
		Returns :class:`.Blob` with :class:`.BlobProperties` and a metadata dict.

		:param str container_name:
			Name of existing container.
		:param str blob_name:
			Name of existing blob.
		:param str snapshot:
			The snapshot parameter is an opaque DateTime value that,
			when present, specifies the blob snapshot to retrieve.
		:param str lease_id:
			Required if the blob has an active lease.
		:param datetime if_modified_since:
			A DateTime value. Azure expects the date value passed in to be UTC.
			If timezone is included, any non-UTC datetimes will be converted to UTC.
			If a date is passed in without timezone info, it is assumed to be UTC.
			Specify this header to perform the operation only
			if the resource has been modified since the specified time.
		:param datetime if_unmodified_since:
			A DateTime value. Azure expects the date value passed in to be UTC.
			If timezone is included, any non-UTC datetimes will be converted to UTC.
			If a date is passed in without timezone info, it is assumed to be UTC.
			Specify this header to perform the operation only if
			the resource has not been modified since the specified date/time.
		:param str if_match:
			An ETag value, or the wildcard character (*). Specify this header to perform
			the operation only if the resource's ETag matches the value specified.
		:param str if_none_match:
			An ETag value, or the wildcard character (*). Specify this header
			to perform the operation only if the resource's ETag does not match
			the value specified. Specify the wildcard character (*) to perform
			the operation only if the resource does not exist, and fail the
			operation if it does exist.
		:param int timeout:
			The timeout parameter is expressed in seconds.
		:return: a blob object including properties and metadata.
		:rtype: :class:`~azure.storage.blob.models.Blob`
		"""
		raise NotImplementedError(self._not % (self.__class__.__name__, function_name()))

	# def set_blob_properties
	@abc.abstractmethod
	def exists(self, container_name, blob_name=None, snapshot=None, timeout=None):
		"""
		Returns a boolean indicating whether the container exists (if blob_name
		is None), or otherwise a boolean indicating whether the blob exists.

		:param str container_name:
			Name of a container.
		:param str blob_name:
			Name of a blob. If None, the container will be checked for existence.
		:param str snapshot:
			The snapshot parameter is an opaque DateTime value that,
			when present, specifies the snapshot.
		:param int timeout:
			The timeout parameter is expressed in seconds.
		:return: A boolean indicating whether the resource exists.
		:rtype: bool
		"""
		raise NotImplementedError(self._not % (self.__class__.__name__, function_name()))
	
	@abc.abstractmethod
	def get_blob_to_path(
		self, container_name, blob_name, file_path, open_mode='wb',
		snapshot=None, start_range=None, end_range=None,
		range_get_content_md5=None, progress_callback=None,
		max_connections=1, max_retries=5, retry_wait=1.0, lease_id=None,
		if_modified_since=None, if_unmodified_since=None,
		if_match=None, if_none_match=None, timeout=None):
		"""
		Downloads a blob to a file path, with automatic chunking and progress
		notifications. Returns an instance of :class:`Blob` with
		properties and metadata.

		:param str container_name:
			Name of existing container.
		:param str blob_name:
			Name of existing blob.
		:param str file_path:
			Path of file to write out to.
		:param str open_mode:
			Mode to use when opening the file.
		:param str snapshot:
			The snapshot parameter is an opaque DateTime value that,
			when present, specifies the blob snapshot to retrieve.
		:param int start_range:
			Start of byte range to use for downloading a section of the blob.
			If no end_range is given, all bytes after the start_range will be downloaded.
			The start_range and end_range params are inclusive.
			Ex: start_range=0, end_range=511 will download first 512 bytes of blob.
		:param int end_range:
			End of byte range to use for downloading a section of the blob.
			If end_range is given, start_range must be provided.
			The start_range and end_range params are inclusive.
			Ex: start_range=0, end_range=511 will download first 512 bytes of blob.
		:param bool range_get_content_md5:
			When this header is set to True and specified together
			with the Range header, the service returns the MD5 hash for the
			range, as long as the range is less than or equal to 4 MB in size.
		:param progress_callback:
			Callback for progress with signature function(current, total)
			where current is the number of bytes transfered so far, and total is
			the size of the blob if known.
		:type progress_callback: callback function in format of func(current, total)
		:param int max_connections:
			Set to 1 to download the blob sequentially.
			Set to 2 or greater if you want to download a blob larger than 64MB in chunks.
			If the blob size does not exceed 64MB it will be downloaded in one chunk.
		:param int max_retries:
			Number of times to retry download of blob chunk if an error occurs.
		:param int retry_wait:
			Sleep time in secs between retries.
		:param str lease_id:
			Required if the blob has an active lease.
		:param datetime if_modified_since:
			A DateTime value. Azure expects the date value passed in to be UTC.
			If timezone is included, any non-UTC datetimes will be converted to UTC.
			If a date is passed in without timezone info, it is assumed to be UTC.
			Specify this header to perform the operation only
			if the resource has been modified since the specified time.
		:param datetime if_unmodified_since:
			A DateTime value. Azure expects the date value passed in to be UTC.
			If timezone is included, any non-UTC datetimes will be converted to UTC.
			If a date is passed in without timezone info, it is assumed to be UTC.
			Specify this header to perform the operation only if
			the resource has not been modified since the specified date/time.
		:param str if_match:
			An ETag value, or the wildcard character (*). Specify this header to perform
			the operation only if the resource's ETag matches the value specified.
		:param str if_none_match:
			An ETag value, or the wildcard character (*). Specify this header
			to perform the operation only if the resource's ETag does not match
			the value specified. Specify the wildcard character (*) to perform
			the operation only if the resource does not exist, and fail the
			operation if it does exist.
		:param int timeout:
			The timeout parameter is expressed in seconds. This method may make
			multiple calls to the Azure service and the timeout will apply to
			each call individually.
		:return: A Blob with properties and metadata.
		:rtype: :class:`~azure.storage.blob.models.Blob`
		"""
		raise NotImplementedError(self._not % (self.__class__.__name__, function_name()))
	
	# def get_blob_to_stream
	# def get_blob_to_bytes
	# def get_blob_to_text
	# def get_blob_metadata
	# def set_blob_metadata
	# def acquire_blob_lease
	# def renew_blob_lease
	# def release_blob_lease
	# def break_blob_lease
	# def change_blob_lease
	# def snapshot_blob
	# def copy_blob
	# def abort_copy_blob
	
	@abc.abstractmethod
	def delete_blob(self, container_name, blob_name, snapshot=None,
		lease_id=None, delete_snapshots=None,
		if_modified_since=None, if_unmodified_since=None,
		if_match=None, if_none_match=None, timeout=None):
		"""
		Marks the specified blob or snapshot for deletion.
		The blob is later deleted during garbage collection.

		Note that in order to delete a blob, you must delete all of its
		snapshots. You can delete both at the same time with the Delete
		Blob operation.

		:param str container_name:
			Name of existing container.
		:param str blob_name:
			Name of existing blob.
		:param str snapshot:
			The snapshot parameter is an opaque DateTime value that,
			when present, specifies the blob snapshot to delete.
		:param str lease_id:
			Required if the blob has an active lease.
		:param delete_snapshots:
			Required if the blob has associated snapshots.
		:type delete_snapshots:
			One of the values listed in the :class:`~azure.storage.blob.models.DeleteSnapshot` enum.
		:param datetime if_modified_since:
			A DateTime value. Azure expects the date value passed in to be UTC.
			If timezone is included, any non-UTC datetimes will be converted to UTC.
			If a date is passed in without timezone info, it is assumed to be UTC.
			Specify this header to perform the operation only
			if the resource has been modified since the specified time.
		:param datetime if_unmodified_since:
			A DateTime value. Azure expects the date value passed in to be UTC.
			If timezone is included, any non-UTC datetimes will be converted to UTC.
			If a date is passed in without timezone info, it is assumed to be UTC.
			Specify this header to perform the operation only if
			the resource has not been modified since the specified date/time.
		:param str if_match:
			An ETag value, or the wildcard character (*). Specify this header to perform
			the operation only if the resource's ETag matches the value specified.
		:param str if_none_match:
			An ETag value, or the wildcard character (*). Specify this header
			to perform the operation only if the resource's ETag does not match
			the value specified. Specify the wildcard character (*) to perform
			the operation only if the resource does not exist, and fail the
			operation if it does exist.
		:param int timeout:
			The timeout parameter is expressed in seconds.
		"""
		raise NotImplementedError(self._not % (self.__class__.__name__, function_name()))
	
	#
	#    From azure.storage.blob.blockblobservice.BlockBlobService
	#
	
	def create_blob_from_path(
		self, container_name, blob_name, file_path, content_settings=None,
		metadata=None, progress_callback=None,
		max_connections=1, max_retries=5, retry_wait=1.0,
		lease_id=None, if_modified_since=None, if_unmodified_since=None,
		if_match=None, if_none_match=None, timeout=None):
		"""
		Creates a new blob from a file path, or updates the content of an
		existing blob, with automatic chunking and progress notifications.

		:param str container_name:
			Name of existing container.
		:param str blob_name:
			Name of blob to create or update.
		:param str file_path:
			Path of the file to upload as the blob content.
		:param ~azure.storage.blob.models.ContentSettings content_settings:
			ContentSettings object used to set blob properties.
		:param metadata:
			Name-value pairs associated with the blob as metadata.
		:type metadata: a dict mapping str to str
		:param progress_callback:
			Callback for progress with signature function(current, total) where
			current is the number of bytes transfered so far, and total is the
			size of the blob, or None if the total size is unknown.
		:type progress_callback: callback function in format of func(current, total)
		:param int max_connections:
			Maximum number of parallel connections to use when the blob size
			exceeds 64MB.
			Set to 1 to upload the blob chunks sequentially.
			Set to 2 or more to upload the blob chunks in parallel. This uses
			more system resources but will upload faster.
		:param int max_retries:
			Number of times to retry upload of blob chunk if an error occurs.
		:param int retry_wait:
			Sleep time in secs between retries.
		:param str lease_id:
			Required if the blob has an active lease.
		:param datetime if_modified_since:
			A DateTime value. Azure expects the date value passed in to be UTC.
			If timezone is included, any non-UTC datetimes will be converted to UTC.
			If a date is passed in without timezone info, it is assumed to be UTC.
			Specify this header to perform the operation only
			if the resource has been modified since the specified time.
		:param datetime if_unmodified_since:
			A DateTime value. Azure expects the date value passed in to be UTC.
			If timezone is included, any non-UTC datetimes will be converted to UTC.
			If a date is passed in without timezone info, it is assumed to be UTC.
			Specify this header to perform the operation only if
			the resource has not been modified since the specified date/time.
		:param str if_match:
			An ETag value, or the wildcard character (*). Specify this header to perform
			the operation only if the resource's ETag matches the value specified.
		:param str if_none_match:
			An ETag value, or the wildcard character (*). Specify this header
			to perform the operation only if the resource's ETag does not match
			the value specified. Specify the wildcard character (*) to perform
			the operation only if the resource does not exist, and fail the
			operation if it does exist.
		:param int timeout:
			The timeout parameter is expressed in seconds. This method may make
			multiple calls to the Azure service and the timeout will apply to
			each call individually.
		"""
		raise NotImplementedError(self._not % (self.__class__.__name__, function_name()))
