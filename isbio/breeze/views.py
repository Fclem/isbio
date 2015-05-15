# -*- coding: utf-8 -*-
from Bio.Sequencing.Ace import rt
from social_auth.backends.pipeline import user
import auxiliary as aux
import forms as breezeForms
import urllib, pprint, os, copy, tempfile, zipfile, shutil, fnmatch, rpy2, os.path  # mimetypes, urllib2, glob,  sys
import rora as rora
import shell as rshell
import xml.etree.ElementTree as xml
import json, pickle
from datetime import datetime
from breeze.models import Rscripts, Jobs, DataSet, UserProfile, InputTemplate, Report, ReportType, Project, Post, Group, \
	Statistics, Institute, Script_categories, CartInfo  # , User_date
from collections import OrderedDict
from dateutil.relativedelta import relativedelta
from django import http
from django.conf import settings
from django.contrib import auth  #, messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import User  # , Group
from django.core.files import File
from django.core.servers.basehttp import FileWrapper
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.db.models import Q
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render_to_response
from django.template.context import RequestContext
from django.template import loader
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils import simplejson
from django.utils.http import urlencode
from django.views.decorators.csrf import csrf_exempt
from mimetypes import MimeTypes
from multiprocessing import Process

# from django.contrib.auth import models
# from django.core.context_processors import request
# import json
# from django.forms import forms
# import thread
# from django.core.files.uploadedfile import SimpleUploadedFile
# from django.views.decorators.csrf import ensure_csrf_cookie
# import sys, traceback
# from six.moves.urllib import request, request, request
# from breeze import auxiliary


class RequestStorage():
	form_details = OrderedDict()

	def get_param_list(self):
		class creepy():
			pass

		tmp = creepy()
		plist = list()
		pkeys = self.form_details.keys()
		for key in pkeys:
			tmp.var = self.form_details[key][0].cleaned_data['inline_var']
			tmp.type = self.form_details[key][0].cleaned_data['type']
			plist.append(copy.deepcopy(tmp))
		return plist

	def del_param(self, var):
		del self.form_details[var]


storage = RequestStorage()
storage.progress = 10


def breeze(request):
	return render_to_response('index.html', RequestContext(request, {'layout': 'inline'}))


def logout(request):
	auth.logout(request)
	return HttpResponseRedirect('/')


def register_user(request):
	if request.user.is_authenticated():
		return HttpResponseRedirect('/home/')
	if request.method == 'POST':
		form = breezeForms.RegistrationForm(request.POST)
		if form.is_valid():
			user = User.objects.create_user(username=form.cleaned_data['username'],
			                                email=form.cleaned_data['email'], password=form.cleaned_data['password'])
			g = Group.objects.get(name='USERS')
			g.user_set.add(user)
			user.is_staff = False
			user.save()
			profile = UserProfile(user=user, first_name=form.cleaned_data['first_name'],
			                      last_name=form.cleaned_data['last_name'], fimm_group=form.cleaned_data['fimm_group'])
			profile.save()
			return render_to_response('forms/welcome_modal.html', RequestContext(request))
		else:
			return render_to_response('forms/register.html', RequestContext(request, {'form': form}))
	else:
		form = breezeForms.RegistrationForm()
		return render_to_response('forms/register.html', RequestContext(request, {'form': form}))

	return 1


def base(request):
	return render_to_response('base.html')


@login_required(login_url='/')
def home(request, state="feed"):
	user_info = User.objects.get(username=request.user)
	db_access = False
	try:
		user_profile = UserProfile.objects.get(user=user_info)
		user_info_complete = True
		db_access = user_profile.db_agreement
	except UserProfile.DoesNotExist:
		user_info_complete = False

	occurrences = dict()

	if state == 'feed' or state == None:
		menu = 'feed_menu'
		show_menu = 'show_feed'
		explorer_tab = 'datasets_tab'
		explorer_pane = 'show_datasets'
		pref_tab = 'projects_tab'
		pref_pane = 'show_projects'
		stat_tab = 'analysis_stat_tab'
		stat_pane = 'show_analysis_stat'
	elif state == 'projects':
		menu = 'preferences_menu'
		show_menu = 'show_preferences'
		explorer_tab = 'datasets_tab'
		explorer_pane = 'show_datasets'
		pref_tab = 'projects_tab'
		pref_pane = 'show_projects'
		stat_tab = 'analysis_stat_tab'
		stat_pane = 'show_analysis_stat'
	elif state == 'groups':
		menu = 'preferences_menu'
		show_menu = 'show_preferences'
		explorer_tab = 'datasets_tab'
		explorer_pane = 'show_datasets'
		pref_tab = 'usergroups_tab'
		pref_pane = 'show_usergroups'
		stat_tab = 'analysis_stat_tab'
		stat_pane = 'show_analysis_stat'

	projects = Project.objects.exclude(~Q(author__exact=request.user) & Q(collaborative=False)).order_by("name")
	groups = Group.objects.filter(author__exact=request.user).order_by("name")

	# get all the script info
	# rscripts = Rscripts.objects.all().get(draft=True)
	# get all the report info
	stats = Statistics.objects.all()
	occurrences['jobs_running'] = Jobs.objects.filter(juser__exact=request.user).filter(status__exact="active").count()
	occurrences['jobs_scheduled'] = Jobs.objects.filter(juser__exact=request.user).filter(
		status__exact="scheduled").count()
	occurrences['jobs_history'] = Jobs.objects.filter(juser__exact=request.user).exclude(
		status__exact="scheduled").exclude(status__exact="active").count()

	occurrences['scripts_total'] = Rscripts.objects.filter(draft="0").count()
	occurrences['scripts_tags'] = Rscripts.objects.filter(draft="0").filter(istag="1").count()

	# Get Screens
	screens = dict()  # rora.get_screens_info()

	# Patients
	patients = dict()

	posts = Post.objects.all().order_by("-time")
	for each in posts:
		each.fname = each.author.get_full_name()
		each.email = each.author.email
		each.icon = "icon-comment"
		if user_info_complete:
			# emphasis Un-read news
			if user_profile.last_active == None:
				user_profile.last_active = user_info.last_login
			if each.time > user_profile.last_active:
				each.icon = "icon-fire"

	server, server_info = aux.updateServer_routine()

	if user_info_complete:
		user_profile.last_active = timezone.now()
		user_profile.save()

	return render_to_response('home.html', RequestContext(request, {
		'home_status': 'active',
		str(menu): 'active',
		str(show_menu): 'active',
		str(explorer_tab): 'active',
		str(explorer_pane): 'active',
		str(pref_tab): 'active',
		str(pref_pane): 'active',
		str(stat_tab): 'active',
		str(stat_pane): 'active',
		'dbStat': occurrences,
		'projects': projects,
		'groups': groups,
		'posts': posts,
		'screens': screens,
		'patients': patients,
		'stats': stats,
		'user_info': user_info_complete,
		'server_info': server_info,
		'server_status': server,
		'db_access': db_access
	}))


def updateServer(request):
	server, server_info = aux.updateServer_routine()

	return HttpResponse(simplejson.dumps({'server_status': server, 'server_info': server_info}),
	                    mimetype='application/json')


@login_required(login_url='/')
def jobs(request, state="", error_msg=""):
	#if settings.DEBUG: print("State says : " + str(state))
	if state == "scheduled":
		tab = "scheduled_tab"
		show_tab = "show_sched"
	elif state == "current":
		tab = "current_tab"
		show_tab = "show_curr"
	else:
		state == "history"
		tab = "history_tab"
		show_tab = "show_hist"

	scheduled_jobs = Jobs.objects.filter(juser__exact=request.user).filter(status__exact="scheduled").order_by("-id")
	history_jobs = Jobs.objects.filter(juser__exact=request.user).exclude(status__exact="scheduled").exclude(
		status__exact="active").exclude(status__exact="queued_active").order_by("-id")
	active_jobs = Jobs.objects.filter(juser__exact=request.user).filter(status__exact="active").order_by("-id")
	queued_jobs = Jobs.objects.filter(juser__exact=request.user).filter(status__exact="queued_active").order_by("-id")

	active_reports = Report.objects.filter(status="active").filter(author__exact=request.user).order_by('-created')
	queued_reports = Report.objects.filter(status="queued_active").filter(author__exact=request.user).order_by(
		'-created')

	queued_merged = aux.merge_job_history(queued_jobs, queued_reports)
	merged_active = aux.merge_job_history(active_jobs, active_reports)
	merged_active = aux.merge_job_lst(merged_active, queued_merged)

	ready_reports = Report.objects.exclude(status="active").exclude(status="queued_active").filter(
		author__exact=request.user).order_by('-created')

	merged_history = aux.merge_job_history(history_jobs, ready_reports)

	paginator = Paginator(merged_history, 15)  # show 15 items per page

	# If AJAX - check page from the request
	# Otherwise return the first page
	if request.is_ajax() and request.method == 'GET':
		if 'get-live' in request.GET:
			hist_jobs = paginator.page(1)

			return render_to_response('jobs-live.html', RequestContext(request, {
			'dash_history': hist_jobs[0:3],
			'current': merged_active,
			}))
		else:
			page = request.GET.get('page')
			try:
				hist_jobs = paginator.page(page)
			except PageNotAnInteger:  # if page isn't an integer
				hist_jobs = paginator.page(1)
			except EmptyPage:  # if page out of bounds
				hist_jobs = paginator.page(paginator.num_pages)

			return render_to_response('jobs-hist-paginator.html', RequestContext(request, {'history': hist_jobs}))
	else:
		for jobitem in active_jobs:
			rshell.track_sge_job(jobitem, True)  # forces job refresh from sge rather than just db status
		for jobitem in queued_jobs:
			rshell.track_sge_job(jobitem, True)  # forces job refresh from sge rather than just db status
		for jobitem in active_reports:
			rshell.track_sge_job(jobitem, True)  # forces job refresh from sge rather than just db status
		for jobitem in queued_reports:
			rshell.track_sge_job(jobitem, True)  # forces job refresh from sge rather than just db status

		user_profile = UserProfile.objects.get(user=request.user)
		db_access = user_profile.db_agreement
		hist_jobs = paginator.page(1)

		if state is None and len(merged_active) > 0:
			tab = "current_tab"
			show_tab = "show_curr"
			state = 'current'

		return render_to_response('jobs.html', RequestContext(request, {
			str(tab): 'active',
			str(show_tab): 'active',
			'active_tab': state,
			'jobs_status': 'active',
			'dash_history': hist_jobs[0:3],
			'scheduled': scheduled_jobs,
			'history': hist_jobs,
			'current': merged_active,
			'pagination_number': paginator.num_pages,
			'db_access': db_access,
			'error_message': error_msg,
			'current_nb': merged_active.__len__()
		}))


