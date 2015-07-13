import django
import os, shutil, re, stat, copy
from datetime import datetime
import xml.etree.ElementTree as xml
from Bio import Entrez
from django.template.defaultfilters import slugify
from django.conf import settings
from django.core.files import File, base
import breeze.models
import auxiliary as aux
import logging

from breeze.models import Report, Jobs, JobStat
from exceptions import Exception
# import hashlib
# from django.utils import timezone
# from datetime import timedelta
# import socket
# from multiprocessing import Process
# from views import breeze
# from django.template.defaulttags import now

if settings.HOST_NAME.startswith('breeze'):
	import drmaa

logger = logging.getLogger(__name__)


# TODO : integrate into script data model
def init_script(name, inline, person):
	spath = str(settings.MEDIA_ROOT) + str(get_folder_name("scripts", name, None))

	if not os.path.isdir(spath):
		os.makedirs(spath)
		dbitem = breeze.models.Rscripts(name=name,
										category=breeze.models.Script_categories.objects.get(category="general"),
										inln=inline, author=person, details="empty", order=0)

		# create empty files for header, code and xml
		dbitem.header.save('name.txt', base.ContentFile('# write your header here...'))
		dbitem.code.save('name.r', base.ContentFile('# copy and paste main code here...'))
		dbitem.save()

		root = xml.Element('rScript')
		root.attrib['ID'] = str(dbitem.id)
		input_array = xml.Element('inputArray')
		input_array.text = "empty"
		root.append(input_array)

		newxml = open(str(settings.TEMP_FOLDER) + 'script_%s.xml' % (person), 'w')
		xml.ElementTree(root).write(newxml)
		newxml.close()

		dbitem.docxml.save('script.xml', File(open(str(settings.TEMP_FOLDER) + 'script_%s.xml' % (person))))
		dbitem.save()
		os.remove(str(settings.TEMP_FOLDER) + 'script_%s.xml' % (person))
		# dbitem.docxml.save('name.xml', base.ContentFile(''))

		return spath

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

	if str(script.name) != str(form.cleaned_data['name']):
		new_folder = str(settings.MEDIA_ROOT) + str(get_folder_name("scripts", str(form.cleaned_data['name']), None))
		old_folder = str(settings.MEDIA_ROOT) + str(get_folder_name("scripts", script.name, None))
		new_slug = slugify(form.cleaned_data['name'])

		if not os.path.isdir(new_folder):
			os.makedirs(new_folder)
			script.name = form.cleaned_data['name']
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


# TODO : integrate into script data model
def del_script(script):
	folder = str(settings.MEDIA_ROOT) + str(get_folder_name("scripts", script.name, None))

	if os.path.isdir(folder):
		shutil.rmtree(folder)
		script.delete()
		return True

	return False


# TODO : integrate into Pipe data model
def del_pipe(pipe):
	slug = slugify(str(pipe.id) + '_' + pipe.type)
	folder = str(settings.MEDIA_ROOT) + 'pipelines/%s/' % (slug)

	if os.path.isdir(folder):
		shutil.rmtree(folder)
		pipe.delete()
		return True

	return False

# DELETED del_report on 30/06/2015 (now part of Runnable.del)
# DELETED del_job on 30/06/2015 (now part of Runnable.del)
# DELETED schedule_job on 10/07/2015 (now part of Runnable.assemble)
# DELETED run_job on 10/07/2015 (now part of Runnable.run)
# DELETED run_report on 30/06/2015 (now part of Runnable.run)
# DELETED abort_report on 30/06/2015 (now part of Runnable.abort)
# DELETED track_sge_job on 30/06/2015 (now part of Watcher)
# DELETED track_sge_job_bis on 30/06/2015 (now part of Watcher)

