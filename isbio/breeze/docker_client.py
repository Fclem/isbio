from docker import Client as DockerApiClient
from docker.errors import NotFound, APIError, NullResource
from threading import Thread, Lock
from datetime import datetime
from utilz import get_md5, advanced_pretty_print, TermColoring, new_thread, get_named_tuple, ObjectCache,\
	this_function_caller_name
import curses
import json
import requests
import time
import re
import string

__version__ = '0.1.6.1'
__author__ = 'clem'
DOCKER_HUB_URL = 'https://index.docker.io'

a_lock = Lock()


# clem 07/04/2016
class DaemonNotConnected(Exception):
	pass


# clem 07/04/2016
class CannotConnectToDaemon(DaemonNotConnected):
	pass


# clem 10/03/2016
class DockerVolume(object):
	path = ''
	mount_point = ''
	mode = ''

	def __init__(self, path, mount_point, mode='ro'):
		assert isinstance(path, basestring) and isinstance(mount_point, basestring) and\
			isinstance(mode, basestring)
		self.path = path
		self.mount_point = mount_point
		self.mode = mode

	# clem 15/03/2016
	def pretty_print(self):
		advanced_pretty_print(self.__dict__)

	# clem 14/03/2016
	def __str__(self):
		return '<DockerVolume %s:%s:%s>' % (self.mode, self.path, self.mount_point)

	# clem 08/04/2016
	def __repr__(self):
		return 'DockerVolume' + str((self.path, self.mount_point, self.mode))


# clem 10/03/2016
class DockerRun(object):
	image_full_name = ''
	_image = None
	cmd = ''
	_volumes = list()
	auto_rm = False
	container_given_name = ''
	created_container_id = ''
	created_container = None
	event_listener = None
	env = None

	# clem 11/03/2016
	@property
	def volumes(self):
		return self._volumes

	# _check_volumes deleted 14/03/2016 (last git commit 32844a2)
	# _check_if_volume_exists deleted 14/03/2016 (last git commit 32844a2)
	# _volume_exists deleted 14/03/2016 (last git commit 32844a2)

	def __init__(self, image_full_name_tag, cmd='', volumes=None, ev_listener=None, stream=False, auto_rm=False,
		env=None, cont_name=''):
		assert isinstance(image_full_name_tag, (DockerImage, basestring)) and isinstance(cmd, basestring) and\
			(volumes is None or isinstance(volumes, (list, DockerVolume))) and type(auto_rm) is bool and\
			(env is None or isinstance(env, dict)) and isinstance(cont_name, basestring)
		self.env = env
		self.container_given_name = re.compile('[\W]+').sub('', cont_name) if cont_name else ''
		self.image_full_name = image_full_name_tag
		self.cmd = cmd
		self.stream = stream # TODO #notImplemented
		self._volumes = volumes
		self.auto_rm = auto_rm
		self.event_listener = ev_listener

	# clem 17/03/2016
	def container_created(self, container):
		"""
		Take care of registering the event listener (if any) to the provided container
		:type container: DockerContainer
		"""
		# container._log('Container created')
		if isinstance(container, DockerContainer):
			self.created_container = container
			self.created_container_id = container.Id
			container.register_run(self)
			if self.event_listener and callable(self.event_listener):
				container.register_event_listener(self.event_listener)

	# clem 14/03/2016
	@property # renamed from config_dict on 28/11/2016
	def volume_dict(self):
		a_dict = dict()
		vol_list = self._volumes if isinstance(self._volumes, list) else [self._volumes]
		for each in vol_list:
			assert isinstance(each, DockerVolume)
			a_dict[each.path] = {
				'bind': each.mount_point,
				'mode': each.mode,
			}
		return a_dict
	
	# clem 28/11/2016
	@property
	def extra_host_dict(self):
		# TODO
		# host_conf = dict()
		a_host = 'breeze-db'
		a_addr = '10.0.0.4'
		host_conf = ['%s:%s' % (a_host, a_addr), ]
		return host_conf

	# clem 28/11/2016
	@property
	def config_dict(self):
		return {'binds': self.volume_dict, 'extra_hosts': self.extra_host_dict}

	# clem 16/03/2016
	@property # temp wrapper
	def image(self):
		if self._image:
			return self._image
		return self.image_full_name

	# temp wrapper
	def link_image(self, client=None):
		if self._image:
			return self._image
		elif isinstance(client, DockerClient):
			self._image = client.get_image(self.image_full_name)
			return self.link_image()
		return DockerImage({ 'RepoTags': self.image_full_name })

	# clem 15/03/2016
	def pretty_print(self):
		advanced_pretty_print(self.__dict__)

	# clem 08/04/2016
	def __str__(self):
		return '<DockerRun %s$%s:%s@%s>' % (self.image_full_name, self.cmd, self.volumes, self.event_listener)

	def __repr__(self):
		return 'DockerRun' + str((self.image, self.cmd, [self.volumes], self.event_listener, self.stream, self.auto_rm))


# clem 10/03/2016
class DockerRepo(object):
	# url = ''
	login = ''
	pwd = ''
	email = ''

	def __init__(self, login, pwd, email='', url=DOCKER_HUB_URL):
		try:
			assert isinstance(login, basestring) and isinstance(pwd, basestring) and isinstance(email, basestring) and \
			isinstance(url, basestring)
		except AssertionError as e:
			print 'CRITICAL : %s' % e
			print 'args: %s' % (str((login, pwd, email, url)))
		self.login = login
		self.pwd = pwd
		self.email = email
		self.url = url

	def __hash__(self):
		return (self.login + self.email + self.url).__hash__()

	def __str__(self):
		return '<DockerRepo %s>' % self.__hash__()


# clem 09/03/2016
class DockerImage(object):
	Created = 0
	Labels = dict()
	VirtualSize = 0
	ParentId = u''
	Size = 0
	RepoDigests = None
	Id = u''
	RepoTags = list()
	_sig = ''
	_repo = ''
	_name = ''
	_tag = ''

	def __init__(self, a_dict):
		assert isinstance(a_dict, dict)
		self.__dict__.update(a_dict)
		_ = self.sig

	def _get_sig(self):
		new_dict = self.__dict__
		if '_sig' in new_dict:
			new_dict.pop('_sig')
		return get_md5(str(new_dict))

	@property
	def sig(self):
		if not self._sig:
			self._sig = self._get_sig()
		return self._sig

	# clem 16/03/2016
	def _process_name(self):
		full_n = self.full_name
		if '/' in full_n:
			self._repo, rest = full_n.split('/', 1)
		else:
			self._repo, rest = 'library', full_n

		if ':' in rest:
			self._name, self._tag = rest.split(':', 1)
		else:
			self._name, self._tag = rest, ''

	# clem 16/03/2016
	@property
	def tag(self):
		if not self._tag:
			self._process_name()
		return self._tag

	# clem 16/03/2016
	@property
	def name(self):
		if not self._name:
			self._process_name()
		return self._name

	# clem 16/03/2016
	@property
	def repo_name(self):
		if not self._repo:
			self._process_name()
		return self._repo

	# clem 16/03/2016
	@property
	def repo_and_name(self):
		return '%s/%s' % (self.repo_name, self.name)

	# clem 10/03/2016
	@property
	def full_name(self):
		if type(self.RepoTags) is list and len(self.RepoTags) > 0:
			return str(self.RepoTags[0])
		else:
			return str(self.RepoTags)

	# clem 15/03/2016
	def pretty_print(self):
		advanced_pretty_print(self.__dict__)

	# clem 18/03/2016
	@property
	def textual(self):
		return self.full_name

	def __repr__(self):
		return '<DockerImage %s>' % self.textual

	# clem 10/03/2016
	def __str__(self):
		return self.Id