@login_required(login_url='/')
def scripts(request, layout="list"):
	if layout == "nails":
		nails = True
	else:
		nails = False
	categories = Script_categories.objects.all()
	# all_scripts = Rscripts.objects.all()
	user = User.objects.get(username=request.user)
	all_scripts = user.users.all()
	cat_list = dict()
	cate = list()
	for each_cate in categories:
		if all_scripts.filter(category=each_cate, istag="0", draft="0").count() > 0:
			cat_list[str(each_cate.category).capitalize()] = all_scripts.filter(category=each_cate, istag="0",
			                                                                    draft="0")
			cate.append(str(each_cate.category).capitalize())

	# cat_list['reports'] = all_scripts.filter(istag="1")
	# reports = all_scripts.filter(istag="1")
	''''
	cat_list = dict()
	categories = list()
	for script in all_scripts:
		if str(script.category).capitalize() not in categories:
			categories.append(str(script.category).capitalize())
			cat_list[str(script.category).capitalize()] = Rscripts.objects.filter(category__exact=str(script.category)).filter(draft="0").filter(istag="0")
	'''
	# if request.user.has_perm('breeze.add_rscripts'):
	# cat_list['_My_Scripts_'] = Rscripts.objects.filter(author__exact=request.user)
	#    cat_list['_Datasets_'] = DataSet.objects.all()
	user_profile = UserProfile.objects.get(user=request.user)
	db_access = user_profile.db_agreement
	return render_to_response('scripts.html', RequestContext(request, {
		'script_list': all_scripts,
		'scripts_status': 'active',
		'cate': cate,
		'cat_list': sorted(cat_list.iteritems()),
		'thumbnails': nails,
		'db_access': db_access
	}))


@login_required(login_url='/')
def reports(request):
	page_index, entries_nb = aux.report_common(request)

	# get the user's institute
	insti = UserProfile.objects.get(user=request.user).institute_info
	all_reports = Report.objects.filter(status="succeed", institute=insti).order_by('-created')
	user_rtypes = request.user.pipeline_access.all()
	# later all_users will be changed to all users from the same institute
	all_users = UserProfile.objects.filter(institute_info=insti).order_by('user')
	# first find all the users from the same institute, then find their accessible report types
	reptypelst = list()
	for each in all_users:
		rtypes = each.user.pipeline_access.all()
		if rtypes:
			for each_type in rtypes:
				if each_type not in reptypelst:
					reptypelst.append(each_type)

	# report_type_lst = ReportType.objects.filter(access=request.user)
	all_projects = Project.objects.filter(institute=insti)
	paginator = Paginator(all_reports, entries_nb)  # show 30 items per page

	# If AJAX - check page from the request
	# Otherwise return the first page
	if request.is_ajax() and request.method == 'GET':
		try:
			reports = paginator.page(page_index)
		except PageNotAnInteger:  # if page isn't an integer
			reports = paginator.page(1)
		except EmptyPage:  # if page out of bounds
			reports = paginator.page(paginator.num_pages)
		# access rights
		for each in reports:
			each.user_is_owner = each.author == request.user
			each.user_has_access = request.user in each.shared.all() or each.user_is_owner

		return render_to_response('reports-paginator.html', RequestContext(request, {'reports': reports,
		                                                                             'pagination_number': paginator.num_pages,
		                                                                             'page': page_index}))
	else:
		reports = paginator.page(1)
		# access rights
		for each in reports:
			each.user_is_owner = each.author == request.user
			each.user_has_access = request.user in each.shared.all() or each.user_is_owner
		user_profile = UserProfile.objects.get(user=request.user)
		db_access = user_profile.db_agreement
		return render_to_response('reports.html', RequestContext(request, {
			'reports_status': 'active',
			'reports': reports,
			'rtypes': reptypelst,
			'user_rtypes': user_rtypes,
			'users': all_users,
			'projects': all_projects,
			'pagination_number': paginator.num_pages,
			'page': page_index,
			'db_access': db_access
		}))


@login_required(login_url='/')
def dbviewer(request):
	return render_to_response('dbviewer.html', RequestContext(request, {
		'dbviewer_status': 'active',
	}))


def ajax_patients_data(request, which):
	"""
        Generic function to extract data from RORA tables;
        Aimed to serve: Patients (ENTITY), Screens and Samples
        in json format for DataTables
    """
	# copy parameters
	params = request.GET

	# Call corresponding rora (R) function
	data_tbl = rora.get_patients_info(params, str(which))

	aadata = data_tbl['aaData']

	iTotalRecords = data_tbl['iTotalRecords']
	iTotalDisplayRecords = data_tbl['iTotalRecords']

	response_data = {
		'draw': int(params.get('draw')),
		'data': aadata,
		'recordsTotal': iTotalRecords,
		'recordsFiltered': iTotalDisplayRecords
	}

	return HttpResponse(simplejson.dumps(response_data), mimetype='application/json')


def ajax_patients(request, which):
	# patient_id = which
	if request.method == 'POST':
		patient_form = breezeForms.PatientInfo(request.POST)

		if patient_form.is_valid():
			patient = dict()
			patient['id'] = patient_form.cleaned_data.get('patient_id')
			patient['identifier'] = patient_form.cleaned_data.get('identifier')
			patient['source'] = patient_form.cleaned_data.get('source')
			patient['description'] = patient_form.cleaned_data.get('description')
			patient['organism'] = patient_form.cleaned_data.get('organism')
			patient['sex'] = patient_form.cleaned_data.get('sex')
			# print(type(patient_form.cleaned_data.get('birthdate')))
			patient['birthdate'] = str(patient_form.cleaned_data.get('birthdate'))
			rora.update_patient(patient)
			return HttpResponseRedirect('/dbviewer')
		else:
			patient_info = breezeForms.PatientInfo(request.POST)

	else:
		data = rora.patient_data(which)
		if isinstance(data[3], rpy2.rinterface.NACharacterType):
			data[3] = ''
		if isinstance(data[5], rpy2.rinterface.NACharacterType):
			patient_info = breezeForms.PatientInfo(initial={
				'patient_id': data[0], 'identifier': data[1], 'source': data[2], 'birthdate': data[6].split()[0],
				'organism': int(data[4]),
				'description': data[3]
			})
		else:
			patient_info = breezeForms.PatientInfo(initial={
				'patient_id': data[0], 'identifier': data[1], 'source': data[2], 'birthdate': data[6].split()[0],
				'organism': int(data[4]),
				'sex': int(data[5]), 'description': data[3]
			})

	return render_to_response('forms/basic_form_dialog.html', RequestContext(request, {
		'form': patient_info,
		'action': '/patient-data/0',
		'header': 'Update Patient Info',
		'layout': 'horizontal',
		'submit': 'Save'
	}))


def ajax_patients_new(request):
	# patient_id = which
	if request.method == 'POST':
		patient_form = breezeForms.PatientInfo(request.POST)

		if patient_form.is_valid():
			patient = dict()
			patient['identifier'] = patient_form.cleaned_data.get('identifier')
			patient['source'] = patient_form.cleaned_data.get('source')
			patient['description'] = patient_form.cleaned_data.get('description')
			patient['organism'] = patient_form.cleaned_data.get('organism')
			patient['sex'] = patient_form.cleaned_data.get('sex')
			# print(type(patient_form.cleaned_data.get('birthdate')))
			patient['birthdate'] = str(patient_form.cleaned_data.get('birthdate'))
			rora.insert_row("patients", patient)
			return HttpResponseRedirect('/dbviewer')
		else:
			patient_info = breezeForms.PatientInfo(request.POST)

	else:
		patient_info = breezeForms.PatientInfo()
	return render_to_response('forms/basic_form_dialog.html', RequestContext(request, {
		'form': patient_info,
		'action': '/patient-new/',
		'header': 'Create New Patient',
		'layout': 'horizontal',
		'submit': 'Save'
	}))


def screen_data(request, which):
	if request.method == 'POST':
		screen_form = breezeForms.ScreenInfo(request.POST)

		if screen_form.is_valid():
			screen = dict()
			screen['id'] = screen_form.cleaned_data.get('screen_id')
			screen['entity_id'] = screen_form.cleaned_data.get('patient')
			screen['alias'] = screen_form.cleaned_data.get('alias')
			screen['sample_type'] = screen_form.cleaned_data.get('st')
			screen['disease_sub'] = screen_form.cleaned_data.get('dst')
			screen['media_type'] = screen_form.cleaned_data.get('mt')
			screen['histology'] = screen_form.cleaned_data.get('histology')
			screen['disease_state'] = screen_form.cleaned_data.get('dstate')
			screen['experiment_type'] = screen_form.cleaned_data.get('et')
			screen['plate_count'] = screen_form.cleaned_data.get('plate_count')
			screen['disease_grade'] = screen_form.cleaned_data.get('dg')
			screen['disease_stage'] = screen_form.cleaned_data.get('disease_stage')
			screen['read_out'] = screen_form.cleaned_data.get('read_out')
			screen['createdate'] = str(screen_form.cleaned_data.get('createdate'))
			# print(screen)
			rora.update_screen(screen)
			return HttpResponseRedirect('/dbviewer')
		else:
			screen_info = breezeForms.ScreenInfo(request.POST)

	else:
		data = rora.screen_data(which)
		# print(data[22])
		if isinstance(data[2], rpy2.rinterface.NACharacterType):
			data[2] = ''
		screen_info = breezeForms.ScreenInfo(initial={
			'screen_id': data[0], 'identifier': data[1], 'description': data[2], 'source_id': data[3],
			'source': data[5], 'protocol': data[4], 'patient': int(data[6]), 'alias': data[7], 'st': int(data[8]),
			'dst': int(data[9]), 'mt': int(data[10]), 'histology': int(data[11]), 'dstate': int(data[12]), 'et':
				int(data[13]), 'plate_count': data[14], 'dg': int(data[15]), 'disease_stage': int(data[16]), 'read_out':
				int(data[21]), 'createdate': data[22].split()[0]
		})
	# print(screen_info)
	return render_to_response('forms/basic_form_dialog.html', RequestContext(request, {
		'form': screen_info,
		'action': '/screen-data/0',
		'header': 'Update Screen Info',
		'layout': 'horizontal',
		'submit': 'Save'
	}))


