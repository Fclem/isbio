from compute_interface_module import * # has os, abc, JobStat, Runnable, ComputeTarget and utilities.*
from breeze.b_exceptions import NoSuchJob, SGEError # , InvalidArgument
from django.conf import settings
import StringIO
import copy


__version__ = '0.1.6'
__author__ = 'clem'
__date__ = '06/05/2016'

# clem 20/01/2017
_drmaa_if = None


def get_drmaa_if():
	global _drmaa_if
	if not _drmaa_if:
		_drmaa_if = DrmaaIf()
	return _drmaa_if


class ConfigNames(enumerate):
	q_master = 'SGE_MASTER_HOST'
	q_master_port = 'SGE_QMASTER_PORT'
	exec_port = 'SGE_EXECD_PORT'
	queue = 'SGE_QUEUE'
	r_home = 'R_HOME'
	shell_path = 'DEFAULT_SHELL'
	engine_section = 'sge'
	q_bin_folder_path = 'Q_BIN'
	qstat_bin_path = 'QSTAT_BIN'
	qdel_bin_path = 'QDEL_BIN'


class DrmaaIf(object):
	_has_session = False
	
	def __init__(self):
		from import_drmaa import drmaa, drmaa_mutex
		self.drmaa = drmaa
		self.mutex = drmaa_mutex
		self.session = self.drmaa.Session
		# self._has_session = False
	
	def __enter__(self):
		if self.has_session:
			return self.session
		# with self.mutex:
		self.session.initialize()
		self._has_session = True
		return self.session
	
	@property
	def has_session(self):
		return self._has_session or self.mutex.locked()
	
	def __exit__(self, exc_type, exc_val, exc_tb):
		try:
			self.session.exit()
		finally:
			self._has_session = False
			try:
				self.mutex.release() # just in case
			except:
				pass


# clem 01/12/2016
class SGEInterfaceConnector(ComputeInterfaceBase):
	DEFAULT_V_MEM = '15G'
	DEFAULT_H_CPU = '999:00:00'
	DEFAULT_H_RT = '999:00:00'
	SGE_RQ_TEMPLATE = settings.SGE_REQUEST_TEMPLATE
	SGE_REQUEST_FN = settings.SGE_REQUEST_FN
	connected = False
	_compute_target = None # FIXME HACK
	
	def __init__(self, compute_target, storage_backend=None):
		"""

		:type storage_backend: module
		"""
		super(SGEInterfaceConnector, self).__init__(compute_target, storage_backend)
		self.apply_config()
		# from import_drmaa import drmaa, drmaa_mutex
		# self.drmaa = drmaa
		# self.drmaa_mutex = drmaa_mutex
		# self.drmaa_if = DrmaaIf()
		self.drmaa_if = get_drmaa_if()
		self.session = self.drmaa_if
	
	# clem 12/12/2016
	@property
	def drmaa(self):
		return self.drmaa_if.drmaa

	# clem 12/12/2016
	@property
	def has_session(self):
		return self.drmaa_if.has_session

	# clem 17/05/2016
	@property  # writing shortcut
	def config_qstat_bin_path(self):
		return self.engine_obj.get(ConfigNames.qstat_bin_path)
	
	# clem 17/05/2016
	@property  # writing shortcut
	def config_qdel_bin_path(self):
		return self.engine_obj.get(ConfigNames.qdel_bin_path)
	
	# clem 17/05/2016
	@property  # writing shortcut
	def config_shell_path(self):
		return self.engine_obj.get(ConfigNames.shell_path)
	
	# clem 17/05/2016
	@property  # writing shortcut
	def config_queue_name(self):
		return self.target_obj.get(ConfigNames.queue, ConfigNames.engine_section) if self.target_obj else ''
	
	# clem 02/12/2016
	@property  # writing shortcut
	def config_qmaster_host(self):
			return self.target_obj.get(ConfigNames.q_master, ConfigNames.engine_section) if self.target_obj else ''
	
	# clem 02/12/2016
	@property  # writing shortcut
	def config_qmaster_port(self):
		return self.target_obj.get(ConfigNames.q_master_port, ConfigNames.engine_section) if self.target_obj else ''
	
	# clem 09/05/2016
	def write_config(self): # FIXME obsolete
		""" Writes a custom config file for SGE to read from for config

		:return: success
		:rtype: bool
		"""
		assert isinstance(self.target_obj, ComputeTarget)
		a_dict = {
			'shell' : self.config_shell_path,
			'h_vmem': self.DEFAULT_V_MEM,
			'h_cpu' : self.DEFAULT_H_CPU,
			'h_rt'  : self.DEFAULT_H_RT,
			'queue' : self.config_queue_name,
		}
		return gen_file_from_template(self.SGE_RQ_TEMPLATE, a_dict, '~/%s' % self.SGE_REQUEST_FN)
	
	# del apply_config on 15/09/2017 moved to super class
	
	# clem 20/10/2016
	@property
	def online(self):
		# clem on 20/08/2015 from system_check.py commit 5998b638d96826d907a3b3655220e4832b892d7c
		def check_sge():
			""" Check if SGE queue master server host is online, and drmaa can initiate a valid session

			:rtype: bool
			"""
			if is_host_online(self.config_qmaster_host, 2):
				try:
					if self.has_session:
						return True
					else:
						with self.session:
							return True
				except Exception as e:
					raise e
			return False
		
		return check_sge()
	
	@property
	def can_connect(self):
		return self.online


