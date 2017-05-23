import os, shutil, re #, stat, copy
from datetime import datetime
import xml.etree.ElementTree as xml
from Bio import Entrez
from django.template.defaultfilters import slugify
from django.conf import settings
from django.core.files import File, base
import breeze.models
import logging
from breeze.models import Report, Jobs, JobStat, Rscripts # , Runnable
# import django
# import auxiliary as aux
# from exceptions import Exception
# import hashlib
# from django.utils import timezone
# from datetime import timedelta
# import socket
# from multiprocessing import Process
# from views import breeze
# from django.template.defaulttags import now

logger = logging.getLogger(__name__)


# TODO : integrate into script data model
def init_script(name, inline, person, category):
	
	category = breeze.models.ScriptCategories.objects.get(pk=category)
	dbitem = breeze.models.Rscripts(name=name,
									category=category,
									inln=inline, author=person, details="empty", order=0)
	if not os.path.isdir(dbitem.home_folder_full_path):
		os.makedirs(dbitem.home_folder_full_path)
		# create empty files for header, code and xml
		dbitem.header.save(settings.SCRIPT_CODE_HEADER_FN, base.ContentFile(settings.SCRIPT_HEADER_DEF_CONTENT))
		dbitem.code.save(settings.SCRIPT_CODE_BODY_FN, base.ContentFile(settings.SCRIPT_BODY_DEF_CONTENT))
		# dbitem.save()

		root = xml.Element('rScript')
		root.attrib['ID'] = str(dbitem.id)
		input_array = xml.Element('inputArray')
		input_array.text = "empty"
		root.append(input_array)
		
		target_path = settings.SCRIPT_FORM_FN
				
		dbitem.docxml.save(settings.SCRIPT_FORM_FN, base.ContentFile(''))
		with open(dbitem.docxml.path, 'w') as new_xml:
			xml.ElementTree(root).write(new_xml)
		
		dbitem.save()
		
		# return dbitem.home_folder_full_path
		return dbitem
	
	return False


# TODO : integrate into Pipe data model
def init_pipeline(form):
	"""
		Initiates a new RetortType item in the DB.
		Creates a folder for initial pipeline data.
	"""
	# First Save the data that comes with a form:
	# 'type', 'description', 'search', 'access'
	new_pipeline = form.save()

	# Add configuration file
	new_pipeline.config.save('config.txt', base.ContentFile('#          Configuration Module  \n'))
	new_pipeline.save()

	return True


# TODO : integrate into script data model
def update_script_dasics(script, form):
	"""
		Update script name and its inline description. In case of a new name it
		creates a new folder for script and makes file copies but preserves db istance id
	"""
	assert isinstance(script, Rscripts)
	if str(script.name) != str(form.cleaned_data['name']):
		# new_folder = str(settings.MEDIA_ROOT) + str(get_folder_name("scripts", str(form.cleaned_data['name']), None))
		# old_folder = str(settings.MEDIA_ROOT) + str(get_folder_name("scripts", script.name, None))
		old_folder = script.home_folder_full_path
		new_slug = slugify(form.cleaned_data['name'])

		script.name = form.cleaned_data['name']
		if not os.path.isdir(script.home_folder_full_path):
			os.makedirs(script.home_folder_full_path)

			script.inln = form.cleaned_data['inline']
			script.save()
			# copy folder
			files_list = os.listdir(old_folder)
			for item in files_list:
				fileName, fileExtension = os.path.splitext(item)
				# shutil.copy2(old_folder + item, str(new_folder) + str(new_slug) + str(fileExtension))
				if fileExtension == '.xml':
					script.docxml.save('name.xml', File(open(old_folder + item)))
				elif fileExtension == '.txt':
					script.header.save('name.txt', File(open(old_folder + item)))
				elif fileExtension == '.r' or fileExtension == '.R':
					script.code.save('name.r', File(open(old_folder + item)))
				else:
					script.logo.save('name' + str(fileExtension), File(open(old_folder + item)))

			# delete old folder
			shutil.rmtree(old_folder)

			script.creation_date = datetime.now()
			script.save()
		return True
	else:
		script.inln = form.cleaned_data['inline']
		script.creation_date = datetime.now()
		script.save()
		return True


# TODO : integrate into script data model
def update_script_description(script, post_data):
	script.details = str(post_data['description_field'])
	script.creation_date = datetime.now()
	script.save()
	return True


# TODO : integrate into script data model
def update_script_xml(script, xml_data):
	file_path = str(settings.MEDIA_ROOT) + str(script.docxml)

	if os.path.isfile(file_path):
		handle = open(file_path, 'w')
		handle.write(str(xml_data))
		handle.close()

		script.creation_date = datetime.now()
		script.save()
		return True
	else:
		return False


