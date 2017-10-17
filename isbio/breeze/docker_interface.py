from compute_interface_module import * # has os, abc, self.js, Runnable, ComputeTarget and utilities.*
from docker_client import *
from django.conf import settings
from utils import safe_rm
from storage import StorageModulePrototype # StorageServicePrototype
from breeze.non_db_objects import RunServer
import os
a_lock = Lock()
container_lock = Lock()

__version__ = '0.11.3'
__author__ = 'clem'
__date__ = '15/03/2016'
KEEP_TEMP_FILE = False # i.e. debug


# clem 21/10/2016
class DockerInterfaceConnector(ComputeInterfaceBase):
	ssh_tunnel = None
	_client = None
	__connect_port = None
	connected = False
	_compute_target = None # FIXME HACK
	
	SSH_CMD_BASE = ['ssh', '-CfNnL']
	SSH_KILL_ALL = 'killall ssh && killall ssh'
	SSH_LOOKUP_BASE = 'ps aux|grep "%s"|grep -v grep'
	
	# from engine
	CONFIG_HUB_PWD_FILE = 'hub_password_file'
	CONFIG_HUB_LOGIN = 'hub_login'
	CONFIG_HUB_EMAIL = 'hub_email'
	CONFIG_DAEMON_IP = 'daemon_ip'
	CONFIG_DAEMON_PORT = 'daemon_port'
	CONFIG_DAEMON_URL = 'daemon_url'
	# from exec/docker
	CONFIG_SUP_SECTION = 'docker'
	CONFIG_SUP_IMAGE = 'image'
	CONFIG_SUP_CONT_CMD = 'cont_cmd'
	CONFIG_VOLUMES = 'volumes'
	DO_ASSEMBLE = 'parse_source'
	
	def __init__(self, compute_target, storage_backend=None, auto_connect=False):
		"""

		:param compute_target: the compute target for this job
		:type compute_target: ComputeTarget
		:param storage_backend: the storage backend python module as defined in the target
		:type storage_backend: StorageModulePrototype
		"""
		super(DockerInterfaceConnector, self).__init__(compute_target, storage_backend)
		# TODO rework the ssh configuration vs daemon conf
		self.config_local_bind_address = (self.config_daemon_ip, self._connect_port)
		self._label = self.config_tunnel_host[0:2]
		
		if auto_connect: # unless explicitly asked for, connection is now made upon access
			self._connect()
	
	##########################
	#  CONFIG FILE SPECIFIC  #
	##########################
	
	# clem 17/06/2016
	@property
	def config_daemon_ip(self):
		return self.engine_obj.get(self.CONFIG_DAEMON_IP)
	
	# clem 17/06/2016
	@property
	def config_daemon_port(self):
		return self.engine_obj.get(self.CONFIG_DAEMON_PORT)
	
	# clem 17/06/2016
	@property
	def config_daemon_url_base(self):
		return str(self.engine_obj.get(self.CONFIG_DAEMON_URL)) % self._connect_port
	
	# clem 07/11/2016 # writing shortcut
	def get_exec_specific(self, prop_name):
		return self.execut_obj.get(prop_name, self.CONFIG_SUP_SECTION)
	
	# clem 17/06/2016
	@property
	def config_image(self):
		return self.get_exec_specific(self.CONFIG_SUP_IMAGE)
	
	# clem 13/10/2017
	@property
	def config_volumes(self):
		# return self.get_exec_specific(self.CONFIG_VOLUMES)
		return self.engine_obj.get(self.CONFIG_VOLUMES)
	
	# clem 13/10/2017
	@property
	def config_do_assemble(self):
		try:
			result = self.engine_obj.get(self.DO_ASSEMBLE).lower() in ['true', 'on', 'yes']
		except Exception as e:
			self.log.warning(str(e))
			result = True
		return result
	
	# clem 17/06/2016
	@property
	def config_cmd(self):
		return self.get_exec_specific(self.CONFIG_SUP_CONT_CMD)
	
	# clem 17/06/2016
	@property
	def config_hub_email(self):
		return self.engine_obj.get(self.CONFIG_HUB_EMAIL)
	
	# clem 17/06/2016
	@property
	def config_hub_login(self):
		return self.engine_obj.get(self.CONFIG_HUB_LOGIN)
	
	# clem 17/06/2016
	@property
	def config_hub_password_file_path(self):
		return self.engine_obj.get(self.CONFIG_HUB_PWD_FILE)
	
	# clem 17/06/2016
	@property
	def config_tunnel_host(self):
		return self.target_obj.tunnel_host
	
	# clem 11/10/2016
	@property
	def config_tunnel_user(self):
		return self.target_obj.tunnel_user
	
	# clem 11/10/2016
	@property
	def config_tunnel_port(self):
		return self.target_obj.tunnel_port
	
	# clem 17/05/2016
	@property
	def docker_hub_pwd(self):
		return get_key(self.config_hub_password_file_path)
	
	# clem 17/05/2016
	@property
	def docker_repo(self):
		return DockerRepo(self.config_hub_login, self.docker_hub_pwd, email=self.config_hub_email)
	
	#########################
	#  CONNECTION SPECIFIC  #
	#########################
	
	# clem 07/11/2016
	def __online_accessor(self, handle_exceptions=False):
		return self._test_connection(self.config_local_bind_address, handle_exceptions)
	
	# clem 20/10/2016
	@property
	def online(self):
		""" Tells if the docker daemon is online, i.e. allows TCP connect (might succeed even if daemon
		
		is actually down, as it does not say anything about the daemon status)
		
		:rtype: bool
		:raise: IOError | Exception
		"""
		return self.__online_accessor()
	
	# clem 07/11/2016
	@property
	def _online(self):
		""" Tells if the docker daemon is online, i.e. allows TCP connect (might succeed even if daemon

		is actually down, as it does not say anything about the daemon status)

		This is the same as the public property self.online, except it handles exceptions and return False on exceptions

		:rtype: bool
		"""
		return self.__online_accessor(True)
	
	# clem 21/10/2016
	# noinspection PyBroadException,PyPep8
	@property
	def can_connect(self):
		try:
			if self._connect():
				try:
					self.client.close()
					self._client = None
				except Exception:
					pass
				return True
		except Exception:
			return False
	
	# clem 12/10/2016
	@property
	def _connect_port(self):
		""" Tell which port to connect to.

		for a ssh tunnel, its the locally mapped port, otherwise its the remote daemon port

		:rtype: int
		"""
		if not self.__connect_port: # 24/08/2017 trying to fix ssh tunneling
			# if self.target_obj.target_use_tunnel: # FIXME
			# 	self.__connect_port = self._get_a_port()
			# else:
			self.__connect_port = self.config_daemon_port
		return self.__connect_port
	
	# clem 10/05/2016
	# noinspection PyBroadException
	def _get_a_port(self):
		""" Give the port number of an existing ssh tunnel, or return a free port if no (or more than 1) tunnel exists

		:return: a TCP port number
		:rtype: int
		"""
		lookup = ' '.join(self.__ssh_cmd_list('.*'))
		full_string = self.SSH_LOOKUP_BASE % lookup
		tmp = sp.Popen(full_string, shell=True, stdout=sp.PIPE).stdout
		lines = []
		for line in tmp.readlines():
			try:
				lines.append(line.split(' ')[-2].split(':')[0])
			except IndexError:
				pass
		if len(lines) > 0:
			if len(lines) == 1:
				logger.debug('Found pre-existing active ssh tunnel, gonna re-use it')
				return int(lines[0])
			else:
				logger.warning('Found %s active ssh tunnels, killing them all...' % len(lines))
				sp.Popen(self.SSH_KILL_ALL, shell=True, stdout=sp.PIPE)
		return int(get_free_port())
	
	# clem 08/09/2016 # This might succeed even if there is not endpoint if using an external tunneling
	@staticmethod
	def _test_connection(target, handle_exceptions=False):
		time_out = 2
		import socket
		
		def do_test_tcp():
			logger.debug('testing connection to %s Tout: %s sec' % (str(target), time_out))
			if test_tcp_connect(target[0], target[1], time_out):
				logger.debug('success')
				return True
			
		if handle_exceptions:
			try:
				return do_test_tcp()
			except socket.timeout:
				logger.warning('connect %s: Time-out' % str(target))
			except socket.error as e:
				logger.warning('connect %s: %s' % (str(target), e))
			except Exception as e:
				logger.exception('connect %s' % str((type(e), e)))
			return False
		else:
			return do_test_tcp()
	
	# clem 07/04/2016
	def _connect(self):
		if not self.connected:
			if self.target_obj.target_use_tunnel and not self._online:
				logger.debug('Establishing %s tunnel' % self.target_obj.target_tunnel)
				if not self._get_ssh():
					return False
			if not (self.enabled and self._online and self._do_connect()):
				logger.error('FAILURE connecting to docker daemon, cannot proceed')
				raise DaemonNotConnected
		return True
	
	# clem 20/10/2016
	@property
	def client(self):
		if not self._client:
			self._connect()
		return self._client
	
	# clem 07/04/2016
	def _do_connect(self):
		if not self._client:
			auto_watcher = True
			self._client = get_docker_client(self.config_daemon_url_base, self.docker_repo, False, auto_watcher)
		self.connected = bool(self._client.cli)
		# self.client.DEBUG = False # suppress debug messages from DockerClient
		return self.connected
	
	# TODO externalize
	# clem 06/04/2016
	def _get_ssh(self):
		if self.config_tunnel_host:
			try:
				logger.debug('Establishing ssh tunnel, running %s ...' % str(self._ssh_cmd_list))
				self.ssh_tunnel = sp.Popen(self._ssh_cmd_list, stdout=sp.PIPE, stderr=sp.PIPE, preexec_fn=os.setsid)
				logger.debug('done,')
				stat = self.ssh_tunnel.poll()
				while stat is None:
					stat = self.ssh_tunnel.poll()
				logger.debug('bg PID : %s' % self.ssh_tunnel.pid)
				return True
			except Exception as e:
				logger.exception('While establishing ssh tunnel : %s ' % str(e))
				logger.info('ssh was : %s' % str(self._ssh_cmd_list))
		else:
			raise AttributeError('Cannot establish ssh tunnel since no ssh_host provided during init')
	
	# clem 29/04/2016
	@property
	def _ssh_cmd_list(self):
		return self.__ssh_cmd_list(self._connect_port)
	
	# clem 17/05/2016
	def __ssh_cmd_list(self, local_port):
		assert isinstance(self.config_tunnel_host, basestring)
		user = ''
		port = []
		if self.config_tunnel_user:
			user = self.config_tunnel_user + '@'
		if self.config_tunnel_port:
			port = ['-p ' + str(self.config_tunnel_port)]
		return self.SSH_CMD_BASE + ['%s:%s:%s' % (local_port, self.config_daemon_ip, self.config_daemon_port)] + \
			[user + self.config_tunnel_host] + port