# clem 06/05/2016
class SGEInterface(SGEInterfaceConnector, ComputeInterface):
	def __init__(self, compute_target, storage_backend=None):
		super(SGEInterface, self).__init__(compute_target, storage_backend)

	# clem 06/10/2016
	def name(self):
		return "sge queue %s" % self.config_queue_name

	# clem 06/05/2016
	@property
	def _sge_obj(self): # TODO move it all here ( or not )
		return Qstat(self).job_info()

	# clem 06/05/2016
	def status(self): # TODO move it all here
		# self.log.debug("status from %s says : %s" % (repr(self), self._sge_obj.state))
		return self._sge_obj.state

	# clem 16/03/2016
	def _write_log(self, txt):
		self.log.debug(txt)

	# clem 23/05/2016
	def assemble_job(self):
		pass

	# moved here on 21/06/2016
	# FIXME port of legacy code
	# TODO check
	# @new_thread
	def __old_job_run(self):
		"""
			Submits reports as an R-job to cluster with SGE;
			This submission implements REPORTS concept in BREEZE
			(For SCRIPTS submission see Jobs.run)
		"""
		a_run = self._runnable
		config = a_run.sh_file_path
		try:
			if a_run.is_report and a_run.fm_flag: # Report specific
				a_run.start_jdc()

			# *MAY* prevent db from being dropped
			# django.db.close_connection()
			a_run.breeze_stat = JobStat.PREPARE_RUN
		except Exception as e:
			self.log.error('pre-run error %s (process continues)' % e)
		try:
			# with self.drmaa_mutex:
				# with self.drmaa.Session() as session:
			with self.session as session:
				jt = session.createJobTemplate()
				jt.workingDirectory = a_run.home_folder_full_path
				# print "wd '%s'" % jt.workingDirectory
				jt.jobName = a_run.sge_job_name
				jt.email = [str(a_run.author.email)]
				jt.nativeSpecification = ""
				if a_run.mailing != '':
					jt.nativeSpecification += "-m " + a_run.mailing
				jt.nativeSpecification += "-w n -q %s " % self.config_queue_name # FIXME hack
				if a_run.email is not None and a_run.email != '':
					jt.email.append(str(a_run.email))
				jt.blockEmail = False

				jt.remoteCommand = config
				jt.joinFiles = False

				a_run.progress = 25
				a_run.save()
				if not a_run.aborting:
					with self.drmaa_if.mutex:
						a_run.sgeid = copy.deepcopy(session.runJob(jt))
					self.log.debug('returned sge_id "%s"' % a_run.sgeid)
					a_run.breeze_stat = JobStat.SUBMITTED
				# waiting for the job to end
				# self.busy_waiting(True)
				self.busy_waiting()
				jt.delete()
		except (self.drmaa.AlreadyActiveSessionException, self.drmaa.InvalidArgumentException, self.drmaa.InvalidJobException,
		Exception) as e:
			self.log.error('drmaa submit failed : %s' % e)
			a_run.manage_run_failed(-1, '')
			raise e

		self.log.debug('drmaa submit ended successfully !')
		return True

	def send_job(self):
		# TODO fully switch to qsub, to get finally totally rid of DRMAA F*****G SHIT
		if self.apply_config() and self.drmaa:
			self.__old_job_run()
			return True
		return False

	# moved here on 21/06/2016
	# FIXME port of legacy code
	# TODO check
	# @new_thread
	def __old_drmaa_waiting(self, drmaa_waiting):
		"""

		:param drmaa_waiting: use drmaa module waiting, or self busy waiting
		:type drmaa_waiting: bool
		:rtype: drmaa.JobInfo
		"""
		exit_code = 42
		aborted = False
		# log = get_logger()
		a_run = self._runnable
		if a_run.is_sgeid_empty or a_run.is_done:
			return
		sge_id = copy.deepcopy(a_run.sgeid) # useless
		try:
			ret_val = None
			if drmaa_waiting and self.drmaa :
				self.log.debug('start drmaa_waiting')
				# with self.drmaa_mutex:
				# with self.drmaa.Session() as session:
				with self.session as session:
					# with self.drmaa_if.mutex:
					ret_val = session.wait(sge_id, self.drmaa.Session.TIMEOUT_WAIT_FOREVER)
			else:
				# acquire job
				time_out = settings.NO_SGEID_EXPIRY
				wait_sec = 0.25
				i = 0
				self.log.debug('waiting until the job shows up in SGE (t_out=%s)' % time_out)
				while True:
					try:
						time.sleep(wait_sec)
						i += wait_sec
						if self._sge_obj:
							break
						if i >= time_out:
							a_run.log.info('Job never showed up on SGE !')
							exit_code = 666
					except NoSuchJob:
						pass
				self.log.debug('Job acquired, starts polling')
				try:
					while True:
						self.status()
						time.sleep(1)
						if a_run.aborting:
							self.log.debug('Got user abort')
							break
				except NoSuchJob:
					self.log.debug('NoSuchJob')
					exit_code = 0

			# ?? FIXME
			a_run.breeze_stat = JobStat.DONE
			a_run.save()

			# FIXME this is SHITTY
			if a_run.aborting:
				aborted = True
				exit_code = 1
				a_run.breeze_stat = JobStat.ABORTED

			if self.drmaa and isinstance(ret_val, self.drmaa.JobInfo):
				if ret_val.hasExited:
					exit_code = ret_val.exitStatus
				# dic = ret_val.resourceUsage # TODO FUTURE use for mail reporting
				aborted = ret_val.wasAborted

			a_run.progress = 100
			if exit_code == 0:  # normal termination
				a_run.breeze_stat = JobStat.DONE
				a_run.log.info('sge job finished !')
				if not a_run.is_r_successful: # R FAILURE or USER ABORT (to check if that is true)
					a_run.log.info('exit code %s, SGE success !' % exit_code)
					a_run.manage_run_failed(ret_val, exit_code, drmaa_waiting, 'r')
				else: # FULL SUCCESS
					a_run.manage_run_success(ret_val)
			else: # abnormal termination
				if not aborted: # SGE FAILED
					a_run.log.info('exit code %s, SGE FAILED !' % exit_code)
					a_run.manage_run_failed(ret_val, exit_code, drmaa_waiting, 'sge')
				else: # USER ABORTED
					a_run.manage_run_aborted(ret_val, exit_code)
			a_run.save()
			return exit_code
		except Exception as e:
			a_run.log.error(' while waiting : %s' % str(e))
			raise e
		# return self._runnable.old_sge_waiter(*args)

	# clem 06/05/2016
	def busy_waiting(self, *args):
		# assert len(args) >= 1
		do_drmaa_waiting = args[0] if len(args) >= 1 else False
		return self.__old_drmaa_waiting(do_drmaa_waiting)

	# clem 09/05/2016
	def job_is_done(self):
		self.log.debug('done')

	# clem 06/05/2016
	def abort(self):
		if self._runnable.breeze_stat != JobStat.DONE:
			self._runnable.breeze_stat = JobStat.ABORT
			if not self._runnable.is_sgeid_empty:
				self._sge_obj.abort()
			else:
				self._runnable.breeze_stat = JobStat.ABORTED
			return True
		return False

	# clem 21/04/2016
	def get_results(self):
		pass


