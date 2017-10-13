from storage_module_prototype import * # import interface, already has os, sys and abc
import shutil

__version__ = '0.2'
__author__ = 'clem'
__date__ = '13/10/2017'


# general config
__DEV__ = True
__path__ = os.path.realpath(__file__)
__dir_path__ = os.path.dirname(__path__)
__file_name__ = os.path.basename(__file__)

STORAGE_FOLDER = '/storage'


class FimmStorage(StorageServicePrototype):
	missing_res_exception = FileNotFoundError
	
	def __init__(self, container):
		assert isinstance(container, basestring_t)
		self.container = container
	
	def update_self(self, container=None):
		""" Download a possibly updated version of this script from *

		:param container: target container (default to MNGT_CONTAINER)
		:type container: basestring_t | None
		:return: success ?
		:rtype: bool
		:raise: AssertionError
		"""
		assert FROM_COMMAND_LINE
		super(FimmStorage, self).update_self(container)
		return self._update_self_do(__file_name__, __file__, container)
	
	# clem 20/04/2016
	def upload_self(self, container=None):
		""" Upload this script to target storage system, provides auto-updating feature for the other end
		
		:param container: target container (default to MNGT_CONTAINER)
		:type container: basestring_t | None
		:return: Info on the created blob as a Blob object
		:rtype:
		"""
		super(FimmStorage, self).upload_self(container)
		
		return self._upload_self_do(__file_name__, __file__, container)
	
	# clem 06/09/2017
	@property
	def load_environement(self):
		""" define here ENV vars you want to be set on the target execution environement in
		relation with storage, like storage account credentials.

		:return: ENV vars to be set on target
		:rtype: dict[str, str]
		"""
		return {}
	
	def _make_path(self, remote_path, container=''):
		if not container:
			container = self.container
		result = '%s/%s/%s' % (STORAGE_FOLDER, container, remote_path)
		dir_path = os.path.dirname(result)
		if not os.path.isdir(dir_path):
			os.makedirs(dir_path)
		return result
	
	def _copy_file(self, remote_path, local_path, container=None, verbose=True):
		""" copy a local file to the a specified path on the local shared storage folder

		:param remote_path: Name/path of the file as to be stored in local shared storage folder
		:type remote_path: basestring_t
		:param local_path: Path of the local file to be copied
		:type local_path: basestring_t
		:param container: Name of the container to use to store the blob (default to self.container)
		:type container: basestring_t | None
		:param verbose: Print actions (default to True)
		:type verbose: bool | None
		:return: is success
		:rtype: bool
		:raise: IOError or FileNotFoundError
		"""
		if verbose:
			self._print_call('_copy_file', (remote_path, local_path, container))
		if os.path.exists(local_path):
			remote_path = self._make_path(remote_path, container)
			shutil.copyfile(local_path, remote_path)
		else:
			raise FileNotFoundError("File '%s' not found in '%s' !" % (os.path.basename(local_path),
			os.path.dirname(local_path)))
		return True
	
	# clem 28/04/201
	def upload(self, target_path, file_path, container=None, verbose=True):
		""" "Upload" wrapper/interface for docker-interface of copy_file

		:param target_path: Name/path of the object as to be stored in * storage
		:type target_path: basestring_t
		:param file_path: Path of the local file to upload
		:type file_path: basestring_t
		:param container: Name of the container to use to store the blob (default to self.container)
		:type container: basestring_t | None
		:param verbose: Print actions (default to True)
		:type verbose: bool | None
		:return: is success
		:rtype: str
		:raise: IOError or FileNotFoundError
		"""
		return target_path if self._copy_file(target_path, file_path, container, verbose) else ''
	
	# clem 28/04/201
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
		return self._copy_file(target_path, file_path, container, verbose)
	
	# clem 28/04/201
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
		if os.path.exists(target_path):
			target_path = self._make_path(target_path, container)
			os.remove(target_path)
			return True
		if not no_fail:
			raise MissingResException('Cannot remove, Not found %s / %s' % (container, target_path), 404)
		return False


def back_end_initiator(container):
	return FimmStorage(container)


if __name__ == '__main__':
	a, b, c = input_pre_handling()
	storage_inst = back_end_initiator(ACT_CONT_MAPPING[a])
	command_line_interface(storage_inst, a, b, c)