# clem 15/03/2016
class DockerInterface(DockerInterfaceConnector, ComputeInterface):
	auto_remove = True
	_run_server = None
	run_id = '' # stores the md5 of the sent archive ie. the job id
	proc = None
	_container_lock = None
	_label = ''
	my_volumes = list()
	my_run = None
	_container = None
	_container_logs = ''
	cat = DockerEventCategories

	# SSH_CMD_BASE = ['ssh', '-CfNnL']
	# SSH_KILL_ALL = 'killall ssh && killall ssh'
	# SSH_LOOKUP_BASE = 'ps aux|grep "%s"|grep -v grep'
	# CONTAINER SPECIFIC
	NORMAL_ENDING = ['Running R script... done !', 'Success !', 'done']

	LINE3 = '\x1b[34mCreating archive /root/out.tar.xz'
	LINE2 = '\x1b[1m''create_blob_from_path\x1b[0m(' # FIXME NOT ABSTRACT
	LINES = dict([(-3, LINE3), (-2, LINE2)])

	_status = ''

	START_TIMEOUT = 30 # Start timeout in seconds #FIXME HACK

	job_file_archive_name = 'temp.tar.bz2' # FIXME : Move to config ?
	container_log_file_name = 'container.log'  # FIXME : Move to config

	def __init__(self, compute_target, storage_backend=None, auto_connect=False):
		""" TODO
		
		:param compute_target: the compute target for this job
		:type compute_target: ComputeTarget
		:param storage_backend: a storage module implementing StorageModulePrototype
		:type storage_backend: StorageModulePrototype
		:param auto_connect: Should a connection be established upon instantiation
		:type auto_connect: bool
		"""
		super(DockerInterface, self).__init__(compute_target, storage_backend, auto_connect)
		# TODO fully integrate !optional! tunneling
		self._status = self.js.INIT # FIXME misplaced
		if self._runnable.breeze_stat != self.js.INIT: # TODO improve
			self._status = self._runnable.breeze_stat
		self._container_lock = Lock()
		# parsing volume line from config to assign DockerVolumes object to mount points
		volumes = self.config_volumes
		self.my_volumes = list()
		for each in volumes.split(','):
			each = each.strip()
			each = each.split(' ' if ' ' in each else ':')
			if len(each) == 2:
				each.append('ro')
			self.my_volumes.append(DockerVolume(each[0], each[1], each[2]))
		self.log.debug(str(self.my_volumes))

	# ALL CONFIG SPECIFIC MOVED TO CONNECTOR
	# ALL CONNECTION SPECIFIC MOVED TO CONNECTOR
	
	# clem 11/05/2016
	@property
	def label(self):
		return '<docker%s%s>' % ('_' + self._label, '' if self.client else ' ?')
	
	# clem 11/05/2016
	@property
	def log(self):
		# noinspection PyBroadException
		try:
			log_obj = LoggerAdapter(self._compute_target.runnable.log_custom(1), dict())
			bridge = log_obj.process
			log_obj.process = lambda msg, kwargs: bridge(self.label + ' ' + str(msg), kwargs)
		except Exception:
			log_obj = None
		return log_obj or logger
	
	# clem 06/10/2016
	# noinspection SpellCheckingInspection
	def name(self):
		try:
			img_id = self.client.get_image(self.config_image).Id
		except AttributeError:
			# FIXME backward compatibility safeguard
			img_id = 'sha256:15d72773148517814d1539647d5aea971ccdef566eafb9f796f975b8325e9731'
		return "docker image %s (%s)" % (self.config_image, img_id)

	#####################
	#  DOCKER SPECIFIC  #
	#####################

	def _attach_event_manager(self):
		try:
			if self.my_run and isinstance(self.my_run, DockerRun):
				self.my_run.event_listener = self._event_manager_wrapper()
				self.log.debug('Attached event listener to run')
			return True
		except Exception as e:
			self.log.error(str(e))
		return False

	# clem 25/05/2016
	@property
	def is_start_timeout(self):
		return not (self._container.has_failed or self._container.has_normal_exit) and\
			self._container.time_since_creation.total_seconds() > self.START_TIMEOUT

	# clem 25/05/2016
	def _check_start_timeout(self): # FIXME HACK
		if self.container and not self._container.is_dead and not self._container.is_running:
			# self.log.debug('Time since creation : %s' % self._container.time_since_creation)
			if self.is_start_timeout: # FIXME HACK
				if self._container.status_text == 'created' and not self.container.has_failed:
					self.log.info('Start TO : HACK START of %s' % self._container.status_text)
					self._start_container()
				else:
					self.log.info('Start TO, starting not possible since status is %s ' %
						self._container.status_text)
					self._set_global_status(self.js.FAILED)
					self._runnable.manage_run_failed(0, 888)

	# clem 25/05/2016
	def _container_thread_safe(self):
		with self._container_lock: # Thread safety
			if not self._container and self.client and self._runnable.sgeid:
				# This is only useful on "resume" situation.
				# on a standard run, the _container is filled by self._run() method
				self._container = self.client.get_container(self._runnable.sgeid)
				if self._container.name:
					self.log.info('Acquired container %s :: %s' % (self._container.name, self.status()))
					try:
						if self._container.is_running:
							self._set_global_status(self.js.RUNNING)
						else:
							if self._container.is_dead:
								self.log.warning('container is dead !')
					except AttributeError:
						self.log.error('AttributeError: %s' % str(self._container.status_obj))
				else: # TODO : has to set job to failed
					self.log.error('Container not found !')
					self._set_global_status(self.js.FAILED)
		return self._container

	# clem 12/05/2016
	@property
	def container(self):
		if not self._container and self.client and self._runnable.sgeid:
			self._container_thread_safe()
		return self._container

	# clem 25/05/2016
	def _wait_until_container(self):
		while not self.container:
			time.sleep(.5)
		return self._container

	# clem 25/05/2016
	def _start_container(self):
		self._wait_until_container().start()
		self.log.info('%s started' % self._container.name)
		return True

	def _run(self):
		try:
			container = self.client.run(self.my_run)
			with self._container_lock:
				self._container = container
			self.log.debug('Got %s' % repr(self._container))
			self._runnable.sgeid = self._container.short_id
			self._set_global_status(self.js.SUBMITTED)
			return True
		except Exception as e:
			self.log.error(str(e))
		return False

	def _event_manager_wrapper(self):
		def my_event_manager(event):
			assert isinstance(event, DockerEvent)
			# self.write_log(event)
			if event.description in (DockerEventCategories.DIE, DockerEventCategories.KILL):
				self.job_is_done()
			elif event.description == DockerEventCategories.CREATE:
				self._start_container()
			elif event.description == DockerEventCategories.START:
				self.log.debug('%s started' % event.container.name)
				self._set_global_status(self.js.RUNNING)

		return my_event_manager

	# clem 24/03/2016
	@property
	def container_log_path(self):
		return self.runnable_path + self.container_log_file_name

	def _save_container_log(self):
		if self.container.logs: # not self._container_logs:
			self._container_logs = str(self.container.logs)
		with open(self.container_log_path, 'w') as fo:
			fo.write(self._container_logs)
		self.log.debug('Container log saved in report folder as %s' % self.container_log_file_name)
		return True

	#######################
	#  STORAGE INTERFACE  #
	#######################

	# 15/09/2017 moved to super class (compute_interface_module)
	# _job_storage
	# _result_storage
	# _docker_storage

	#######################
	#  ASSEMBLY SPECIFIC  #
	#######################

	@property
	# clem 23/05/2016
	def assembly_folder_path(self):
		""" The absolute path to the assembly folder, that is used to hold the temp files until they get archived

		:return: the path
		:rtype: str
		"""
		return self.run_server.storage_path

	@property
	# clem 23/05/2016
	def runnable_path(self): # writing shortcut
		""" The absolute path to the report folder

		:return: the path
		:rtype: str
		"""
		return self._runnable.home_folder_full_path

	@property
	# clem 23/05/2016
	def relative_runnable_path(self): # writing shortcut
		""" The old-style pseudo-absolute path to the report folder

		:return: the path
		:rtype: str
		"""
		return self._remove_sup(self.runnable_path)

	@property
	# clem 23/05/2016
	def assembly_archive_path(self):
		""" Return the absolute path to the archive of the assembly (archive that hold all the job code and data)

		:return: the path
		:rtype: str
		"""
		return '%s%s_job.tar.bz2' % (settings.SWAP_PATH, self._runnable.short_id)

	@property
	# clem 24/05/2016
	def results_archive_path(self):
		""" The absolute path to the archive holding the whole results of the job

		:return: the path
		:rtype: str
		"""
		return '%s%s_results.tar.bz2' % (settings.SWAP_PATH, self._runnable.short_id)

	# clem 23/05/2016
	@property
	def _sh_file_path(self):
		""" The absolute path to this specific in-between sh file (called by the container, calling the job sh)

		:return: the path
		:rtype: str
		"""
		return self.assembly_folder_path + settings.DOCKER_SH_STAGE2_NAME

	# clem 24/05/2016
	@property
	def _sh_log_file_path(self):
		""" The absolute path to the log file resulting of the execution of the job's sh file

		:return: the path
		:rtype: str
		"""
		return self.runnable_path + settings.DOCKER_SH_STAGE2_NAME + '.log'

	@staticmethod
	def _remove_sup(path):
		""" removes the PROJECT_FOLDER_PREFIX from the path

		:param path: the path to handle
		:type path: str
		:return: the resulting path
		:rtype: str
		"""
		return path.replace(settings.PROJECT_FOLDER_PREFIX, '')

	# clem 23/05/2016
	def _copy_source_folder(self):
		""" Copy all the source data from the report folder, to the assembly one

		:return: is success
		:rtype: bool
		"""
		ignore_list = [self.execut_obj.exec_file_in]

		def remote_ignore(_, names):
			"""
			:type _: ?
			:type names: str
			:rtype: list

			Return a list of files to ignores amongst names
			"""
			import fnmatch
			out = list()
			for each in names:
				if each[:-1] == '~':
					out.append(each)
				else:
					for ignore in ignore_list:
						if fnmatch.fnmatch(each, ignore):
							out.append(each)
							break
			return out
		
		def code_ignore(_, names):
			out = list()
			for each in names:
				if each.startswith('.'):
					out.append(each)
			return out

		return custom_copytree(self.runnable_path, self.assembly_folder_path + self.relative_runnable_path,
			ignore=remote_ignore) and custom_copytree(settings.SPECIAL_CODE_FOLDER,
			self.assembly_folder_path + settings.SPECIAL_CODE_FOLDER, ignore=code_ignore, no_raise=True)

	# clem 23/05/2016
	def _gen_kick_start_file(self):
		""" Generate the sh file which will be triggered by the container, and which shall triggers the job sh

		The main purpose of this file is to hold the path and file name of this next sh to be run

		:return: is success
		:rtype: bool
		"""
		conf_dict = {
			'job_full_path'	: self.relative_runnable_path,
			'run_job_sh'	: settings.GENERAL_SH_NAME,
		}

		res = gen_file_from_template(settings.DOCKER_STAGE2_SH_TEMPLATE, conf_dict, self._sh_file_path)
		chmod(self._sh_file_path, ACL.RX_RX_)

		return res

	# clem 23/05/2016 # TODO find a better integration design for that
	def _assemble_source_tree(self):
		""" Trigger the 'compilation' of the source tree from the run-server

		Parse the source file, to grab all the dependencies, etc (check out RunServer for more info)

		:return: is success
		:rtype: bool
		"""
		# return self.run_server.parse_all(settings.SPECIAL_CODE_FOLDER) if self.config_do_assemble else True
		self.run_server.skip_parsing = not self.config_do_assemble
		return self.run_server.parse_all(settings.SPECIAL_CODE_FOLDER)

	# clem 24/05/2016
	@property
	def run_server(self):
		""" Return, and get if empty, the run-server of this instance

		:return: the run_server of this instance
		:rtype: RunServer
		"""
		if not self._run_server:
			self._run_server = RunServer(self._runnable)
		assert isinstance(self._run_server, RunServer)
		return self._run_server

	# clem 23/05/2016
	def _upload_assembly(self):
		""" Uploads the assembly folder as an archive to the storage backend

		:return: is success
		:rtype: bool
		"""
		try:
			settings.NO_SGEID_EXPIRY = 60 # FIXME
			self._docker_storage.upload_self() # update the cloud version of azure_storage.py
			self.run_id = get_file_md5(self.assembly_archive_path) # use the archive hash as an id for storage
			if self._job_storage.upload(self.run_id, self.assembly_archive_path):
				if not KEEP_TEMP_FILE:
					remove_file_safe(self.assembly_archive_path)
				return True
		except Exception as e:
			self.log.error(str(e))
		return False

	# clem 10/05/2016
	def _set_status(self, status):
		""" Set status of local object for state tracking

		:param status: status
		:type status: self.js
		"""
		self._status = status

	# clem 10/05/2016
	def _set_global_status(self, status):
		""" Set status of both local and runnable object for state tracking

		:param status: status
		:type status: self.js
		"""
		self._set_status(status)
		self._runnable.breeze_stat = status

	# clem 24/05/2016
	def _clear_report_folder(self):
		""" Empty the report dir, before extracting the result archive there

		:return: is success
		:rtype: bool
		"""
		for each in listdir(self.runnable_path):
			remove_file_safe(self.runnable_path + each)
		return True

	# clem 24/05/2016
	@property
	def job_has_failed(self):
		return isfile(self._runnable.failed_file_path) or isfile(self._runnable.incomplete_file_path)\
			or not isfile(self._runnable.exec_out_file_path) or not isfile(self._sh_log_file_path)

	# clem 24/05/2016  # TODO re-write
	def _check_container_logs(self):
		""" filter the end of the log to match it to a specific pattern, to ensure no unexpected event happened """
		cont = self.container
		log = str(cont.logs)
		the_end = log.split('\n')[-6:-1] # copy the last 5 lines
		for (k, v) in self.LINES.items():
			if the_end[k].startswith(v):
				del the_end[k]
		if the_end != self.NORMAL_ENDING:
			self.log.warning('Container log contains unexpected output !')
		return True

	#####################
	#  CLASS INTERFACE  #
	#####################

	# clem 23/05/2016
	def assemble_job(self):
		""" extra assembly for the job to run into a container :
			_ parse the source file, to change the paths
			_ to grab the dependencies and parse them
			_ create the kick-start sh file
			_ make an archive of it all

		:return: if success
		:rtype: bool
		"""
		self._set_global_status(self.js.PREPARE_RUN)
		# copy all the original data from report folder
		# create the virtual source tree and create the kick-start sh file
		if self._copy_source_folder() and self._assemble_source_tree() and self._gen_kick_start_file():
			if self.make_tarfile(self.assembly_archive_path, self.assembly_folder_path):
				if not KEEP_TEMP_FILE:
					safe_rm(self.assembly_folder_path) # delete the temp folder used to create the archive
				return True

		self.log.error('Job super-assembly failed')
		self._set_global_status(self.js.FAILED)
		self._runnable.manage_run_failed(1, 89)
		return False

	def send_job(self):
		self._set_global_status(self.js.PREPARE_RUN) # TODO change
		
		try:
			if self.apply_config() and self._upload_assembly():
				env = self.remote_env_conf
				# TODO add host_sup passing
				self.my_run = DockerRun(self.config_image,
					self.config_cmd % '%s %s' % (self.run_id, self._compute_target.target_storage_engine),
					self.my_volumes, env=env, cont_name='%s_%s' % (self._runnable.short_id, self._runnable.author))
				self._attach_event_manager()
				if self._run():
					return self.busy_waiting()
				else:
					error = [87, 'container kickoff failed']
			else:
				error = [88, 'assembly upload failed']
		except Exception as e:
			error = [90, str(e)]
		self.log.error(error[1])
		self._set_global_status(self.js.FAILED)
		self._runnable.manage_run_failed(1, error[0])
		return False

	# clem 21/04/2016
	def get_results(self):
		try:
			if self._result_storage.download(self.run_id, self.results_archive_path):
				self._result_storage.erase(self.run_id, no_fail=True)
				self._clear_report_folder()
				if self.extract_tarfile(self.results_archive_path, self.runnable_path):
					if not KEEP_TEMP_FILE:
						remove_file_safe(self.results_archive_path)
					return True
		except self._missing_exception:
			self.log.error('No result found for job %s' % self.run_id)
			raise
		return False

	# clem 06/05/2016
	@new_thread
	def abort(self):
		if self._runnable.breeze_stat != self.js.DONE:
			self._set_global_status(self.js.ABORT)
			try:
				if self.container:
					try:
						self.container.stop()
					except Exception as e:
						self.log.error('Stopping container failed : %s' % str(e))
					try:
						self.container.kill()
					except Exception as e:
						self.log.error('Killing container failed : %s' % str(e))
					try:
						if self.auto_remove:
							self.container.remove_container()
					except Exception as e:
						self.log.error('Removing container failed : %s' % str(e))
			except Exception as e:
				self.log.error(str(e))
			self._set_global_status(self.js.ABORTED)
			self._runnable.manage_run_aborted(1, 95)
			return True
		return False

	# clem 06/05/2016
	def busy_waiting(self, *args):
		if not self.container:
			return False
		while self.container.is_running and not self._runnable.aborting:
			time.sleep(.5)
		return True

	# clem 06/05/2016 # TODO improve
	def status(self):
		self._check_start_timeout()
		return self._status

	# clem 06/05/2016
	def job_is_done(self):
		if self._runnable.aborting:
			return False
		cont = self.container
		assert isinstance(cont, DockerContainer)
		self._set_global_status(self.js.GETTING_RESULTS)
		self.log.info('Died code %s. Total execution time : %s' % (cont.exit_code, cont.delta_display))
		try:
			get_res = self.get_results()
		except Exception as e:
			self.log.error(e)
			self.log.warning('Failure ! (breeze failed while getting back results)')
			self._set_global_status(self.js.FAILED)
			self._runnable.manage_run_failed(0, 92)
			return False
			
		ex_code = cont.exit_code
		try:
			self._save_container_log()
			if self.auto_remove:
				cont.remove_container()
		except Exception as e:
			self.log.warning(str(e))

		if ex_code > 0:
			if not self.job_has_failed:
				self.log.warning('Failure ! (container failed)')
			else:
				self.log.warning('Failure ! (script failed)')
			self._set_global_status(self.js.FAILED)
			self._runnable.manage_run_failed(1, ex_code)
		elif get_res:
			self.log.debug('Success, job completed !')
			try:
				self._check_container_logs()
			except Exception as e:
				self.log.warning(str(e))
			self._set_status(self.js.SUCCEED)
			self._runnable.manage_run_success(0)
			return True
		return False
		
	# clem 20/09/2016
	def delete(self):
		""" implements necessary cleanup feature for deletion of parent object """
		try:
			if self.container:
				self.container.remove_container()
			return True
		except Exception as e:
			self.log.warning('Cannot delete %s: %s' % (self.container.name, str(e)))
		return False


use_caching = True and 'ObjectCache' in dir()
expire_after = 0 # DO NOT set to positive value, otherwise run_id will be lost and the job results will never be
# retrieved upon completion when the job running time is greater than the expiry time # 30 * 60 # 30 minutes
idle_expiry = 6*30*60 # 6 hours


# clem 04/05/2016
def initiator(compute_target, *_):
	assert isinstance(compute_target, ComputeTarget)

	def new_if():
		return DockerInterface(compute_target)
		
	with a_lock:
		if use_caching:
			key_id = compute_target.runnable.short_id if hasattr(compute_target.runnable, 'short_id') else ''
			key = '%s:%s' % ('DockerInterface', key_id)
			return ObjectCache.get_or_add(key, new_if, expire_after, idle_expiry)
		return new_if()

# removed DockerIfTest from azure_test commit 422cc8e on 24/05/2016


def is_ready(compute_target, *_):
	assert isinstance(compute_target, ComputeTarget)
	return DockerInterfaceConnector(compute_target).ready