def gen_params_string_job_temp(tree, data, runnable_inst, files):
	assert isinstance(runnable_inst, Report) or isinstance(runnable_inst, Jobs)
	tmp = dict()
	params = ''
	for item in tree.getroot().iter('inputItem'):
		item.set('val', str(data.cleaned_data[item.attrib['comment']]))
		if item.attrib['type'] == 'CHB':
			params = params + str(item.attrib['rvarname']) + ' <- ' + str(
				data.cleaned_data[item.attrib['comment']]).upper() + '\n'
		elif item.attrib['type'] == 'NUM':
			params = params + str(item.attrib['rvarname']) + ' <- ' + str(
				data.cleaned_data[item.attrib['comment']]) + '\n'
		elif item.attrib['type'] == 'TAR':
			lst = re.split(', |,|\n|\r| ', str(data.cleaned_data[item.attrib['comment']]))
			seq = 'c('
			for itm in lst:
				if itm != "":
					seq = seq + '\"%s\",' % itm
			seq = seq[:-1] + ')'
			params = params + str(item.attrib['rvarname']) + ' <- ' + str(seq) + '\n'
		elif item.attrib['type'] == 'FIL' or item.attrib['type'] == 'TPL':
			# add_file_to_job(jname, juser, FILES[item.attrib['comment']])
			# add_file_to_report(runnable_inst.home_folder_full_path, files[item.attrib['comment']])
			runnable_inst.add_file(files[item.attrib['comment']])
			params = params + str(item.attrib['rvarname']) + ' <- "' + str(
				data.cleaned_data[item.attrib['comment']]) + '"\n'
		elif item.attrib['type'] == 'DTS':
			path_to_datasets = str(settings.MEDIA_ROOT) + "datasets/"
			slug = slugify(data.cleaned_data[item.attrib['comment']]) + '.RData'
			params = params + str(item.attrib['rvarname']) + ' <- "' + str(path_to_datasets) + str(slug) + '"\n'
		elif item.attrib['type'] == 'MLT':
			res = ''
			seq = 'c('
			for itm in data.cleaned_data[item.attrib['comment']]:
				if itm != "":
					res += str(itm) + ','
					seq = seq + '\"%s\",' % itm
			seq = seq[:-1] + ')'
			item.set('val', res[:-1])
			params = params + str(item.attrib['rvarname']) + ' <- ' + str(seq) + '\n'
		else:  # for text, text_are, drop_down, radio
			params = params + str(item.attrib['rvarname']) + ' <- "' + str(
				data.cleaned_data[item.attrib['comment']]) + '"\n'
	return params

# TODO integrate in Jobs or Runnable and integrate with reports' equivalent funct
def assemble_job_folder(jname, juser, tree, data, code, header, files, job=None):
	"""
		Builds (singe) R-executable file: puts together sources, header
		and input parameters from user
	"""
	# create job folder
	directory = get_job_folder(jname, juser)
	if not os.path.exists(directory):
		os.makedirs(directory)

	rexec = open(str(settings.TEMP_FOLDER) + 'rexec.r', 'w')
	script_header = open(str(settings.MEDIA_ROOT) + str(header), "rb").read()
	script_code = open(str(settings.MEDIA_ROOT) + str(code), "rb").read()

	gen_params_string_job_temp(tree, data, job, files)

	tree.write(str(settings.TEMP_FOLDER) + 'job.xml')

	rexec.write("setwd(\"%s\")\n" % directory)
	rexec.write("#####################################\n")
	rexec.write("###       Code Section            ###\n")
	rexec.write("#####################################\n")
	rexec.write(script_code)
	rexec.write("\n\n#####################################\n")
	rexec.write("### Parameters Definition Section ###\n")
	rexec.write("#####################################\n")
	rexec.write(params)
	rexec.write("\n\n#####################################\n")
	rexec.write("###       Assembly Section        ###\n")
	rexec.write("#####################################\n")
	rexec.write(script_header)

	rexec.close()
	return 1


# TODO : job related find out what is this
def build_header(data):
	header = open(str(settings.TEMP_FOLDER) + 'header.txt', 'w')
	string = str(data)
	header.write(string)
	header.close()
	return header


def add_file_to_report(directory, f):
	if not os.path.exists(directory):
		os.makedirs(directory)

	with open(directory + "/" + f.name, 'wb+') as destination:
		for chunk in f.chunks():
			destination.write(chunk)

# DELETED add_file_to_job on 13/07/2015 (now replaced by add_file_to_report)


# TODO : replace with job.folder_path
def get_job_folder(name, user=None):
	return str(settings.MEDIA_ROOT) + str(get_folder_name('jobs', name, user))


