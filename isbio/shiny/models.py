from __future__ import unicode_literals
from django.template.defaultfilters import slugify
from django.contrib.auth.models import User
from django.db import models
from breeze.utils import *
from breeze.non_db_objects import CustomList
from breeze.models import CustomModel
from django.utils.deconstruct import deconstructible


def shiny_tag_fn_zip(self, filename):
	import os
	base = os.path.splitext(os.path.basename(filename))
	path = str('%s%s_%s.%s' % (settings.UPLOAD_FOLDER, self.get_name, slugify(base[0]), slugify(base[1])))
	return str(path)


def shiny_header():
	fileh = open(str(settings.SHINY_REPORT_TEMPLATE_PATH + settings.SHINY_HEADER_FILE_NAME))
	return str(fileh.read())


# 17/06/2015
def shiny_loader():
	fileh = open(str(settings.SHINY_REPORT_TEMPLATE_PATH + settings.SHINY_LOADER_FILE_NAME))
	return str(fileh.read())


# 17/06/2015
def shiny_files():
	fileh = open(str(settings.SHINY_REPORT_TEMPLATE_PATH + settings.SHINY_FILE_LIST))
	return str(fileh.read())


# 08/06/2015
# TODO change from CustomModel to CustomModelAbstract
# TODO change the institute field to a ManyToManyField
@deconstructible
class ShinyReport(CustomModel):
	FILE_UI_NAME = settings.SHINY_UI_FILE_NAME
	FILE_SERVER_NAME = settings.SHINY_SERVER_FILE_NAME
	# FILE_DASH_UI = settings.SHINY_DASH_UI_FN
	# FILE_DASH_SERVER = settings.SHINY_DASH_SERVER_FN
	FILE_HEADER_NAME = settings.SHINY_HEADER_FILE_NAME
	FILE_GLOBAL = settings.SHINY_GLOBAL_FILE_NAME
	FILE_LIST = settings.SHINY_FILE_LIST
	# FILE_LOADER = settings.SHINY_LOADER_FILE_NAME
	# SERVER_FOLDER = settings.SHINY_SERVER_FOLDER
	# UI_FOLDER = settings.SHINY_UI_FOLDER
	RES_FOLDER = settings.SHINY_RES_FOLDER
	SHINY_REPORTS = settings.SHINY_REPORTS
	REPORT_TEMPLATE_PATH = settings.SHINY_REPORT_TEMPLATE_PATH
	SYSTEM_FILE_LIST = [FILE_UI_NAME, FILE_SERVER_NAME, FILE_GLOBAL, FILE_HEADER_NAME, RES_FOLDER, RES_FOLDER[:-1]]
	# FS_ACL = 0775
	FS_ACL = ACL.RWX_RX_
	FS_REMOTE_ACL = ACL.RWX_RX_

	title = models.CharField(max_length=55, unique=True, blank=False, help_text="Choose a title for this Shiny Report")
	description = models.CharField(max_length=350, blank=True, help_text="Optional description text")
	author = models.ForeignKey(User)
	created = models.DateTimeField(auto_now_add=True)

	# objects = managers.ObjectsWithAuth()
	# institute = ForeignKey(Institute, default=Institute.default)

	custom_header = models.TextField(blank=True, default=shiny_header(),
		help_text="Use R Shiny code here to customize the header of the dashboard<br />"
			"Here is a basic example of what you can do.<br />\n"
			"For more information, please refer to Shiny documentation.")

	custom_loader = models.TextField(blank=True, default=shiny_loader(),
		help_text="Use R Shiny code here to customize the global server part of the "
				  "dashboard<br />This is usefull to load files, or declare variables "
				  "that will be accessible to each attached tags:<br />NB : you may "
				  "reference, in the next field, every file you use here. Use a $ to "
				  "reference your file according to the 'tname' you associated with it.")

	custom_files = models.TextField(blank=True, default=shiny_files(),
		help_text="Use the following JSON format to reference your files<br />This "
			"enables Breeze to dynamically check for the files you marked as "
			"required.<br />")

	enabled = models.BooleanField(default=True)

	@property
	def get_name(self):
		return slugify(str(self.title))

	@property
	def __folder_path_remote(self):
		return str('%s%s/app/' % (settings.SHINY_REMOTE_REPORTS_INTERNAL, self.get_name))

	def __folder_path_base_gen(self, remote=False):
		return str('%s%s/' % (self.SHINY_REPORTS if not remote else settings.SHINY_REMOTE_REPORTS, self.get_name))

	@property
	def _folder_path_base(self):
		return self.__folder_path_base_gen()

	def __folder_path_gen(self, remote=False):
		return str('%sapp/' % self.__folder_path_base_gen(remote))

	@property
	def folder_path(self):
		return self.__folder_path_gen()

	def server_path(self, remote=False):
		return str('%s%s' % (self.__folder_path_gen(remote), self.FILE_SERVER_NAME))

	def ui_path(self, remote=False):
		return str('%s%s' % (self.__folder_path_gen(remote), self.FILE_UI_NAME))

	def global_path(self, remote=False):
		return str('%s%s' % (self.__folder_path_gen(remote), self.FILE_GLOBAL))

	def res_folder_path(self, remote=False):
		return str('%s%s' % (self.__folder_path_gen(remote), self.RES_FOLDER))

	# path_template_folder = REPORT_TEMPLATE_PATH
	path_server_r_template = REPORT_TEMPLATE_PATH + FILE_SERVER_NAME
	path_ui_r_template = REPORT_TEMPLATE_PATH + FILE_UI_NAME
	path_global_r_template = REPORT_TEMPLATE_PATH + FILE_GLOBAL

	# path_heade_r_template = REPORT_TEMPLATE_PATH + FILE_HEADER_NAME
	# path_global_r_template = REPORT_TEMPLATE_PATH + FILE_GLOBAL
	# path_loader_r_template = str(REPORT_TEMPLATE_PATH + FILE_LOADER)
	# path_file_lst_template = str(REPORT_TEMPLATE_PATH + FILE_LIST)
	# path_dash_ui_r_template = REPORT_TEMPLATE_PATH + FILE_DASH_UI
	# path_dash_server_r_template = REPORT_TEMPLATE_PATH + FILE_DASH_SERVER

	# TODO rework the next 3 functions
	@property
	def shiny_mode(self):
		if self.shiny_remote_ok:
			return 'remote'
		elif self.shiny_local_ok:
			return 'local'

	@property
	def shiny_remote_ok(self):
		return settings.SHINY_REMOTE_ENABLE and settings.SHINY_MODE == 'remote'

	@property
	def shiny_local_ok(self):
		return settings.SHINY_LOCAL_ENABLE and settings.SHINY_MODE == 'local'

	def url(self, report, force_remote=False, force_local=False):
		assert isinstance(report, Report)
		if force_remote or self.shiny_remote_ok and not force_local:
			return '%s%s/' % (settings.SHINY_TARGET_URL, report.shiny_key)
		elif self.shiny_local_ok:
			from django.core.urlresolvers import reverse
			from views import report_shiny_in_wrapper
			return reverse(report_shiny_in_wrapper, kwargs={ 'rid': report.id })

	@property # relative path to link holder directory
	def _link_holder_rel_path(self):
		# the point of this property, is that you can change the folder structure by only changing this
		return '%s/lnk' % self.get_name

	def _link_holder_path(self, remote=False): # full path to lnk holder directory
		return '%s%s/' % (
			self.SHINY_REPORTS if not remote else settings.SHINY_REMOTE_REPORTS, self._link_holder_rel_path)

	def report_link_rel_path(self, data):
		"""
		Return the path to the symlink file to the actual report WITHOUT a trailing /
		:param data: a valid Report id
		:return: path to the symlink file to the actual report WITHOUT a trailing /
		:rtype: str
		"""
		return '%s/%s' % (self._link_holder_rel_path, data)

	def report_link(self, data, rel=False, remote=False):
		if rel:
			return self.report_link_rel_path(data)
		return '%s%s' % (
			self.SHINY_REPORTS if not remote else settings.SHINY_REMOTE_REPORTS, self.report_link_rel_path(data))

	# Clem 22/09/2015
	@staticmethod
	def check_csc_mount():
		from system_check import check_csc_mount
		return check_csc_mount()

	# Clem 05/10/2015
	@staticmethod
	def remote_shiny_ready():
		return settings.SHINY_REMOTE_ENABLE and ShinyReport.check_csc_mount()

	# Clem 23/09/2015
	@property # may be dynamic in the future and return if this very report should go to remote Shiny
	def make_remote_too(self):
		"""
		If remote Shiny report should be generated, if SHINY_REMOTE_ENABLE and CSC FS is mounted
		:return:
		:rtype:
		"""
		return self.remote_shiny_ready()

	def update_folder(self):
		"""
		Creates the directory structure, removing any previously existing content,
		creates sever and ui sub-folders and link server and ui dashboard 'tag'
		Handles both local and remote Shiny
		"""
		# import os.path
		from os import mkdir

		if settings.SHINY_LOCAL_ENABLE:
			safe_rm(self._folder_path_base, ignore_errors=True)
			mkdir(self._folder_path_base, self.FS_ACL)
			mkdir(self._link_holder_path(), self.FS_ACL)
			mkdir(self.folder_path, self.FS_ACL)
			mkdir('%s%s/' % (self.folder_path, self.RES_FOLDER), self.FS_ACL)

		if self.make_remote_too:
			safe_rm(self.__folder_path_base_gen(True), ignore_errors=True)
			mkdir(self.__folder_path_base_gen(True), self.FS_REMOTE_ACL)
			mkdir(self.report_link('', remote=True), self.FS_REMOTE_ACL)
			mkdir(self.__folder_path_gen(True), self.FS_REMOTE_ACL)
			mkdir('%s%s/' % (self.__folder_path_gen(True), self.RES_FOLDER), self.FS_REMOTE_ACL)

	def _link_all_reports(self, force=False):
		"""
		Triggers the linking of each Reports that exists of every attached ReportType
		Handle both local and remote Shiny
		:param force: force linking of each Reports, even if files are missing, or the link already existent
		:type force: bool
		"""
		has_remote = self.make_remote_too
		if ReportType.objects.filter(shiny_report=self).count() > 0: # if attached to any Report
			for rtype in ReportType.objects.filter(shiny_report=self):
				for report in Report.objects.f.get_done(False, False).filter(type=rtype):
					if True: # report.is_r_successful:
						self.link_report(report, force, has_remote)

	# Clem 24/09/2015
	def _remote_ignore_wrapper(self, report):
		"""
		return the remote_ignore with specific report context to be called by copythree
		:type report: Report
		:rtype: callable()
		"""
		assert isinstance(report, Report)

		def remote_ignore(_, names):
			"""
			:type names: str
			:rtype: list
			Return a list of files to ignores amongst names
			"""
			import fnmatch
			ignore_list = self.SYSTEM_FILE_LIST + report.hidden_files
			out = list()
			for each in names:
				# if each in ignore_list or each[:-1] == '~' or fnmatch.fnmatch():
				if each[:-1] == '~':
					out.append(each)
				else:
					for ignore in ignore_list:
						if fnmatch.fnmatch(each, ignore):
							out.append(each)
							break
			return out

		return remote_ignore

	def link_report(self, report, force=False, remote_too=False):
		"""
		Link a standard report to this ShinyReport using soft-links. (updates or creates linking)
		If the ShinyReport skeleton has previously been generated,
			this step is enough to enable a report to be visualized through Shiny
		Handle both local and remote Shiny (with remote_too = True)
		:param report: a valid Report instance
		:type report: Report
		:param force: force linking even if files are missing, or the link already existent
		:type force: bool
		"""
		log_obj = get_logger()
		log_obj.debug(
			"updating shinyReport %s-%s slink for report %s %s" % (
				self.get_name, self.id, report.id, 'FORCING' if force else ''))

		from os.path import isdir, isfile, islink
		from os import listdir, access, R_OK # , mkdir

		assert isinstance(report, Report)
		# handles individually each generated report of this type
		report_home = report.home_folder_full_path
		report_link = self.report_link(report.id)
		report_remote_link = self.report_link(report.shiny_key, remote=True) if remote_too else ''
		# if the home folder of the report exists, and the link doesn't yet
		if isdir(report_home[:-1]) and report_home != settings.MEDIA_ROOT:
			# check that the report has all required files
			if not force:
				j = self.related_files()
				for each in j: # for every required registered file
					path = '%s%s' % (report_home, each['path'])
					if each['required'] and not (isfile(path) and access(path, R_OK)):
						log_obj.warning("%s missing required file %s" % (report.id, path))
						return
			# LOCAL make of soft-link for each files/folder of the shinyReport folder into the Report folder
			if settings.SHINY_LOCAL_ENABLE and (force or not islink(report_link)):
				for item in listdir(self.folder_path): # TODO should be recursive ?
					auto_symlink('%s%s' % (self.folder_path, item), '%s%s' % (report_home, item))
				# Creates a slink in shinyReports to the actual report
				auto_symlink(report_home, report_link)
			# REMOTE make of soft-link for each files/folder of the shinyReport folder into the Report folder
			if remote_too and (force or not islink(report_remote_link)):
				# del the remote report copy folder
				safe_rm(report.remote_shiny_path, ignore_errors=True)
				try:
					# copy the data content of the report
					safe_copytree(report.home_folder_full_path, report.remote_shiny_path,
						ignore=self._remote_ignore_wrapper(report))
				except Exception as e:
					log_obj.warning("%s ShinyReport copy error %s" % (report.id, e))

				# link ShinyReport files
				for item in listdir(self.folder_path): # TODO should be recursive ?
					# remove_file_safe('%s%s' % (report.remote_shiny_path, item))
					auto_symlink('%s%s' % (self.__folder_path_remote, item), '%s%s' % (report.remote_shiny_path, item))

				# Creates a slink in shinyReports to the actual report
				auto_symlink(report.remote_shiny_path, report_remote_link)
		else: # the target report is missing we remove the link
			self.unlink_report(report)

	# TODO upgrade to remote shiny
	def unlink_report(self, report, remote=False):
		"""
		Do the opposite of link_report, useful if a specific Report has been individually deleted
		:param report: a valid Report instance
		:type report: Report
		"""
		assert isinstance(report, Report)
		import os
		# handles individually each generated report of this type
		report_home = report.home_folder_full_path
		report_link = self.report_link(report.id)

		# if the home folder of the report exists, and the link doesn't yet
		if os.path.isdir(report_home) and report_home != settings.MEDIA_ROOT:
			# removes the soft-link for each files/folder of the shinyReport folder into the Report folder
			for item in os.listdir(self.folder_path):
				remove_file_safe('%s%s' % (report_home, item)) # TODO check
		if os.path.islink(report_link):
			# removes the slink in shinyReports to the actual report
			remove_file_safe(report_link) # unlink from shiny TODO check

	# TODO upgrade to remote shiny
	def _unlink_all_reports(self, remote=False):
		"""
		Do the opposite of _link_all_reports , usefull if a this ShinyReport has been delete, or unlink from a
		ReportType
		Triggers the unlinking of each Reports that exists of every attached ReportType
		"""
		if ReportType.objects.filter(shiny_report=self).count() > 0: # if attached to any Report
			for rtype in ReportType.objects.filter(shiny_report=self):
				for report in Report.objects.filter(type=rtype):
					self.unlink_report(report, remote)

	def import_tag_res(self, tag):
		"""
		Import every resources ( www folder) of a specific tag
		:param tag: a valid ShinyTag instance
		:type tag: ShinyTag
		"""
		from distutils.dir_util import copy_tree

		assert isinstance(tag, ShinyTag)
		copy_tree(tag.path_res_folder, self.res_folder_path()) # TODO replace with symlimks ?
		if self.make_remote_too:
			copy_tree(tag.path_res_folder, self.res_folder_path(True)) # TODO replace with symlimks ?

	def related_files(self, formatted=False):
		"""
		Returns a list of related files for the report
		:rtype: dict or list
		"""
		# fixed on 11/09/2015
		# fixed on 18/12/2015
		# TODO check expected behavior regarding templates
		j = list()
		if self.custom_files is not None and self.custom_files != '':
			import json
			log_obj = get_logger()

			try:
				# jfile = open(ShinyReport.path_file_lst_template)
				# j = json.load(jfile)
				j = json.loads(self.custom_files)
			# jfile.close()
			except ValueError as e:
				log_obj.exception(e.message)
			# raise ValueError(e)
			if formatted:
				d = dict()
				for each in j:
					d.update({ each['tname']: each['path'] })
				return d
		return j

	# TODO expired design
	def get_parsed_loader(self):
		from string import Template

		# file_loaders = open(ShinyReport.path_loader_r_template)
		# src = Template(file_loaders.read())
		if self.custom_loader is not None and self.custom_loader != '':
			src = Template(self.custom_loader)
			# file_loaders.close()
			# return src.safe_substitute(ShinyReport.related_files(formatted=True))
			return src.safe_substitute(self.related_files(formatted=True))

	def generate_server(self, a_user=None, remote=False): # generate the report server.R file to include all the tags
		"""
		Handle either LOCAL or REMOTE at once
		:param a_user:
		:type a_user:
		:param remote:
		:type remote:
		:return:
		:rtype:
		"""
		from string import Template
		import auxiliary as aux

		SEP = '\n  '

		if a_user is None or not isinstance(a_user, (User, OrderedUser)):
			a_user = self.author
		# opens server.R template file
		filein = open(self.path_server_r_template)
		src = Template(filein.read())
		# document data
		generated = 'Generated on %s for user %s (%s)' % (self.created, self.author.get_full_name(), self.author)
		updated = 'Last updated on %s for user %s (%s)' % (aux.date_t(), a_user.get_full_name(), a_user)
		alist = list()
		if ShinyTag.objects.filter(attached_report=self).count() > 0:
			for each in self.shinytag_set.all().order_by('order'):
				if each.enabled:
					# add it to the source list
					alist.append('### Tag %s by %s (%s) %s%ssource("%s",local = TRUE)' % (
						each.name, each.author.get_full_name(), each.author, each.created, SEP,
						each.path_dashboard_server(remote)))
				else:
					alist.append('### DISABLED Tag %s by %s (%s) %s' % (
						each.name, each.author.get_full_name(), each.author, each.created))
		loaders = self.get_parsed_loader() # TODO redo
		alist.append('') # avoid join errors if list is empty
		d = {
			'title'    : self.title,
			'generated': generated,
			'updated'  : updated,
			'loaders'  : loaders,
			'sources'  : SEP.join(alist)
		}
		assert (isinstance(src, Template))
		result = src.safe_substitute(d)
		f = open(self.server_path(remote), 'w')
		f.write(result)
		f.close()
		return

	def generate_ui(self, a_user=None, remote=False):  # generate the report ui.R file to include all the tags
		"""
		Handle either LOCAL or REMOTE at once
		:param a_user:
		:type a_user:
		:param remote:
		:type remote:
		:return:
		:rtype:
		"""
		from string import Template
		import auxiliary as aux

		SEP = '\n'
		SEP2 = ',\n  '

		if a_user is None or not isinstance(a_user, (User, OrderedUser)):
			a_user = self.author
		# opens ui.R template file
		filein = open(self.path_ui_r_template)
		src = Template(filein.read())
		filein.close()
		# document data
		generated = 'Generated on %s for user %s (%s)' % (self.created, self.author.get_full_name(), self.author)
		updated = 'Last updated on %s for user %s (%s)' % (aux.date_t(), a_user.get_full_name(), a_user)
		alist = list()
		tag_vars = list()
		menu_list = list()
		if ShinyTag.objects.filter(attached_report=self).count() > 0:
			for each in self.shinytag_set.all().order_by('order'):
				if each.enabled:
					self.import_tag_res(each)
					alist.append('### Tag %s by %s (%s) %s%ssource("%s",local = TRUE)' % (
						each.name, each.author.get_full_name(), each.author, each.created, SEP,
						each.path_dashboard_body(remote)))
					tag_vars.append(each.get_name.upper())
					menu_list.append(each.menu_entry)
				else:
					alist.append('### DISABLED Tag %s by %s (%s) %s' % (
						each.name, each.author.get_full_name(), each.author, each.created))
		alist.append('')
		menu_list.append('')
		d = {
			'title'     : self.title,
			'header'    : self.custom_header,
			'generated' : generated,
			'updated'   : updated,
			'menu_items': SEP2.join(menu_list),
			'sources'   : SEP.join(alist),
			'tag_vars'  : SEP2.join(tag_vars),
		}
		# do the substitution
		result = src.substitute(d)
		f = open(self.ui_path(remote), 'w')
		f.write(result)
		f.close()
		return

	def generate_global(self, a_user=None, remote=False):  # generate the report ui.R file to include all the tags
		"""
		Handle either LOCAL or REMOTE at once
		:param a_user:
		:type a_user:
		:param remote:
		:type remote:
		:return:
		:rtype:
		"""
		from string import Template
		import auxiliary as aux

		SEP = '\n'

		if a_user is None or not isinstance(a_user, (User, breeze.models.OrderedUser)):
			a_user = self.author
		# opens ui.R template file
		filein = open(self.path_global_r_template)
		src = Template(filein.read())
		# document data
		generated = 'Generated on %s for user %s (%s)' % (self.created, self.author.get_full_name(), self.author)
		updated = 'Last updated on %s for user %s (%s)' % (aux.date_t(), a_user.get_full_name(), a_user)
		alist = list()
		if ShinyTag.objects.filter(attached_report=self).count() > 0:
			for each in self.shinytag_set.all().order_by('order'):
				# base, ui_path, _ = self.get_tag_path(each)
				file_glob = open(each.folder_name + self.FILE_GLOBAL)
				alist.append('### from tag %s by %s (%s) %s\n%s' % (
					each.name, each.author.get_full_name(), each.author, each.created, file_glob.read()))
				file_glob.close()
		alist.append('')
		d = {
			'generated' : generated,
			'updated'   : updated,
			'tag_global': SEP.join(alist)
		}
		# do the substitution
		result = src.substitute(d)
		f = open(self.global_path(remote), 'w')
		f.write(result)
		f.close()
		return

	# TODO implement a lock mechanism for concurrency safety
	def regen_report(self, a_user=None):
		"""
		Handle BOTH local and remote Shiny at Once
		:param a_user:
		:type a_user:
		:return:
		:rtype:
		"""
		log_obj = get_logger()
		log_obj.info("rebuilding shinyReport %s-%s for user %s" % (self.id, self.get_name, a_user))
		self.update_folder()
		# local : TODO should generate disregarding of local shiny status ?
		if settings.SHINY_LOCAL_ENABLE:
			log_obj.debug("rebuilding LOCAL on shinyReport %s-%s" % (self.id, self.get_name))
			self.generate_server(a_user)
			self.generate_ui(a_user)
			self.generate_global(a_user)
		# remote
		if self.make_remote_too:
			log_obj.debug("rebuilding REMOTE on shinyReport %s-%s" % (self.id, self.get_name))
			self.generate_server(a_user, True)
			self.generate_ui(a_user, True)
			self.generate_global(a_user, True)
		log_obj.debug("re-linking and eventual remote copy on shinyReport %s-%s" % (self.id, self.get_name))
		self._link_all_reports()

	def clean(self):
		pass

	def save(self, *args, **kwargs):
		super(ShinyReport, self).save(*args, **kwargs) # Call the "real" save() method.
		self.regen_report()

	def delete(self, using=None):
		import shutil

		log_obj = get_logger()
		log_obj.info("deleted shinyReport %s : %s" % (self.id, self))
		# unlinking all attached Reports
		self._unlink_all_reports()
		# Deleting the folder
		shutil.rmtree(self._folder_path_base, ignore_errors=True)
		if self.make_remote_too:
			log_obj.info("deleted remote shinyReport %s : %s" % (self.id, self))
			self._unlink_all_reports(True)
			shutil.rmtree(self.__folder_path_base_gen(True), ignore_errors=True)
		super(ShinyReport, self).delete(using=using) # Call the "real" delete() method.

	class Meta(object):
		ordering = ('created',)

	def __unicode__(self):
		return self.get_name

	def __eq__(self, other):
		return self.foo == other.foo
	
	def __init__(self, foo=1):
		self.foo = foo
		super(ShinyReport, self).__init__()