def ajax_rora_screens(request, gid):
	if request.method == 'POST':
		screengroup_form = breezeForms.ScreenGroupInfo(request.POST)

		if screengroup_form.is_valid():
			screen = dict()
			screen['list'] = screengroup_form.cleaned_data.get('dst')
			rora.updateScreenGroupContent(screen['list'], gid)
			return HttpResponseRedirect('/dbviewer')
	else:
		# response_data = rora.getScreenGroupContent(groupID=gid)
		group_content = rora.getScreenGroup(groupID=gid)
		content_list = list()
		for each in group_content:
			content_list.append(int(each))
		screen_groupinfo = breezeForms.ScreenGroupInfo(initial={'dst': content_list})
	return render_to_response('forms/basic_form_dialog.html', RequestContext(request, {
		'form': screen_groupinfo,
		'action': '/ajax-rora-plain-screens/' + gid,
		'header': 'Update Screen Group Info',
		'layout': 'horizontal',
		'submit': 'Save'
	}))


@login_required(login_url='/')
def addtocart(request, sid=None):
	# check if this item in the cart already
	try:

		# scr = Rscripts.objects.get(id = sid)
		# print(scr.author)

		items = CartInfo.objects.get(product=sid, script_buyer=request.user)
		return HttpResponse(simplejson.dumps({"exist": "Yes"}), mimetype='application/json')
	except CartInfo.DoesNotExist:
		# print("shit")
		scripts = Rscripts.objects.get(id=sid)
		# print(scripts)
		mycart = CartInfo()
		mycart.script_buyer = request.user
		mycart.product = scripts
		if (scripts.price > 0):
			mycart.type_app = False
		else:
			mycart.type_app = True
		mycart.active = True
		mycart.save()
		return HttpResponse(simplejson.dumps({"exist": "No"}), mimetype='application/json')


@login_required(login_url='/')
def updatecart(request):
	count_mycart = CartInfo.objects.filter(script_buyer=request.user).count()
	html = render_to_string('countcart.html', {'count_mycart': count_mycart})
	return HttpResponse(html)


@login_required(login_url='/')
def mycart(request):
	# all_items = CartInfo.objects.filter(script_buyer=request.user)
	items_free = CartInfo.objects.filter(script_buyer=request.user, type_app=True)
	items_nonfree = CartInfo.objects.filter(script_buyer=request.user, type_app=False)
	html = render_to_string('cartinfo.html', {  # 'mycart_status': 'active',
	                                            'items_free': items_free,
	                                            'items_nonfree': items_nonfree  # 'all_items': all_items
	})
	return HttpResponse(html)


def ajax_rora_action(request):
	params = request.POST
	table = params.get('table', '')

	action = params.get('action', '')

	if action == 'remove':
		# Clean up row IDs:
		ids = aux.clean_up_dt_id(params.getlist('id[]', ''))

		if ids and table in ['patients', 'groups', 'content', 'screen']:
			feedback = rora.remove_row(table=table, ids=ids)

	elif action == 'create':
		data = dict()
		data['group_name'] = params.get('data[group_name]', '')
		data['group_user'] = params.get('group_author', 'unknown')

		if len(data['group_name']):
			feedback = rora.insert_row(table=table, data=data)

	elif action == 'edit':
		par = [params.get('id', '')]
		group = aux.clean_up_dt_id(par)
		screens = params.getlist('screens[]', '')

		if table in ['patients', 'groups']:
			feedback = rora.update_row(table=table, content=screens, iid=group)

	response_data = {}

	return HttpResponse(simplejson.dumps(response_data), mimetype='application/json')


@login_required(login_url='/')
def groupName(request):
	if request.method == 'POST':
		screen_group = breezeForms.screenGroup(request.POST)

		if screen_group.is_valid():
			group = dict()
			group['group_name'] = screen_group.cleaned_data.get('name')
			group['group_user'] = request.user.username
			table = 'groups'
			# print(request.user.username)
			feedback = rora.insert_row(table=table, data=group)
			# rora.update_screen(screen)
			return HttpResponseRedirect('/dbviewer')
	else:
		screen_group = breezeForms.screenGroup()
	return render_to_response('forms/basic_form_dialog.html', RequestContext(request, {
		'form': screen_group,
		'action': '/ajax-rora-groupname/',
		'header': 'Create New Group',
		'layout': 'horizontal',
		'submit': 'Save'
	}))


def reports_search(request):
	# TODO is this still in use/ finished ?
	query_string = ''
	found_entries = None
	if ('q' in request.GET) and request.GET['q'].strip():
		query_string = request.GET['q']

		entry_query = aux.get_query(query_string, ['title', 'body', ])

	# found_entries = Entry.objects.filter(entry_query).order_by('-pub_date')

	return render_to_response('search/search_results.html',
	                          {'query_string': query_string, 'found_entries': found_entries},
	                          context_instance=RequestContext(request))


@login_required(login_url='/')
def dbPolicy(request):
	userprofile = UserProfile.objects.get(user=request.user)
	userprofile.db_agreement = True
	userprofile.save()
	return HttpResponseRedirect('/dbviewer/')


@login_required(login_url='/')
def report_overview(request, rtype, iname=None, iid=None, mod=None):
	tags_data_list = list()
	files = None
	title = None

	# print rtype, iname, iid

	if mod == 'reload':
		try:
			report = Report.objects.get(id=iid)
		except ObjectDoesNotExist:
			return aux.failWith404(request, 'There is no report with id '+ iid + ' in database')
		rtype = str(report.type)
		iname =	report.name + '_bis'
		iid = report.rora_id
		try:
			# filter tags according to report type (here we pick non-draft tags):
			tags = Rscripts.objects.filter(draft="0").filter(istag="1").filter(
			report_type=ReportType.objects.get(id=report.type_id)).order_by('order')
		except ObjectDoesNotExist:
			return aux.failWith404(request, 'There is ReportType with id ' + str(report.type_id) + ' in database')
		data = pickle.loads(report.conf_params) if report.conf_params is not None and len(report.conf_params) > 0 else None
		files = json.loads(report.conf_files) if report.conf_files is not None and len(report.conf_files) > 0 else None
		title = 'ReRun report ' + report.name
	else:
		try:
			# filter tags according to report type (here we pick non-draft tags):
			tags = Rscripts.objects.filter(draft="0").filter(istag="1").filter(
				report_type=ReportType.objects.get(type=rtype)).order_by('order')
		except ObjectDoesNotExist:
			return aux.failWith404(request, 'There is ReportType with id ' + str(rtype) + ' in database')
		data = request.POST
		files = request.FILES if request.FILES else None

	overview = dict()
	overview['report_type'] = rtype
	overview['instance_name'] = iname
	overview['instance_id'] = iid
	overview['details'] = rshell.get_report_overview(rtype, iname, iid)
	manual = str(ReportType.objects.get(type=rtype).manual) or None
	overview['manual'] = None
	if manual is not None:
		overview['manual'] = settings.MEDIA_URL + manual

	if request.method == 'POST':
		#pprint.pprint(request.POST)
		# Validates input info and creates (submits) a report
		property_form = breezeForms.ReportPropsForm(request.POST, request=request)
		#property_form = breezeForms.ReportPropsForm(request=request)
		tags_data_list = breezeForms.validate_report_sections(tags, request)

		sections_valid = breezeForms.check_validity(tags_data_list)

		if property_form.is_valid() and sections_valid and mod != 'reload':
			# lunches the script generation in a separate thread in order to avoid long blocking operation
			# thread.start_new_thread(rshell.build_report, (overview, request, property_form, tags))
			rshell.build_report(overview, request, property_form, tags)
			# print request.POST['shared']
			"""
			for tag in tags:
				secID = 'Section_dbID_' + str(tag.id)
				if secID in request.POST and request.POST[secID] == '1':
					# update the statistics table
					print("hello")


				else:
					pass
			"""
			return HttpResponse(True)
		else:
			#print('Has posted, not valid')
			for x in tags_data_list:
				x['value'] = request.POST.get('Section_dbID_' + str(x['id']))
				if not 'size' in x:
					x['size'] = len(x['form'].fields)
				x['opened'] = x['value'] == '1' and not x['isvalid']
	else:
		# Renders report overview and available tags
		if mod == 'reload' and report:
			property_form = breezeForms.ReportPropsFormRE(instance=report, request=request)
			loc = str(settings.MEDIA_ROOT) + report.home
			tags_data_list = breezeForms.create_report_sections(tags, request, data, files, path=loc)
		else:
			property_form = breezeForms.ReportPropsForm(request=request)
			tags_data_list = breezeForms.create_report_sections(tags, request, data, files)
		#print('Not posted')
		for x in tags_data_list:
			if not 'value' in x: x['value'] = '0'
			x['opened'] = x['value'] == '1'

	script = list()
	access_script = list(request.user.users.all().values('name'))
	for each in access_script:
		script.append(each['name'])

	return render_to_response('search.html', RequestContext(request, {
		'overview': True,
		'reports_status': 'active',
		'overview_info': overview,
		'props_form': property_form,
		'tags_available': tags_data_list,
		'access_script': script,
		'disable_zopim': True,
	    'title': title
	}))


@login_required(login_url='/')
def showdetails(request, sid=None):
	try:
		tags = ReportType.objects.get(id=sid).rscripts_set.all()
	except ObjectDoesNotExist:  # TODO protect all alike request as such
		return aux.failWith404(request, 'There is no object with id ' + sid + ' in database')
	app_installed = request.user.users.all()

	return render_to_response('store-tags.html', RequestContext(request, {
		'tags': tags,
		'app_installed': app_installed
	})
	                          )


@login_required(login_url='/')
def search(request, what=None):
	report_type_lst = ReportType.objects.filter(search=True)
	ds = DataSet.objects.all()
	ds_count = len(ds)

	overview = dict()
	query_val = str()
	overview['report_type'] = str()

	# when query
	if request.method == 'POST':
		result_type = what

		# search for ENTITIES (right bar)
		if what == 'entity':
			report_type = request.POST['type']
			query_val = str(request.POST['query'])
			rtype = ReportType.objects.get(type=report_type)

			if rtype.search:
				# if searchable
				overview['report_type'] = report_type
				output = rshell.report_search(ds, overview['report_type'], query_val)
			else:
				# if not searchable - redirects directly to overview
				if (len(query_val) == 0):
					query_val = "Noname"
				res = '/reports/overview/%s-%s-00000' % (report_type, query_val)
				return HttpResponseRedirect(res)

		# search for DATASETS (left bar)
		if what == 'dataset':
			output = ds

		return render_to_response('search.html', RequestContext(request, {
			'search_status': 'active',
			'search_bars': True,
			'search_result': True,
			'rtypes': report_type_lst,
			'ds_count': ds_count,
			'result_type': result_type,
			'query_value': query_val,
			'overview_info': overview,
			'output': output
		}))

	else:
		pass

	return render_to_response('search.html', RequestContext(request, {'search_status': 'active', 'search_bars': True,
	                                                                  'ds_count': ds_count, 'rtypes': report_type_lst}))


