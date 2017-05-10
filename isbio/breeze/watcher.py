from breeze.models import Report, Jobs, JobStat
from utils import *

# FIXME obsolete module / design / feature
# TODO : redesign, re-implement

if settings.ENABLE_DATADOG:
	from datadog import statsd
else:
	statsd = False

DB_REFRESH = settings.WATCHER_DB_REFRESH
PROC_REFRESH = settings.WATCHER_PROC_REFRESH

proc_lst = dict()


class ProcItem(object): # TODO rename to ThreadItem
	def __init__(self, proc, dbitem):
		assert isinstance(proc, Thread) or proc is None
		assert isinstance(dbitem, Report) or isinstance(dbitem, Jobs)
		self.process = proc
		self._db_item_id = dbitem.id
		self.inst_type = dbitem.instance_of

	@property
	def db_item(self):
		return self.inst_type.objects.get(pk=self._db_item_id)


def refresh_db():
	"""
	Scan the db for new reports to be run or updated
	"""
	# django.db.close_connection()
	lst_r = Report.objects.f.get_run_wait()
	lst_j = Jobs.objects.f.get_run_wait()
	for item in lst_r:
		_spawn_the_job(item)
	for item in lst_j:
		_spawn_the_job(item)

	lst_r = Report.objects.f.get_active()
	lst_j = Jobs.objects.f.get_active()
	for item in lst_r:
		if item.id not in proc_lst.keys():
			item.log.debug('found active report but not monitored : %s, %s' % (item.name, item.status))
			_reattach_the_job(item)
	for item in lst_j:
		if item.id not in proc_lst.keys():
			item.log.debug('found active job but not monitored : %s, %s' % (item.name, item.status))
			_reattach_the_job(item)


def end_tracking(proc_item):
	"""

	:param proc_item:
	:type proc_item: ProcItem
	"""
	# TODO check that
	proc_item.db_item.log.debug('ending tracking')
	del proc_lst[proc_item.db_item.id]
	if statsd:
		statsd.decrement('python.breeze.running_jobs')


def refresh_proc():
	"""
		Checks each running process that waits against an DRMAA job to end
		There might also be jobs on the list that have no process :
		i.e. if the waiter crashed, server restarted etc
	"""
	for each in proc_lst.keys():
		proc_item = proc_lst[each]
		assert isinstance(proc_item, ProcItem)
		try:
			dbitem = proc_item.db_item
			dbitem.log.debug("refresh_proc")
			proc = proc_item.process

			if not proc.is_alive(): # thread finished
				exit_c = 0
				end_tracking(proc_item)
				msg = 'waiting process ended with code %s' % exit_c
				if exit_c != 0:
					dbitem.log.error(msg)
					# drmaa waiter failed on first wait run
					dbitem.breeze_stat = JobStat.FAILED
					# re-lunch wait to check out
					_reattach_the_job(dbitem)
				else:
					dbitem.log.debug(msg)
				# else : clean exit, success assessment code is managed by waiter
			else:
				refresh_qstat(proc_item)
		except proc_item.inst_type.DoesNotExist:
			del proc_lst[each]


def refresh_qstat(proc_item):
	""" Update the status of one Report; Can trigger job abortion if instructed to

	:param proc_item: a ProcItem object
	:type proc_item: ProcItem
	"""
	assert isinstance(proc_item, ProcItem)
	dbitem = proc_item.db_item
	assert isinstance(dbitem, (Report, Jobs))

	status = None
	if not dbitem.is_sgeid_empty:
		if not dbitem.is_done:
			try:
				dbitem.log.debug('status()')
				status = dbitem.compute_if.status()
			except NoSuchJob as e:
				dbitem.log.warning('qstat InvalidJobException (%s)' % (e,))
				end_tracking(proc_item)
			# if the status has changed and is not consistent with one from the object
			if status and status != dbitem.breeze_stat and not dbitem.aborting:
				dbitem.log.debug('status says %s db.breeze_stat says %s' % (status, dbitem.breeze_stat))
				dbitem.breeze_stat = status
			else:
				dbitem.log.debug('no change %s, %s' % (status, dbitem.get_status()))
	elif dbitem.is_sgeid_timeout: # and not dbitem.is_done:
		dbitem.log.warning('SgeId timeout !')
		end_tracking(proc_item)
		dbitem.re_submit()


def _reattach_the_job(dbitem):
	"""

	:param dbitem: Runnable
	:type dbitem: Report | Jobs
	"""
	assert isinstance(dbitem, Report) or isinstance(dbitem, Jobs)
	try:
		if not dbitem.is_done:
			# p = Thread(target=dbitem.waiter, args=(s, ))
			p = Thread(target=dbitem.compute_if.busy_waiting, args=(False, ))
			p.start()
			# dbitem.waiter(s)
			proc_lst.update({ dbitem.id: ProcItem(p, dbitem) })

			dbitem.log.debug('reattaching job.waiter in tID%s' % p.ident)
			if statsd:
				statsd.increment('python.breeze.running_jobs')
	except Exception as e:
		dbitem.log.exception('unhandled exception : %s' % e)
		return False


def _spawn_the_job(dbitem):
	"""

	:param dbitem: Runnable
	:type dbitem: Report | Jobs
	"""
	assert isinstance(dbitem, Report) or isinstance(dbitem, Jobs)
	if not dbitem.aborting:
		try:
			p = Thread(target=dbitem.compute_if.send_job)
			p.start()
			# dbitem.run()
			proc_lst.update({ dbitem.id: ProcItem(p, dbitem) })

			dbitem.log.debug('spawning job.run in tID%s' % p.ident)
			if statsd:
				statsd.increment('python.breeze.running_jobs')
		except Exception as e:
			dbitem.log.exception('unhandled exception : %s' % e)
			return False
	else:
		dbitem.breeze_stat = JobStat.ABORTED


def runner():
	""" Worker that post the jobs, and update their status, Runs until killed or crashed

	TO BE RUN ONLY_ONCE IN A SEPARATE THREAD
	"""
	get_logger().debug('JobKeeper started')

	i = 0
	j = 0
	sleep_time = min(DB_REFRESH, PROC_REFRESH)
	while True:
		i += 1 # DB refresh time counter
		j += 1 # PROC refresh time counter
		if i == (DB_REFRESH / sleep_time):
			i = 0
			refresh_db()

		if j == (PROC_REFRESH / sleep_time):
			j = 0
			refresh_proc()

		time.sleep(sleep_time)