# TODO : replace with job.folder_name but has to be checked
def get_folder_name(loc, name, user=None):
	#return Jobs.objects.get()
	if loc == "jobs":
		slug = slugify(name + '_' + str(user))
	else:
		slug = slugify(name)
	return '%s/%s/' % (loc, slug)


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
		if item.attrib['type'] == 'CHB':
			params = params + str(item.attrib['rvarname']) + ' <- ' + str(
				data.get(item.attrib['comment'], "NA")).upper() + '\n'
		elif item.attrib['type'] == 'NUM':
			params = params + str(item.attrib['rvarname']) + ' <- ' + str(data.get(item.attrib['comment'], "NA")) + '\n'
		elif item.attrib['type'] == 'TAR':
			lst = re.split(', |,|\n|\r| ', str(data.get(item.attrib['comment'], "NA")))
			seq = 'c('
			for itm in lst:
				if itm != "":
					seq = seq + '\"%s\",' % itm

			if lst == ['']:
				seq = seq + ')'
			else:
				seq = seq[:-1] + ')'
			params = params + str(item.attrib['rvarname']) + ' <- ' + str(seq) + '\n'
		elif item.attrib['type'] == 'FIL' or item.attrib['type'] == 'TPL':

			if files:
				try:
					#add_file_to_report(runnable_inst.home_folder_full_path, files[item.attrib['comment']])
					runnable_inst.add_file(files[item.attrib['comment']])
					params = params + str(item.attrib['rvarname']) + ' <- "' + str(
						files[item.attrib['comment']].name) + '"\n'
				except:
					pass
			else:
				params = params + str(item.attrib['rvarname']) + ' <- ""\n'
		elif item.attrib['type'] == 'DTS':
			path_to_datasets = str(settings.MEDIA_ROOT) + "datasets/"
			slug = slugify(data.get(item.attrib['comment'], "NA")) + '.RData'
			params = params + str(item.attrib['rvarname']) + ' <- "' + str(path_to_datasets) + str(slug) + '"\n'
		elif item.attrib['type'] == 'MLT':
			res = ''
			seq = 'c('
			for itm in data.getlist(item.attrib['comment'], "NA"):
				if itm != "":
					res += str(itm) + ','
					seq = seq + '\"%s\",' % itm
			seq = seq[:-1] + ')'
			item.set('val', res[:-1])
			params = params + str(item.attrib['rvarname']) + ' <- ' + str(seq) + '\n'
		elif item.attrib['type'] == 'DTM_SAMPLES':
			res = ''
			seq = 'c('
			for itm in data.getlist(item.attrib['comment'], "NA"):
				if itm != "":
					res += str(itm) + ','
					seq = seq + '\"%s\",' % itm
			seq = seq[:-1] + ')'
			item.set('val', res[:-1])
			params = params + '# First character of each element in the vector below\n# serves to distinguish Group (G) and Sample (S) Ids;\n# ! You have to trim each element to get original Id !\n'
			params = params + str(item.attrib['rvarname']) + ' <- ' + str(seq) + '\n'
		elif item.attrib['type'] == 'SCREEN_GROUPS':
			res = ''
			seq = 'c('
			for itm in data.getlist(item.attrib['comment'], "NA"):
				if itm != "":
					res += str(itm) + ','
					seq = seq + '\"%s\",' % itm
			seq = seq[:-1] + ')'
			item.set('val', res[:-1])
			params = params + '# This shows the selected screen group IDs!\n'
			params = params + "Screen_groups" + ' <- ' + str(seq) + '\n'
		# params = params + "Screen_groups" + ' <- "' + str(data.get(item.attrib['comment'], "NA")) + '"\n'
		else:  # for text, text_are, drop_down, radio
			params = params + str(item.attrib['rvarname']) + ' <- "' + str(
				data.get(item.attrib['comment'], "NA")) + '"\n'

	return params


def report_search(data_set, report_type, query):
	"""
        Each report type assumes its own search implementation;
        RPy2 could be a good option (use local installation on VM):
            - each report is assosiated with an r-script for searching;
            - each report should have another r-script to generate an overview
    """
	lst = list()

	# !!! HANDLE EXCEPTIONS IN THIS FUNCTION !!! #

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