# clem 09/03/2016
class DockerContainer(object):

	RestartCount = 0
	Labels = dict()
	Image = ''
	NetworkSettings = dict()
	HostConfig = dict()
	State = dict()
	GraphDriver = dict()
	Config = dict()
	Status = u''
	ProcessLabel = u''
	Command = u''
	Created = u''
	LogPath = u''
	AppArmorProfile = u''
	HostsPath = u''
	ResolvConfPath = u''
	Id = u''
	Path = u''
	Driver = u''
	HostnamePath = u''
	MountLabel = u''
	Name = u''
	Names = list()
	Ports = list()
	Args = list()
	Mounts = list()
	_start_time = 0
	_end_time = 0
	_sig = u''
	_log = u''
	_event_list = list()
	_event_buffer = list()
	_event_listener = None
	_has_failed = False
	__run = None
	__client = None

	def __init__(self, a_dict, client=None, event_callback=None):
		assert not client or isinstance(client, DockerClient)
		self.__client = client
		self.__dict__.update(a_dict)
		# _ = self.get_image # CAUSES DEADLOCKING
		self.register_event_listener(event_callback)

	# clem 05/04/20196
	def _grab_logs(self):
		if self.__client:
			self._log = self.__client.logs(self.Id)

	# clem 05/04/2016
	def start(self, client=None):
		assert isinstance(client, DockerClient) or isinstance(self.__client, DockerClient)
		the_client = client or self.__client
		the_client.start(self)

	# clem 06/05/2016
	def pause(self, client=None):
		assert isinstance(client, DockerClient) or isinstance(self.__client, DockerClient)
		the_client = client or self.__client
		return the_client.pause(self)

	# clem 06/05/2016
	def resume(self, client=None):
		assert isinstance(client, DockerClient) or isinstance(self.__client, DockerClient)
		the_client = client or self.__client
		return the_client.unpause(self)

	# clem 06/05/2016
	def unpause(self, client=None):
		return self.resume(client)

	# clem 06/05/2016
	def stop(self, client=None):
		assert isinstance(client, DockerClient) or isinstance(self.__client, DockerClient)
		the_client = client or self.__client
		return the_client.stop(self)

	# clem 06/05/2016
	def kill(self, client=None):
		assert isinstance(client, DockerClient) or isinstance(self.__client, DockerClient)
		the_client = client or self.__client
		from signal import SIGTERM
		return the_client.kill(self, SIGTERM)

	# clem 08/04/2016
	def register_run(self, run_object):
		assert isinstance(run_object, DockerRun)
		self.__run = run_object

	# clem 15/03/2016
	def register_event_listener(self, listener, replace=False):
		# if listener and callable(listener):
		if not self._event_listener or replace:
			self._event_listener = new_thread(listener)
			# if there is any unprocessed events in the buffer
			while self._event_buffer:
				self._event_dispatcher(self._event_buffer.pop())

	# clem 16/03/2016
	@property
	def has_event_listener(self):
		return self._event_listener and callable(self._event_listener)

	# clem 05/04/2016
	# @new_thread
	def _event_dispatcher(self, event):
		if self.has_event_listener:
			self._event_list.append(event)
			self._event_listener(event)
		else:
			# if no event listener is registered, we save the event.
			# if and once one got registered, all the buffered events will be processed
			self._event_buffer.append(event)

	# clem 11/04/2016
	def remove_container(self, force=True):
		self._grab_logs()
		if self.__run and self.__client:
				self.__client.rm(self, force=force)

	# clem 15/03/2016
	@new_thread
	def new_event(self, event):
		self._event_dispatcher(event)
		if event.description == DockerEventCategories.DIE:
			self._end_time = event.dt
			self._grab_logs()
			if self.__run and self.__run.auto_rm:
				self.remove_container()
		if event.description == DockerEventCategories.CREATE:
			# self.start()
			pass
		elif event.description == DockerEventCategories.START:
			self._start_time = event.dt

	# clem 11/04/2016
	@property
	def total_run_time(self):
		""" Return the current / total running time of the container

		:return: time delta since container started
		"""
		if self._start_time:
			end_time = self._end_time if self._end_time else datetime.utcnow() # FIXME not time-zone aware
			return end_time - self._start_time
		return 0 # FIXME should be a dt object

	# clem 25/05/2016
	@property
	def time_since_creation(self):
		""" Return the current time since creation of the container

		:return: time delta since container was created
		"""
		return datetime.utcnow() - self.dt_created # FIXME not time-zone aware

	# clem 11/04/2016
	@property
	def delta_display(self):
		d = self.total_run_time
		if d:
			return '+%.03fs' % self.total_run_time.total_seconds()
		return ''

	# clem 18/03/2016
	@property
	def last_event(self):
		return self._event_list[-1]

	# clem 15/03/2016
	@property
	def logs(self):
		if not self._log:
			self._grab_logs()
		return self._log

	# clem 18/03/2016
	@property
	def get_image(self):
		if self.Image and isinstance(self.Image, DockerImage):
			return self.Image
		else:
			if not self.Image and self.Config and 'Image' in self.Config:
				self.Image = self.Config.get('Image', '')
			if self.__client:
				self.Image = self.__client.get_image(self.Image)
				return self.Image

	# clem 08/04/2016
	@property
	def short_id(self):
		return self.Id[0:12]

	# clem 14/03/2016
	@property
	def name(self):
		if self.Names and len(self.Names) > 0:
			return self.Names[0]
		elif self.Name:
			return self.Name
		else:
			return self.short_id

	# clem 15/03/2016
	def pretty_print(self):
		advanced_pretty_print(self.__dict__)

	# clem 18/03/2016
	@property
	def textual(self):
		return self.name

	# clem 08/04/2016
	def get_status(self):
		return get_named_tuple('ContainerState', self.State)

	# clem 08/04/2016
	@property
	def status_obj(self):
		return self.get_status()

	# clem 25/05/2016
	@property
	def dt_created(self):
		from datetime import datetime
		return datetime.strptime(self.Created[:26], '%Y-%m-%dT%H:%M:%S.%f') # "2016-05-25T11:53:46.860873042Z"

	# clem 25/05/2016
	@property
	def status_text(self):
		return str(self.status_obj.Status)

	# clem 08/04/2016
	@property
	def is_running(self):
		return self.status_obj.Running

	# clem 08/04/2016
	@property
	def is_dead(self):
		return self.status_obj.Dead

	# clem 08/04/2016
	@property
	def is_paused(self):
		return self.status_obj.Paused

	# clem 08/04/2016
	@property
	def is_restarting(self):
		return self.status_obj.Restarting
	
	# clem 21/10/2016
	@property
	def exit_code(self):
		return int(self.status_obj.ExitCode)
	
	# clem 21/10/2016
	@property
	def has_normal_exit(self):
		return self.exit_code == 0 and (self.is_dead or not self.is_running)
	
	# clem 21/10/2016
	@property
	def has_failed(self):
		self._has_failed = self._has_failed or\
			((not self.is_running or self.is_dead or self.is_restarting) and self.exit_code != 0)
		return self._has_failed

	# clem 18/03/2016
	def __nonzero__(self):
		return bool(self.Id)

	def __str__(self):
		return self.Id

	def __repr__(self):
		return '<DockerContainer %s>' % self.textual


