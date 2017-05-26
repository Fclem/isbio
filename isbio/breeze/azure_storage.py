#!/usr/bin/python
from blob_storage_module import * # import interface, already has os, sys and abc
from azure.common import AzureMissingResourceHttpError as MissingResException
from azure.storage.blob import BlockBlobService

__version__ = '0.4.3'
__author__ = 'clem'


# general config
SERVICE_BLOB_BASE_URL = 'https://%s.blob.core.windows.net/%s/'
__DEV__ = True
__path__ = os.path.realpath(__file__)
__dir_path__ = os.path.dirname(__path__)
__file_name__ = os.path.basename(__file__)

AZURE_ACCOUNT = 'breezedata'
AZURE_PWD_FILE = 'azure_pwd_%s' % AZURE_ACCOUNT


def azure_key():
	return get_key_bis(AZURE_PWD_FILE)


class NoProgressException(BaseException):
	pass


class BlockingTransfer(object):
	import time
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
				self._start_time = self.time.time()
				self._transfer_func(self._progress_func)
				self._started = True
				self._wait()
				return True
			except:
				self._failed = True
				self._waiting = False
		return False
		
	def _wait(self):
		if self._started and not self._waiting:
			self._waiting = True
			while not self.is_complete:
				self.time.sleep(0.005)
				if (self.time.time() - self._start_time) % 2 == 0:
					# check every two seconds if some progress was made
					if self._per100 == self._last_progress:
						print 'NoProgressException'
						raise NoProgressException
	
	def _progress_func(self, current, total):
		self._last_progress = self._per100
		self._per100 = (current // total) * 100
		if self._verbose:
			print 'transfer: %.2f%%\r' % self._per100,
		if current == total:
			self._completed = True
			if self._verbose:
				print 'transfer complete'
			
	@property
	def is_complete(self):
		return self._completed and not self._failed
	
	@property
	def progress(self):
		return self._per100


# clem 14/04/2016
class AzureStorage(StorageModule):
	_interface = BlockBlobService
	missing_res_exception = MissingResException

	# clem 19/04/2016
	def _container_url(self, container):
		return SERVICE_BLOB_BASE_URL % (self.ACCOUNT_LOGIN, container)

	# clem 20/04/2016
	def list_containers(self, do_print=False):
		""" The list of container in the current Azure storage account

		:param do_print: print the resulting list ? (default to False)
		:type do_print: bool
		:return: generator of the list of containers in self.ACCOUNT_LOGIN storage account
		:rtype: azure.storage.models.ListGenerator
		"""
		generator = self.blob_service.list_containers()
		if do_print:
			print('Azure account \'%s\' containers list :' % self.ACCOUNT_LOGIN)
			for container in generator:
				print(container.name)
		return generator

	# clem 19/04/2016
	def _list_blobs(self, container, do_print=False):
		"""
		:param container: name of the container to list content from
		:type container: str
		:param do_print: print the resulting list ? (default to False)
		:type do_print: bool
		:rtype: azure.storage.models.ListGenerator
		"""
		generator = self.blob_service.list_blobs(container)
		if do_print:
			print('Azure container \'%s\' content :' % container)
			for blob in generator:
				print(blob.name)
		return generator

	# clem 19/04/2016
	def _blob_info(self, cont_name, blob_name):
		return self.blob_service.get_blob_properties(cont_name, blob_name)

	# clem 20/04/2016 @override
	def upload_self(self, container=None):
		""" Upload this script to azure blob storage

		:param container: target container (default to MNGT_CONTAINER)
		:type container: str|None
		:return: Info on the created blob as a Blob object
		:rtype: Blob
		"""
		return super(AzureStorage, self).upload_self(container) and self._upload_self_sub(__file_name__, __file__,
			container)

	# clem 20/04/2016
	def update_self(self, container=None):
		""" Download a possibly updated version of this script from azure blob storage
		Will only work from command line.

		:param container: target container (default to MNGT_CONTAINER)
		:type container: str|None
		:return: success ?
		:rtype: bool
		:raise: AssertionError or AzureMissingResourceHttpError
		"""
		assert __name__ == '__main__' # restrict access
		return super(AzureStorage, self).update_self(container) and self._update_self_sub(__file_name__, __file__,
			container)

	# clem 15/04/2016
	def upload(self, blob_name, file_path, container=None, verbose=True):
		""" Upload wrapper (around BlockBlobService().blob_service.get_blob_properties) for Azure block blob storage :\n
		upload a local file to the default container or a specified one on Azure storage
		if the container does not exists, it will be created using BlockBlobService().blob_service.create_container

		:param blob_name: Name of the blob as to be stored in Azure storage
		:type blob_name: str
		:param file_path: Path of the local file to upload
		:type file_path: str
		:param container: Name of the container to use to store the blob (default to self.container)
		:type container: str or None
		:param verbose: Print actions (default to True)
		:type verbose: bool or None
		:return: object corresponding to the created blob
		:rtype: azure.storage.blob.models.Blob
		:raise: IOError or FileNotFoundError
		"""
		if not container:
			container = self.container
		err = getattr(__builtins__, 'FileNotFoundError', IOError)
		
		def do_upload(progress_func):
			assert callable(progress_func)
			if verbose:
				self._print_call('create_blob_from_path', (container, blob_name, file_path))
			self.blob_service.create_blob_from_path(container, blob_name, file_path, progress_callback=progress_func)
		
		if os.path.exists(file_path):
			if not self.blob_service.exists(container):
				# if container does not exist yet, we create it
				if verbose:
					self._print_call('create_container', container)
				self.blob_service.create_container(container)
			trans = BlockingTransfer(do_upload, verbose=False).do_blocking_transfer()
			if not trans:
				raise err("Blocking Upload failed")
			# self.blob_service.create_blob_from_path(container, blob_name, file_path)
		else:
			raise err("File '%s' not found in '%s' !" % (os.path.basename(file_path),
				os.path.dirname(file_path)))
		return self.blob_service.get_blob_properties(container, blob_name)

	# clem 15/04/2016
	def download(self, blob_name, file_path, container=None, verbose=True):
		""" Download wrapper (around BlockBlobService().blob_service.get_blob_to_path) for Azure block blob storage :\n
		download a blob from the default container (or a specified one) from azure storage and save it as a local file
		if the container does not exists, the operation will fail

		:param blob_name: Name of the blob to retrieve from Azure storage
		:type blob_name: str
		:param file_path: Path of the local file to save the downloaded blob
		:type file_path: str
		:param container: Name of the container to use to store the blob (default to self.container)
		:type container: str or None
		:param verbose: Print actions (default to True)
		:type verbose: bool or None
		:return: success?
		:rtype: bool
		:raise: azure.common.AzureMissingResourceHttpError
		"""
		if not container:
			container = self.container
		
		def do_download(progress_func):
			assert callable(progress_func)
			if verbose:
				self._print_call('get_blob_to_path', (container, blob_name, file_path))
			self.blob_service.get_blob_to_path(container, blob_name, file_path, progress_callback=progress_func)
		
		if self.blob_service.exists(container, blob_name): # avoid error, and having blank files on error
			# purposely not catching AzureMissingResourceHttpError (to be managed from caller code)
			trans = BlockingTransfer(do_download).do_blocking_transfer()
			if not trans:
				raise IOError("Blocking Download failed")
			# self.blob_service.get_blob_to_path(container, blob_name, file_path)
			return True
		raise MissingResException('Not found %s / %s' % (container, blob_name), 404)

	# clem 21/04/2016
	def erase(self, blob_name, container=None, verbose=True, no_fail=False):
		""" Delete the specified blob in self.container or in the specified container if said blob exists

		:param blob_name: Name of the blob to delete from Azure storage
		:type blob_name: str
		:param container: Name of the container where the blob is stored (default to self.container)
		:type container: str or None
		:param verbose: Print actions (default to True)
		:type verbose: bool or None
		:param no_fail: suppress raising an exception if the named blob does not exists
		:type no_fail: bool or None (default to False)
		:return: success?
		:rtype: bool
		:raise: azure.common.AzureMissingResourceHttpError
		"""
		if not container:
			container = self.container
		if self.blob_service.exists(container, blob_name):
			if verbose:
				self._print_call('delete_blob', (container, blob_name))
			self.blob_service.delete_blob(container, blob_name)
			return True
		if not no_fail:
			raise MissingResException('Not found %s / %s' % (container, blob_name), 404)
		return False


# clem 29/04/2016
def back_end_initiator(container):
	return AzureStorage(AZURE_ACCOUNT, azure_key(), container)


if __name__ == '__main__':
	a, b, c = input_pre_handling()
	storage_inst = back_end_initiator(ACT_CONT_MAPPING[a])
	command_line_interface(storage_inst, a, b, c)