@login_required(login_url='/')
def resources(request):
	usage_graph = ({'url': 'http://192.168.0.225/S/D', 'html_alt': 'queue stats on the last 24h',
	                'html_title': 'queue stats on the last 24h', 'legend': 'queue stats on the last 24h', 'href': ''},
	               {'url': 'http://192.168.0.225/S/B', 'html_alt': 'This is an exemple of another graph',
	                'html_title': 'This is an exemple of another graph',
	                'legend': 'This is an exemple of another graph', })

	return render_to_response('resources.html', RequestContext(request, {'resources_status': 'active',
	                                                                     'usage_graph': usage_graph}))


@login_required(login_url='/')
def manage_scripts(request):
	all_scripts = Rscripts.objects.all()
	paginator = Paginator(all_scripts, 25)

	# If AJAX - check page from the request
	# Otherwise return the first page
	if request.is_ajax() and request.method == 'GET':
		page = request.GET.get('page')
		try:
			# TODO change this, since it's not the way to do it
			# this session var is for the paginator to stay on the same page number after
			# sending forms (add or delete forms) for consistency and clarity
			request.session['manage-scripts-page'] = page
			scripts = paginator.page(page)
		except PageNotAnInteger:  # if page isn't an integer
			request.session['manage-scripts-page'] = 1
			scripts = paginator.page(1)
		except EmptyPage:  # if page out of bounds
			request.session['manage-scripts-page'] = paginator.num_pages
			scripts = paginator.page(paginator.num_pages)
		return render_to_response('manage-scripts-paginator.html', RequestContext(request, {'script_list': scripts}))

	else:
		if 'manage-scripts-page' in request.session:
			page = request.session['manage-scripts-page']
		else:
			page = 1
		scripts = paginator.page(page)
		return render_to_response('manage-scripts.html', RequestContext(request, {
			'resources_status': 'active',
			'script_list': scripts,
			'pagination_number': paginator.num_pages,
			'page': page  # to keep the paginator synced
		}))


@login_required(login_url='/')
def manage_pipes(request):
	all_pipelines = ReportType.objects.all()
	paginator = Paginator(all_pipelines, 10)

	# If AJAX - check page from the request
	# Otherwise ruturn the first page
	if request.is_ajax() and request.method == 'GET':
		page = request.GET.get('page')
		try:
			pipes = paginator.page(page)
		except PageNotAnInteger:  # if page isn't an integer
			pipes = paginator.page(1)
		except EmptyPage:  # if page out of bounds
			pipes = paginator.page(paginator.num_pages)

		return render_to_response('manage-pipelines-paginator.html', RequestContext(request, {'pipe_list': pipes}))
	else:
		pipes = paginator.page(1)
		return render_to_response('manage-pipes.html', RequestContext(request, {
			'resources_status': 'active',
			'pipe_list': pipes,
			'pagination_number': paginator.num_pages
		}))


@login_required(login_url='/')
def dochelp(request):
	user_profile = UserProfile.objects.get(user=request.user)
	db_access = user_profile.db_agreement
	return render_to_response('help.html', RequestContext(request, {'help_status': 'active', 'db_access': db_access}))


@login_required(login_url='/')
def store(request):
	categories = Script_categories.objects.all()
	cate = list()
	scripts = Rscripts.objects.filter(draft="0", istag="0")
	# filter cartinfo by user
	count_app = CartInfo.objects.filter(script_buyer=request.user).count()
	cat_list = dict()
	# categories = list()
	for each_cate in categories:
		if Rscripts.objects.filter(category=each_cate, istag="0", draft="0").count() > 0:
			cat_list[str(each_cate.category).capitalize()] = Rscripts.objects.filter(category=each_cate, istag="0",
			                                                                         draft="0")
			cate.append(str(each_cate.category).capitalize())
	# get the tags
	tags = Rscripts.objects.filter(istag="1")
	reports = ReportType.objects.all()
	# get all the scripts that users have installed
	app_installed = request.user.users.all()
	# get all the pipelines that user has installed
	report_installed = request.user.pipeline_access.all()
	user_profile = UserProfile.objects.get(user=request.user)
	db_access = user_profile.db_agreement
	'''
    for script in all_scripts:
        if str(script.category).capitalize() not in categories:
            categories.append(str(script.category).capitalize())
            cat_list[str(script.category).capitalize()] = Rscripts.objects.filter(category__exact=str(script.category)).filter(draft="0").filter(istag="0")
    '''
	return render_to_response('store.html', RequestContext(request, {
		'store_status': 'active',
		'cate': cate,
		'script_list': scripts,
		'cat_list': sorted(cat_list.iteritems()),
		'count_mycart': count_app,
		'reports': reports,
		'app_installed': app_installed,
		'report_installed': report_installed,
		'db_access': db_access  # 'tags': tags
	}))


@login_required(login_url='/')
def deletecart(request, sid=None):
	try:
		items = CartInfo.objects.get(product=sid, script_buyer=request.user)
		cate = items.type_app
		count_app = CartInfo.objects.filter(type_app=cate, script_buyer=request.user).count()
		items.delete()
		return HttpResponse(simplejson.dumps({"delete": "Yes", 'count_app': count_app}), mimetype='application/json')
	except CartInfo.DoesNotExist:
		return HttpResponse(simplejson.dumps({"delete": "No"}), mimetype='application/json')


@login_required(login_url='/')
def deletefree(request):
	try:
		items = CartInfo.objects.filter(type_app=True, script_buyer=request.user)
		items.delete()
		return HttpResponse(simplejson.dumps({"delete": "Yes"}), mimetype='application/json')
	except CartInfo.DoesNotExist:
		return HttpResponse(simplejson.dumps({"delete": "No"}), mimetype='application/json')


@login_required(login_url='/')
def install(request, sid=None):
	try:
		# get the script
		scr = Rscripts.objects.get(id=sid)
		scr.access.add(request.user)
		return HttpResponse(simplejson.dumps({"install_status": "Yes"}), mimetype='application/json')
	except Rscripts.DoesNotExist:
		return HttpResponse(simplejson.dumps({"install_status": "No"}), mimetype='application/json')


@login_required(login_url='/')
def installreport(request, sid=None):
	try:
		# get the report type by id
		report_type = ReportType.objects.get(id=sid)
		report_type.access.add(request.user)
		return HttpResponse(simplejson.dumps({"install_status": "Yes"}), mimetype='application/json')
	except ReportType.DoesNotExist:
		return HttpResponse(simplejson.dumps({"install_status": "No"}), mimetype='application/json')


######################################
###      SUPPLEMENTARY VIEWS       ###
######################################

@login_required(login_url='/')
def script_editor(request, sid=None, tab=None):
	script = Rscripts.objects.get(id=sid)

	f_basic = breezeForms.ScriptBasics(edit=script.name, initial={'name': script.name, 'inline': script.inln})
	f_attrs = breezeForms.ScriptAttributes(instance=script)
	f_logos = breezeForms.ScriptLogo()

	if tab is None:
		tab = '-general_tab'

	return render_to_response('script-editor.html', RequestContext(request, {
		str(tab)[1:]: 'active',
		'resources_status': 'active',
		'script': script,
		'basic_form': f_basic,
		'attr_form': f_attrs,
		'logo_form': f_logos
	}))


@login_required(login_url='/')
def script_editor_update(request, sid=None):
	script = Rscripts.objects.get(id=sid)
	if request.method == 'POST':
		# General Tab
		if request.POST['form_name'] == 'general':
			f_basic = breezeForms.ScriptBasics(script.name, request.POST)
			if f_basic.is_valid():
				rshell.update_script_dasics(script, f_basic)
				return HttpResponseRedirect('/resources/scripts/script-editor/' + str(script.id) + '-general_tab')
		else:
			f_basic = breezeForms.ScriptBasics(edit=script.name, initial={'name': script.name, 'inline': script.inln})

		# Description Tab
		if request.POST['form_name'] == 'description' and request.is_ajax():
			return HttpResponse(rshell.update_script_description(script, request.POST))
		else:
			pass

		# Attributes Tab
		if request.POST['form_name'] == 'attributes':
			f_attrs = breezeForms.ScriptAttributes(request.POST, instance=script)
			if f_attrs.is_valid():
				f_attrs.save()
				script.creation_date = datetime.now()
				script.save()
				return HttpResponseRedirect('/resources/scripts/script-editor/' + str(script.id) + '-attribut_tab')
		else:
			f_attrs = breezeForms.ScriptAttributes(instance=script)

		# Form Builder Tab
		if request.POST['form_name'] == 'xml_data' and request.is_ajax():
			return HttpResponse(rshell.update_script_xml(script, request.POST['xml_data']))
		else:
			pass  # return HttpResponse(False)

		# Sources Tab
		if request.POST['form_name'] == 'source_files' and request.is_ajax():
			rshell.update_script_sources(script, request.POST)
			return HttpResponse(True)
		else:
			pass  # return HttpResponse(False)

		# Logos Tab
		if request.POST['form_name'] == 'logos':
			f_logos = breezeForms.ScriptLogo(request.POST, request.FILES)
			if f_logos.is_valid():
				rshell.update_script_logo(script, request.FILES['logo'])
				return HttpResponseRedirect('/resources/scripts/script-editor/' + str(script.id) + '-logos_tab')
		else:
			f_logos = breezeForms.ScriptLogo()

		return render_to_response('script-editor.html', RequestContext(request, {
			'resources_status': 'active',
			'script': script,
			'basic_form': f_basic  # 'attr_form': f_attrs,  # 'logo_form': f_logos
		}))
	# if NOT POST
	return HttpResponseRedirect('/resources/scripts/script-editor/' + script.id)


@login_required(login_url='/')
def get_form(request, sid=None):
	script = Rscripts.objects.get(id=sid)
	builder_form = ""

	if request.method == 'GET' and sid is not None:
		file_path = rshell.settings.MEDIA_ROOT + str(script.docxml)

		if os.path.isfile(file_path):
			tree = xml.parse(file_path)
			if tree.getroot().find('builder') is not None:
				builder_form = tree.getroot().find('builder').text
			else:
				builder_form = "False"
		else:
			builder_form = "False"

	return HttpResponse(builder_form)