# clem 15/03/2016
class DockerEventCategories(object):
	CREATE = 's:create'
	START = 's:start'
	DIE = 's:die'
	KILL = 's:kill'
	PAUSE = 's:pause'
	UNPAUSE = 's:unpause'
	DELETE = 's:delete'
	DESTROY = 's:destroy'
	UNTAG = 's:untag'
	TAG = 's:tag'
	PULL = 's:pull'
	CONNECT = 'A:connect'
	DISCONNECT = 'A:disconnect'
	MOUNT = 'A:mount'
	UNMOUNT = 'A:unmount'
	RESTART = 'A:restart'
	UNKNOWN = ''

	a_dict = { CREATE: CREATE, START: START, DIE: DIE, KILL: KILL, PAUSE: PAUSE, UNPAUSE: UNPAUSE, CONNECT: CONNECT,
				DISCONNECT: DISCONNECT, MOUNT: MOUNT, UNMOUNT: UNMOUNT, RESTART: RESTART}

	def __init__(self):
		pass


# clem 14/03/2016
class DockerEvent(object):
	status = u''
	Action = u''
	Type = u''
	id = u''
	# from = u''
	timeNano = int()
	time = int()
	Actor = dict()
	_container = None
	__client = None

	def __init__(self, a_dict, client=None):
		assert isinstance(a_dict, (dict, str)) and (not client or isinstance(client, DockerClient))
		if type(a_dict) is str:
			import json
			a_dict = json.loads(a_dict)
		self.__dict__.update(a_dict)
		# if client: # if we got a client in argument, we chain this container to its DockerImage object
		self.__client = client
		# self.get_container() # we''ll do it upon access, as this container might not yet be in the ps list

	# clem 16/03/2016 # FIXME : very slow
	def _attach_container(self, res_id):
		if self.__client:
			self._container = self.__client.get_container(res_id)
		return self._container

	# FIXME : very slow
	def get_container(self, no_update=False):
		if not no_update and (not self._container or not self._container.name):
			# if not a container or container has no name, refresh
			if self.Type == 'container':
				try:
					return self._attach_container(self.res_id)
				except NotFound:
					pass
			elif 'Attributes' in self.Actor and 'container' in self.Actor['Attributes']:
				return self._attach_container(self.Actor['Attributes']['container'])
			return self.res_id
		if not self._container:
			return self.short_id
		return self._container

	@property
	def container(self):
		return self.get_container()

	@property
	def res_id(self):
		ret = ''
		if self.id:
			ret = self.id
		elif self.Type == 'container':
			ret = self.Actor['Attributes']['container']
		return ret

	# clem 08/04/2016
	@property
	def short_id(self):
		return self.res_id[0:12]

	# clem 16/03/2016
	@property
	def _get_resource(self):
		if self.Type == 'container':
			return self.container
		return self.res_id

	# clem 15/03/2016
	@property
	def dt(self):
		from datetime import datetime
		secs = float(self.timeNano / 1e9)
		return datetime.fromtimestamp(secs)

	# clem 15/03/2016
	@property
	def dt_formatted(self):
		return self.dt.strftime('%Y-%m-%dT%Hh%M:%S.%f')

	# clem 15/03/2016
	@property
	def date_formatted(self):
		return self.dt.strftime('%Y-%m-%d')

	# clem 15/03/2016
	@property
	def time_formatted(self):
		return self.dt.strftime('%Hh%M:%S.%f')

	# clem 15/03/2016
	@property
	def now(self):
		from datetime import datetime
		return datetime.now().strftime('%Hh%M:%S.%f')

	# clem 05/04/2016
	@property
	def delta(self):
		from datetime import datetime
		delta = datetime.now() - self.dt
		return '+%.03fs' % delta.total_seconds()

	# clem 15/03/2016
	def pretty_print(self):
		advanced_pretty_print(self.__dict__)

	# clem 15/03/2016
	@property
	def description(self):
		return 's:%s' % self.status if self.status else 'A:%s' % self.Action

	# clem 15/03/2016
	@property
	def category(self):
		desc = self.description
		return DockerEventCategories.a_dict.get(desc, DockerEventCategories.UNKNOWN)

	# TODO rewrite / re-design
	def __str__(self):
		cont_title = self.get_container(True)
		if cont_title:
			if isinstance(cont_title, DockerContainer):
				cont_title = cont_title.name
		else:
			cont_title = self.short_id
		return u'%s [%s] %s %s [%s]' % (cont_title, self.time_formatted, self.Type, self.description, self.delta)

	def __repr__(self):
		txt = 's:%s' % self.status if self.status else 'A:%s' % self.Action
		return '<DockerEvent [%s] %s %s>' % (self.timeNano, self.Type, txt)


