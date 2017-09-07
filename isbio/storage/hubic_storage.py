#!/usr/bin/python2
from __future__ import print_function
import lhubic
from storage_module_prototype import *
from concurrent.futures import ThreadPoolExecutor
from os.path import isfile, getsize, basename
# clem 31/08/2017


HUBIC_TOKEN_FILE = '.hubic_token'
HUBIC_CLIENT_ID = get_key_bis('hubic_api_id')
HUBIC_CLIENT_SECRET = get_key_bis('hubic_api_secret')
HUBIC_USERNAME = get_key_bis('hubic_username')
HUBIC_PASSWORD = get_key_bis('hubic_password')
SHOW_SPEED_AND_PROGRESS = True
_10_KiBi = 10 * 1024
_50_KiBi = 50 * 1024
_100_KiBi = 100 * 1024
_512_KiBi = 512 * 1024
_1_MiBi = 1 * 1024 * 1024
_2_MiBi = 2 * 1024 * 1024

MissingResException = lhubic.HubicObjectNotFound
HUBIC_SOLE_CONTAINER = 'default'
MINIMUM_TIMEOUT = 5.


class HubicClient(StorageServicePrototype):
	missing_res_exception = lhubic.HubicObjectNotFound
	__hubic = None
	__auth_token = None
	
	def __init__(self, username, password, client_id, client_secret, refresh_token='', container=''):
		self.client_id = client_id
		self.client_secret = client_secret
		self.username = username
		self.password = password
		self.refresh_token = refresh_token
		self.container = container
		if self._auth():
			self._save_token()
	
	@property
	def __token_connection_args(self):
		return {'client_id': self.client_id, 'client_secret': self.client_secret, 'refresh_token': self._auth_token}
	
	@property
	def __creds_connection_args(self):
		return self.client_id, self.client_secret, self.username, self.password
	
	@property
	def _auth_token(self):
		""" Reads and store auth token from HUBIC_TOKEN_FILE file, if exists
		
		:return: auth token or ''
		:rtype: str
		"""
		if not self.__auth_token and isfile(HUBIC_TOKEN_FILE):
			with open(HUBIC_TOKEN_FILE) as f:
				self.__auth_token = f.read()
			log.debug('read auth token from %s' % HUBIC_TOKEN_FILE)
		return self.__auth_token
	
	def _connect(self):
		""" Connect to hubic api service if not already connected, using either connection token, or credentials,
		
		and store the hubic connection object
		
		:return: is success
		:rtype: bool
		"""
		if not self.__hubic:
			if self._auth_token:
				log.debug('connection with auth token')
				self.__hubic = lhubic.Hubic(**self.__token_connection_args)
			else:
				log.debug('connection with account auth info')
				self.__hubic = lhubic.Hubic(*self.__creds_connection_args)
			return True
		return False
	
	@property
	def hubic(self):
		""" provide the Hubic object, with auto-connection
		
		:return: the hubic connection object
		:rtype: lhubic.Hubic
		"""
		self._connect()
		return self.__hubic
	
	def reset(self):
		""" clears the hubic connection object and saved auth token
		
		:return: is success
		:rtype: bool
		"""
		from os import remove
		try:
			self.__hubic.close()
			log.debug('connection closed')
		except Exception as e:
			log.warning(str(e))
		self.__hubic = None
		self.__auth_token = ''
		if isfile(HUBIC_TOKEN_FILE):
			remove(HUBIC_TOKEN_FILE)
		log.debug('auth token cleared')
		return True
	
	def _auth(self):
		""" Proceeds with authentication, clears token and try again on HubicTokenFailure
		
		:return: is success
		:rtype: bool
		"""
		try:
			self.hubic.os_auth() # To get an openstack swift token
			log.debug('connected')
			return True
		except lhubic.HubicTokenFailure:
			self.reset()
		except lhubic.HubicAccessFailure:
			waiter('Waiting %s sec before next retry', 65)
			# waiter('Waiting %s sec before next retry', 2)
		return self._auth()
	
	def _save_token(self):
		""" Save the content of refresh_token to get access without user/password in HUBIC_TOKEN_FILE file
		
		:return: is success
		:rtype: bool
		"""
		try:
			token = self.hubic.refresh_token
			if token != self.__auth_token:
				with open(HUBIC_TOKEN_FILE, 'w') as f:
					f.write(self.hubic.refresh_token)
				log.debug('auth token saved')
			return True
		except Exception as e:
			log.exception(e)
		return False
	
	def __up_and_down_wrapper(self, container, local_file_path, remote_file_path, up_or_down, measure_speed=True):
		remote_file_path, container = self._handle_container(remote_file_path, container)
		
		def _upload_wrapper():
			total_size = getsize(local_file_path)
			total_size_str = human_readable_byte_size(total_size)
			if not isfile(local_file_path):
				raise FileNotFoundError('File %s does not exists.' % local_file_path)
			with open(local_file_path, 'rb') as f:
				from time import sleep
				i = 0.
				interval = .25 # refresh interval
				io_timeout = MINIMUM_TIMEOUT + (float(total_size) / _50_KiBi) / interval # Timeout based on 50KiBi/s transfer speed
				with ThreadPoolExecutor(max_workers=1) as executor:
					future = executor.submit(self.hubic.put_object, container, remote_file_path, f)
					start = time.time()
					log.debug('uploading %s %s to %s' % (local_file_path, total_size_str, remote_file_path))
					while not future.done():
						read_position = f.tell()
						progress = (read_position / float(total_size)) * 100.
						elapsed = time.time() - start
						if read_position < total_size:
							current_speed_avg = human_readable_byte_size(int(read_position / elapsed))
						else:
							current_speed_avg = human_readable_byte_size(0)
						print('%.02i%% %s at avg %s/s        \r' %
							(progress, human_readable_byte_size(read_position), current_speed_avg), end='')
						i += 1.
						if i >= io_timeout:
							print()
							raise TimeoutError('Transfer exceeded maximum allowed time of %s sec' %
								str(io_timeout * interval))
						sleep(interval)
					print()
				return future.result() # file_md5
			
		def _download_wrapper():
			header = self.hubic.head_object(container, remote_file_path)
			total_size = int(header.get('content-length', 0))
			total_size_str = human_readable_byte_size(total_size)
			if isfile(local_file_path):
				raise FileExistsError('File %s exists. For safety files will not be overwritten' % local_file_path)
			with open(local_file_path, 'wb') as f:
				with ThreadPoolExecutor(max_workers=1) as executor:
					temp = dict()
					future = executor.submit(self.hubic.get_object, container, remote_file_path, response_dict=temp)
					log.debug('downloading %s %s to %s' % (remote_file_path, total_size_str, local_file_path))
					
					header, content = future.result()
					f.write(content)
				return header.get('etag', '')
		
		try:
			func = _upload_wrapper if up_or_down == 'up' else _download_wrapper
			res = timed(func) if measure_speed else (func(), 0)
			
			sup = ''
			speed = compute_speed(local_file_path, res[1])
			if speed:
				sup = ' in %.02s sec, avg %s' % (res[1], speed)
			log.info('%s %s%s' % (local_file_path, res[0], sup))
			return True
		except Exception as e:
			log.error('ERROR: %s' % e)
			return False
	
	# clem 07/09/2017
	def _handle_container(self, target_path, container=None):
		if container and HUBIC_SOLE_CONTAINER:
			target_path = '%s/%s' % (container, target_path)
			container = HUBIC_SOLE_CONTAINER
		return target_path, container
	
	# clem 06/09/2017
	@property
	def load_environement(self):
		""" define here ENV vars you want to be set on the target execution environement in
		relation with storage, like storage account credentials.

		:return: ENV vars to be set on target
		:rtype: dict
		"""
		# TODO send fewer info when refresh token is available
		return {
			'HUBIC_CLIENT_ID':     self.client_id,
			'HUBIC_CLIENT_SECRET': self.client_secret,
			'HUBIC_USERNAME':      self.username,
			'HUBIC_PASSWORD':      self.password,
			'HUBIC_REFRESH_TOKEN': self.refresh_token,
		}
	
	# clem 05/09/2017
	def upload(self, target_path, file_path, container=None, verbose=True):
		""" Upload wrapper for * storage :\n
		upload a local file to the default container or a specified one on * storage
		if the container does not exists, it will be created using *

		:param target_path: Name of the blob as to be stored in * storage
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
		return self._verbose_print_and_call(verbose, self.__up_and_down_wrapper,
			container, file_path, target_path, 'up', SHOW_SPEED_AND_PROGRESS)
		# return self.__up_down_stud(container, file_path, target_path, 'up', SHOW_SPEED_AND_PROGRESS)
	
	# clem 05/09/2017
	def download(self, target_path, file_path, container=None, verbose=True):
		""" Download wrapper for * storage :\n
		download a blob from the default container (or a specified one) from * storage and save it as a local file
		if the container does not exists, the operation will fail

		:param target_path: Name of the blob to retrieve from * storage
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
		return self._verbose_print_and_call(verbose, self.__up_and_down_wrapper,
			container, file_path, target_path, 'down', SHOW_SPEED_AND_PROGRESS)
		# return self.__up_down_stud(container, file_path, target_path, 'down', SHOW_SPEED_AND_PROGRESS)
	
	# clem 05/09/2017
	def erase(self, target_path, container=None, verbose=True, no_fail=False):
		""" Delete the specified blob in self.container or in the specified container if said blob exists

		:param target_path: Name of the blob to delete from * storage
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
		try:
			target_path, container = self._handle_container(target_path, container)
			self._verbose_print_and_call(verbose, self.hubic.delete_object, container, target_path)
			return True
		except Exception as e:
			log.error(e)
			if not no_fail:
				raise
			return False
		

def back_end_initiator(container):
	return HubicClient(HUBIC_USERNAME, HUBIC_PASSWORD,  HUBIC_CLIENT_ID, HUBIC_CLIENT_SECRET, container)