# clem 04/05/2016
def initiator(compute_target, *_):
	"""

	:type compute_target: ComputeTarget
	:type _: object
	"""
	assert isinstance(compute_target, ComputeTarget)
	return SGEInterface(compute_target)


# clem 21/10/2016
def is_ready(compute_target, *_):
	assert isinstance(compute_target, ComputeTarget)
	return SGEInterfaceConnector(compute_target).ready

# moved here on 17/05/2016


# clem 17/06/2016
def sub_proc(cmd, shell=True):
	""" Shortcut for subprocess.Popen()

	:param cmd: the command to run
	:type cmd: basestring
	:param shell: shell param of Popen, default to True
	:type shell: bool
	:return: process object
	:rtype: subprocess.Popen
	"""
	assert isinstance(cmd, basestring)
	assert isinstance(shell, bool)
	from subprocess import Popen, PIPE
	return Popen(cmd, shell=shell, stdout=PIPE)


# clem on 20/08/2015
def sys_user_name():
	""" Return current system user name

	:rtype: str
	"""
	return sub_proc('whoami').stdout.readline().replace('\n', '')


class SgeJob(object):
	"""
	Represents a SGE job from qstat output
	"""

	runnable = None
	id = 0
	prior = ''
	name = ''
	full_name = ''
	user = ''
	full_user = ''
	_state = ''
	start_d = ''
	start_t = ''
	queue = ''
	slot = ''
	qstat = None

	def __init__(self, output, qstat=None):
		""" Parse one qstat line output, as one SgeJob obj

		:type output: str
		:rtype: None
		"""
		assert not qstat or isinstance(qstat, Qstat)
		init = output.strip().replace('\n', '').replace('     ', ' ')
		while init != init.replace('  ', ' '):
			init = init.replace('  ', ' ')
		a_list = init.split(' ')
		self.id = int(a_list[0] or 0) # SgeId
		self.prior = a_list[1]
		self.name = a_list[2]
		# self.full_name = ''
		self.user = a_list[3]
		# self.full_user = ''
		self._state = a_list[4]
		self.start_d = a_list[5]
		self.start_t = a_list[6]
		self.queue = a_list[7] if len(a_list) > 7 else ''
		self.slot = a_list[8] if len(a_list) > 8 else ''
		self.qstat = qstat
		if self.qstat and self.qstat.runnable:
			self.runnable = self.qstat.runnable # Runnable.find_sge_instance(self.id)
		else:
			self.runnable = Runnable.find_sge_instance(self.id)
		if self.runnable:
			self.user = str(self.runnable.author)
			self.full_user = self.runnable.author.get_full_name()
			self.full_name = self.runnable.sge_job_name

	@property
	def state(self):
		"""

		:return: the SgeJob state as a JobStat parameter
		:rtype: str
		"""
		jps = self.runnable.compute_if.js.job_ps
		if self._state in jps:
			return jps[self._state]
		else:
			return str(self._state)

	@property
	def raw_out(self):
		"""

		:return: text line output similar to qstat output
		:rtype: str
		"""
		return '\t'.join(self.raw_out_tab)

	@property
	def raw_out_tab(self):
		"""

		:return: text line output similar to qstat output
		:rtype: list[a, b]
		"""
		return [str(self.id), self.prior, self.name, self.user, self.state, self.start_d, self.start_t, self.queue,
			self.slot]

	def abort(self):
		""" Abort a job using command line

		"""
		if self.qstat.qdel_bin_path:
			return sub_proc('%s %s' % (self.qstat.qdel_bin_path, self.id)).stdout
		return StringIO.StringIO()

	def __repr__(self):
		return '<SgeJob %s>' % self.name

	def __str__(self):
		return '\t'.join(
			[str(self.id), self.name, self.user, self.state, self.start_d, self.start_t, self.queue, self.slot])