# clem 31/03/2016
class DockerInfo(object):
	ContainersPaused = 0
	Labels = None
	ContainersRunning = 0
	NGoroutines = 0
	LoggingDriver = u''
	OSType = u''
	HttpProxy = u''
	DriverStatus = list()
	OperatingSystem = u''
	Containers = 0
	HttpsProxy = u''
	BridgeNfIp6tables = False
	MemTotal = 0
	Driver = u''
	IndexServerAddress = u''
	ClusterStore = u''
	InitPath = u''
	ExecutionDriver = u''
	SystemStatus = None
	OomKillDisable = False
	ClusterAdvertise = u''
	SystemTime = u''
	Name = u''
	CPUSet = False
	RegistryConfig = dict()
	ContainersStopped = 0
	NCPU = 0
	NFd = 0
	Architecture = u''
	CpuCfsQuota = False
	Debug = False
	ID = u''
	IPv4Forwarding = False
	KernelVersion = u''
	BridgeNfIptables = False
	NoProxy = u''
	InitSha1 = u''
	ServerVersion = u''
	CpuCfsPeriod = False
	ExperimentalBuild = False
	MemoryLimit = False
	SwapLimit = False
	Plugins = dict()
	Images = 0
	DockerRootDir = u''
	NEventsListener = 0
	CPUShares = False

	def __init__(self, a_dict):
		assert isinstance(a_dict, (dict, str))
		if type(a_dict) is str:
			a_dict = json.loads(a_dict)
		self.__dict__.update(a_dict)

	def summary(self):
		from utilz import human_readable_byte_size, UnitSystem
		return 'Docker daemon at "%s" running on (%s %s %s) %s\n' %\
			(self.Name, self.Architecture, self.OSType, self.KernelVersion, self.OperatingSystem) + \
			'Containers :\n' \
			'\ttotal: %s\n' % self.Containers + \
			'\tstopped: %s\n' % self.ContainersStopped + \
			'\tpaused: %s\n' % self.ContainersPaused + \
			'\trunning: %s\n' % self.ContainersRunning + \
			'Images: %s\n' % self.Images + \
			'nCPUs: %s\n' % self.NCPU + \
			'memTotal: %s\n' % human_readable_byte_size(self.MemTotal, unit=UnitSystem.alternative) + \
			'version: %s' % self.ServerVersion

	# clem 05/04/2016
	def dump(self):
		return self.__dict__

	# clem 05/04/2016
	def __str__(self):
		return self.summary()

	def __repr__(self):
		return '<%s %s %s/%s>' % (str.rpartition(str(self.__class__), '.')[2], self.SystemTime, self.ContainersRunning,
		self.Containers)