# TODO integrate in Report or Runnable and integrate with job's equivalent funct
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

	from breeze.models import Project, UserProfile, ReportType, Report
	from django.contrib.auth.models import User
	log = logger.getChild('build_report')
	assert isinstance(log, logging.getLoggerClass())
	assert isinstance(request_data.user, User)

	# get the request ReportType
	rt = ReportType.objects.get(type=report_data['report_type'])
	# list of users that will have access to this report
	shared_users = aux.extract_users(request_data.POST.get('Groups'), request_data.POST.get('Individuals'))
	if shared_users == list() and request_data.POST.get('shared'):
		shared_users = request_data.POST.getlist('shared')
	# author
	the_user = request_data.user
	the_user.prof = UserProfile.objects.get(user=the_user)
	assert isinstance(the_user.prof, UserProfile)

	# create initial instance so that we can use its db id
	dbitem = Report(
		_type=rt,
		_name=str(report_data['instance_name']),
		_author=the_user,
		progress=8,
		project=Project.objects.get(id=request_data.POST.get('project')),
		_institute=the_user.prof.institute_info,
		_breeze_stat=JobStat.INIT,
		rora_id=report_data['instance_id']
	)
	dbitem.assemble(request_data=request_data, shared_users=shared_users, sections=sections)
	dbitem.submit_to_cluster()

	return True


# TODO integrate in Report or Runnable and integrate with job's equivalent funct
def build_script(report_data, request_data, sections):
	""" Assembles job home folder, configures DRMAA and R related files
		and spawns a new process for reports DRMAA job on cluster.
	"""

	from breeze.models import Project, UserProfile, ReportType, Report
	from django.contrib.auth.models import User

	log = logger.getChild('build_report')
	assert isinstance(log, logging.getLoggerClass())
	assert isinstance(request_data.user, User)

	# get the request ReportType
	rt = ReportType.objects.get(type=report_data['report_type'])
	# list of users that will have access to this report
	shared_users = aux.extract_users(request_data.POST.get('Groups'), request_data.POST.get('Individuals'))
	if shared_users == list() and request_data.POST.get('shared'):
		shared_users = request_data.POST.getlist('shared')
	# author
	the_user = request_data.user
	the_user.prof = UserProfile.objects.get(user=the_user)
	assert isinstance(the_user.prof, UserProfile)

	# create initial instance so that we can use its db id
	dbitem = Report(
		_type=rt,
		_name=str(report_data['instance_name']),
		_author=the_user,
		progress=8,
		project=Project.objects.get(id=request_data.POST.get('project')),
		_institute=the_user.prof.institute_info,
		_breeze_stat=JobStat.INIT,
		rora_id=report_data['instance_id']
	)
	dbitem.assemble(request_data=request_data, shared_users=shared_users, sections=sections)
	dbitem.submit_to_cluster()


	#JOB
	rshell.assemble_job_folder(str(head_form.cleaned_data['job_name']), str(request.user), tree, custom_form,
							   str(script.code), str(script.header), request.FILES)
	new_job._name = head_form.cleaned_data['job_name']
	new_job._description = head_form.cleaned_data['job_details']
	new_job._type = script
	# new_job.status = request.POST['job_status']
	new_job.status = u"scheduled"
	new_job._author = request.user
	# TODO finish testing and debug
	new_job.email = mail_addr
	new_job.progress = 0
	new_job._rexec.save('name.r', File(open(str(settings.TEMP_FOLDER) + 'rexec.r')))
	new_job._doc_ml.save('name.xml', File(open(str(settings.TEMP_FOLDER) + 'job.xml')))
	new_job._rexec.close()
	new_job._doc_ml.close()
	new_job.breeze_stat = 'scheduled'

	# shell.schedule_job(new_job, request.POST)
	new_job.assemble()
	try:
		stat = Statistics.objects.get(script=script)
		stat.times += 1
		stat.save()
	except Statistics.DoesNotExist:
		stat = Statistics()
		stat.script = script
		stat.author = script.author
		stat.istag = script.istag
		stat.times = 1
		stat.save()

	# TODO ? improve the manipulation with XML - tmp folder not a good idea!
	os.remove(str(settings.TEMP_FOLDER) + 'job.xml')
	os.remove(str(settings.TEMP_FOLDER) + 'rexec.r')

	state = "scheduled"
	if request.POST.get('run_job') or request.POST.get('action') and request.POST.get('action') == 'run_job':
		# run_script(request, new_job.id)
		new_job.breeze_stat = JobStat.RUN_WAIT
		state = "current"

	print vars(request.POST)