# TODO : integrate into script data model
def update_script_sources(script, post_data):
	assert isinstance(script, Rscripts)
	if post_data['source_file'] == 'Header':
		file_path = settings.MEDIA_ROOT + str(script.header)
	elif post_data['source_file'] == 'Main':
		file_path = settings.MEDIA_ROOT + str(script.code)

	handle = open(file_path, 'w')
	handle.write(str(post_data['mirrorEditor']))
	handle.close()

	script.creation_date = datetime.now()
	script.save()
	return True


# TODO : integrate into script data model
def update_script_logo(script, pic):
	if script.logo:
		os.remove(str(settings.MEDIA_ROOT) + str(script.logo))

	script.logo = pic
	script.creation_date = datetime.now()
	script.save()
	return True


# DELETED del_script on 		14/07/2015 (now part of Rscript)
# DELETED del_pipe on 			14/07/2015 (now part of ReportType)
# DELETED del_report on 		30/06/2015 (now part of Runnable)
# DELETED del_job on 			30/06/2015 (now part of Runnable)
# DELETED schedule_job on 		10/07/2015 (now part of Runnable.assemble)
# DELETED run_job on 			10/07/2015 (now part of Runnable.run)
# DELETED run_report on 		30/06/2015 (now part of Runnable.run)
# DELETED abort_report on 		30/06/2015 (now part of Runnable.abort)
# DELETED track_sge_job on 		30/06/2015 (now part of Watcher)
# DELETED track_sge_job_bis on 	30/06/2015 (now part of Watcher)


# Jobs


# DELETED assemble_job_folder on 16/07/2015 (now part of Runnable.assemble)


# TODO : job related find out what is this
def build_header(data):
	header = open(str(settings.TEMP_FOLDER) + settings.SCRIPT_CODE_HEADER_FN, 'w')
	string = str(data)
	header.write(string)
	header.close()
	return header

# DELETED add_file_to_report on 13/07/2015 (now part of Runnable)
# DELETED add_file_to_job on 	13/07/2015 (now part of Runnable)
# DELETED get_job_folder on 	14/07/2015 (now part of Runnable)
# DELETED get_folder_name on 	14/07/2015 (now part of Rsript and ReportType)


# TODO : seems useless
def get_dataset_info(path):
	path = str(settings.MEDIA_ROOT) + str(path)
	lst = list()

	# r('library(vcd)')
	#    r.assign('dataset', str(path))
	#    r('load(dataset)')
	#    r('dataSet1 <- sangerSet[1:131,]')
	#    drugs = r('featureNames(dataSet1)')
	#
	#    for pill in drugs:
	#        lst.append(dict(name=str(pill), db="Sanger.RData"))

	return lst