# clem 29/03/2016
class TermStreamer(object):
	"""
	use "with TermStreamer() as stream:" instantiation method rather than direct instantiation
	"""
	stdscr = None

	class ProgressObj(object):
		_done = None
		_total = None
		_progress = None
		text = ''

		def __init__(self, text, done=None, total=None, progress=None):
			assert ((done, total) is not (None, None) and done <= total) or\
				(progress is not None and progress in range(0, 100))
			self.text = text
			self._done = done
			self._total = total
			self._progress = progress

		@property
		def progress(self):
			if not self._progress:
				self._progress = float(self._done) / float(self._total) * 100
			return self._progress

		def __str__(self):
			return "{1} [{2:10}] {0:.2%}".format((self.progress / 100), self.text, "#" * int(self.progress // 10))

	def __init__(self):
		self._start()

	def __enter__(self):
		self._start()
		return self

	@property
	def _term_is_ok(self):
		import os
		return str(os.environ.get("TERM", "unknown")) != 'emacs'

	def _start(self):
		if not self.stdscr and self._term_is_ok:
			self.stdscr = curses.initscr()
			curses.noecho()
			curses.cbreak()

	def __exit__(self, *_):
		if self.stdscr and self._term_is_ok:
			try:
				curses.echo()
				curses.nocbreak()
				curses.endwin()
			except Exception:
				pass

	def __delete__(self, _):
		self.__exit__()

	def close(self):
		self.__exit__()

	@classmethod
	def _legacy_term_stream(self, a_dict):
		import sys
		import os
		os.system('clear')
		for value in a_dict.itervalues():
			sys.stdout.write('%s\n' % value)
			sys.stdout.flush()  # As suggested by Rom Ruben

	# inspired from http://stackoverflow.com/a/6840469/5094389
	def full_write(self, a_dict):
		from _curses import error
		if not self.stdscr:
			return self._legacy_term_stream(a_dict)
		i = 0
		try:
			for value in a_dict.itervalues():
				i += 1
				self.stdscr.addstr(i, 0, str(value).ljust(80))
		except error:
			pass
		self.stdscr.refresh()


# clem 08/03/2016
class DockerClient(object):
	RAISE_ERR = False
	DEV = False
	DEBUG = True
	repo = None
	_raw_cli = DockerApiClient
	_logged_in = False
	__console_mutex = None # use to ensure exclusive access to console
	__data_mutex = None # use to ensure exclusive access to console

	_daemon_url = ''

	_images_list = list()
	__image_dict_by_id = dict()
	__image_dict_by_tag = dict()
	__image_tree = dict()
	__watcher = None
	_container_list = list()
	_container_dict_by_id = dict()
	_container_dict_by_name = dict()
	_event_list = list()
	_run_wait = 0
	_run_dict = dict()
	_destroyed_objects = dict()
	_last_connection = ''

	#
	# CLASS MANAGEMENT
	#

	def __init__(self, daemon_url, repo=None, auto_connect=True, auto_watcher=True):
		assert isinstance(daemon_url, basestring)
		if repo:
			assert isinstance(repo, DockerRepo)
			self.repo = repo
		self._daemon_url = daemon_url
		self.__connect_to_daemon(auto_connect, auto_watcher)

	# clem 14/03/2016
	def __cleanup(self):
		if self.__watcher:
			if self.__watcher:
				self._force_log('clearing watcher')
				del self.__watcher # GC
				self.__watcher = None

	# clem 14/03/2016
	def __del__(self):
		self.__cleanup()

	# clem 14/03/2016
	def __delete__(self, _):
		self.__cleanup()

	# clem 14/03/2016
	def __exit__(self, *_):
		self.__cleanup()

	# clem 16/05/2016
	def __repr__(self):
		return '<%s@%s>' % (self.__class__.__name__, hex(id(self)))

	# clem 31/03/2016
	@property
	def _console_mutex(self):
		if not self.__console_mutex:
			self.__console_mutex = Lock()
		return self.__console_mutex

	# clem 31/03/2016
	@property
	def _data_mutex(self):
		if not self.__data_mutex:
			self.__data_mutex = Lock()
		return self.__data_mutex

	# clem 17/03/2016
	def _auto_raise(self, e, force=False):
		if self.RAISE_ERR or force:
			raise e

	# clem 17/03/2016
	def _exception_handler(self, e, msg='', force_log=False, force_raise=False):
		msg = '%s:%s' % (type(e), str(e)) if not msg else str(msg)
		msg = TermColoring.warning('ERR in %s: %s' % (this_function_caller_name(), msg))
		self._force_log(msg) if force_log else self._log(msg)
		self._auto_raise(e, force_raise)

	#
	# LOGGING
	#

	# clem 01/04/2016
	def write_log_entry(self, text):
		self._log(text)

	# clem 10/03/2016
	def _log(self, obj, force_print=False, sup_text='', direct=False):
		if self.DEBUG or force_print:
			if type(obj) is dict:
				if direct:
					advanced_pretty_print(obj)
				else:
					with self._console_mutex:
						advanced_pretty_print(obj)
			else:
				if direct:
					print str(obj) + str(sup_text)
				else:
					with self._console_mutex:
						print str(obj) + str(sup_text)
		# TODO log

	# clem 10/03/2016
	def _json_log(self, obj, force_print=False):
		self._log(self._json_parse(obj), force_print)

	# clem 10/03/2016
	def _force_log(self, obj, sup_text=''):
		if type(obj) is str:
			obj = TermColoring.bold(obj)
		self._log(obj, True, sup_text)

	# clem 16/03/2016
	@classmethod
	def _json_parse(self, obj):
		if type(obj) is str:
			try:
				obj = json.loads(obj)
			except ValueError:
				pass
		return obj

	# clem 14/03/2016
	def _event_log(self, obj, sup_text=''):
		self._force_log(self._json_parse(obj), str(sup_text))

	#
	# INTERNALS
	#

	# clem 05/04/2016
	def __connect_to_daemon(self, auto_login=False, auto_watcher=True):
		try:
			if self._last_connection != 'failed':
				self._log('Connecting to docker daemon at %s ...' % self._daemon_url)
				self._raw_cli = DockerApiClient(base_url=self._daemon_url)
				self._raw_cli.info()
				if auto_watcher:
					self._start_event_watcher()
				if auto_login:
					self.login()
		except requests.exceptions.ConnectionError as e:
			self._force_log(TermColoring.fail('FATAL: Connection to docker daemon failed'))
			self._last_connection = 'failed'
			self._raw_cli = None
			self._exception_handler(e)

	# clem 08/04/2016
	@property
	def __connection_state(self):
		return bool(self._raw_cli)

	# clem 29/03/2016
	@property
	def __connected(self):
		if not self.__connection_state:
			try:
				from time import sleep
				self.__connect_to_daemon()
			except Exception:
				raise CannotConnectToDaemon
		return self.__connection_state

	# __pp_cli removed on 19/05/2016 from azure_test / commit 3ae8f9d

	# clem 01/04/2016
	@classmethod
	def _time_stamp(self):
		from datetime import datetime
		return datetime.now()

	# clem 01/04/2016
	@classmethod
	def _readable_time(self, dt):
		return dt.strftime('%Hh%M:%S.%f')

	# clem 01/04/2016
	@property
	def _readable_time_stamp(self):
		return self._readable_time(self._time_stamp())

	# _term_stream removed 29/03/2016 from 7398ad0 (replaced with class TermStreamer)

	# clem 16/03/2016
	def _img_exists_or_pulled(self, run):
		"""
		check if image exists locally, and pull it if not
		Return True if image exists, or pulled successfully, False otherwise

		@params:
			run  - Required  : current iteration (DockerRun)
		@return: True if image exists, or pulled successfully, False otherwise
		@rtype: bool
		"""
		# TODO check if connected to repo
		image_name = run.image_full_name
		if not isinstance(run.image, DockerImage) and image_name not in self.images_by_repo_tag:
			# image not found, let's try to pull it
			img = run.link_image(self)
			self._log('Unable to find image \'%s\' locally, let\'s try pulling it...' % image_name)
			return self.pull(img.repo_and_name, img.tag)
		return True

	# clem 17/03/2016
	def __error_managed(func):
		""" Error management wrapper for _run and _start

		:type func: function
		:rtype: function
		"""

		def decorated_func(self, arg):
			assert isinstance(self, DockerClient) and isinstance(arg, (DockerRun, DockerContainer))
			msg = 'creation' if isinstance(arg, DockerRun) else 'start'
			try:
				if isinstance(arg, DockerRun):
					return func(self, arg)
				elif isinstance(arg, DockerContainer):
					return func(self, arg)
			except NotFound as e:
				self._exception_handler(e, '%s: %s' % (msg, str(e)))
			except APIError as e:
				# self._log('Container %s failed : %s' % (msg, e))
				self._log('Container %s failed : %s [%s]' % (msg, e, self._readable_time_stamp))
				if self.DEV and isinstance(arg, DockerContainer): # FIXME dev code
					out_log = self.logs(arg.Id)
					if out_log:
						self._log('Container run log :\n%s' % advanced_pretty_print(out_log, get_output=True))
				self._auto_raise(e)
			except NullResource as e:
				self._exception_handler(e, '%s: %s' % (msg, e))
			except Exception as e:
				self._exception_handler(e, 'Unhandled %s exception : %s' % (msg, e))

		return decorated_func

	_error_managed = staticmethod(__error_managed)

	# clem 28/11/2016
	def _host_config_dict(self, run_instance):
		assert isinstance(run_instance, DockerRun)
		return self.cli.create_host_config(**run_instance.config_dict)

	# clem 09/03/2016
	@_error_managed.__func__
	def _run(self, run):
		"""
		TBD

		:type run: DockerRun
		:rtype: DockerContainer
		"""
		assert isinstance(run, DockerRun)

		image_name = str(run.image_full_name)
		# check if image exists locally, and pull it if not
		if not self._img_exists_or_pulled(run): # if pulled failed
			return None

		host_conf = self._host_config_dict(run)
		
		kwargs = {
			'volumes'    : run.volume_dict.keys(),
			'environment': run.env,
			'host_config': host_conf,
		}
		
		# container name
		name_str = ''
		if run.container_given_name:
			kwargs.update({'name' : run.container_given_name })
			name_str = '--name %s ' % kwargs['name']
		
		self._log('docker run %s %s %s-e %s\n%s' % (image_name, run.cmd, name_str, run.env, str(host_conf)))
		
		# Create the container
		container = self.get_container(self.cli.create_container(image_name, run.cmd, **kwargs)['Id'])
		if container: # container was successfully created and acquired
			run.container_created(container)
			return container
		# If you are not in detached mode:
		# Attach to the container, using logs=1 (to have stdout and stderr from the container's start) and stream=1
		# If in detached mode or only stdin is attached, display the container's id.

	# clem 17/03/2016
	@new_thread
	@_error_managed.__func__
	def _start(self, container):
		"""
		:type container: basestring | DockerContainer
		:rtype: None
		"""
		assert isinstance(container, DockerContainer)
		self.cli.start(str(container))

	# clem 17/03/2016
	def _inspect_container(self, container_desc):
		""" Get all the refreshed raw information about the container

		:type container_desc: basestring
		:rtype: str
		"""
		try:
			return self.cli.inspect_container(container_desc)
		except (NotFound, APIError) as e:
			if this_function_caller_name() != self._update_container_data.im_func.__name__:
				self._exception_handler(e)
		except Exception as e:
			self._exception_handler(e)
		return dict()

	# clem 17/03/2016
	def _make_container(self, container_desc):
		""" Return a new DockerContainer object, from a container_id

		:type container_desc: basestring
		:rtype: DockerContainer
		"""
		return DockerContainer(self._inspect_container(container_desc), self)

	# clem 18/03/2016
	def _update_container_data(self, container):
		assert isinstance(container, DockerContainer)
		container.__dict__.update(self._inspect_container(str(container)))
		return container

	# clem 17/03/2016
	def _get_container(self, container_desc):
		"""
		Check if container in cache, if so return its object update with self._inspect_container,
		if not it is created self.make_container and store it in the dict

		:type container_desc: basestring
		:rtype: DockerContainer
		"""
		with self._data_mutex: # solves concurrency issues with event_manager
			container_desc = str(container_desc)
			if container_desc in self._container_dict_by_id.keys():
				# self._log('%s in id' % container_desc)
				container = self._update_container_data(self._container_dict_by_id[container_desc])
			else:
				cont_names = self._get_containers_by_name(self._container_dict_by_id)
				if container_desc in cont_names.keys():
					container = self._update_container_data(cont_names[container_desc])
				else:
					container = self._make_container(container_desc)

			self._container_dict_by_id[container.Id] = container
		return container

	#
	# CLASS INTERFACE
	#

	# clem 09/03/2016
	@property
	def cli(self):
		"""

		:return: the docker client API direct command line interface
		:rtype: DockerApiClient
		"""
		if self.__connected: # system wide check for active connection
			return self._raw_cli
		else:
			self._auto_raise(DaemonNotConnected('Cannot use cli as Docker daemon is not connected'), True)

	# run_default removed 18/03/2016 from commit bc9d5d3

	# clem 09/03/2016
	def img_run(self, img_name_tag, command, volume_list=list()):
		""" TBD

		:type img_name_tag: str
		:type command: str
		:type volume_list: DockerVolume|list
		:rtype:
		"""
		return self._run(DockerRun(img_name_tag, command, volume_list))

	# clem 14/03/2016
	def get_container(self, container_id=None):
		""" Refresh the cached container list, and return the cached container

		:type container_id: str
		:rtype: DockerContainer
		"""
		if container_id:
			time.sleep(.5)
			_ = self.containers_by_id # refresh cache
			return self._get_container(container_id)
		return None

	# clem 16/03/2016
	def get_image(self, image_descriptor=None):
		"""
		Get the cached image, and if not found try to refresh the cache for this entry only
		image_descriptor can be either the id, or the full name as repo/image:tag

		:type image_descriptor: str | DockerImage | None
		:rtype: DockerImage | None
		"""
		if image_descriptor:
			image_descriptor = str(image_descriptor)
			images_ids = self.images_by_id
			images_tags = self._get_images_by_repo_tag(images_ids) # call the sub-method to save time
			if image_descriptor in images_ids.keys():
				return images_ids.get(image_descriptor)
			elif image_descriptor in images_tags.keys():
				return images_tags.get(image_descriptor)
		return None

	# clem 18/03/2016
	def get_resource(self, res_id):
		img = self.get_image(res_id)
		if img:
			return img
		cont = self._get_container(res_id)
		if cont:
			return cont

	# clem 18/03/2016
	def remove_resource(self, res_id, force=False):
		res_id = self.get_resource(res_id)
		if isinstance(res_id, DockerContainer):
			self.rm([res_id], force=force)
		elif isinstance(res_id, DockerImage):
			self.rmi([res_id], force=force)

	# clem 31/03/2016
	# def show_info(self):
	# 	print self.info()

	#
	# DOCKER CLIENT MAPPINGS
	#

	# clem 07/04/2016
	def close(self):
		self.__cleanup()
		del self

	# clem 06/05/2016
	def stop(self, container, timeout=10):
		try:
			self.cli.stop(str(container), timeout)
			return True
		except Exception as e:
			self._exception_handler(e)
		return False

	# clem 12/05/2016
	def start(self, container):
		self._start(container)

	# clem 06/05/2016
	def pause(self, container):
		try:
			self.cli.pause(str(container))
			return True
		except Exception as e:
			self._exception_handler(e)
		return False

	# clem 06/05/2016
	def unpause(self, container):
		try:
			self.cli.unpause(str(container))
			return True
		except Exception as e:
			self._exception_handler(e)
		return False

	# clem 06/05/2016
	# Alias of unpause
	def resume(self, container):
		self.unpause(container)

	# clem 06/05/2016
	def kill(self, container, signal):
		try:
			self.cli.kill(str(container), signal)
			return True
		except Exception as e:
			self._exception_handler(e)

	# clem 18/03/2016
	def run(self, run_obj):
		""" Run interface

		:type run_obj: DockerRun
		:rtype: DockerContainer
		"""
		return self._run(run_obj)

	# clem 10/03/2016
	def login(self):
		if self.repo:
			if not self._logged_in:
				try:
					self._log('Login as %s to %s ...' % (self.repo.login, self.repo.url))
					result = self.cli.login(self.repo.login, self.repo.pwd, self.repo.email, self.repo.url)
					self._log(result)
					self._logged_in = 'username' in result or result[u'Status'] == u'Login Succeeded'
				except APIError as e:
					self._exception_handler(e)
				except Exception as e:
					self._exception_handler(e, 'Unable to connect : %s' % e)
			return self._logged_in
		return False

	# clem 17/03/2016
	def rm(self, container_list, v=False, link=False, force=False):
		""" Removes a list of containers, designated by name or Id

		:type container_list: list | DockerContainer | basestring
		:type v: bool
		:type link: bool
		:type force: bool
		:rtype: None
		"""
		if not isinstance(container_list, list):
			container_list = [container_list]
		try:
			assert isinstance(container_list, list) # bug-fix for PyCharm code assistance
			for container in container_list:
				self._log('docker rm %s%s%s%s' % ('-v ' if v else '', '', '--force ' if force else '',
				str(container)))
				self.cli.remove_container(str(container), v, link, force)
			return True
		except Exception as e:
			self._exception_handler(e)
		return None

	# clem 16/03/2016
	def rmi(self, image_list, force=False):
		""" Removes a list of images, designated by tag or Id

		:type image_list: list | basestring
		:type force: bool
		:rtype: None
		"""
		if not isinstance(image_list, list):
			image_list = [image_list]
		try:
			assert isinstance(image_list, list) # bug-fix for PyCharm code assistance
			for image in image_list:
				self.cli.remove_image(str(image), force)
			return True
		except Exception as e:
			self._exception_handler(e)
		return None

	# clem 16/03/2016
	def pull(self, image_name, tag=''):
		def printer(generator):
			a_dict = dict()
			count = 0
			if generator:
				with TermStreamer() as stream:
					for line in generator:
						obj = self._json_parse(line)
						if 'status' in obj:
							status = ''
							progress = obj.get('progressDetail', None)
							if progress and 'current' in progress and 'total' in progress:
								txt = '%s: %s' % (obj['id'], obj['status'])
								status = TermStreamer.ProgressObj(txt, float(progress['current']), float(progress['total']))
							elif 'id' in obj:
								status = '%s: %s' % (obj['id'], obj['status'])
							a_dict.update({ obj.get('id', count): status })
						elif 'error' in obj:
							stream.close()
							self._log(str(obj['error']))
							return False
						stream.full_write(a_dict)
						count += 1
					return True
			return False

		# TODO : parse full images_names
		if not tag:
			tag = 'latest'
		try:
			self.login()
			# do_stream = self.DEBUG or force_print
			do_stream = False
			gen = self.cli.pull(image_name, tag, stream=do_stream)
			if do_stream:
				return printer(gen)
			return True
		except KeyboardInterrupt as e:
			self._exception_handler(e)
		except Exception as e:
			self._exception_handler(e)
		return False

	# clem 17/03/2016
	def logs(self, container):
		try:
			return self.cli.logs(str(container))
		except Exception as e:
			self._exception_handler(e, 'cli.logs: %s' % e)
		return ''

	# clem 10/03/2016 # TODO #notImplemented
	def ps(self):
		"""
		Params:

		quiet (bool): Only display numeric Ids
		all (bool): Show all containers. Only running containers are shown by default
		trunc (bool): Truncate output
		latest (bool): Show only the latest created container, include non-running ones.
		since (str): Show only containers created since Id or Name, include non-running ones
		before (str): Show only container created before Id or Name, include non-running ones
		limit (int): Show limit last created containers, include non-running ones
		size (bool): Display sizes
		filters (dict): Filters to be processed on the image list. Available filters:
		exited (int): Only containers with specified exit code
		status (str): One of restarting, running, paused, exited
		label (str): format either "key" or "key=value"
		"""
		pass

	#
	# EVENTS LISTENER, PROCESSOR AND DISPATCHER
	#

	# clem 14/03/2016
	def _start_event_watcher(self):
		# if watcher not yet started, start it in a new Thread
		if not self.__watcher or (isinstance(self.__watcher, Thread) and not self.__watcher.is_alive):
			if self.__connected:
				self.__watcher = Thread(target=self._event_watcher)
				self._log('starting event watcher as Thread')
				self.__watcher.start()
			else:
				self._force_log('Watcher wont start because there is no active docker daemon connection.')
		else:
			self._force_log('Watcher wont start because there is already a registered event watcher.')

	# clem 29/03/2016
	def _restart_event_watcher(self):
		"""
		The only purpose of this function is to delay in a non blocking way the watcher restart, so that the error
		message related to watcher can be displayed, before-hand, and an exception eventually raised, while still
		triggering its restart.
		"""

		@new_thread
		def delayed_starter():
			time.sleep(2)
			self._start_event_watcher()

		self.__watcher = None
		delayed_starter()
		return True

	# clem 16/03/2016
	def _del_res(self, a_dict, res_id):
		""" Delete res_id from a_dict with error handling

		:type a_dict: dict
		:type res_id: basestring
		:rtype: None
		"""
		from copy import copy
		assert isinstance(a_dict, dict)
		try:
			if res_id in a_dict:
				with self._data_mutex:
					self._destroyed_objects[res_id] = copy(a_dict[res_id])
					del a_dict[res_id]
		except Exception as e:
			self._exception_handler(e)

	# TODO : REDESIGN
	# clem 16/03/2016
	def _process_event(self, event, container=None):
		assert isinstance(event, DockerEvent)
		self._event_list.append(event)

		if event.description != DockerEventCategories.DELETE:
			if event.Type == 'image':
				pass
			elif event.Type == 'container':
				pass
		if event.description == DockerEventCategories.DELETE:
			if event.Type == 'image':
				self._del_res(self.__image_dict_by_id, event.res_id )
			elif event.Type == 'container':
				self._dispatch_event(event, container) # manual dispach for antecedance
				self._del_res(self._container_dict_by_id, event.res_id)
				return False
		if event.description == DockerEventCategories.DIE:
			pass
			# self._log('%s died' % container)
			# event.container.
			# check destroy
		if event.description == DockerEventCategories.DESTROY:
			if event.Type == 'container':
				self._dispatch_event(event, container) # manual dispach for antecedance
				self._del_res(self._container_dict_by_id, event.res_id)
				return False
		return True

	# clem 16/03/2016
	# TODO : REDESIGN
	# @new_thread
	def _dispatch_event(self, event, cont=None):
		assert isinstance(event, DockerEvent)
		# cont = event.container(True)
		# TODO add any resources
		if cont and isinstance(cont, DockerContainer):
			if not cont.has_event_listener:
				# if dispatch target exists but don't capture events, then we log it here
				self._event_log(event, ' <UE>')
			cont.new_event(event)
		else: # if no dispatch target exists, then we log it here
			# print cont, 'of type', type(cont)
			self._log('<%s> (no related containers, i.e. external event)' % event)

	# clem 16/03/2016
	# TODO : REDESIGN
	# @new_thread
	def _new_event(self, event_literal):
		event = DockerEvent(event_literal, self)
		cont = event.get_container(True) # get rel. container, with no refresh (the container might not exist anymore)
		# process the event (for example removing object from image or container dict)
		if self._process_event(event, cont):
			cont = event.get_container() # the container has not been deleted / destroy we update it's data
			# dispatch the event to the related container
			self._dispatch_event(event, cont)

	# clem 14/03/2016
	def _event_watcher(self):
		"""
		Blocking procedure to receive events
		MUST RUN IN A SEPARATE THREAD

		:rtype: None
		"""
		try:
			self._log('Event watcher started')
			for event in self.cli.events(): # Generator, do no run code in here, but rather in _new_event for non blocking
				if self.DEV: # FIXME dev code
					self._event_log(DockerEvent(event), ' <RT>')
				self._new_event(event)
		except requests.exceptions.ConnectionError as e:
			self._exception_handler(e, 'Starting event watcher failed: %s' % e)
		# except requests.packages.urllib3.
		except requests.packages.urllib3.exceptions.ProtocolError as e:
			self._raw_cli = None
			self._exception_handler(e, 'Lost connection to docker daemon: %s' % e)
		except IndexError as e:
			self._exception_handler(e, 'Unusual behavior: %s' % e)
		except Exception as e:
			# let'as try to restart it
			self._restart_event_watcher()
			self._exception_handler(e, 'Event watcher failed: %s' % e, force_raise=True)

	#
	# CONTAINERS DATA OBJECT MANAGEMENT AND INTERFACE
	#

	# clem 10/03/2016
	@property
	def containers_by_id(self, show_all=False):
		"""
		a dictionary of DockerContainer objects indexed by Id
		internally containers lists is stored in a dict indexed with containers' Ids.
		Each time this property is used the dict is refreshed by calling 'docker containers'
		DockerContainer objects from the cache dict are altered only if container entry changed.
		DockerContainer objects stores an internal md5 of its dictionary so that a modified container (invariant Id)
			will be updated
		similar to images_by_id()

		:type show_all: bool
		:rtype: dict(DockerContainer.Id: DockerContainer)
		"""
		try:
			containers = self.cli.containers(all=show_all)
			for e in containers: # retrieve, updates, or create the container object
				self._get_container(e.get('Id'))
			return self._container_dict_by_id
		except KeyError as e:
			self._exception_handler(e)
		except NotFound as e:
			self._exception_handler(e)

	# _init_containers_cache removed 05/04/2016 from commit 825f312

	# clem 17/03/2016
	def _get_containers_list(self, container_ids):
		""" extracts all DockerContainer objects from containers_by_id to return a list of them

		:type container_ids: dict
		:rtype: list(DockerContainer.Id: DockerContainer, )
		"""
		assert isinstance(container_ids, dict)
		self._container_list = list()
		for container in container_ids.itervalues():
			self._container_list.append(container)
		return self._container_list

	# clem 10/03/2016
	@property
	def containers_list(self):
		""" extracts all DockerContainer objects from containers_by_id to return a list of them

		:rtype: list(DockerContainer.Id: DockerContainer, )
		"""
		return self._get_containers_list(self.containers_by_id)

	# clem 17/03/2016
	def _get_containers_by_name(self, container_ids):
		"""
		a dictionary of DockerContainer objects indexed by Name[0]
		similar to ps_by_id, except here the DockerContainer objects are referenced by their first Names
		DockerContainer object are referenced from the other dict and thus not modified nor copied.

		:type container_ids: dict
		:rtype: dict(DockerContainer.Name: DockerContainer)
		"""
		assert isinstance(container_ids, dict)
		self._container_dict_by_name = dict()
		for container in container_ids.itervalues():
			self._container_dict_by_name[container.name] = container
		return self._container_dict_by_name

	# clem 10/03/2016
	@property
	def containers_by_name(self):
		"""
		a dictionary of DockerContainer objects indexed by Name[0]
		similar to ps_by_id, except here the DockerContainer objects are referenced by their first Names
		DockerContainer object are referenced from the other dict and thus not modified nor copied.

		:rtype: dict(DockerContainer.Name: DockerContainer)
		"""
		return self._get_containers_by_name(self.containers_by_id)

	#
	# IMAGES DATA OBJECT MANAGEMENT AND INTERFACE
	#

	# clem 09/03/2016
	@property
	def images_by_id(self):
		"""
		a dictionary of DockerImage objects indexed by Id
		internally images lists is stored in a dict indexed with images' Ids.
		Each time this property is used the dict is refreshed by calling 'docker images'
		DockerImage objects from the cache dict are altered only if image entry changed.
		DockerImage objects stores an internal md5 of its dictionary so that a modified image (invariant Id) will be
			updated
		similar to ps_by_id()

		:rtype: dict(DockerImage.Id: DockerImage)
		"""
		try:
			images = self.cli.images()
			for e in images:
				img = DockerImage(e)
				if img.Id not in self.__image_dict_by_id: # or self.__image_dict_by_id[img.Id].sig != img.sig:
					with self._data_mutex: # updates the image dict
						self.__image_dict_by_id[img.Id] = img # DockerImage(e)
			return self.__image_dict_by_id
		except Exception as e:
			self._exception_handler(e)

	# clem 17/03/2016
	def _get_image_list(self, image_ids):
		""" extracts all DockerImage objects from images_by_id to return a list of them

		:type image_ids: dict
		:rtype: list(DockerImage.Id: DockerImage, )
		"""
		assert isinstance(image_ids, dict)
		self._images_list = list()
		for image in image_ids.itervalues():
			self._images_list.append(image)
		return self._images_list

	# clem 09/03/2016
	@property
	def images_list(self):
		""" extracts all DockerImage objects from images_by_id to return a list of them

		:rtype: list(DockerImage.Id: DockerImage, )
		"""
		return self._get_image_list(self.images_by_id)

	# clem 17/03/2016
	def _get_images_by_repo_tag(self, image_ids):
		"""
		a dictionary of DockerImage objects indexed by RepoTag[0]
		similar to images_by_id, except here the DockerImage objects are referenced by their first RepoTag
		DockerImage object are referenced from the other dict and thus not modified nor copied.

		:type image_ids: dict
		:rtype: dict(DockerImage.tag: DockerImage)
		"""
		assert isinstance(image_ids, dict)
		self.__image_dict_by_tag = dict()
		for image in image_ids.itervalues():
			self.__image_dict_by_tag[image.full_name] = image

		return self.__image_dict_by_tag

	# clem 09/03/2016
	@property
	def images_by_repo_tag(self):
		"""
		a dictionary of DockerImage objects indexed by RepoTag[0]
		similar to images_by_id, except here the DockerImage objects are referenced by their first RepoTag
		DockerImage object are referenced from the other dict and thus not modified nor copied.

		:rtype: dict(DockerImage.tag: DockerImage)
		"""
		return self._get_images_by_repo_tag(self.images_by_id)

	# clem 09/03/2016
	@property
	def images_tree(self):
		images = self.images_by_repo_tag
		self.__image_tree = dict()
		for name, img in images.iteritems():
			assert isinstance(img, DockerImage)
			if img.repo_name not in self.__image_tree:
				self.__image_tree[img.repo_name] = dict()
			repo = self.__image_tree[img.repo_name]
			if img.repo_name not in repo:
				repo[img.name] = dict()
			repo[img.name][img.tag] = images[name]

		return self.__image_tree

	# clem 09/03/2016
	def show_repo_tree(self):
		advanced_pretty_print(self.images_tree)


use_caching = True
expire_after = 60 * 60 # 1 hour


# clem 10/05/2016
def get_docker_client(daemon_url, repo=None, auto_connect=True, auto_watcher=True):
	""" Return and save the DockerClient, so that only one get instantiated per daemon_url / repo couple

	:param daemon_url: The url of the target Docker daemon. Can be anything docker api will accept (socket, tcp, etc)
	:type daemon_url: basestring
	:param repo: an object representing configuration for the docker hub repository to use, default: None
	:type repo: DockerRepo | None
	:param auto_connect: connect upon creation of the object, default: True
	:type auto_connect: bool | None
	:param auto_watcher: start the event watcher upon connection, default: True
	:type auto_watcher: bool | None
	:return: The client
	:rtype: DockerClient
	"""

	def new_if():
		return DockerClient(daemon_url, repo, auto_connect, auto_watcher)

	with a_lock:
		if use_caching:
			key = 'DockerClient:%s' % hex(('%s%s' % (daemon_url, repo)).__hash__())
			cached = ObjectCache.get(key)
			if not cached:
				ObjectCache.add(new_if(), key, expire_after)
			return ObjectCache.get(key)
		return new_if()