@login_required(login_url='/')
def get_rcode(request, sid=None, sfile=None):
	script = Rscripts.objects.get(id=sid)
	rcode = ""
	if request.method == 'GET' and sid is not None:

		if sfile == 'Header':
			file_path = rshell.settings.MEDIA_ROOT + str(script.header)
		elif sfile == 'Main':
			file_path = rshell.settings.MEDIA_ROOT + str(script.code)

		if os.path.isfile(file_path):
			handle = open(file_path, 'r')
			rcode = handle.read()
			handle.close()
		else:
			rcode = "file does not exist"

	return HttpResponse(rcode)


@login_required(login_url='/')
def delete_job(request, jid, state):
	job = Jobs.objects.get(id=jid)
	# Enforce access rights
	if job.juser != request.user:
		raise PermissionDenied
	if job.status == "scheduled":
		tab = "scheduled"
	elif job.status == "active" or job.status == "queued_active":
		tab = "current"
	else:
		tab = "history"
	rshell.del_job(job)
	return HttpResponseRedirect('/jobs/' + tab)


@login_required(login_url='/')
def delete_script(request, sid):
	script = Rscripts.objects.get(id=sid)
	# Enforce access rights
	if script.author != request.user:
		raise PermissionDenied
	rshell.del_script(script)
	return HttpResponseRedirect('/resources/scripts/')


@login_required(login_url='/')
def delete_pipe(request, pid):
	pipe = ReportType.objects.get(id=pid)
	# Enforce access rights
	if pipe.author != request.user:
		raise PermissionDenied
	rshell.del_pipe(pipe)
	return HttpResponseRedirect('/resources/pipes/')


@login_required(login_url='/')
def delete_report(request, rid, redir):
	if redir == '-dash':
		redir = '/jobs/history'
	else:
		redir = '/reports/'

	report = Report.objects.get(id=rid)
	# Enforce access rights
	if report.author != request.user:
		raise PermissionDenied
	rshell.del_report(report)
	return HttpResponseRedirect(redir)


@login_required(login_url='/')
def edit_report_access(request, rid):
	report_inst = Report.objects.get(id=rid)
	form_action = 'reports/edit_access/' + str(rid)
	form_title = 'Edit "' + report_inst.name + '" access'

	# Enforce access rights
	if report_inst.author != request.user:
		raise PermissionDenied

	if request.method == 'POST':
		# Validates input info and creates (submits) a report
		property_form = breezeForms.EditReportSharing(request.POST, instance=report_inst)
		if property_form.is_valid():
			property_form.save()
			return HttpResponse(True)

	property_form = breezeForms.EditReportSharing(instance=report_inst)

	pprint.pprint(vars(property_form.fields['shared']))

	return render_to_response('forms/basic_form_dialog.html', RequestContext(request, {
		'form': property_form,
		'action': form_action,
		'header': form_title,
		'layout': 'horizontal',
		'submit': 'Save'
	}))


@login_required(login_url='/')
def delete_project(request, pid):
	project = Project.objects.get(id=pid)
	# Enforce access rights
	if project.author != request.user:
		raise PermissionDenied
	aux.delete_project(project)

	return HttpResponseRedirect('/home/projects')


@login_required(login_url='/')
def delete_group(request, gid):
	group = Group.objects.get(id=gid)
	# Enforce access rights
	if group.author != request.user:
		raise PermissionDenied
	aux.delete_group(group)

	return HttpResponseRedirect('/home/groups')


@login_required(login_url='/')
def read_descr(request, sid=None):
	script = Rscripts.objects.get(id=sid)
	return render_to_response('forms/descr_modal.html', RequestContext(request, {'scr': script}))


# Wrapper for report edition/ReRunning
@login_required(login_url='/')
def edit_report(request, jid=None, mod=None):
	return report_overview(request, rtype=None, iid=jid, mod='reload')


@login_required(login_url='/')
def edit_reportMMMMM(request, jid=None, mod=None):
	if not settings.DEV_MODE:
		return HttpResponseRedirect('/jobs')

	report = Report.objects.get(id=jid)
	rtype = report.type
	iname = report.name + '_bis'
	# filter tags according to report type (here we pick non-draft tags):
	tags = Rscripts.objects.filter(draft="0").filter(istag="1").filter(
		report_type=ReportType.objects.get(id=report.type_id)).order_by('order')
	data = str(pickle.loads(report.conf_params) if report.conf_params else '')
	files = str(json.loads(report.conf_files) if report.conf_files is not None and len(report.conf_files) > 0 else None)
	return HttpResponse(data + '\n' + files)


@login_required(login_url='/')
def check_reports(request):
	#reports = Report.objects.all().order_by('-created')
	reports = Report.objects.filter(status='succeed').order_by('-created')
	i = 0
	malst = list()
	for each in reports:
		local_path, path_to_file, fileE, folderE = aux.get_report_path_test(each, None, True)
		if not folderE or not fileE:
			malst.append({
			'id': str(each.id),
			'type': str(each.type),
			'created': str(each.created),
			'author': unicode(each.author.get_full_name() or each.author.username),
			'name': str(each.name),
			'project': str(each.project),
			'path': (local_path, path_to_file, fileE, folderE),
			})
			i += 1

	return render_to_response('list.html', RequestContext(request, {
	'reports': malst,
	'missing': i,
	'total': reports.count,
	}))


@login_required(login_url='/')
def edit_job(request, jid=None, mod=None):
	job = Jobs.objects.get(id=jid)
	tree = xml.parse(str(settings.MEDIA_ROOT) + str(job.docxml))
	user_info = User.objects.get(username=request.user)

	if mod is not None:
		mode = 'replicate'
		tmpname = str(job.jname) + '_REPL'
		edit = ""
	else:
		mode = 'edit'
		tmpname = str(job.jname)
		edit = str(job.jname)

	if request.method == 'POST':
		head_form = breezeForms.BasicJobForm(request.user, edit, request.POST)
		custom_form = breezeForms.form_from_xml(xml=tree, req=request, usr=request.user)
		if head_form.is_valid() and custom_form.is_valid():

			if mode == 'replicate':
				tmpscript = job.script
				job = Jobs()
				job.script = tmpscript
				job.status = "scheduled"
				job.juser = request.user
				job.progress = 0
			else:
				loc = rshell.get_job_folder(str(job.jname), str(job.juser.username))
				shutil.rmtree(loc)

			rshell.assemble_job_folder(str(head_form.cleaned_data['job_name']), str(request.user), tree, custom_form,
			                           str(job.script.code), str(job.script.header), request.FILES)

			job.jname = head_form.cleaned_data['job_name']
			job.jdetails = head_form.cleaned_data['job_details']

			job.rexecut.save('name.r', File(open(str(settings.TEMP_FOLDER) + 'rexec.r')))
			job.docxml.save('name.xml', File(open(str(settings.TEMP_FOLDER) + 'job.xml')))
			job.rexecut.close()
			job.docxml.close()

			rshell.schedule_job(job, request.POST)

			# improve the manipulation with XML - tmp folder not a good idea!
			os.remove(str(settings.TEMP_FOLDER) + 'job.xml')
			os.remove(str(settings.TEMP_FOLDER) + 'rexec.r')
			return HttpResponseRedirect('/jobs')
	else:
		head_form = breezeForms.BasicJobForm(user=request.user, edit=str(job.jname),
		                                     initial={'job_name': str(tmpname), 'job_details': str(job.jdetails),
		                                              'report_to': str(job.email if job.email else user_info.email)})
		custom_form = breezeForms.form_from_xml(xml=tree, usr=request.user)

	return render_to_response('forms/user_modal.html', RequestContext(request, {
		'url': "/jobs/edit/" + str(jid),
		'name': str(job.script.name),
		'inline': str(job.script.inln),
		'headform': head_form,
		'custform': custom_form,
		'layout': "horizontal",
		'mode': mode,
		'email': user_info.email
	}))


@login_required(login_url='/')
def create_job(request, sid=None):
	script = Rscripts.objects.get(id=sid)

	new_job = Jobs()
	tree = xml.parse(str(settings.MEDIA_ROOT) + str(script.docxml))
	script_name = str(script.name)  # tree.getroot().attrib['name']
	script_inline = script.inln
	user_info = User.objects.get(username=request.user)

	mail_addr = user_info.email
	mails = {'Started': '', 'Ready': '', 'Aborted': ''}
	# print(request.method)
	if request.method == 'POST':
		# after fill the forms for creating the new job
		head_form = breezeForms.BasicJobForm(request.user, None, request.POST)
		custom_form = breezeForms.form_from_xml(xml=tree, req=request, usr=request.user)
		mail_addr = request.POST['report_to']
		for key in mails:
			if key in request.POST:
				mails[key] = u'checked'
				new_job.mailing += request.POST[key]

		if head_form.is_valid() and custom_form.is_valid():
			rshell.assemble_job_folder(str(head_form.cleaned_data['job_name']), str(request.user), tree, custom_form,
			                           str(script.code), str(script.header), request.FILES)
			new_job.jname = head_form.cleaned_data['job_name']
			new_job.jdetails = head_form.cleaned_data['job_details']
			new_job.script = script
			# new_job.status = request.POST['job_status']
			new_job.status = u"scheduled"
			new_job.juser = request.user
			# TODO finish testing and debug
			new_job.email = mail_addr
			new_job.progress = 0
			new_job.rexecut.save('name.r', File(open(str(settings.TEMP_FOLDER) + 'rexec.r')))
			new_job.docxml.save('name.xml', File(open(str(settings.TEMP_FOLDER) + 'job.xml')))
			new_job.rexecut.close()
			new_job.docxml.close()

			rshell.schedule_job(new_job, request.POST)
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
			if u'run_job' in request.POST:
				run_script(request, new_job.id)
				state = "current"
			# p = Process(target=rshell.run_job, args=(new_job))
			#p.start()
			#print("running jobs")
			if u'action' in request.POST:
				if request.POST['action'] == 'run_job':
					run_script(request, new_job.id)
					state = "current"

			print vars(request.POST)

			# return HttpResponseRedirect('/jobs/')
			#request = HttpResponse()
			#request.method = "GET"
			return jobs(request, state)
	else:
		mails = {'Started': u'checked', 'Ready': u'checked', 'Aborted': u'checked'}
		head_form = breezeForms.BasicJobForm(user=request.user, edit=None, initial={'report_to': mail_addr})
		custom_form = breezeForms.form_from_xml(xml=tree, usr=request.user)

	data = {
		'url': "/scripts/apply-script/" + str(sid),
		'name': script_name,
		'inline': script_inline,
		'headform': head_form,
		'custform': custom_form,
		'layout': "horizontal",
		'mode': 'create',
		'report_to': mail_addr
	}
	data.update(mails)

	return render_to_response('forms/user_modal.html', RequestContext(request, data))


