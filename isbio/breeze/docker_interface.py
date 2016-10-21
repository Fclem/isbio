from compute_interface_module import * # has os, abc, self.js, Runnable, ComputeTarget and utilities.*
from docker_client import *
from django.conf import settings
from utils import safe_rm
from blob_storage_module import StorageModule
from breeze.models import RunServer
import os
a_lock = Lock()
container_lock = Lock()

__version__ = '0.5.3'
__author__ = 'clem'
__date__ = '15/03/2016'
KEEP_TEMP_FILE = False # i.e. debug


# clem 21/10/2016
class DockerInterfaceConnector(ComputeInterfaceBase):
	# __metaclass__ = abc.ABCMeta
	ssh_tunnel = None
	_client = None
	__connect_port = None
	connected = False
	_compute_target = None # FIXME HACK
	
	SSH_CMD_BASE = ['ssh', '-CfNnL']
	SSH_KILL_ALL = 'killall ssh && killall ssh'
	SSH_LOOKUP_BASE = 'ps aux|grep "%s"|grep -v grep'
	
	CONFIG_HUB_PWD_FILE = 'hub_password_file'
	CONFIG_HUB_LOGIN = 'hub_login'
	CONFIG_HUB_EMAIL = 'hub_email'
	CONFIG_DAEMON_IP = 'daemon_ip'
	CONFIG_DAEMON_PORT = 'daemon_port'
	CONFIG_DAEMON_URL = 'daemon_url'
	CONFIG_CONTAINER = 'container'
	CONFIG_CMD = 'cmd'
	
	def __init__(self, compute_target, storage_backend=None, auto_connect=False):
		"""

		:type storage_backend: module
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
	
	# clem 17/06/2016
	@property
	def config_container(self):
		return self.engine_obj.get(self.CONFIG_CONTAINER)
	
	# clem 17/06/2016
	@property
	def config_cmd(self):
		return self.engine_obj.get(self.CONFIG_CMD)
	
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
	def docker_repo(self): # TODO check
		return DockerRepo(self.config_hub_login, self.docker_hub_pwd, email=self.config_hub_email)
	
	#########################
	#  CONNECTION SPECIFIC  #
	#########################
	
	# clem 20/10/2016
	@property
	def online(self):
		return self._test_connection(self.config_local_bind_address)
	
	# clem 21/10/2016
	@property
	def can_connect(self):
		try:
			return self._connect()
		except:
			return False
	
	# clem 12/10/2016
	@property
	def _connect_port(self):
		""" Tell which port to connect to.

		for a ssh tunnel, its the locally mapped port, otherwise its the remote daemon port

		:rtype: int
		"""
		if not self.__connect_port:
			if self.target_obj.target_use_tunnel:
				self.__connect_port = self._get_a_port()
			else:
				self.__connect_port = self.config_daemon_port
		return self.__connect_port
	
	# clem 10/05/2016
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
			except Exception:
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
	def _test_connection(self, target):
		time_out = 2
		import socket
		try:
			logger.debug('testing connection to %s Tout: %s sec' % (str(target), time_out))
			if test_tcp_connect(target[0], target[1], time_out):
				logger.debug('success')
				return True
		except socket.timeout:
			logger.exception('connect %s: Time-out' % str(target))
		except socket.error as e:
			logger.exception('connect %s: %s' % (str(target), e[1]))
		except Exception as e:
			logger.error('connect %s' % str((type(e), e)))
		return False
	
	# clem 07/04/2016
	def _connect(self):
		if not self.connected:
			if self.target_obj.target_use_tunnel and not self.online:
				logger.debug('Establishing %s tunnel' % self.target_obj.target_tunnel)
				if not self._get_ssh():
					return False
			if not (self.enabled and self.online and self._do_connect()):
				logger.error('FAILURE connecting to docker daemon, cannot proceed')
				# self._set_status(self.js.FAILED)
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
			self._client = get_docker_client(self.config_daemon_url_base, self.docker_repo, False)
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
	# ssh_tunnel = None
	auto_remove = True
	__docker_storage = None
	_data_storage = None
	_jobs_storage = None
	_run_server = None
	run_id = '' # stores the md5 of the sent archive ie. the job id
	proc = None
	# _client = None
	_container_lock = None
	_label = ''
	my_volume = DockerVolume('/home/breeze/data/', '/breeze')
	my_run = None
	_container = None
	_container_logs = ''
	cat = DockerEventCategories
	# _connect_port = None
	# connected = False

	# SSH_CMD_BASE = ['ssh', '-CfNnL']
	# SSH_KILL_ALL = 'killall ssh && killall ssh'
	# SSH_LOOKUP_BASE = 'ps aux|grep "%s"|grep -v grep'
	# CONTAINER SPECIFIC
	NORMAL_ENDING = ['Running R script... done !', 'Success !', 'done']
	AZURE_KEY_VAR = 'AZURE_KEY'

	LINE3 = '\x1b[34mCreating archive /root/out.tar.xz'
	LINE2 = '\x1b[1m''create_blob_from_path\x1b[0m(' # FIXME NOT ABSTRACT
	LINES = dict([(-3, LINE3), (-2, LINE2)])

	_status = ''

	START_TIMEOUT = 30 # Start timeout in seconds #FIXME HACK

	job_file_archive_name = 'temp.tar.bz2'
	container_log_file_name = 'container.log'

	def __init__(self, compute_target, storage_backend=None, auto_connect=False):
		"""

		:type storage_backend: module
		"""
		assert isinstance(self._runnable, Runnable)
		super(DockerInterface, self).__init__(compute_target, storage_backend, auto_connect)
		# TODO fully integrate !optional! tunneling
		self._status = self.js.INIT # FIXME misplaced
		if self._runnable.breeze_stat != self.js.INIT: # TODO improve
			self._status = self._runnable.breeze_stat
		self._container_lock = Lock()

	# ALL CONFIG SPECIFICs MOVED TO CONNECTOR
	# ALL CONNECTION SPECIFICs MOVED TO CONNECTOR
	
	# clem 11/05/2016
	@property
	def label(self):
		return '<docker%s%s>' % ('_' + self._label, '' if self.client else ' ?')
	
	# clem 11/05/2016
	@property
	def log(self):
		try:
			log_obj = LoggerAdapter(self._compute_target.runnable.log_custom(1), dict())
			bridge = log_obj.process
			log_obj.process = lambda msg, kwargs: bridge(self.label + ' ' + str(msg), kwargs)
		except Exception as e:
			log_obj = None
		return log_obj or logger
	
	# clem 06/10/2016
	def name(self):
		img = self.client.get_image(self.config_container)
		return "docker image %s (%s)" % (self.config_container, img.Id)

	#####################
	#  DOCKER SPECIFIC  #
	#####################

	def _attach_event_manager(self):
		if self.my_run and isinstance(self.my_run, DockerRun):
			self.my_run.event_listener = self._event_manager_wrapper()
			self.log.debug('Attached event listener to run')
		return True

	# clem 25/05/2016
	@property
	def is_start_timeout(self):
		return not (self._container.is_running or self._container.is_dead) and \
			self._container.time_since_creation.total_seconds() > self.START_TIMEOUT

	# clem 25/05/2016
	def _check_start_timeout(self): # FIXME HACK
		if self._container and not self._container.is_dead and not self._container.is_running:
			# self.log.debug('Time since creation : %s' % self._container.time_since_creation)
			if self.is_start_timeout: # FIXME HACK
				if self._container.status_text == 'created':
					self.log.info('Start TO : HACK START of %s' % self._container.status_text)
					self._start_container()
				else:
					self.log.info('Start TO, starting not possible since status is %s ' %
						self._container.status_text)
					self._set_status(self.js.FAILED)
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
						self.log.exception('AttributeError: %s' % str(self._container.status_obj))
				else:
					self.log.error('Container not found !')
		return self._container

	# clem 12/05/2016
	@property
	def container(self):
		if not self._container and self.client and self._runnable.sgeid:
			self._container_thread_safe()
		return self._container

	# clem 25/05/2016
	def _wait_until_container(self):
		while not self._container:
			time.sleep(.5)
		return self._container

	# clem 25/05/2016
	def _start_container(self):
		self._wait_until_container().start()
		return True

	def _run(self):
		container = self.client.run(self.my_run)
		with self._container_lock:
			self._container = container
		self.log.debug('Got %s' % repr(self._container))
		self._runnable.sgeid = self._container.short_id
		self._set_global_status(self.js.SUBMITTED)
		return True

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

	# clem 20/04/2016
	@property
	def _job_storage(self):
		""" The storage backend to use to store the jobs-to-run archives

		:return: an implementation of
		:rtype: StorageModule
		"""
		if not self._jobs_storage:
			self._jobs_storage = self._get_storage(self.storage_backend.jobs_container())
		return self._jobs_storage

	# clem 21/04/2016
	@property
	def _result_storage(self):
		""" The storage backend to use to store the results archives

		:return: an implementation of
		:rtype: StorageModule
		"""
		if not self._data_storage:
			self._data_storage = self._get_storage(self.storage_backend.data_container())
		return self._data_storage

	# clem 21/04/2016
	@property
	def _docker_storage(self):
		""" The storage backend to use to store the storage backend files

		:return: an implementation of
		:rtype: StorageModule
		"""
		if not self.__docker_storage:
			self.__docker_storage = self._get_storage(self.storage_backend.management_container())
		return self.__docker_storage

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
		return self.assembly_folder_path + settings.DOCKER_SH_NAME

	# clem 24/05/2016
	@property
	def _sh_log_file_path(self):
		""" The absolute path to the log file resulting of the execution of the job's sh file

		:return: the path
		:rtype: str
		"""
		return self.runnable_path + settings.DOCKER_SH_NAME + '.log'

	def _remove_sup(self, path):
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

		return custom_copytree(self.runnable_path, self.assembly_folder_path + self.relative_runnable_path,
			ignore=remote_ignore)

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

		res = gen_file_from_template(settings.DOCKER_BOOTSTRAP_SH_TEMPLATE, conf_dict, self._sh_file_path)
		chmod(self._sh_file_path, ACL.RX_RX_)

		return res

	# clem 23/05/2016 # TODO find a better integration design for that
	def _assemble_source_tree(self):
		""" Trigger the 'compilation' of the source tree from the run-server

		Parse the source file, to grab all the dependencies, etc (check out RunServer for more info)

		:return: is success
		:rtype: bool
		"""
		return self.run_server.parse_all()

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
		self._docker_storage.upload_self() # update the cloud version of azure_storage.py
		self.run_id = get_file_md5(self.assembly_archive_path) # use the archive hash as an id for storage
		if self._job_storage.upload(self.run_id, self.assembly_archive_path):
			if not KEEP_TEMP_FILE:
				remove_file_safe(self.assembly_archive_path)
			return True
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
		for (k, v) in self.LINES.iteritems():
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

		self.log.exception('Job super-assembly failed')
		self._set_status(self.js.FAILED)
		self._runnable.manage_run_failed(1, 89)
		return False

	def send_job(self):
		self._set_global_status(self.js.PREPARE_RUN) # TODO change
		if self._upload_assembly():
			env = { 'AZURE_KEY': self._job_storage.ACCOUNT_KEY } # passing the blob storage secret key to the cont
			self.my_run = DockerRun(self.config_container, self.config_cmd % self.run_id, self.my_volume, env=env)
			self._attach_event_manager()
			if self._run():
				return True
			else:
				error = [87, 'container kickoff failed']
		else:
			error = [88, 'assembly upload failed']
		self.log.exception(error[1])
		self._set_status(self.js.FAILED)
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
			self._set_status(self.js.FAILED)
			self._runnable.manage_run_failed(1, 92)
			raise
		self._set_status(self.js.FAILED)
		self._runnable.manage_run_failed(1, 91)
		return False

	# clem 06/05/2016
	def abort(self):
		if self._runnable.breeze_stat != self.js.DONE:
			self._set_global_status(self.js.ABORT)
			try:
				if self.container:
					try:
						self.container.stop()
					except Exception as e:
						self.log.exception('Stopping container failed : %s' % str(e))
					try:
						self.container.kill()
					except Exception as e:
						self.log.exception('Killing container failed : %s' % str(e))
					try:
						self.container.remove_container()
					except Exception as e:
						self.log.exception('Removing container failed : %s' % str(e))
			except Exception as e:
				self.log.exception(str(e))
			self._set_status(self.js.ABORTED)
			self._runnable.manage_run_aborted(1, 95)
			return True
		return False

	# clem 06/05/2016
	def busy_waiting(self, *args):
		if not self.container:
			return False
		while self.container.is_running and not self._runnable.aborting:
			time.sleep(1)
		return True

	# clem 06/05/2016 # TODO improve
	def status(self):
		self._check_start_timeout()
		return self._status

	# clem 06/05/2016 # TODO improve (status assessment)
	def job_is_done(self):
		cont = self.container
		assert isinstance(cont, DockerContainer)
		self._set_global_status(self.js.GETTING_RESULTS)
		self.log.info('Died code %s. Total execution time : %s' % (cont.status_obj.ExitCode, cont.delta_display))
		get_res = self.get_results()
		ex_code = cont.status_obj.ExitCode
		self._save_container_log()

		if self.auto_remove:
			cont.remove_container()

		if ex_code > 0:
			if not self.job_has_failed:
				self.log.warning('Failure ! (container failed)')
			else:
				self.log.warning('Failure ! (script failed)')
			self._set_status(self.js.FAILED)
			self._runnable.manage_run_failed(1, ex_code)
			return False
		elif get_res:
			self.log.info('Success, job completed !')
			self._check_container_logs()
			self._set_status(self.js.SUCCEED)
			self._runnable.manage_run_success(0)
			return True
		self.log.warning('Failure ! (script failed)')
		self._set_status(self.js.FAILED)
		self._runnable.manage_run_failed(0, 999)
		return False


use_caching = True
expire_after = 30 * 60 # 30 minutes


# clem 04/05/2016
def initiator(compute_target, *_):
	assert isinstance(compute_target, ComputeTarget)

	def new_if():
		if compute_target.runnable:
			return DockerInterface(compute_target)
		else: # if the target has no associated runnable object
			return DockerInterfaceConnector(compute_target)

	with a_lock:
		if use_caching:
			key_id = compute_target.runnable.short_id if hasattr(compute_target.runnable, 'short_id') else ''
			key = '%s:%s' % ('DockerInterface', key_id)
			cached = ObjectCache.get(key)
			if not cached:
				ObjectCache.add(new_if(), key, expire_after)
			return ObjectCache.get(key)
		return new_if()

# removed DockerIfTest from azure_test commit 422cc8e on 24/05/2016