# Reports
def gen_params_string(docxml, data, runnable_inst, files):
	"""
		Iterates over script's/tag's parameters to bind param names and user input;
		Produces a (R-specific) string with one parameter definition per lines,
		so the string can be pushed directly to R file.
	"""
	assert isinstance(runnable_inst, Report) or isinstance(runnable_inst, Jobs)
	tmp = dict()
	params = str()
	for item in docxml.getroot().iter('inputItem'):
		# item.set('val', str(data.cleaned_data[item.attrib['comment']])) # FIXME
		if item.attrib['type'] == 'CHB':
			params += str(item.attrib['rvarname']) + ' <- "' + str(
				data.get(item.attrib['comment'], "NA")).upper() + '"\n'
		elif item.attrib['type'] == 'NUM':
			params += str(item.attrib['rvarname']) + ' <- ' + str(data.get(item.attrib['comment'], "NA")) + '\n'
		elif item.attrib['type'] == 'TAR':
			lst = re.split(', |,|\n|\r| ', str(data.get(item.attrib['comment'], "NA")))
			seq = 'c('
			for itm in lst:
				if itm != "":
					seq += '\"%s\",' % itm

			seq = seq + ')' if lst == [''] else seq[:-1] + ')'
			params += str(item.attrib['rvarname']) + ' <- ' + str(seq) + '\n'
		elif item.attrib['type'] == 'FIL' or item.attrib['type'] == 'TPL':
			if files:
				try:
					runnable_inst.add_file(files[item.attrib['comment']])
					params += str(item.attrib['rvarname']) + ' <- "' + str(
						files[item.attrib['comment']].name) + '"\n'
				except:
					pass
			else:
				params += str(item.attrib['rvarname']) + ' <- ""\n'
		elif item.attrib['type'] == 'DTS':
			path_to_datasets = str(settings.MEDIA_ROOT) + "datasets/"
			slug = slugify(data.get(item.attrib['comment'], "NA")) + '.RData'
			params += str(item.attrib['rvarname']) + ' <- "' + str(path_to_datasets) + str(slug) + '"\n'
		elif item.attrib['type'] == 'MLT':
			res = ''
			seq = 'c('
			for itm in data.getlist(item.attrib['comment'], "NA"):
				if itm != "":
					res += str(itm) + ','
					seq += '\"%s\",' % itm
			seq = seq[:-1] + ')'
			item.set('val', res[:-1])
			params += str(item.attrib['rvarname']) + ' <- ' + str(seq) + '\n'
		elif item.attrib['type'] == 'DTM_SAMPLES':
			res = ''
			seq = 'c('
			for itm in data.getlist(item.attrib['comment'], "NA"):
				if itm != "":
					res += str(itm) + ','
					seq += '\"%s\",' % itm
			seq = seq[:-1] + ')'
			item.set('val', res[:-1])
			params += '# First character of each element in the vector below\n# serves to distinguish Group (G) and Sample (S) Ids;\n# ! You have to trim each element to get original Id !\n'
			params += str(item.attrib['rvarname']) + ' <- ' + str(seq) + '\n'
		elif item.attrib['type'] == 'SCREEN_GROUPS':
			res = ''
			seq = 'c('
			for itm in data.getlist(item.attrib['comment'], "NA"):
				if itm != "":
					res += str(itm) + ','
					seq += '\"%s\",' % itm
			seq = seq[:-1] + ')'
			item.set('val', res[:-1])
			params += '# This shows the selected screen group IDs!\n'
			params += "Screen_groups" + ' <- ' + str(seq) + '\n'
		# params = params + "Screen_groups" + ' <- "' + str(data.get(item.attrib['comment'], "NA")) + '"\n'
		else:  # for text, text_are, drop_down, radio
			params += str(item.attrib['rvarname']) + ' <- "' + str(
				data.get(item.attrib['comment'], "NA")) + '"\n'

	return params


def report_search(data_set, report_type, query):
	"""
	Each report type assumes its own search implementation;
	RPy2 could be a good option (use local installation on VM):
		- each report is associated with an r-script for searching;
		- each report should have another r-script to generate an overview
	"""
	lst = list()

	# TODO !!! HANDLE EXCEPTIONS IN THIS FUNCTION !!! #

	# GENE - Entrez search with BioPython #
	if str(report_type) == 'Gene' and len(query) > 0:
		Entrez.email = "dmitrii.bychkov@helsinki.fi"  # <- bring user's email here
		instance = str(query) + '[Gene/Protein Name]'  # e.g. 'DMPK[Gene/Protein Name]'
		species = 'Homo sapiens[Organism]'
		search_query = instance + ' AND ' + species
		handle = Entrez.esearch(db='gene', term=search_query)
		record = Entrez.read(handle)

		for item in record['IdList']:
			record_summary = Entrez.esummary(db='gene', id=item)
			record_summary = Entrez.read(record_summary)
			if record_summary[0]['Name']:
				lst.append(
					dict(id=str(record_summary[0]['Id']), name=str(record_summary[0]['Name']), db='Entrez[Gene]'))

	# Other report types should be implemented in a generalized way! #
	else:
		pass

	return lst


def get_report_overview(report_type, instance_name, instance_id):
	"""
	Most likely will call rCode to generate overview in order
	to separate BREEZE and report content.
	"""
	summary_srting = str()

	if str(report_type) == 'Drug' and len(instance_name) > 0:
		summary_srting = ""

	if str(report_type) == 'Gene' and len(instance_name) > 0:
		if instance_id is not None:
			record_summary = Entrez.esummary(db="gene", id=instance_id)
			record_summary = Entrez.read(record_summary)

			if record_summary[0]["NomenclatureName"]:
				summary_srting += record_summary[0]["NomenclatureName"]
			if record_summary[0]["Orgname"]:
				summary_srting += " [" + record_summary[0]["Orgname"] + "] "
		else:
			summary_srting = "Instance ID is missing!"

	return summary_srting

# DELETED dump_project_parameters on 13/07/2015 (now part of Report)
# DELETED dump_pipeline_config on 13/07/2015 (now part of Report)
# DELETED get_user_and_groups on 23/05/2017 (moved to Report)