@login_required(login_url='/')
def run_script(request, jid):
	job = Jobs.objects.get(id=jid)
	script = str(job.script.code)
	p = Process(target=rshell.run_job, args=(job, script))
	p.start()

	return HttpResponseRedirect('/jobs/')


@login_required(login_url='/')
def abort_sge(request, id, type):
	try:
		if type == "report":
			item = Report.objects.get(id=id)
		elif type == "job":
			item = Jobs.objects.get(id=id)
	except (Report.DoesNotExist, Jobs.DoesNotExist):
		return jobs(request, error_msg="job/report " + id + " does not exists\nPlease contact Breeze support")

	s = rshell.abort_report(item)

	if s == True:
		return HttpResponseRedirect('/jobs/')
	else:
		return jobs(request, error_msg=s + "\nOn DRMAA job/report id " + id + "\nPlease contact Breeze support")


@login_required(login_url='/')
def abort_report(request, rid):
	if settings.DEBUG: print("aborting report")

	return abort_sge(request, rid, "report")


@login_required(login_url='/')
def abort_job(request, jid):
	if settings.DEBUG: print("aborting job")

	return abort_sge(request, jid, "job")


@login_required(login_url='/')
def delete_param(request, which):
	storage.del_param(which)
	local_representation = storage.get_param_list()
	return render_to_response('new-script.html', RequestContext(request, {
		'hidden_form': storage.hidden_form,
		'general_form': storage.form_general,
		'params_form': local_representation,
		'source_form': storage.form_sources,
		'layout': 'inline',
		'curr_tab': 'params',
		'status': 'info',
	}))


@login_required(login_url='/')
def append_param(request, which):
	basic_form = breezeForms.AddBasic(request.POST or None)
	extra_form = None
	extra_form_valid = True
	if which == 'NUM':
		msg = 'NUMERIC'
	elif which == 'CHB':
		msg = 'CHECK BOX'
	elif which == 'DRP':
		msg = 'DROP DOWN'
		extra_form = breezeForms.AddOptions(request.POST or None)
		extra_form_valid = extra_form.is_valid()
	elif which == 'RAD':
		msg = 'RADIO BUTTONS'
		extra_form = breezeForms.AddOptions(request.POST or None)
		extra_form_valid = extra_form.is_valid()
	elif which == 'TEX':
		msg = 'TEXT INPUT'
	elif which == 'TAR':
		msg = 'TEXT AREA'
	elif which == 'FIL':
		msg = 'FILE INPUT'
	elif which == 'HED':
		msg = 'SECTION NAME'
	elif which == 'TPL':
		msg = 'TEMPLATE INPUT'
		extra_form = breezeForms.AddTemplateInput(request.POST or None)
		extra_form_valid = extra_form.is_valid()
	elif which == 'DTS':
		msg = 'DATASET SELECTOR'
		extra_form = breezeForms.AddDatasetSelect(request.POST or None)
		extra_form_valid = extra_form.is_valid()
	else:
		pass

	if basic_form.is_valid() and extra_form_valid:
		# implement adding new param as a separate function in STORAGE class
		storage.form_details[str(basic_form.cleaned_data['inline_var'])] = list()
		storage.form_details[str(basic_form.cleaned_data['inline_var'])].append(basic_form)
		storage.form_details[str(basic_form.cleaned_data['inline_var'])].append(extra_form)
		local_representation = storage.get_param_list()
		return render_to_response('new-script.html', RequestContext(request, {
			'hidden_form': storage.hidden_form,
			'general_form': storage.form_general,
			'params_form': local_representation,
			'source_form': storage.form_sources,
			'layout': 'inline',
			'curr_tab': 'params',
			'status': 'info',
		}))
	return render_to_response('forms/new_param_modal.html', RequestContext(request, {
		'msg': msg, 'basic': basic_form, 'extra': extra_form, "type": which,
	}))


@login_required(login_url='/')
@permission_required('breeze.add_rscripts', login_url="/")
def create_script(request):
	tab = 'general'
	if request.method == 'POST':
		storage.hidden_form = breezeForms.HiddenForm(request.POST)
		tab = storage.hidden_form['next'].value()
		if storage.hidden_form['curr'].value() == 'general':
			storage.form_general = breezeForms.ScriptMainForm(request.POST, request.FILES)
			storage.form_general.is_valid()
			local_representation = storage.get_param_list()
		elif storage.hidden_form['curr'].value() == 'params':
			local_representation = storage.get_param_list()
		elif storage.hidden_form['curr'].value() == 'source':
			storage.form_sources = breezeForms.ScriptSources(request.POST, request.FILES)
			local_representation = storage.get_param_list()
			if storage.form_sources.is_valid():
				storage.code = request.FILES['code']
		elif storage.hidden_form['curr'].value() == 'summary':
			pass
	else:
		storage.hidden_form = breezeForms.HiddenForm()
		storage.form_general = breezeForms.ScriptMainForm()
		storage.form_details = OrderedDict()
		local_representation = storage.get_param_list()
		storage.form_sources = breezeForms.ScriptSources()

	return render_to_response('new-script.html', RequestContext(request, {
		'hidden_form': storage.hidden_form,
		'general_form': storage.form_general,
		'params_form': local_representation,
		'source_form': storage.form_sources,
		'layout': 'inline',
		'curr_tab': tab,
		'status': 'info',
		'scripts_status': 'active',
	}))


@login_required(login_url='/')
def save(request):
	# validate form_details also somehow in the IF below
	if storage.form_general.is_valid() and storage.form_sources.is_valid():
		# .xml_from_form() - creates doc in tmp for now
		breezeForms.xml_from_form(storage.form_general, storage.form_details, storage.form_sources)
		rshell.build_header(storage.form_sources.cleaned_data['header'])

		dbinst = storage.form_general.save(commit=False)

		dbinst.author = request.user
		dbinst.code = storage.code
		dbinst.docxml.save('name.xml', File(open(str(settings.TEMP_FOLDER) + 'test.xml')))
		dbinst.header.save('name.txt', File(open(str(settings.TEMP_FOLDER) + 'header.txt')))

		dbinst.save()

		# improve the manipulation with XML - tmp folder not a good idea!
		os.remove(str(settings.TEMP_FOLDER) + 'test.xml')
		os.remove(str(settings.TEMP_FOLDER) + 'header.txt')

		return HttpResponseRedirect('/scripts/')
	else:
		# need an error handler here!
		return HttpResponseRedirect('/scripts/')


def show_rcode(request, jid):
	job = Jobs.objects.get(id=jid)
	docxml = xml.parse(str(settings.MEDIA_ROOT) + str(job.docxml))
	script = job.jname  # docxml.getroot().attrib["name"]
	inline = job.script.inln  # docxml.getroot().find('inline').text

	fields = list()
	values = list()
	input_array = docxml.getroot().find('inputArray')
	if input_array != None:
		for input_item in input_array:
			fields.append(input_item.attrib["comment"])
			values.append(input_item.attrib["val"])
	parameters = zip(fields, values)

	return render_to_response('forms/code_modal.html', RequestContext(request, {
		'name': str(job.jname),
		'script': script,
		'inline': inline,
		'description': str(job.jdetails),
		'input': parameters,
	}))


def veiw_project(request, pid):
	project = Project.objects.get(id=pid)
	context = {'project': project}

	return render_to_response('forms/project_info.html', RequestContext(request, context))


def view_group(request, gid):
	group = Group.objects.get(id=gid)
	context = {'group': group}

	return render_to_response('forms/group_info.html', RequestContext(request, context))


@login_required(login_url='/')
def send_zipfile(request, jid, mod=None):
	job = Jobs.objects.get(id=jid)
	loc = rshell.get_job_folder(str(job.jname), str(job.juser.username))
	files_list = os.listdir(loc)
	zipname = 'attachment; filename=' + str(job.jname) + '.zip'

	temp = tempfile.TemporaryFile()
	archive = zipfile.ZipFile(temp, 'w', zipfile.ZIP_DEFLATED)

	if mod is None:
		for item in files_list:
			archive.write(loc + item, str(item))
	elif mod == "-code":
		for item in files_list:
			if fnmatch.fnmatch(item, '*.r') or fnmatch.fnmatch(item, '*.Rout'):
				archive.write(loc + item, str(item))
	elif mod == "-result":
		for item in files_list:
			if not fnmatch.fnmatch(item, '*.xml') and not fnmatch.fnmatch(item, '*.r*') and not fnmatch.fnmatch(item,
			                                                                                                    '*.sh*'):
				archive.write(loc + item, str(item))

	archive.close()
	wrapper = FileWrapper(temp)
	response = HttpResponse(wrapper, content_type='application/zip')
	response['Content-Disposition'] = zipname  # 'attachment; filename=test.zip'
	response['Content-Length'] = temp.tell()
	temp.seek(0)
	return response


@login_required(login_url='/')
def send_template(request, name):
	template = InputTemplate.objects.get(name=name)
	path_to_file = str(settings.MEDIA_ROOT) + str(template.file)
	f = open(path_to_file, 'r')
	myfile = File(f)
	response = HttpResponse(myfile, mimetype='application/force-download')
	folder, slash, file = str(template.file).rpartition('/')
	response['Content-Disposition'] = 'attachment; filename=' + file
	return response


@login_required(login_url='/')
def send_file(request, ftype, fname):
	"""
        Supposed to be generic function that can send single file to client.
        Each IF case prepare dispatch data of a certain type.
        ! Should substitute send_template() function soon !
    """
	# TODO : substitute with send_template() ?
	if ftype == 'dataset':
		try:
			fitem = DataSet.objects.get(name=str(fname))
		except ObjectDoesNotExist:
			return aux.failWith404(request, 'There is no report with id ' + str(fname) + ' in database')
		# TODO Enforce user access restrictions ?
		local_path, path_to_file = aux.get_report_path(fitem)

	if ftype == 'report':
		try:
			fitem = Report.objects.get(id=str(fname))
		except ObjectDoesNotExist:
			return aux.failWith404(request, 'There is no report with id ' + str(fname) + ' in database')
		#  Enforce user access restrictions
		if request.user not in fitem.shared.all() and fitem.author != request.user:
			raise PermissionDenied

		local_path, path_to_file = aux.get_report_path(fitem)

	f = open(path_to_file, 'r')
	myfile = File(f)
	response = HttpResponse(myfile, mimetype='application/force-download')
	folder, slash, file = local_path.rpartition('/')
	response['Content-Disposition'] = 'attachment; filename=' + file
	return response