@deconstructible
class ShinyTag(CustomModel):
	# ACL_RW_RW_R = 0664
	FILE_UI_NAME = settings.SHINY_UI_FILE_NAME
	FILE_SERVER_NAME = settings.SHINY_SERVER_FILE_NAME
	# FILE_DASH_UI = settings.SHINY_DASH_UI_FILE
	TAG_FOLDER = settings.SHINY_TAGS
	RES_FOLDER = settings.SHINY_RES_FOLDER
	FILE_TEMPLATE = settings.SHINY_TAG_CANVAS_PATH
	FILE_TEMPLATE_URL = settings.MOULD_URL + settings.SHINY_TAG_CANVAS_FN
	DEFAULT_MENU_ITEM = 'menuItem("Quality Control", icon = icon("filter", lib = "glyphicon"), tabName = "REPLACE BY ' \
		'THE NAME OF YOUR TAG IN UPPER CASE HERE",' \
		'badgeLabel = "QC", badgeColor = "green")'

	name = models.CharField(max_length=55, unique=True, blank=False,
		help_text="Must be unique, no special characters, no withe spaces."
			"<br />NB : Use the same (in upper case) in the tabName field of the menu entry")
	# label = models.CharField(max_length=32, blank=False, help_text="The text to be display on the dashboard")
	description = models.CharField(max_length=350, blank=True, help_text="Optional description text")
	author = models.ForeignKey(User)
	created = models.DateTimeField(auto_now_add=True)
	# institute = ForeignKey(Institute, default=Institute.default)
	order = models.PositiveIntegerField(default=0, help_text="sorting index number (0 is the topmost)")
	menu_entry = models.TextField(default=DEFAULT_MENU_ITEM,
		help_text="Use menuItem or other Shiny  Dashboard items to customize the menu entry "
			"of your tag.<br /><u>NB : tabName MUST be identical to the uppercase name of your tag.</u>")

	@property
	def get_name(self):
		return str(slugify(str(self.name)))

	@staticmethod
	def remove_file_safe(fname):
		import os.path
		from django.db.models.fields.files import FieldFile
		if type(fname) == file or type(fname) == FieldFile:
			fname = fname.path
		try:
			if os.path.isfile(fname):
				os.remove(fname)
		except os.error:
			pass

	def folder_name_gen(self, remote=False):
		return str('%s%s/' % (self.TAG_FOLDER if not remote else settings.SHINY_REMOTE_TAGS, self.get_name))

	@property
	def folder_name_remote_internal(self):
		return str('%s%s/' % (settings.SHINY_REMOTE_TAGS_INTERNAL, self.get_name))

	@property
	def folder_name(self):
		return self.folder_name_gen()

	def path_dashboard_server(self, remote=False):
		if not remote:
			return str('%s%s' % (self.folder_name, self.FILE_SERVER_NAME))
		else:
			return str('%s%s' % (self.folder_name_remote_internal, self.FILE_SERVER_NAME))

	def path_dashboard_body(self, remote=False):
		if not remote:
			return str('%s%s' % (self.folder_name, self.FILE_UI_NAME))
		else:
			return str('%s%s' % (self.folder_name_remote_internal, self.FILE_UI_NAME))

	def path_res_folder_gen(self, remote=False):
		if not remote:
			return str('%s%s' % (self.folder_name, self.RES_FOLDER))
		else:
			return str('%s%s' % (self.folder_name_remote_internal, self.RES_FOLDER))

	@property
	def path_res_folder(self):
		return self.path_res_folder_gen()

	zip_file = models.FileField(upload_to=shiny_tag_fn_zip, blank=True, null=False,
		help_text="Upload a zip file containing all the files required for your tag, and "
				" following the structure of the <a href='%s'>provided canvas</a>.<br />\n"
				"Check the <a href='%s'>available libraries</a>. If the one you need is not"
				" present, please contact an admin." % (FILE_TEMPLATE_URL, settings.SHINY_LIBS_TARGET_URL))
	enabled = models.BooleanField()
	attached_report = models.ManyToManyField(ShinyReport)

	# clem 22/12/2015
	def __init__(self, *args, **kwargs):
		if not 'foo' not in kwargs.keys():
			self.foo = 1
		super(ShinyTag, self).__init__(*args, **kwargs)
		self.__prev_reports = list()
		if self.id:
			self.__prev_reports = list(self.attached_report.all() or None)
		self.__prev_name = self.name or None

	# clem 05/10/2015
	def copy_to_remote(self):
		import os
		log_obj = get_logger()
		log_obj.debug("updating %s on RemoteShiny" % self.__repr__)

		# del the remote report copy folder
		path = self.folder_name_gen(True)
		if not os.path.isdir(path) or safe_rm(path):
			try:
				# copy the data content of the report
				safe_copytree(self.folder_name, path)
			except Exception as e:
				log_obj.warning("%s copy error %s" % (self.__repr__, e))
			return True
		log_obj.warning("failed to copy %s to %s" % (self.__repr__, path))
		return False

	def save(self, *args, **kwargs):
		import shutil
		import os
		import zipfile

		# zf = kwargs.pop('zf', None)
		zf = None
		try:
			zf = zipfile.ZipFile(self.zip_file, allowZip64=True)
		except Exception as e:
			logger.warning(str(e))
		# rebuild = kwargs.pop('rebuild', False)

		new_name = self.name
		if self.name != self.__prev_name and self.__prev_name:
			# name has changed we should rename the folder as well
			self.name = self.__prev_name
			logger.debug(str(('old path :', self.folder_name[:-1], 'to:', new_name)))
			old_dir = self.folder_name[:-1]
			self.name = new_name
			shutil.move(old_dir, self.folder_name[:-1])

		if zf:
			# clear the folder
			shutil.rmtree(self.folder_name[:-1], ignore_errors=True)
			logger.debug(str(('new path:', self.folder_name[:-1])))

			# extract the zip
			zf.extractall(path=self.folder_name)
			# changing files permission
			for item in os.listdir(self.folder_name[:-1]):
				path = '%s%s' % (self.folder_name, item)
				if os.path.isfile(path):
					os.chmod(path, ACL.RW_RW_)
			# removes the zip from temp upload folder
			self._zip_clean()

		super(ShinyTag, self).save(*args, **kwargs) # Call the "real" save() method.

		# refresh ??
		# self = ShinyTag.objects.get(pk=self.id)

		if self.enabled and ShinyReport.remote_shiny_ready():
			self.copy_to_remote()
		logger.debug(str(('before list', self.__prev_reports)))
		logger.debug(str(('after list', self.attached_report.all())))
		for each in (CustomList(self.attached_report.all()).union(self.__prev_reports)).unique():
			each.regen_report()

	# clem 22/12/2015
	def _zip_clean(self): # removes the zip from temp upload folder (thus forcing re-upload)
		import os
		if os.path.isfile(self.zip_file.path):
			self.remove_file_safe(self.zip_file.path)

	# Manages folder creation, zip verification and extraction
	def clean(self):
		import zipfile
		if self.__prev_reports and len(self.__prev_reports):
			logger.debug(str(('list before', self.__prev_reports)))  # self.attached_report.all()
		log_obj = get_logger()

		# checks if attached list changed :
		# shared_users = request_data.POST.getlist('shared')
		##
		# Zip file and folder management
		##
		try: # loads zip file
			zf = zipfile.ZipFile(self.zip_file, allowZip64=True)
		except Exception as e:
			zf = None
			self._zip_clean()
			if self.id: # not the first time this item is saved, so no problem
				log_obj.info("%s, No zip submitted, no rebuilding" % self.__repr__)
				# rebuild = False
				return # self.save()
			else:
				raise ValidationError({ 'zip_file': ["while loading zip_lib says : %s" % e] })
		# check both ui.R and server.R are in the zip and non empty
		for filename in [self.FILE_SERVER_NAME, self.FILE_UI_NAME]:
			try:
				info = zf.getinfo(filename)
			except KeyError:
				self._zip_clean()
				raise ValidationError({ 'zip_file': ["%s not found in zip's root" % filename] })
			except Exception as e:
				self._zip_clean()
				raise ValidationError({ 'zip_file': ["while listing zip_lib says : %s" % e] })
			# check that the file is not empty
			if info.file_size < settings.SHINY_MIN_FILE_SIZE:
				self._zip_clean()
				raise ValidationError({ 'zip_file': ["%s file is empty" % filename] })
		log_obj.info("%s, Rebuilding..." % self.__repr__)

	def delete(self, using=None, keep_parents=False):
		import shutil

		log_obj = get_logger()
		log_obj.info("deleted %s" % self.__repr__)

		# Deleting the folder
		shutil.rmtree(self.folder_name[:-1], ignore_errors=True)
		super(ShinyTag, self).delete(using=using, keep_parents=keep_parents) # Call the "real" delete() method.

	class Meta(object):
		ordering = ('order',)

	def __repr__(self):
		return '<%s %s:%s>' % (self.__class__.__name__, self.id, self.__unicode__())

	def __unicode__(self):
		return self.name

	def __eq__(self, other):
		return self.foo == other.foo