# TODO integrate in BreezeForm ? or Report or Runnable
def build_report(report_data, request_data, report_property, sections):
	""" Assembles report home folder, configures DRMAA and R related files
		and spawns a new process for reports DRMAA job on cluster.

	:param report_data: report info dictionary
	:type report_data: dict
	:param request_data: a copy of request object
	:type request_data: HTTPrequest
	:param report_property: report property form
	:type report_property: breezeForms.ReportPropsForm
	:param sections: a list of 'Rscripts' db objects
	:type sections: list
	:return: True
	:rtype: bool
	"""

	from breeze.models import Project, UserProfile, ReportType, Report, ComputeTarget
	from django.contrib.auth.models import User
	log = logger.getChild('build_report')
	assert isinstance(log, logging.getLoggerClass())
	assert isinstance(request_data.user, User)
	
	# get the request ReportType
	rt = ReportType.objects.get(type=report_data['report_type'])
	# list of users that will have access to this report
	shared_users, shared_groups = Report.get_user_and_groups(request_data.POST.getlist('shared'))
	# author
	the_user = request_data.user
	the_user.prof = UserProfile.objects.get(user=the_user)
	assert isinstance(the_user.prof, UserProfile)
	
	# target profile :
	from django.core.exceptions import ObjectDoesNotExist
	target_id = request_data.POST.get('target')
	try:
		# target = ComputeTarget.objects.get_ready().filter(pk=target_id)
		target = ComputeTarget.objects.get(pk=target_id)
	except ObjectDoesNotExist:
		from django.contrib import messages
		messages.add_message(request_data, messages.ERROR, 'No such target %s' % target_id)
		return False
	if not target.is_ready:
		from django.contrib import messages
		messages.add_message(request_data, messages.ERROR, 'target %s is either disabled or not ready' % target)
		return False
	# target = ComputeTarget.objects.get(pk=request_data.POST.get('target'))
	# if target.id not in rt.ready_id_list: # TODO make a validator in the form section
	# if target not in ComputeTarget.objects.ready():
	# 	from django.contrib import messages
	# 	messages.add_message(request_data, messages.INFO, 'target %s is either disable or not ready' % target)
	# 	return False
	
	# create initial instance so that we can use its db id
	dbitem = Report(
		_type=rt,
		_name=report_data['instance_name'],
		_author=the_user,
		project=Project.objects.get(id=request_data.POST.get('project')),
		_institute=the_user.prof.institute_info,
		_breeze_stat=JobStat.INIT,
		target=target,
		rora_id=report_data['instance_id']
	)
	dbitem.assemble(request_data=request_data, shared_users=shared_users, shared_groups=shared_groups,
		sections=sections)
	dbitem.submit_to_cluster()
	
	return True


# clem 15/09/2015
# TODO integrate in BreezeForm or fuse with the report one
def build_script(request_data, script, go_run=False, job_inst=None):
	""" Assembles job home folder, configures DRMAA and R related files
		and spawns a new process for reports DRMAA job on cluster.
	"""

	from breeze.models import Jobs
	from django.contrib.auth.models import User
	from breeze.forms import BasicJobForm, form_from_xml

	log = logger.getChild('build_job')
	assert isinstance(log, logging.getLoggerClass())
	assert isinstance(request_data.user, User)

	# author
	the_user = request_data.user
	if job_inst is not None:
		assert isinstance(job_inst, Jobs)
		tree = job_inst.xml_tree
	else:
		tree = script.xml_tree

	# after fill the forms for creating the new job
	head_form = BasicJobForm(the_user, None, request_data.POST)
	custom_form = form_from_xml(xml_parser=tree, req=request_data, usr=the_user)

	if head_form.is_valid() and custom_form.is_valid():
		# create initial instance so that we can use its db id
		dbitem = Jobs(
			_type=script,
			_name=str(head_form.cleaned_data['job_name']),
			_description=head_form.cleaned_data['job_details'],
			_author=the_user,
			# project=Project.objects.get(id=request_data.POST.get('project')),
			# _institute=the_user.prof.institute_info,
			_breeze_stat=JobStat.SCHEDULED,
			mailing=gen_mail_str(request_data),
			email=head_form.cleaned_data['report_to']
		)
		dbitem.assemble(sections=tree, request_data=request_data, custom_form=custom_form)

		if go_run:
			dbitem.submit_to_cluster()

	return custom_form, head_form


# clem 15/09/2015
def gen_mail_str(request_data):
	mails = { 'Started': '', 'Ready': '', 'Aborted': '' }
	mail_str = str()
	for key in mails:
		if key in request_data.POST:
			mails[key] = u'checked'
			mail_str += request_data.POST[key]
	return mail_str
