#!/usr/bin/python
from __future__ import print_function
from blob_storage_module import * # import interface, already has os, sys and abc
from azure.common import AzureMissingResourceHttpError as MissingResException
from azure.storage.blob import BlockBlobService

__version__ = '0.5'
__author__ = 'clem'


# general config
SERVICE_BLOB_BASE_URL = 'https://%s.blob.core.windows.net/%s/'
__DEV__ = True
__path__ = os.path.realpath(__file__)
__dir_path__ = os.path.dirname(__path__)
__file_name__ = os.path.basename(__file__)

AZURE_ACCOUNT_VAR = 'AZURE_ACCOUNT'
AZURE_KEY_VAR = 'AZURE_KEY'


# clem 15/09/2017
def azure_account():
	# print('getenv(%s) = %s' % (AZURE_ACCOUNT_VAR, os.getenv(AZURE_ACCOUNT_VAR)))
	return os.getenv(AZURE_ACCOUNT_VAR)


# clem 15/09/2017
def azure_pwd_file():
	return 'azure_pwd_%s' % azure_account()


def azure_key():
	key = get_key_bis(azure_pwd_file()) or os.getenv(AZURE_KEY_VAR) or os.getenv(azure_pwd_file())
	# print('key is %s' % key)
	return key


# clem 14/04/2016
class AzureStorage(BlobStorageService):
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
		super(AzureStorage, self).upload_self(container)
		return self._upload_self_do(__file_name__, __file__, container)

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
		assert FROM_COMMAND_LINE # restrict access
		super(AzureStorage, self).update_self(container)
		return self._update_self_do(__file_name__, __file__, container)
	
	# clem 06/09/2017
	@property
	def load_environement(self):
		return {
			# azure_pwd_file():  azure_key(),
			AZURE_KEY_VAR: azure_key(),
			# AZURE_ACCOUNT_VAR: azure_account()
		}

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
		# err = getattr(__builtins__, 'FileNotFoundError', IOError)
		
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
				raise FileNotFoundError("Blocking Upload failed")
			# self.blob_service.create_blob_from_path(container, blob_name, file_path)
		else:
			raise FileNotFoundError("File '%s' not found in '%s' !" % (os.path.basename(file_path),
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
	return AzureStorage(azure_account(), azure_key(), container)


if __name__ == '__main__':
	a, b, c = input_pre_handling()
	storage_inst = back_end_initiator(ACT_CONT_MAPPING[a])
	command_line_interface(storage_inst, a, b, c)