# TODO : Split this object in two : one general and one runnable / config related
# clem on 25/08/2015
class Qstat(object): # would need some proper error management if SGE is not set up properly
	runnable = None
	sge_if = None
	target_obj = None
	qstat_bin_path = ''
	qdel_bin_path = ''
	queue_name = ''

	def __init__(self, sge_interface):
		assert isinstance(sge_interface, SGEInterface)
		try:
			self.sge_if = sge_interface
			self.target_obj = self.sge_if.target_obj
			self.runnable = self.target_obj.runnable
			self._job_list = dict()
			self.qstat_bin_path = self.sge_if.config_qstat_bin_path
			self.qdel_bin_path = self.sge_if.config_qdel_bin_path
			self.queue_name = self.sge_if.config_queue_name
			self._refresh_qstat()
		except Exception as e:
			self.sge_if.log.warning('Qstat : %s' % str(e))
			pass

	def __sub_proc(self, arg):
		if self.qstat_bin_path:
			return sub_proc('%s|grep %s' % (self.qstat_bin_path, str(arg))).stdout
		return StringIO.StringIO()

	# clem 12/10/2015
	@property
	def queue_stat(self, _=''):
		from collections import namedtuple
		if self.qstat_bin_path and self.queue_name:
			try:
				p = sub_proc('%s -g c|grep %s' % (self.qstat_bin_path, str(self.queue_name)))
				output, err = p.communicate()
				server_info = dict()
				for each in output.splitlines():
					if self.queue_name in each.split():
						server_info['s_name'] = str(each.split()[0])
						server_info['cqload'] = str(float(each.split()[1]) * 100)
						server_info['used'] = str(each.split()[2])
						server_info['avail'] = str(each.split()[4])
						server_info['total'] = str(each.split()[5])
						server_info['cdsuE'] = str(each.split()[7])
						server_info['cdsuE'] = str(each.split()[7])
						break

				return namedtuple('Struct', server_info.keys())(*server_info.values())
			except Exception as e:
				raise SGEError('SGE seems to be not properly configured : %s' % str(e))
		else:
			return namedtuple('Struct', [])(*[])

	# clem 12/10/2015
	@property
	def queue_stat_int(self):
		q = self.queue_stat
		for each in q.__dict__:
			if each != 's_name':
				q.__dict__[each] = 0 + int(float(q.__dict__[each]))
		return q

	# clem 12/10/2015
	@property
	def is_queue_full(self):
		return False

	@property
	def job_dict(self):
		"""
		:rtype: dict()
		"""
		self._refresh_qstat()
		return self._job_list

	@property
	def job_list(self):
		"""
		:rtype: dict()
		"""
		l = list()
		self._refresh_qstat()
		for each in self._job_list:
			l.append(self._job_list[each])
		return l

	# clem on 25/08/2015
	def _refresh_qstat(self):
		"""
		:return:
		:rtype: int
		"""
		self._job_list = dict()
		lines = self.__sub_proc(sys_user_name()).readlines()
		for e in lines:
			j = SgeJob(e, self)
			self._job_list[j.id] = j
		return len(lines)

	def job_info(self, jid=None):
		"""
		:type jid: int
		:rtype: SgeJob | NoSuchJob
		"""
		if not jid and self.runnable:
			jid = self.runnable.sgeid
		if jid is not None:
			if type(jid) == unicode:
				jid = int(jid or 0 )
			self._refresh_qstat()
			if jid in self._job_list:
				return self._job_list[jid]
			else:
				raise NoSuchJob('%s was not found. It usually mean the SgeJob run was completed.' % jid)

	# Clem 22/09/2015
	@property
	def html(self):
		"""
		Format job_list as an smart HTML output
		replace default sge user, by job owner, and owner fullname as tooltip
		and add the job full name as tooltip

		:rtype: str
		"""
		q = self.job_list

		result = ''
		for each in q:
			assert isinstance(each, SgeJob)
			tab = each.raw_out_tab
			tab[2] = "<span title='%s'>%s</span>" % (each.full_name, each.name)
			tab[3] = "<span title='%s'>%s</span>" % (each.full_user, each.user)
			if each.runnable is None:
				sup = ' &lt;ext&gt; '
			else:
				sup = ' &lt;%s&gt; ' % each.runnable.short_id
			result += '<code>%s%s%s</code><br />' % (sup, '\t'.join(tab), sup)

		if result == '':
			result = 'There is no SGE jobs running at the moment.<br />'

		return result

	# Clem 22/09/2015
	@property
	def md5(self):
		"""
		Return the md5 of the current qstat full output
		Used for long_poll refresh :
		Client check his last known status md5 against this,
		and only get a reply when this output changes compared to his md5

		:return:
		:rtype: str
		"""
		return get_md5(str(self.html))