# TODO delete
@login_required(login_url='/')
def report_shiny_view(request, rid, fname=None):
	try:
		fitem = Report.objects.get(id=rid)
	except ObjectDoesNotExist:
		return aux.failWith404(request, 'There is no report with id '+ rid +' in DB')

	# Enforce user access restrictions
	if request.user not in fitem.shared.all() and fitem.author != request.user:
		raise PermissionDenied

	source = "Test"
	title = fitem.name

	return render_to_response('shiny.html', RequestContext(request, {
		'source': source,
		'title': title
	}))


# TODO delete
@login_required(login_url='/')
def report_shiny_view2(request, rid, fname=None):
	try:
		fitem = Report.objects.get(id=rid)
	except ObjectDoesNotExist:
		return aux.failWith404(request, 'There is no report with id ' + rid + ' in DB')

	# Enforce user access restrictions
	if request.user not in fitem.shared.all() and fitem.author != request.user:
		raise PermissionDenied

	source = "Test"
	title = fitem.name

	return render_to_response('shiny2.html', RequestContext(request, {
	'source': source,
	'title': title
	}))


# Shiny tab access from inside
@login_required(login_url='/')
def report_shiny_view_tab(request, rid):
	return report_shiny_view_tab_merged(request, rid)


# Shiny tab access from outside (with the key)
def report_shiny_view_tab_out(request, key):
	try:
		fitem = Report.objects.get(shiny_key=key)
		return report_shiny_view_tab_merged(request, fitem.id, True)
	except ObjectDoesNotExist:
		return aux.failWith404(request)


# Shiny tab
# DO NOT CALL THIS VIEW DIRECTLY
def report_shiny_view_tab_merged(request, rid, outside=False):
	try:
		fitem = Report.objects.get(id=rid)
	except ObjectDoesNotExist:
		return aux.failWith404(request, 'There is no report with id ' + rid + ' in DB')

	if not outside:
		base_url = '/shiny/'
		# Enforce user access restrictions
		if request.user not in fitem.shared.all() and fitem.author != request.user:
			raise PermissionDenied
	else:
		base_url = '/shiny-out/' + str(fitem.shiny_key) + '/'

	pages = OrderedDict([])
	args = ''
	source = "Test"
	title = fitem.name

	if fitem.rora_id > 0:
		args = '?' + urlencode([('path', fitem.home), ('roraId', str(fitem.rora_id))])
		# args = '?id=' + str(fitem.id)
		pages = OrderedDict([('Test', 'screenApp1')])

	# TODO should improve this part
	pages.update(OrderedDict([
		('Quality Control', 'blk1.1'),
		('Quality Control (full)', 'qc_full'),
		('Quality Control (extended)', 'qc_ext'),
		('QC 2', 'blk1.2'),
		('Curve', 'blk1.3'),
		('Curve 2', 'blk1.4'),
		('DSS top50', 'blk2.1'),
		('DSS top50 2', 'blk2.2'),
		('Future Genomics', 'blk2.3'),
		('Somatic', 'blk2.4'),
		('Comparaison to other relevant samples', 'blk3.1'),
		('Clinicaly relevant other drug', 'blk3.2'),
		('Drug - Mutations - Patient', 'blk3.3')
	]))

	return render_to_response('shiny_tab.html', RequestContext(request, {
	'source': source,
	'args': args,
	'pages': pages,
	'base_url': base_url,
	'title': title
	}))


# Wrapper for ShinyApp accessed from inside (login + user access to said report)
@csrf_exempt
@login_required(login_url='/')
def report_shiny_in_wrapper(request, path):
	if 'path' in request.GET and 'roraId' in request.GET:
		try:
			fitem = Report.objects.get(home=request.GET.get('path'))
			# qs = urlencode([('path', fitem.home), ('roraId', str(fitem.rora_id))])
		except ObjectDoesNotExist:
			return aux.failWith404(request)
		# Enforce user access restrictions
		if request.user not in fitem.shared.all() and fitem.author != request.user:
			raise PermissionDenied

	return aux.proxy_to(request, path, settings.SHINY_TARGET_URL)


# Wrapper for ShinyApp accessed from OUTSIDE (key needed)
@csrf_exempt
def report_shiny_out_wrapper(request, key, path):
	try:
		fitem = Report.objects.get(shiny_key=key)
	except ObjectDoesNotExist:
		return aux.failWith404(request)

	return aux.proxy_to(request, path, settings.SHINY_TARGET_URL)


@login_required(login_url='/')
def report_file_view(request, rid, fname=None):
	return report_file_server(request, rid, 'view', fname)


@login_required(login_url='/')
def report_file_wrap(request, rid, rest, fname=None):
	return report_file_server(request, rid, 'view', fname)


@login_required(login_url='/')
def report_file_wrap2(request, rid, fname=None):
	return report_file_server(request, rid, 'view', fname)


@login_required(login_url='/')
def report_file_get(request, rid, fname=None):
	return report_file_server(request, rid, 'get', fname)


@login_required(login_url='/')
def report_file_server(request, rid, type, fname=None):
	"""
        Serve report files, while enforcing access rights
    """
	#
	try:
		fitem = Report.objects.get(id=rid)
	except ObjectDoesNotExist:
		return aux.failWith404(request, 'There is no report with id ' + rid + ' in DB')

	# Enforce user access restrictions
	if request.user not in fitem.shared.all() and fitem.author != request.user and not request.user.is_superuser:
		raise PermissionDenied

	local_path, path_to_file = aux.get_report_path(fitem, fname)

	mime = MimeTypes()
	url = urllib.pathname2url(path_to_file)
	mime_type, encoding = mime.guess_type(url)
	mime_type = mime_type or 'application/octet-stream'

	try:
		f = open(path_to_file, 'r')
		myfile = File(f)

		response = HttpResponse(myfile, mimetype=mime_type)
		folder, slash, file = local_path.rpartition('/')
		if type == 'get':
			response['Content-Disposition'] = 'attachment; filename=' + file
		else:
			response['Content-Disposition'] = 'filename=' + file
		return response
	except IOError:
		print 'IOError', path_to_file
		return aux.failWith404(request, 'File not found in expected location')


@login_required(login_url='/')
def update_jobs(request, jid, item):
	if item == 'script':
		job = Jobs.objects.get(id=jid)
		sge_status = rshell.track_sge_job(job)
		# request job instance again to be sure that the data is updated
		response = dict(id=job.id, name=str(job.jname), staged=str(job.staged), status=str(job.status),
		                progress=job.progress, sge=sge_status)
	else:
		report = Report.objects.get(id=jid)
		sge_status = rshell.track_sge_job(report)
		# request job instance again to be sure that the data is updated
		response = dict(id=report.id, name=str(report.name), staged=str(report.created), status=str(report.status),
		                progress=report.progress, sge=sge_status)

	return HttpResponse(simplejson.dumps(response), mimetype='application/json')


@login_required(login_url='/')
def send_dbcontent(request, content, iid=None):
	response = dict()

	if content == "datasets":
		clist = DataSet.objects.all()
	elif content == "templates":
		clist = InputTemplate.objects.all()
	elif content == "description":
		script = Rscripts.objects.get(id=int(iid[1:]))
		response["description"] = script.details
		return HttpResponse(simplejson.dumps(response), mimetype='application/json')
	else:
		# return empty dictionary if content was smth creepy
		return HttpResponse(simplejson.dumps(response), mimetype='application/json')

	for item in clist:
		response[item.name] = item.description

	return HttpResponse(simplejson.dumps(response), mimetype='application/json')


@login_required(login_url='/')
def builder(request):
	form = breezeForms.ScriptMainForm()
	return render_to_response('form-builder.html', RequestContext(request, {'forma': form, }))


@login_required(login_url='/')
def new_script_dialog(request):
	"""
		This view provides a dialog to create a new script and save new script in DB.
		If script name is valid, the view creates an instance in DB which has the following fields completed:
		Name, Category, Creation Date, Author and Script's root folder.
	"""
	form = breezeForms.NewScriptDialog(request.POST or None)

	if form.is_valid():
		sname = str(form.cleaned_data.get('name', None))
		sinline = str(form.cleaned_data.get('inline', None))
		newpath = rshell.init_script(sname, sinline, request.user)
		return manage_scripts(request)  # call back the list rendering function
	# return HttpResponseRedirect('/resources/scripts/')

	return render_to_response('forms/basic_form_dialog.html', RequestContext(request, {
		'form': form,
		'action': '/new-script/',
		'header': 'Create New Script',
		'layout': 'horizontal',
		'submit': 'Add'
	}))


@login_required(login_url='/')
def new_rtype_dialog(request):
	"""
        This view provides a dialog to create a new report type in DB.
    """
	form = breezeForms.NewRepTypeDialog(request.POST or None)

	if form.is_valid():
		rshell.init_pipeline(form)
		return HttpResponse(True)

	return render_to_response('forms/basic_form_dialog.html', RequestContext(request, {
		'form': form,
		'action': '/new-rtype/',
		'header': 'Create New Report Type',
		'layout': 'horizontal',
		'submit': 'Add'
	}))


@login_required(login_url='/')
def user_list(request):
	userlst = User.objects.all()

	lst = dict()
	for each in userlst:
		lst[str(each)] = each.get_full_name()

	data = simplejson.dumps(lst)
	return HttpResponse(data, mimetype='application/json')


@login_required(login_url='/')
def edit_rtype_dialog(request, pid=None, mod=None):
	"""
        This view provides a dialog to edit a report type in DB.
        @type request: django.db.models.query.QuerySet
        @type pid: int
    """
	# file_data = ""
	instance = ReportType.objects.get(id=pid)
	if request.method == "POST":
		#
		if request.FILES is not None:
			form = breezeForms.NewRepTypeDialog(request.POST, request.FILES, instance=instance)
		else:
			form = breezeForms.NewRepTypeDialog(request.POST, instance=instance)

		form.save()

		return HttpResponse(True)
	else:
		form = breezeForms.NewRepTypeDialog(instance=instance)

	# TODO add multiple file management for tutorials
	return render_to_response('forms/basic_form_dialog.html', RequestContext(request, {
		'form': form,
		'action': '/resources/pipes/pipe-editor/',
		'header': 'Edit Report Type',
		'layout': 'horizontal',
		'submit': 'Save'
	}))


@login_required(login_url='/')
def new_project_dialog(request):
	"""
        This view provides a dialog to create a new Project in DB.
    """
	project_form = breezeForms.NewProjectForm(request.POST or None)

	if project_form.is_valid():
		aux.save_new_project(project_form, request.user)
		return HttpResponseRedirect('/home/projects')

	return render_to_response('forms/basic_form_dialog.html', RequestContext(request, {
		'form': project_form,
		'action': '/projects/create',
		'header': 'Create New Project',
		'layout': 'horizontal',
		'submit': 'Save'
	}))


@login_required(login_url='/')
def new_group_dialog(request):
	"""
		This view provides a dialog to create a new Group in DB.
	"""
	group_form = breezeForms.GroupForm(request.POST or None)

	if group_form.is_valid():
		aux.save_new_group(group_form, request.user, request.POST)
		return HttpResponseRedirect('/home/groups')

	return render_to_response('forms/basic_form_dialog.html', RequestContext(request, {
		'form': group_form,
		'action': '/groups/create',
		'header': 'Create New Group',
		'layout': 'horizontal',
		'submit': 'Save'
	}))


@login_required(login_url='/')
def edit_project_dialog(request, pid):
	"""
		This view provides a dialog to create a new Project in DB.
	"""
	project_data = Project.objects.get(id=pid)
	form_action = '/projects/edit/' + str(pid)
	form_title = 'Edit Project: ' + str(project_data.name)

	if request.method == 'POST':
		project_form = breezeForms.EditProjectForm(request.POST)
		if project_form.is_valid():
			aux.edit_project(project_form, project_data)
			return HttpResponseRedirect('/home/projects')
	else:
		project_form = breezeForms.EditProjectForm(
			initial={'eid': project_data.external_id, 'wbs': project_data.wbs, 'description': project_data.description}
		)

	return render_to_response('forms/basic_form_dialog.html', RequestContext(request, {
		'form': project_form,
		'action': form_action,
		'header': form_title,
		'layout': 'horizontal',
		'submit': 'Save'
	}))


@login_required(login_url='/')
def edit_group_dialog(request, gid):
	"""
		This view provides a dialog to edit an existing Group in DB.
	"""
	group_data = Group.objects.get(id=gid)
	form_action = '/groups/edit/' + str(gid)
	form_title = 'Edit Group: ' + str(group_data.name)

	if request.method == 'POST':
		group_form = breezeForms.EditGroupForm(request.POST)
		if group_form.is_valid():
			aux.edit_group(group_form, group_data, request.POST)
			return HttpResponseRedirect('/home/groups')
	else:
		team = {}
		for arr in group_data.team.all():
			team[arr.id] = True

		group_form = breezeForms.EditGroupForm(initial={'group_team': team})

	return render_to_response('forms/basic_form_dialog.html', RequestContext(request, {
		'form': group_form,
		'action': form_action,
		'header': form_title,
		'layout': 'horizontal',
		'submit': 'Save'
	}))


@login_required(login_url='/')
def update_user_info_dialog(request):
	user_info = User.objects.get(username=request.user)

	if request.method == 'POST':
		personal_form = breezeForms.PersonalInfo(request.POST)
		if personal_form.is_valid():
			user_info.first_name = personal_form.cleaned_data.get('first_name', None)
			user_info.last_name = personal_form.cleaned_data.get('last_name', None)
			user_info.email = personal_form.cleaned_data.get('email', None)
			try:
				user_details = UserProfile.objects.get(user=request.user)
				user_details.institute_info = Institute.objects.get(id=request.POST['institute'])
				user_info.save()
				user_details.save()
			except UserProfile.DoesNotExist:

				user_details = UserProfile()
				user_details.user = user_info
				user_details.institute_info = Institute.objects.get(id=request.POST['institute'])
				# print(personal_form.cleaned_data.get('institute', None))
				user_info.save()
				user_details.save()
			return HttpResponseRedirect('/home')

	else:

		try:
			user_details = UserProfile.objects.get(user=user_info.id)
			personal_form = breezeForms.PersonalInfo(
				initial={'first_name': user_info.first_name, 'last_name': user_info.last_name,
				         'institute': user_details.institute_info.id, 'email': user_info.email})
		except UserProfile.DoesNotExist:
			personal_form = breezeForms.PersonalInfo(
				initial={'first_name': user_info.first_name, 'last_name': user_info.last_name,
				         'email': user_info.email})

	return render_to_response('forms/basic_form_dialog.html', RequestContext(request, {
		'form': personal_form,
		'action': '/update-user-info/',
		'header': 'Update Personal Info',
		'layout': 'horizontal',
		'submit': 'Save'
	}))


def ajax_user_stat(request):
	timeinfo = User.objects.values_list('date_joined', flat=True)
	# only keep year and month info
	timeinfo = [each.strftime('%Y-%m') for each in timeinfo]
	# get current time
	current_time = datetime.today()
	# store the date for the last 12 months
	period = [current_time]
	for each_mon in range(1, 12):
		period.append(current_time + relativedelta(months=-each_mon))
	# format the period
	period = [each_month.strftime('%Y-%m') for each_month in period]

	# sort and group the time info
	# time_group = sorted(set(timeinfo))
	response_data = {}
	# response_data['result'] = [["Aug", 1], ["Sep", 2],["Oct", 3], ["Noe", 4]]
	for idx, each_group in enumerate(period):
		count = 0
		for each_time in timeinfo:
			if (each_time <= each_group):
				count = count + 1
		response_data[idx] = [each_group, count]
	# response_data['message'] = ["Aug", "Sep", "Oct", "Nov"]

	return HttpResponse(simplejson.dumps(response_data), mimetype='application/json')


@login_required(login_url='/')
def report_search(request):
	if 'reset' in request.REQUEST:
		return HttpResponseRedirect('/reports/')  # Redirects to the default view
	else:
		entry_query = None
		owned_filter = False

		page_index, entries_nb = aux.report_common(request)

		if ('filt_name' in request.REQUEST) and request.REQUEST['filt_name'].strip():
			query_type = '"' + request.REQUEST['filt_name'] + '"'
			entry_query = aux.get_query(query_type, ['name'])
		# filter by type
		if ('filt_type' in request.REQUEST) and request.REQUEST['filt_type']:
			query_type = '"' + request.REQUEST['filt_type'] + '"'
			if entry_query:
				entry_query = entry_query & aux.get_query_new(query_type, ['type__type'])
			else:
				entry_query = aux.get_query_new(query_type, ['type__type'])
		# filter by author
		if ('filt_author' in request.REQUEST) and request.REQUEST['filt_author']:
			query_type = '"' + request.REQUEST['filt_author'] + '"'
			if entry_query:
				entry_query = entry_query & aux.get_query_new(query_type, ['author__username'])
			else:
				entry_query = aux.get_query_new(query_type, ['author__username'])
		# filter by project
		if ('filt_project' in request.REQUEST) and request.REQUEST['filt_project']:
			query_type = '"' + request.REQUEST['filt_project'] + '"'
			if entry_query:
				entry_query = entry_query & aux.get_query_new(query_type, ['project__name'])
			else:
				entry_query = aux.get_query_new(query_type, ['project__name'])
		# filter by owned reports
		if ('access_filter1' in request.REQUEST) and request.REQUEST['access_filter1']:
			if request.REQUEST['access_filter1'] == 'owned':
				query_type = '"' + request.user.username + '"'
				tmp_query = aux.get_query_new(query_type, ['author__username'])
				if entry_query:
					entry_query = entry_query & tmp_query
				else:
					entry_query = tmp_query
				owned_filter = True
			# filter by accessible reports
			elif request.REQUEST['access_filter1'] == 'accessible':
				query_type = '"' + request.user.username + '"'
				# TODO : fix that, not working as expected
				tmp_query = (aux.get_query_new(query_type, ['author__username']) | aux.get_query_new(
					query_type, ['shared__username']))
				if entry_query:
					entry_query = entry_query & tmp_query
				else:
					entry_query = tmp_query
		# Process the query
		if entry_query is None:
			found_entries = Report.objects.filter(status="succeed").order_by('-created')
		else:
			found_entries = Report.objects.filter(entry_query, status="succeed").order_by('-created')
	# just a shortcut for the template
	for each in found_entries:
		each.user_is_owner = each.author == request.user
		each.user_has_access = request.user in each.shared.all() or each.user_is_owner

	# apply pagination
	paginator = Paginator(found_entries, entries_nb)
	found_entries = paginator.page(page_index)

	# Copy the query for the paginator to work with filtering
	queryS = aux.makeHTTP_query(request)

	return render_to_response('reports-paginator.html', RequestContext(request, {
		'reports': found_entries,
		'pagination_number': paginator.num_pages,
		'page': page_index,
		'url': 'search?',
		'search': queryS,
		'owned_filter': owned_filter
	}))


@login_required(login_url='/')
def home_paginate(request):
	if request.is_ajax() and request.method == 'GET':
		page = request.GET.get('page')
		table = request.GET.get('table')

		if table == 'screens':
			tag_symbol = 'screens'
			paginator = Paginator(rora.get_screens_info(), 15)
			template = 'screens-paginator.html'
		elif table == 'datasets':
			tag_symbol = 'datasets'
			paginator = Paginator(rora.get_screens_info(), 15)
			template = 'datasets-paginator.html'
		elif table == 'screen_groups':
			tag_symbol = 'screen_groups'
			paginator = Paginator(rora.get_screens_info(), 15)
			template = 'screen-groups-paginator.html'

		try:
			items = paginator.page(page)
		except PageNotAnInteger:  # if page isn't an integer
			items = paginator.page(1)
		except EmptyPage:  # if page out of bounds
			items = paginator.page(paginator.num_pages)

		return render_to_response(template, RequestContext(request, {tag_symbol: items}))
	else:
		return False


@csrf_exempt
@login_required(login_url='/')
def proxy_to(request, path, target_url, query_s=''):
	return aux.proxy_to(request, path, target_url, query_s)


def custom_404_view(request, message=None):
	print message
	t = loader.get_template('404.html')
	return http.HttpResponseNotFound(t.render(RequestContext(request, {
		'request_path': request.path,
		'messages': ['test'],
	})))