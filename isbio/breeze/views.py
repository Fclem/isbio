# -*- coding: utf-8 -*-
from datadog import util
from pip._vendor.cachecontrol import wrapper

import auxiliary as aux
import forms as breezeForms
import urllib
import rpy2, os.path
import rora
import shell as rshell
import xml.etree.ElementTree as xml
import pickle
import breeze.system_check as check
from breeze.models import *
from collections import OrderedDict
from rpy2.rinterface import RRuntimeError
from dateutil.relativedelta import relativedelta
from django import http
from django.conf import settings
from django.contrib import auth  # , messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import User  # , Group # replaced with breeze.models.User overload
from django.core.files import File
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.handlers.wsgi import WSGIRequest
from django.core.urlresolvers import reverse
from django.db.models.query_utils import Q
from django.http import HttpResponseRedirect, HttpResponse, HttpResponsePermanentRedirect
from django.shortcuts import render_to_response
from django.template.context import RequestContext
from django.template import loader
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from mimetypes import MimeTypes
from breeze.legacy import get_report_path, get_report_path_test
from breeze.b_exceptions import *
import hashlib
import sys

simplejson = json
logger = utils.logger


def legacy_request(request):
	""" Adds back the REQUEST property as dict(self.GET + self.POST) that seems to be missing
	
	"""
	assert isinstance(request, WSGIRequest)
	if not hasattr(request, 'REQUEST'):
		request.REQUEST = copy.copy(request.GET)
		request.REQUEST.update(request.POST)
	return request


class RequestStorage(object):
	form_details = OrderedDict()

	def get_param_list(self):
		class creepy(object):
			pass

		tmp = creepy()
		plist = list()
		p_keys = self.form_details.keys()
		for key in p_keys:
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
	return HttpResponseRedirect('/')  # FIXME hardcoded url


def register_user(request):
	if request.user.is_authenticated():
		return HttpResponseRedirect('/home/')  # FIXME hardcoded url
	if request.method == 'POST':
		form = breezeForms.RegistrationForm(request.POST)
		if form.is_valid():
			a_user = User.objects.create_user(username=form.cleaned_data['username'],
				email=form.cleaned_data['email'], password=form.cleaned_data['password'])
			g = Group.objects.get(name='USERS')
			g.user_set.add(a_user)
			a_user.is_staff = False
			a_user.save()
			profile = UserProfile(user=a_user, first_name=form.cleaned_data['first_name'],
				last_name=form.cleaned_data['last_name'], fimm_group=form.cleaned_data['fimm_group'])
			profile.save()
			return render_to_response('forms/welcome_modal.html', RequestContext(request))
		else:
			return render_to_response('forms/register.html', RequestContext(request, {'form': form}))
	else:
		form = breezeForms.RegistrationForm()
		return render_to_response('forms/register.html', RequestContext(request, {'form': form}))


def base(request):
	return render_to_response('base.html')


# FIXME obsolete
# TODO rewrite
@login_required(login_url='/')
def home(request, state="feed"):
	# user_info = User.objects.get(username=request.user)
	user_info = request.user
	db_access = False
	try:
		user_profile = UserProfile.objects.get(user=user_info)
		user_info_complete = True
		db_access = user_profile.db_agreement
	except UserProfile.DoesNotExist:
		user_info_complete = False

	occurrences = dict()

	# default / state == 'feed'
	menu = 'feed_menu'
	show_menu = 'show_feed'
	explorer_tab = 'datasets_tab'
	explorer_pane = 'show_datasets'
	pref_tab = 'projects_tab'
	pref_pane = 'show_projects'
	stat_tab = 'analysis_stat_tab'
	stat_pane = 'show_analysis_stat'

	if state == 'projects':
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
	elif state == 'contacts':
		menu = 'preferences_menu'
		show_menu = 'show_preferences'
		explorer_tab = 'datasets_tab'
		explorer_pane = 'show_datasets'
		pref_tab = 'contacts_tab'
		pref_pane = 'show_contacts'
		stat_tab = 'analysis_stat_tab'
		stat_pane = 'show_analysis_stat'

	projects = Project.objects.exclude(~Q(author__exact=request.user) & Q(collaborative=False)).order_by("name")
	groups = Group.objects.filter(author__exact=request.user).order_by("name")

	# get all the script info
	# rscripts = Rscripts.objects.all().get(draft=True)
	# get all the report info
	occurrences['jobs_running'] = len(Jobs.objects.f.get_active()) + len(Report.objects.f.get_active())
	occurrences['jobs_scheduled'] = len(Jobs.objects.f.get_scheduled()) + len(Report.objects.f.get_scheduled())
	occurrences['jobs_history'] = len(Jobs.objects.f.get_done())
	occurrences['reports_history'] = len(Report.objects.f.get_done())

	occurrences['scripts_total'] = Rscripts.objects.filter(draft="0").count()
	occurrences['scripts_tags'] = Rscripts.objects.filter(draft="0").filter(istag="1").count()
	occurrences['report_types'] = len(ReportType.objects.all())

	contacts = OffsiteUser.objects.filter(belongs_to=request.user).order_by('-created')

	analitics_stats = list()

	for each in Rscripts.objects.all().order_by('name'): # .order_by('author', 'name'):
		# REports stats
		assert isinstance(each, Rscripts)
		# script author istag times
		if each.istag:
			count = 0
			for element in each.report_type.all():
				count += Report.objects.filter(type=element).count()
		else:
			count = Jobs.objects.filter(script=each).count()
		analitics_stats.append({'script': each, 'author': each.author, 'istag': each.istag, 'times': count})

	r_type_stats = list()
	for each in ReportType.objects.all():
		# Users stats
		a_user_list = each.get_all_users_ever_with_count()
		tmp_lst = list()
		for each_user, count in a_user_list.iteritems():
			tmp_lst.append({ 'name': each_user.get_full_name() or each_user.username , 'email': each_user.email or
																								'N/A',
				'count': count })
		r_type_stats.append({ 'name': each.type, 'user_lst': tmp_lst})

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
			if user_profile.last_active is None:
				user_profile.last_active = user_info.last_login
			if each.time > user_profile.last_active:
				each.icon = "icon-fire"

	server, server_info = aux.update_server_routine()

	if user_info_complete:
		user_profile.last_active = timezone.now()
		user_profile.save()

	# from django.contrib import messages
	# messages.add_message(request, messages.INFO, 'Hello world.')

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
		'contacts': contacts,
		'projects': projects,
		'groups': groups,
		'posts': posts,
		'screens': screens,
		'patients': patients,
		'stats': analitics_stats,
		'r_type_stats': r_type_stats,
		'user_info': user_info_complete,
		'server_info': server_info,
		'server_status': server,
		'db_access': db_access
	}))


def update_server(request):
	server, server_info = aux.update_server_routine()

	return HttpResponse(simplejson.dumps({'server_status': server, 'server_info': server_info}),
		content_type=c_t.JSON)


@login_required(login_url='/')
def jobs(request, state="", error_msg="", page=1):
	if state == "scheduled":
		tab = "scheduled_tab"
		show_tab = "show_sched"
	elif state == "current":
		tab = "current_tab"
		show_tab = "show_curr"
	else:
		state = "history"
		tab = "history_tab"
		show_tab = "show_hist"

	scheduled_jobs = Jobs.objects.f.get_scheduled().owned(request.user).order_by("-id")
	history_jobs = Jobs.objects.f.get_history().owned(request.user).order_by("-id")
	active_jobs = Jobs.objects.f.get_incomplete().owned(request.user).order_by("-id")

	active_reports = Report.objects.f.get_incomplete().owned(request.user).order_by("-_created")
	ready_reports = Report.objects.f.get_done().owned(request.user).order_by('-_created')

	# TODO get rid of this merge stuff
	merged_active = aux.merge_job_history(active_jobs, active_reports, request.user)
	# merged_active = active_jobs | active_reports
	merged_history = aux.merge_job_history(history_jobs, ready_reports, request.user)

	paginator = Paginator(merged_history, 12)  # show 15 items per page

	# page = request.REQUEST.get('page') or 1
	try:
		hist_jobs = paginator.page(page)
	except PageNotAnInteger:  # if page isn't an integer
		hist_jobs = paginator.page(1)
		page = 1
	except EmptyPage:  # if page out of bounds
		hist_jobs = paginator.page(paginator.num_pages)
		page = paginator.num_pages

	if request.method == 'GET':
		# If AJAX - check page from the request
		# Otherwise return the first page
		if request.is_ajax():
			if 'get-live' in request.GET:
				# hist_jobs = paginator.page(1)

				return render_to_response('jobs-live.html', RequestContext(request, {
					'dash_history': paginator.page(1)[0:3],
					'current': merged_active,
				}))
			else:
				return render_to_response('jobs-hist-paginator.html', RequestContext(request, {'history': hist_jobs, 'page': page}))

	# might be merged trough track_sge_job_bis
	# from itertools import chain

	# all_list = list(chain(active_jobs, queued_jobs, active_reports, queued_reports, no_id_jobs, no_id_reports))
	# rshell.track_sge_job_bis(all_list, True)  # forces job refresh from sge rather than just db status

	user_profile = UserProfile.objects.get(user=request.user)
	db_access = user_profile.db_agreement
	# hist_jobs = paginator.page(1)

	if state is None and len(merged_active) > 0:
		tab = "current_tab"
		show_tab = "show_curr"
		state = 'current'

	# from qstat import Qstat
	# from sge_interface import Qstat

	return render_to_response('jobs.html', RequestContext(request, {
		str(tab): 'active',
		str(show_tab): 'active',
		'active_tab': state,
		'jobs_status': 'active', # high light navbar tab
		'dash_history': paginator.page(1)[0:3],
		'scheduled': scheduled_jobs,
		'history': hist_jobs,
		'current': merged_active,
		'pagination_number': paginator.num_pages,
		'page': page,
		'db_access': db_access,
		'error_message': error_msg,
		# 'queue_is_full': Qstat().is_queue_full,
		'queue_is_full': True,
		'current_nb': merged_active.__len__()
	}))


@login_required(login_url='/')
def scripts(request, layout="list"):
	if layout == "nails":
		nails = True
	else:
		nails = False
	categories = ScriptCategories.objects.all()
	# all_scripts = Rscripts.objects.all()
	# user = User.objects.get(username=request.user)
	a_user = request.user
	all_scripts = a_user.users.all()
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
	user_profile = UserProfile.objects.get(user=request.user) # TODO check if exists #bugfix / FIXME
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
	# Manage sorting
	sorting = aux.get_argument(request, 'sort') or '-created'
	# get the user's institute
	# insti = UserProfile.objects.get(user=request.user).institute_info
	insti = UserProfile.get_institute(request.user)
	all_reports = Report.objects.filter(status="succeed", institute=insti).order_by(sorting)
	# all_reports = Report.objects.filter(status="succeed").order_by(sorting)
	user_rtypes = request.user.pipeline_access.all()
	# later all_users will be changed to all users from the same institute
	# all_users = UserProfile.objects.filter(institute_info=insti).order_by('user__username')
	all_users = UserProfile.objects.all().order_by('user__username')
	# first find all the users from the same institute, then find their accessible report types
	reptypelst = list()
	for each in all_users:
		rtypes = each.user.pipeline_access.all()
		if rtypes:
			for each_type in rtypes:
				if each_type not in reptypelst:
					reptypelst.append(each_type)

	# report_type_lst = ReportType.objects.filter(access=request.user)
	# all_projects = Project.objects.filter(institute=insti)
	all_projects = Project.objects.all()
	count = {'total': all_reports.count()}
	paginator = Paginator(all_reports, entries_nb)  # show 18 items per page

	# If AJAX - use the search view
	# Otherwise return the first page
	if request.is_ajax() and request.method == 'GET':
		return report_search(request)
	else:
		page_index = 1
		reports_list = paginator.page(page_index)
		# access rights
		for each in reports_list:
			each.user_is_owner = each.is_owner(request.user)
			each.user_has_access = each.has_access(request.user)
		user_profile = UserProfile.objects.get(user=request.user)
		db_access = user_profile.db_agreement
		url_lst = {  # TODO remove static url mappings
			'Edit': '/reports/edit_access/',
			'Add': '/off_user/add/',
			'Send': '/reports/send/'
		}
		# paginator counter
		count.update(aux.view_range(page_index, entries_nb, count['total']))
		# count.update(dict(first=1, last=min(entries_nb, count['total'])))

		return render_to_response('reports.html', RequestContext(request, {
			'reports_status': 'active',
			'reports': reports_list,
			'sorting': sorting,
			'rtypes': reptypelst,
			'user_rtypes': user_rtypes,
			'users': all_users,
			'projects': all_projects,
			'pagination_number': paginator.num_pages,
			'page': page_index,
			'db_access': db_access,
			'count': count,
			'url_lst': url_lst
		}))


@login_required(login_url='/')
def send_report(request, rid):
	__self__ = this_function_name()  # instance to self
	report_inst = Report.objects.owner_get(request, rid)  # only for auth
	assert isinstance(report_inst, Report)
	# offsite_u = OffsiteUser.objects.filter(belongs_to=request.user)
	# we need the email since the form is AJAX loaded, and thus cannot just send to url #
	form_action = reverse(__self__, kwargs={'rid': rid})
	# form_action = "get_form(" + str(rid) + ", 'Send', 'Send');"
	form_title = 'Send "' + report_inst.name + ' to Off-Site users'

	# Enforce access rights
	# if report_inst.author != request.user:
	# 	raise PermissionDenied(request=request)

	if request.method == 'POST':
		send_form = breezeForms.SendReportTo(request.POST, request=request)
		# Validates input info and send the mails
		if send_form.is_valid():
			from django.db import IntegrityError
			# from django.core.mail import send_mail
			from django.core.mail import EmailMessage
			# send_form
			msg_blocks = []
			# TODO wrap the sending into try
			for each in send_form.cleaned_data['recipients']:
				try:
					report_inst.offsiteuser_set.add(each)
				except IntegrityError as e:
					console_print('Exception in send_report : %s' % e)
					pass
				off_user = report_inst.offsiteuser_set.get(pk=each)
				data = {
					'recipient': off_user.full_name,
					'sender': str(request.user.get_full_name()),
					'report_name': str(report_inst.name),
					# 'url': 'http://' + settings.FULL_HOST_NAME + reverse(report_shiny_view_tab_out, kwargs={'s_key': report_inst.shiny_key, 'u_key': off_user.user_key})
					'url': report_inst.shiny_url
				}
				msg_html = loader.render_to_string('mail.html', RequestContext(request, data))
				msg = EmailMessage('Check out "' + report_inst.name + '" on Tumor Virtual Board right now !', msg_html, 'Breeze PMS', [off_user.email])
				msg.content_subtype = "html"  # Main content is now text/html
				result = msg.send()
				status = 'Success' if result == 1 else 'Failed'
				msg_blocks.append(status + ' : ' + off_user.email)
			# success
			msg_blocks = [str(len(msg_blocks)) + ' mails has been sent to :'] + msg_blocks
			return render_to_response('forms/basic_modal_dialog.html', RequestContext(request, {
				'header': 'Success',
				'msg_blocks': msg_blocks
			}))
	else:
		send_form = breezeForms.SendReportTo(request=request)

	return render_to_response('forms/send_form_dialog.html', RequestContext(request, {
		'form': send_form,
		'id': rid,
		'action': form_action,
		'header': form_title,
		'layout': 'horizontal',
		'submit': 'Send'
	}))


# Modal view to add an off-site user email address, and either attach it to the user or go to the add off-site user page
@login_required(login_url='/')
def add_offsite_user_dialog(request, rid=None):
	__self__ = this_function_name()  # instance to self
	form_action = reverse(__self__, kwargs={'rid': rid})
	form_title = 'Add an offsite user'

	if request.method == 'POST':
		offsite_user_form = breezeForms.AddOffsiteUserDialog(request.POST)
		if offsite_user_form.is_valid():
			owned_offsite_u = OffsiteUser.objects.filter(belongs_to=request.user)
			email = offsite_user_form.cleaned_data['email']
			# Check if email address is already in DB
			try:
				offone = OffsiteUser.objects.get(email=email)
			except ObjectDoesNotExist:
				# else redirects to the new user form
				return HttpResponse(reverse(add_offsite_user, kwargs={'email': str(email)}))
			# this email is already in DB
			# check if not already in owned off-site user list
			if not owned_offsite_u.filter(pk=offone.pk).exists():  # if offone not in owned_offsite_u:
				# add this off-site user to the list of owned off-site users
				offone.belongs_to.add(request.user)
				# offone.save()
				request.method = 'GET'
				return send_report(request, rid)
			else:
				# fail with standard form error
				from django.forms.util import ErrorList
				errors = offsite_user_form._errors.setdefault("email", ErrorList())
				errors.append(u"This email address is already in your list!")
	else:
		offsite_user_form = breezeForms.AddOffsiteUserDialog()

	return render_to_response('forms/add_form_dialog.html', RequestContext(request, {
		'back':  reverse(send_report, kwargs={'rid': rid}),  # " onclick=\"get_form(" + str(rid) + ", 'Send')\"",
		'form': offsite_user_form,
		'id': rid,
		'action': form_action,
		'header': form_title,
		'layout': 'horizontal',
		'submit': 'Add'
	}))


# TODO fusion with Edit offsite user
# Form to add an user
@login_required(login_url='/')
def add_offsite_user(request, email=None):
	__self__ = this_function_name()  # instance to self
	form_action = reverse(__self__)

	if request.method == 'POST' and email is None:
		off_site_user_form = breezeForms.AddOffsiteUser(request.user, request.POST)
		if off_site_user_form.is_valid():
			# TODO : move the logic out of here and place it in AddOffsiteUser.save() class method
			data = off_site_user_form.save(commit=False)
			data.added_by = request.user
			m = hashlib.md5()
			m.update(settings.SECRET_KEY + data.email + str(datetime.now()))
			data.user_key = str(m.hexdigest())
			data.save()
			data.belongs_to.add(request.user)

			if isinstance(data, OffsiteUser):
				off_site_user = data
			else:
				off_site_user = OffsiteUser(id=data.id)
			off_site_user_form_bis = breezeForms.AddOffsiteUser(request.user, request.POST, instance=off_site_user)
			# use this trick to populate accessible reports directly through Django back-end
			if off_site_user_form_bis.is_valid():
				off_site_user_form_bis.save()

			return HttpResponseRedirect(reverse(home, kwargs={'state': 'contacts'}))
	else:
		off_site_user_form = breezeForms.AddOffsiteUser(request.user, initial={'email': email})

	return render_to_response('forms/off-site_user_modal.html', RequestContext(request, {
		'form': off_site_user_form,
		'action': form_action,
		'layout': 'horizontal',
		'title': 'Add a contact',
		'submit': 'Add'
	}))


# TODO fusion with add
@login_required(login_url='/')
def edit_offsite_user(request, uid):
	__self__ = this_function_name()  # instance to self
	form_action = reverse(__self__, kwargs={'uid': uid})
	try:
		edit_u = OffsiteUser.objects.filter(belongs_to=request.user).get(id=uid)
	except ObjectDoesNotExist:
		raise PermissionDenied(request=request)

	if request.method == 'POST':
		off_site_user_form = breezeForms.AddOffsiteUser(request.user, request.POST, instance=edit_u)
		if off_site_user_form.is_valid():
			off_site_user_form.save()
			return HttpResponseRedirect(reverse(home, kwargs={'state': 'contacts'}))
	else:
		off_site_user_form = breezeForms.AddOffsiteUser(request.user, instance=edit_u)

	return render_to_response('forms/off-site_user_modal.html', RequestContext(request, {
		'form': off_site_user_form,
		# 'user_list': user_list,
		# 'user_list_ex': user_list_ex,
		'action': form_action,
		'layout': 'horizontal',
		'title': 'Edit "' + edit_u.full_name + '"',
		'submit': 'Save'
	}))


@login_required(login_url='/')
def delete_off_site_user(request, uid):
	try:
		off_site_user = OffsiteUser.objects.filter(belongs_to=request.user).get(id=uid)
	except ObjectDoesNotExist:
		raise PermissionDenied(request=request)

	off_site_user.drop(request.user)

	return HttpResponseRedirect(reverse(home, kwargs={ 'state': 'contacts' }))


@login_required(login_url='/')
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

	return HttpResponse(simplejson.dumps(response_data), content_type=c_t.JSON)


@login_required(login_url='/')
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
			patient['birthdate'] = str(patient_form.cleaned_data.get('birthdate'))
			rora.update_patient(patient)
			return ('/dbviewer') # FIXME hardcoded url
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
		'action': '/patient-data/0', # FIXME hardcoded url
		'header': 'Update Patient Info',
		'layout': 'horizontal',
		'submit': 'Save'
	}))


@login_required(login_url='/')
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
			patient['birthdate'] = str(patient_form.cleaned_data.get('birthdate'))
			rora.insert_row("patients", patient)
			return HttpResponseRedirect('/dbviewer') # FIXME hardcoded url
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


@login_required(login_url='/')
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
			rora.update_screen(screen)
			return HttpResponseRedirect('/dbviewer') # FIXME hardcoded url
		else:
			screen_info = breezeForms.ScreenInfo(request.POST)

	else:
		data = rora.screen_data(which)
		if isinstance(data[2], rpy2.rinterface.NACharacterType):
			data[2] = ''
		screen_info = breezeForms.ScreenInfo(initial={
			'screen_id': data[0], 'identifier': data[1], 'description': data[2], 'source_id': data[3],
			'source': data[5], 'protocol': data[4], 'patient': int(data[6]), 'alias': data[7], 'st': int(data[8]),
			'dst': int(data[9]), 'mt': int(data[10]), 'histology': int(data[11]), 'dstate': int(data[12]), 'et':
				int(data[13]), 'plate_count': data[14], 'dg': int(data[15]), 'disease_stage': int(data[16]), 'read_out':
				int(data[21]), 'createdate': data[22].split()[0]
		})
	return render_to_response('forms/basic_form_dialog.html', RequestContext(request, {
		'form': screen_info,
		'action': '/screen-data/0',
		'header': 'Update Screen Info',
		'layout': 'horizontal',
		'submit': 'Save'
	}))


@login_required(login_url='/')
def ajax_rora_screens(request, gid):
	if request.method == 'POST':
		screengroup_form = breezeForms.ScreenGroupInfo(request.POST)

		if screengroup_form.is_valid():
			screen = dict()
			screen['list'] = screengroup_form.cleaned_data.get('dst')
			rora.update_screen_group_content(screen['list'], gid)
			return HttpResponseRedirect('/dbviewer') # FIXME hardcoded url
	else:
		# response_data = rora.getScreenGroupContent(groupID=gid)
		group_content = rora.get_screen_group(group_id=gid)
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
def add_to_cart(request, sid=None):
	# check if this item in the cart already
	try:

		# scr = Rscripts.objects.get(id = sid)

		items = CartInfo.objects.get(product=sid, script_buyer=request.user)
		return HttpResponse(simplejson.dumps({"exist": "Yes"}), content_type=c_t.JSON)
	except CartInfo.DoesNotExist:
		scripts = Rscripts.objects.get(id=sid)
		mycart = CartInfo()
		mycart.script_buyer = request.user
		mycart.product = scripts
		if (scripts.price > 0):
			mycart.type_app = False
		else:
			mycart.type_app = True
		mycart.active = True
		mycart.save()
		return HttpResponse(simplejson.dumps({"exist": "No"}), content_type=c_t.JSON)


@login_required(login_url='/')
def update_cart(request):
	count_mycart = CartInfo.objects.filter(script_buyer=request.user).count()
	html = render_to_string('countcart.html', {'count_mycart': count_mycart})
	return HttpResponse(html)


@login_required(login_url='/')
def my_cart(request):
	# all_items = CartInfo.objects.filter(script_buyer=request.user)
	items_free = CartInfo.objects.filter(script_buyer=request.user, type_app=True)
	items_nonfree = CartInfo.objects.filter(script_buyer=request.user, type_app=False)
	html = render_to_string('cartinfo.html', {  # 'mycart_status': 'active',
		'items_free': items_free,
		'items_nonfree': items_nonfree  # 'all_items': all_items
	})
	return HttpResponse(html)


# FIXME no login ?
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

	return HttpResponse(simplejson.dumps(response_data), content_type=c_t.JSON)


@login_required(login_url='/')
def group_name(request):
	if request.method == 'POST':
		screen_group = breezeForms.ScreenGroup(request.POST)

		if screen_group.is_valid():
			group = dict()
			group['group_name'] = screen_group.cleaned_data.get('name')
			group['group_user'] = request.user.username
			table = 'groups'
			feedback = rora.insert_row(table=table, data=group)
			# rora.update_screen(screen)
			return HttpResponseRedirect('/dbviewer') # FIXME hardcoded url
	else:
		screen_group = breezeForms.ScreenGroup()
	return render_to_response('forms/basic_form_dialog.html', RequestContext(request, {
		'form': screen_group,
		'action': '/ajax-rora-groupname/',
		'header': 'Create New Group',
		'layout': 'horizontal',
		'submit': 'Save'
	}))


@login_required(login_url='/')
def db_policy(request):
	user_profile = UserProfile.objects.get(user=request.user)
	user_profile.db_agreement = True
	user_profile.save()
	return HttpResponseRedirect('/dbviewer/') # FIXME hardcoded url


@csrf_exempt
@login_required(login_url='/')
def report_overview(request, rtype, iname=None, iid=None, mod=None):
	from django.http import HttpResponseServerError
	tags_data_list = list()
	files = None
	title = None
	report = None

	if mod == 'reload':
		try:
			report = Report.objects.secure_get(id=iid, user=request.user)
		except ObjectDoesNotExist:
			return aux.fail_with404(request, 'There is no report with id ' + iid + ' in database')
		rtype = str(report.type)
		iname = report.get_repeat_name()
		iid = report.rora_id
		try:
			# filter tags according to report type (here we pick non-draft tags):
			# TODO : use a manager
			tags = Rscripts.objects.filter(draft="0").filter(istag="1").filter(
				report_type=ReportType.objects.get(id=report.type.id)).order_by('order')
		except ObjectDoesNotExist:
			return aux.fail_with404(request, 'There is ReportType with id ' + str(report.type_id) + ' in database')
		data = pickle.loads(report.conf_params) if report.conf_params is not None and len(report.conf_params) > 0 else None
		files = json.loads(report.conf_files) if report.conf_files is not None and len(report.conf_files) > 0 else None
		title = 'ReRun report ' + report.name
	else:
		try:
			# filter tags according to report type (here we pick non-draft tags):
			tags = Rscripts.objects.filter(draft="0").filter(istag="1").filter(
				report_type=ReportType.objects.get(type=rtype)).order_by('order')
		except ObjectDoesNotExist:
			return aux.fail_with404(request, 'There is ReportType with id ' + str(rtype) + ' in database')
		data = request.POST
		files = request.FILES if request.FILES else None

	overview = dict()
	overview['report_type'] = rtype
	overview['instance_name'] = iname
	request.rtype = rtype
	overview['instance_id'] = iid
	overview['details'] = rshell.get_report_overview(rtype, iname, iid)
	manual = str(ReportType.objects.get(type=rtype).manual) or None
	overview['manual'] = None
	if manual is not None:
		overview['manual'] = settings.MEDIA_URL + manual

	if request.method == 'POST':
		# pprint.pprint(request.POST)
		# Validates input info and creates (submits) a report
		property_form = breezeForms.ReportPropsForm(request.POST, request=request)
		# property_form = breezeForms.ReportPropsForm(request=request)
		try:
			tags_data_list = breezeForms.validate_report_sections(tags, request)
		except RRuntimeError:
			return HttpResponseServerError()

		sections_valid = breezeForms.check_validity(tags_data_list)

		if property_form.is_valid() and sections_valid and mod != 'reload':
			# lunches the script generation in a separate thread in order to avoid long blocking operation
			# thread.start_new_thread(rshell.build_report, (overview, request, property_form, tags))
			return HttpResponse(rshell.build_report(overview, request, property_form, tags))
		else:
			for x in tags_data_list:
				x['value'] = request.POST.get('Section_dbID_' + str(x['id']))
				if not 'size' in x:
					x['size'] = len(x['form'].fields)
				x['opened'] = x['value'] == '1' and not x['isvalid']
	else:
		# Renders report overview and available tags
		if mod == 'reload' and report:
			property_form = breezeForms.ReportPropsFormRE(instance=report, request=request)
			# loc = str(settings.MEDIA_ROOT) + report._home_folder_rel
			loc = report.home_folder_full_path
			try:
				tags_data_list = breezeForms.create_report_sections(tags, request, data, files, path=loc)
			except RRuntimeError:
				return HttpResponseServerError()
		else:
			property_form = breezeForms.ReportPropsForm(request=request)
			try:
				tags_data_list = breezeForms.create_report_sections(tags, request, data, files)
			except RRuntimeError:
				return HttpResponseServerError()

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
		# 'disable_zopim': True,
		'title': title
	}))


@login_required(login_url='/')
def showdetails(request, sid=None):
	try:
		tags = ReportType.objects.get(id=sid).rscripts_set.all()
	except ObjectDoesNotExist:  # TODO protect all alike request as such
		return aux.fail_with404(request, 'There is no object with id ' + sid + ' in database')
	app_installed = request.user.users.all()

	return render_to_response('store-tags.html', RequestContext(request, {
		'tags': tags,
		'app_installed': app_installed
	}))


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
			if not ('type' in request.POST and 'query' in request.POST): # TODO check this fix
				return render_to_response('search.html',
										RequestContext(request, { 'search_status': 'active', 'search_bars': True,
																	'ds_count': ds_count, 'rtypes': report_type_lst }))
			report_type = request.POST['type']
			query_val = request.POST['query']
			rtype = ReportType.objects.get(type=report_type)

			if False and rtype.search: # disabled because deprecated TODO check with dima
				# if searchable
				overview['report_type'] = report_type
				output = rshell.report_search(ds, overview['report_type'], query_val)
			else:
				# if not searchable - redirects directly to overview
				if len(query_val) == 0:
					query_val = "Noname"
				res = '/reports/overview/%s-%s-00000' % (report_type, query_val) # FIXME hardcoded url
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
	from breeze.system_check import get_template_check_list
	usage_graph = (
		{'url': 'http://192.168.0.225/S/D', 'html_alt': 'queue stats on the last 24h',
			'html_title': 'queue stats on the last 24h', 'legend': 'queue stats on the last 24h', 'href': ''},
		{'url': 'http://192.168.0.225/S/B', 'html_alt': 'This is an example of another graph',
			'html_title': 'This is an example of another graph',
			'legend': 'This is an example of another graph', }
	)
	usage_graph = ()
	
	# print advanced_pretty_print(ObjectCache.dump())

	return render_to_response('resources.html', RequestContext(request, {
		'resources_status': 'active',
		'usage_graph': usage_graph,
		'resources': get_template_check_list(),
		'cache': ObjectCache.dump()
	}))


@login_required(login_url='/')
def manage_scripts_all(request, page=1):
	return manage_scripts(request, page, True)


@login_required(login_url='/')
def manage_scripts(request, page=None, view_all=False):
	# script_selection = Rscripts.objects.all()
	assert isinstance(request.user, User)
	if not (request.user.is_superuser or request.user.is_staff):
		raise PermissionDenied(request=request)

	if view_all: # and request.user.is_superuser and settings.SU_ACCESS_OVERRIDE:
		script_selection = Rscripts.objects.all()
	else:
		script_selection = Rscripts.objects.all().filter(author=request.user)
	paginator = Paginator(script_selection, 15)

	page = page or 1

	def page_sub(request, page_id, paginator):
		page = page_id
		try:
			# TODO change this, since it's not the way to do it
			# this session var is for the paginator to stay on the same page number after
			# sending forms (add or delete forms) for consistency and clarity
			# request.session['manage-scripts-page'] = page
			scripts = paginator.page(page)
		except PageNotAnInteger:  # if page isn't an integer
			# request.session['manage-scripts-page'] = 1
			scripts = paginator.page(1)
		except EmptyPage:  # if page out of bounds
			# request.session['manage-scripts-page'] = paginator.num_pages
			scripts = paginator.page(paginator.num_pages)
		return scripts

	# TODO ACL
	# request.session['manage-scripts-page'] = 1

	# If AJAX - check page from the request
	# Otherwise return the first page
	if request.is_ajax() and request.method == 'GET':
		# scripts = page_sub(request, request.GET.get('page'), paginator)
		scripts = page_sub(request, page, paginator)
		return render_to_response('manage-scripts-paginator.html', RequestContext(request, {'script_list': scripts}))

	else:
		#if 'manage-scripts-page' in request.session:
		#	new_page = request.session['manage-scripts-page']
		#	if page == 1:
		#		page = new_page

		scripts = page_sub(request, page, paginator)

		return render_to_response('manage-scripts.html', RequestContext(request, {
			'all': view_all,
			'resources_status': 'active',
			'script_list': scripts,
			'pagination_number': paginator.num_pages,
			'url': '/resources/scripts/' + 'all/' if view_all else '',
			'page': page  # to keep the paginator synced
		}))


@login_required(login_url='/')
def manage_pipes(request):
	all_pipelines = ReportType.objects.all()
	paginator = Paginator(all_pipelines, 10)

	# If AJAX - check page from the request
	# Otherwise return the first page
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
	categories = ScriptCategories.objects.all()
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
		return HttpResponse(simplejson.dumps({"delete": "Yes", 'count_app': count_app}), content_type=c_t.JSON)
	except CartInfo.DoesNotExist:
		return HttpResponse(simplejson.dumps({"delete": "No"}), content_type=c_t.JSON)


@login_required(login_url='/')
def deletefree(request):
	try:
		items = CartInfo.objects.filter(type_app=True, script_buyer=request.user)
		items.delete()
		return HttpResponse(simplejson.dumps({"delete": "Yes"}), content_type=c_t.JSON)
	except CartInfo.DoesNotExist:
		return HttpResponse(simplejson.dumps({"delete": "No"}), content_type=c_t.JSON)


@login_required(login_url='/')
def install(request, sid=None):
	try:
		# get the script
		scr = Rscripts.objects.get(id=sid)
		scr.access.add(request.user)
		return HttpResponse(simplejson.dumps({"install_status": "Yes"}), content_type=c_t.JSON)
	except Rscripts.DoesNotExist:
		return HttpResponse(simplejson.dumps({"install_status": "No"}), content_type=c_t.JSON)


@login_required(login_url='/')
def installreport(request, sid=None):
	try:
		# get the report type by id
		report_type = ReportType.objects.get(id=sid)
		report_type.access.add(request.user)
		return HttpResponse(simplejson.dumps({"install_status": "Yes"}), content_type=c_t.JSON)
	except ReportType.DoesNotExist:
		return HttpResponse(simplejson.dumps({"install_status": "No"}), content_type=c_t.JSON)


######################################
###      SUPPLEMENTARY VIEWS       ###
######################################

@login_required(login_url='/')
def script_editor(request, sid=None, tab=None, script=None):
	assert isinstance(request.user, User)
	# ACL
	if not (request.user.is_superuser or request.user.is_staff):
		raise PermissionDenied(request=request)
	if not script:
		try:
			script = Rscripts.objects.secure_get(id=sid, user=request.user)
		except ObjectDoesNotExist:
			return aux.fail_with404(request, 'There is no Rscript with id ' + sid + ' in database')

	assert isinstance(script, Rscripts)

	# script = Rscripts.objects.get(id=sid)

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
	# script = Rscripts.objects.get(id=sid)
	# ACL
	assert isinstance(request.user, User)
	if not (request.user.is_superuser or request.user.is_staff):
		raise PermissionDenied(request=request)
	try:
		script = Rscripts.objects.secure_get(id=sid, user=request.user)
	except ObjectDoesNotExist:
		return aux.fail_with404(request, 'There is no Rscript with id ' + sid + ' in database')

	if request.method == 'POST':
		# General Tab
		if request.POST['form_name'] == 'general':
			f_basic = breezeForms.ScriptBasics(script.name, request.POST)
			if f_basic.is_valid():
				rshell.update_script_dasics(script, f_basic)
				return HttpResponseRedirect('/resources/scripts/script-editor/' + str(script.id) + '-general_tab') # FIXME hardcoded url
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
				return HttpResponseRedirect('/resources/scripts/script-editor/' + str(script.id) + '-attribut_tab') # FIXME hardcoded url
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
				return HttpResponseRedirect('/resources/scripts/script-editor/' + str(script.id) + '-logos_tab') # FIXME hardcoded url
		else:
			f_logos = breezeForms.ScriptLogo()

		return render_to_response('script-editor.html', RequestContext(request, {
			'resources_status': 'active',
			'script': script,
			'basic_form': f_basic  # 'attr_form': f_attrs,  # 'logo_form': f_logos
		}))
	# if NOT POST
	return HttpResponseRedirect('/resources/scripts/script-editor/' + script.id) # FIXME hardcoded url


@login_required(login_url='/')
def get_form(request, sid=None):
	# script = Rscripts.objects.get(id=sid)
	# ACL
	assert isinstance(request.user, User)
	if not (request.user.is_superuser or request.user.is_staff):
		raise PermissionDenied(request=request)
	try:
		script = Rscripts.objects.secure_get(id=sid, user=request.user)
	except ObjectDoesNotExist:
		return aux.fail_with404(request, 'There is no Rscript with id ' + sid + ' in database')
	builder_form = ""

	if request.method == 'GET' and sid is not None:
		file_path = rshell.settings.MEDIA_ROOT + str(script.docxml) # TODO check for path fitness (MEDIA ROOT)

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
	# ACL
	assert isinstance(request.user, User)
	if not (request.user.is_superuser or request.user.is_staff):
		raise PermissionDenied(request=request)
	try:
		script = Rscripts.objects.secure_get(id=sid, user=request.user)
	except ObjectDoesNotExist:
		return aux.fail_with404(request, 'There is no Rscript with id ' + sid + ' in database')
	# script = Rscripts.objects.get(id=sid)
	rcode = ""
	if request.method == 'GET' and sid is not None:

		if sfile == 'Header':
			file_path = rshell.settings.MEDIA_ROOT + str(script.header) # TODO check MEDIA_PATH
		elif sfile == 'Main':
			file_path = rshell.settings.MEDIA_ROOT + str(script.code) # TODO check MEDIA_PATH

		if os.path.isfile(file_path):
			handle = open(file_path, 'r')
			rcode = handle.read()
			handle.close()
		else:
			rcode = "file does not exist"

	return HttpResponse(rcode)


def dash_redir(request, job=None, state=None):
	ref = request.META.get('HTTP_REFERER')
	if ref:
		# return HttpResponse(True)
		return HttpResponseRedirect(ref)

	tab = "history"
	if job:
		if job.status == "scheduled":
			tab = "scheduled"
		elif job.status == "active" or job.status == "queued_active":
			tab = "current"

	page = request.GET.get('page')
	page = page if page else 1
	return HttpResponseRedirect('/jobs/' + tab + '?page=' + page) # FIXME hardcoded url


@login_required(login_url='/')
def delete_job(request, jid, state='', page=1):
	job = None
	try:
		job = Jobs.objects.get(id=jid)
		# Enforce access rights
		if job._author != request.user:
			raise PermissionDenied(request=request)
		#rshell.del_job(job)
		job.delete()
	except ObjectDoesNotExist:
		return aux.fail_with404(request, 'There is no job with id ' + str(jid) + ' in database')
	except Exception as e:
		console_print('Exception in delete_job : %s' % e)
		pass

	return dash_redir(request, job)


@login_required(login_url='/')
def delete_script(request, sid):
	script = Rscripts.objects.get(id=sid)
	# Enforce access rights
	if script.author != request.user:
		raise PermissionDenied(request=request)
	script.delete()
	return HttpResponseRedirect('/resources/scripts/') # FIXME hardcoded url


@login_required(login_url='/')
def delete_pipe(request, pid):
	pipe = ReportType.objects.get(id=pid)
	# Enforce access rights
	if pipe.author != request.user:
		raise PermissionDenied(request=request)
	pipe.delete()
	return HttpResponseRedirect('/resources/pipes/') # FIXME hardcoded url


@login_required(login_url='/')
def delete_report(request, rid, redir):
	report = None
	try:
		report = Report.objects.owner_get(request, rid)
		# Enforce access rights
		# if report.author != request.user:
		#	raise PermissionDenied(request=request)
		report.delete()
	except ObjectDoesNotExist:
		return aux.fail_with404(request, 'There is no report with id ' + str(rid) + ' in database')
	except Exception as e:
		logger.exception('Exception in delete_report : %s' % e)
		# console_print('Exception in delete_report : %s' % e)

	if redir == '-dash':
		return dash_redir(request, report)
	return HttpResponseRedirect('/reports/') # FIXME hardcoded url


# clem 11/09/2015
@login_required(login_url='/')
@csrf_exempt
def runnable_del(request, page=1, state=None):
	report = None
	lst_del = request.POST.getlist('delete')
	for each in lst_del:
		r_id = str(each).replace('report-', '').replace('script-', '')
		if str(each).startswith('report'):
			obj = Report
		elif str(each).startswith('script'):
			obj = Jobs
		try:
			report = obj.objects.get(id=r_id)
			# Enforce access rights
			if report.author == request.user:
				report.delete()
		except ObjectDoesNotExist as e:
			console_print('Object does not exist: %s' % e)
			pass
		except Exception as e:
			console_print('Exception in delete_report : %s' % e)
			pass

	return HttpResponseRedirect('/jobs/' + page)  # FIXME hardcoded url


@login_required(login_url='/')
def edit_report_access(request, rid):
	report_inst = Report.objects.owner_get(request, rid)
	__self__ = this_function_name()  # instance to self
	form_action = reverse(__self__, kwargs={'rid': rid})
	form_title = 'Edit "' + report_inst.name + '" sharing'

	# Enforce access rights
	# if report_inst.author != request.user:
	#	raise PermissionDenied(request=request)

	if request.method == 'POST':
		# Validates input info and commit the changes to report_inst instance directly through Django back-end
		property_form = breezeForms.EditReportSharing(request.POST, instance=report_inst, request=request)
		if property_form.is_valid():
			property_form.save()
			return HttpResponse(True)
	# TODO check if else is no needed here
	property_form = breezeForms.EditReportSharing(instance=report_inst, request=request)

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
		raise PermissionDenied(request=request)
	aux.delete_project(project)

	return HttpResponseRedirect('/home/projects')  # FIXME hardcoded url


@login_required(login_url='/')
def delete_group(request, gid):
	group = Group.objects.get(id=gid)
	# Enforce access rights
	if group.author != request.user:
		raise PermissionDenied(request=request)
	aux.delete_group(group)

	return HttpResponseRedirect('/home/groups')  # FIXME hardcoded url


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
		return HttpResponseRedirect('/jobs') # FIXME hardcoded url

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
	reports = Report.objects.filter(status='succeed').order_by('-created')
	i = 0
	malst = list()
	for each in reports:
		local_path, path_to_file, fileE, folderE = get_report_path_test(each)
		if not folderE or not fileE:
			malst.append({
				'id': str(each.id),
				'type': str(each.type),
				'created': str(each._created),
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
	# TODO FIXME
	from django.http import HttpResponseServerError
	# job = aux.get_job_safe(request, jid)
	job = Jobs.objects.owner_get(request, jid) # TODO check replacement
	user_info = request.user
	assert isinstance(job, Jobs)

	if mod is not None:
		mode = 'replicate'
		tmp_name = str(job.name) + '_REPL'
		edit = None
	else:
		mode = 'edit'
		tmp_name = str(job.name)
		edit = str(job.name)
	try:
		if request.method == 'POST':
			if edit is None:
				custom_form, head_form = rshell.build_script(request, job._type, job_inst=job)

				return HttpResponseRedirect('/jobs') # FIXME hardcoded url
			else:
				# EDIT :
				head_form = breezeForms.BasicJobForm(request.user, edit, request.POST)
				custom_form = breezeForms.form_from_xml(xml_parser=job.xml_tree, req=request, usr=request.user)
				if head_form.is_valid() and custom_form.is_valid():
					job._name = head_form.cleaned_data['job_name']
					job._description = head_form.cleaned_data['job_details']
					job.mailing = rshell.gen_mail_str(request)
					job.email = head_form.cleaned_data['report_to']
					job.assemble(sections=job.xml_tree, request_data=request)

					return HttpResponseRedirect('/jobs') # FIXME hardcoded url
		else:
			head_form = breezeForms.BasicJobForm(user=request.user, edit=str(job.name),
				initial={'job_name': str(tmp_name), 'job_details': str(job.description),
				'report_to': str(job.email if job.email else user_info.email)})
			custom_form = breezeForms.form_from_xml(xml_parser=job.xml_tree, usr=request.user)
	except RRuntimeError:
		return HttpResponseServerError('R runtime Error.')
	except IOError:
		return HttpResponseServerError('A required file could not be found.')

	return render_to_response('forms/user_modal.html', RequestContext(request, {
		'url': "/jobs/edit/%s%s" % (str(jid), mod if mod is not None else ''),
		'name': str(job.type.name),
		'inline': str(job.type.inln),
		'headform': head_form,
		'custform': custom_form,
		'layout': "horizontal",
		'mode': mode,
		'email': user_info.email
	}))


# TODO rewrite
@login_required(login_url='/')
def create_job(request, sid=None, page=1):
	from django.http import HttpResponseServerError
	script = Rscripts.objects.get(id=sid)
	mail_addr = request.user.email
	mails = dict

	try:
		if request.method == 'POST':
			go_run = request.POST.get('run_job') or request.POST.get('action') and request.POST.get('action') == 'run_job'
			custom_form, head_form = rshell.build_script(request, script, go_run)
			request.POST = custom_form
			state = "scheduled"
			if go_run:
				state = "current"
			return jobs(request, page, state)
		else:
			# Empty form
			mails = {'Started': u'checked', 'Ready': u'checked', 'Aborted': u'checked'}
			head_form = breezeForms.BasicJobForm(user=request.user, edit=None, initial={'report_to': mail_addr})
			custom_form = breezeForms.form_from_xml(xml_parser=script.xml_tree, usr=request.user)
	except RRuntimeError:
		return HttpResponseServerError()

	data = {
		'url': "/scripts/apply-script/" + str(sid),
		'name': script.name,
		'inline': script.inln,
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
	try:
		job = Jobs.objects.get(id=jid, _author=request.user)
	except (Report.DoesNotExist, Jobs.DoesNotExist):
		log = logger.getChild('abort_sge')
		# assert isinstance(log, logging.getLoggerClass())
		log.exception("user %s trying to run job %s that does not belong to him" & (request.user, jid))
		return jobs(request, error_msg="You cannot do that.")
	job.submit_to_cluster()

	# return jobs(request)
	return HttpResponseRedirect('/jobs/') # FIXME hardcoded url


# FIXME obsolete
@login_required(login_url='/')
def abort_sge(request, id, type):
	log = logger.getChild('abort_sge')
	# assert isinstance(log, logging.getLoggerClass())
	item = None
	try:
		if type == "report":
			item = Report.objects.get(id=id)
		elif type == "job":
			item = Jobs.objects.get(id=id)
	except (Report.DoesNotExist, Jobs.DoesNotExist):
		log.exception("job/report %s does not exists" % id)
		return jobs(request, error_msg="job/report  %s  does not exists\nPlease contact Breeze support" % id)

	s = None
	try:
		s = item.abort()
	except Exception as e:
		console_print('Exception in aborting : %s' % e)
		pass

	if s:
		return HttpResponseRedirect('/jobs/') # FIXME hardcoded url
	else:
		log.error("aborting job/report %s failed" % id)
		return jobs(request, error_msg="%s\nOn DRMAA job/report id  %s\nPlease contact Breeze support" % (s, id))


@login_required(login_url='/')
def abort_report(request, rid):
	return abort_sge(request, rid, "report")


@login_required(login_url='/')
def abort_job(request, jid):
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
@permission_required('breeze.add_rscripts', login_url="/") # TODO use everywhere
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


# TODO : find out usage
# FIXE : most likely broken
@login_required(login_url='/')
def save(request):
	logger.warning("Function views.save was called but it's probably BROKEN")
	# validate form_details also somehow in the IF below
	if storage.form_general.is_valid() and storage.form_sources.is_valid():
		# .xml_from_form() - creates doc in tmp for now
		breezeForms.xml_from_form(storage.form_general, storage.form_details, storage.form_sources)
		rshell.build_header(storage.form_sources.cleaned_data['header'])

		db_inst = storage.form_general.save(commit=False)

		db_inst.author = request.user
		db_inst.code = storage.code
		
		tmp_xml = str(settings.TEMP_FOLDER) + settings.SCRIPT_FORM_FN
		tmp_header = str(settings.TEMP_FOLDER) + settings.SCRIPT_CODE_HEADER_FN
		db_inst.docxml.save(settings.SCRIPT_FORM_FN, File(open(tmp_xml)))
		db_inst.header.save(settings.SCRIPT_CODE_HEADER_FN, File(open(tmp_header)))

		db_inst.save()

		# TODO improve the manipulation with XML - tmp folder not a good idea!
		os.remove(tmp_xml)
		os.remove(tmp_header)

		return HttpResponseRedirect(reverse(scripts))
	else:
		# TODO need an error handler here!
		return HttpResponseRedirect(reverse(scripts))


def show_rcode(request, jid):
	job = Jobs.objects.get(id=jid)
	# docxml = xml.parse(str(settings.MEDIA_ROOT) + str(job._doc_ml))
	docxml = xml.parse(str(job._doc_ml))
	script = job._name  # docxml.getroot().attrib["name"]
	inline = job._type.inln  # docxml.getroot().find('inline').text

	fields = list()
	values = list()
	input_array = docxml.getroot().find('inputArray')
	if input_array != None:
		for input_item in input_array:
			fields.append(input_item.attrib["comment"])
			values.append(input_item.attrib["val"])
	parameters = zip(fields, values)

	return render_to_response('forms/code_modal.html', RequestContext(request, {
		'name': str(job._name),
		'script': script,
		'inline': inline,
		'description': str(job._description),
		'input': parameters,
	}))


def veiw_project(request, pid):
	project = Project.objects.get(id=pid)
	context = {'project': project}

	return render_to_response('forms/project_info.html', RequestContext(request, context))


def view_group(request, gid):
	group = Group.objects.get(id=gid)
	context = {'group': group, 'user_list': group.user_list}

	return render_to_response('forms/group_info.html', RequestContext(request, context))


# Clem 28/08/2015
@login_required(login_url='/')
def send_zipfile_r(request, jid, mod=''):
	return send_zipfile(request, jid, mod=mod, serv_obj=Report)


# Clem 28/08/2015
@login_required(login_url='/')
def send_zipfile_j(request, jid, mod=''):
	return send_zipfile(request, jid, mod, Jobs)


@login_required(login_url='/')
def send_zipfile(request, jid, mod='', serv_obj=None):
	# 28/08/2015 changes : ACL, object agnostic, added Reports
	# 02/10/2015 migrated to Runnable and FolderObj
	# 20/01/2017 changed HttpResponse to StreamingHttpResponse for large file transfer
	# 25/01/2017 add nginx internal redirect ( HTTP header X-Accel-Redirect ) if archive already exists,
	# stream otherwise
	assert issubclass(serv_obj, Runnable)
	try:
		run_instance = serv_obj.objects.secure_get(id=jid, user=request.user)
		assert isinstance(run_instance, Runnable)
	except ObjectDoesNotExist:
		return aux.fail_with404(request, 'There is no record with id ' + jid + ' in DB')

	if mod != "-result" and not request.user.is_superuser and not request.user.is_staff:
		raise PermissionDenied(request=request)

	try:
		# wrapper, name, size, stream = run_instance.download_zip(mod)
		temp_file, do_stream = run_instance.download_zip(mod or '')
		
		content_dispo = 'attachment; filename=' + temp_file.name
		if do_stream:
			from django.http import StreamingHttpResponse
			response = StreamingHttpResponse(temp_file.stream(), content_type=c_t.ZIP)
		else:
			response = HttpResponse(content_type=c_t.ZIP)
			response['X-Accel-Redirect'] = '%s%s' % (settings.REPORTS_CACHE_INTERNAL_URL, temp_file.name)
		response['Content-Disposition'] = content_dispo
		response['Content-Length'] = temp_file.size
		response['Content-Transfer-Encoding'] = 'binary'
		return response
	except OSError as e:
		return aux.fail_with404(request, 'Some OS disk operation failed : %s' % e)


@login_required(login_url='/')
def send_template(request, name):
	template = InputTemplate.objects.get(name=name)
	path_to_file = str(settings.MEDIA_ROOT) + str(template.file)
	f = open(path_to_file)
	my_file = File(f)
	response = HttpResponse(my_file, content_type=c_t.FORCE_DL)
	folder, slash, b_file = str(template.file).rpartition('/')
	response['Content-Disposition'] = 'attachment; filename=' + b_file
	return response


@login_required(login_url='/')
# FIXEME : DEPRECATED
def send_file(request, ftype, fname):
	"""
		Supposed to be generic function that can send single file to client.
		Each IF case prepare dispatch data of a certain type.
		! Should substitute send_template() function soon !
	"""
	path_to_file = ''
	local_path = ''
	# TODO : substitute with send_template() ?
	if ftype == 'dataset':
		try:
			fitem = DataSet.objects.get(name=str(fname))
		except ObjectDoesNotExist:
			return aux.fail_with404(request, 'There is no report with id ' + str(fname) + ' in database')
		# TODO Enforce user access restrictions ?
		local_path, path_to_file = get_report_path(fitem)

	if ftype == 'report':
		try:
			fitem = Report.objects.get(id=str(fname))
		except ObjectDoesNotExist:
			return aux.fail_with404(request, 'There is no report with id ' + str(fname) + ' in database')
		#  Enforce user access restrictions
		if request.user not in fitem.shared.all() and fitem.author != request.user:
			raise PermissionDenied(request=request)

		local_path, path_to_file = get_report_path(fitem)

	f = open(path_to_file)
	my_file = File(f)
	response = HttpResponse(my_file, content_type=c_t.FORCE_DL)
	folder, slash, a_file = local_path.rpartition('/')
	response['Content-Disposition'] = 'attachment; filename=' + a_file
	return response


# Shiny tab access from inside
@login_required(login_url='/')
def report_shiny_view_tab(request, rid):
	if not rid or rid == '':
		return aux.fail_with404(request)
	try:
		report = Report.objects.get(id=rid)
		assert isinstance(report, Report)
	except ObjectDoesNotExist:
		return aux.fail_with404(request)
	# Enforce user access restrictions
	if not report.has_access_to_shiny(request.user):
		raise PermissionDenied(request=request)

	# return HttpResponseRedirect(reverse(report_shiny_in_wrapper, kwargs={ 'rid': rid }))
	return HttpResponseRedirect(report.get_shiny_report.url(report))


# Shiny tab access from outside (with the key)
def report_shiny_view_tab_out(request, s_key, u_key):
	__self__ = this_function_name()  # instance to self
	try:  # TODO merge ACL with out wrapper in a new func
		# Enforces access control
		# both request will fail if the object is not found
		# we fetch the report
		fitem = Report.objects.get(shiny_key=s_key)
		# and if found, check the user with this key is in the share list of this report
		fitem.offsiteuser_set.get(user_key=u_key)
	except ObjectDoesNotExist:
		return aux.fail_with404(request)

	if request.GET.get('list'):
		page_index, entries_nb = aux.report_common(request)
		# get off-site user
		off_user = OffsiteUser.objects.get(user_key=u_key)
		# list all shiny-enabled report he has access to
		all_reports = off_user.shiny_access.exclude(shiny_key=None)
		for each in all_reports:
			each.url = reverse(__self__, kwargs={'s_key': each.shiny_key, 'u_key': u_key})

		count = {'total': all_reports.count()}
		paginator = Paginator(all_reports, entries_nb)  # show 18 items per page
		try:
			a_reports = paginator.page(page_index)
		except PageNotAnInteger:  # if page isn't an integer
			page_index = 1
			a_reports = paginator.page(page_index)
		except EmptyPage:  # if page out of bounds
			page_index = paginator.num_pages
			a_reports = paginator.page(page_index)

		count.update({
			'first': (page_index - 1) * entries_nb + 1,
			'last': min(page_index * entries_nb, count['total'])
		})
		base_url = reverse(__self__, kwargs={'s_key': fitem.shiny_key, 'u_key': u_key})
		return render_to_response('out_reports-paginator.html', RequestContext(request, {
			'reports': a_reports,
			'pagination_number': paginator.num_pages,
			'count': count,
			'base_url': base_url,
			'page': page_index
		}))
		# return report_shiny_view_tab_merged(request, fitem.id, outside=True, u_key=u_key)

	return report_shiny_view_tab_merged(request, fitem.id, outside=True, u_key=u_key)


	# Shiny tab
# DO NOT CALL THIS VIEW FROM URL
def report_shiny_view_tab_merged(request, rid, outside=False, u_key=None):
	try:
		fitem = Report.objects.get(id=rid)
	except ObjectDoesNotExist:
		return aux.fail_with404(request, 'There is no report with id ' + rid + ' in DB')

	if outside:
		# TODO
		# nozzle = reverse(report_nozzle_out_wrapper, kwargs={'s_key': fitem.shiny_key, 'u_key': u_key})
		nozzle = ''
		base_url = '' # reverse(report_shiny_view_tab_out, kwargs={'s_key': fitem.shiny_key, 'u_key': u_key})
		frame_src = ''
	else:
		# Enforce user access restrictions for Breeze users
		if not fitem.has_access_to_shiny(request.user):
			raise PermissionDenied(request=request)
		# nozzle = reverse(report_file_view, kwargs={'rid': fitem.id})
		frame_src = reverse(report_file_view, kwargs={'rid': rid})
		nozzle = ''
		base_url = settings.SHINY_URL
		frame_src = '%s%s' % (base_url, fitem.id)

	return render_to_response('shiny_tab.html', RequestContext(request, {
		'nozzle': nozzle,
		'args': fitem.args_string,
		'base_url': base_url,
		'outside': outside,
		'frame_src': frame_src,
		'title': fitem.name
	}))


@csrf_exempt
@login_required(login_url='/')
def standalone_shiny_in_wrapper(request, path=None, sub=None):
	# Enforce user access restrictions

	# p1 = fitem.type.shiny_report.report_link_rel_path(fitem.id)
	path = path or ''
	sub = sub or ''
	return aux.proxy_to(request, path + '/' + sub, settings.SHINY_LOCAL_STANDALONE_BREEZE_URL)


@csrf_exempt
def standalone_pub_shiny_fw(request, path=''):
	from django.shortcuts import redirect
	return redirect(settings.SHINY_PUB_REDIRECT + path)


# Wrapper for ShinyApp accessed from inside (login + user access to said report)
# Proxy access manager
@csrf_exempt
@login_required(login_url='/')
def report_shiny_in_wrapper(request, rid, path=None):
	if not rid or rid == '':
		return aux.fail_with404(request)
	try:
		fitem = Report.objects.get(id=rid)
	except ObjectDoesNotExist:
		return aux.fail_with404(request)
	# Enforce user access restrictions
	if not fitem.has_access_to_shiny(request.user):
		raise PermissionDenied(request=request)

	p1 = fitem.type.shiny_report.report_link_rel_path(fitem.id)
	return aux.proxy_to(request, '%s/%s' % (p1, path), settings.SHINY_TARGET_URL)


# report_shiny_out_wrapper removed 08/03/2016 because it was not used
# report_nozzle_out_wrapper removed 08/03/2016 because it was no used


@csrf_exempt
@login_required(login_url='/')
def shiny_libs(request, path=None):
	return aux.proxy_to(request, '%s' % path, settings.SHINY_LIBS_TARGET_URL)


@login_required(login_url='/')
def report_file_view_redir(request, rid):
	return HttpResponseRedirect(reverse(report_file_view, kwargs={ 'rid': rid }))


def report_statics(request, a_dir, a_path):
	return HttpResponsePermanentRedirect('%sHTMLreport/%s/%s' % (settings.STATIC_URL, a_dir, a_path))


@login_required(login_url='/')
def report_file_view(request, rid, file_name=None):
	return report_file_server(request, rid, 'view', file_name)


@login_required(login_url='/')
def report_file_wrap(request, rid, rest, file_name=None):
	return report_file_server(request, rid, 'view', file_name)


@login_required(login_url='/')
def report_file_wrap2(request, rid, file_name=None):
	return report_file_server(request, rid, 'view', file_name)


@login_required(login_url='/')
def report_file_get(request, rid, file_name=None):
	return report_file_server(request, rid, 'get', file_name)


@login_required(login_url='/')
def report_file_server(request, rid, category, file_name=None):
	"""
	Serve report files, while enforcing access rights
	"""
	try:
		report_inst = Report.objects.secure_get(id=rid, user=request.user)
	except ObjectDoesNotExist:
		msg = 'There is no report with id %s in DB' % rid
		logger.warning(msg)
		return aux.fail_with404(request, msg)

	# Enforce user access restrictions
	# if request.user not in report_inst.shared.all() and report_inst.author != request.user\
	#	and not request.user.is_superuser:
	#	raise PermissionDenied(request=request)

	return report_file_server_sub(request, rid, category, fname=file_name, report_inst=report_inst)


# access from outside
# FIXME DEPRECATED (had no url right now)
def report_file_server_out(request, rid, category, u_key, fname=None):
	try:
		report_inst = Report.objects.get(id=rid)
		report_inst.offsiteuser_set.get(user_key=u_key)
	except ObjectDoesNotExist:
		msg = 'There is no such report'
		logger.warning(msg)
		return aux.fail_with404(request, msg)
	return report_file_server_sub(request, rid, category, fname=fname, report_inst=report_inst)


# DO NOT CALL THIS VIEW FROM url.py
def report_file_server_sub(request, rid, category, report_inst, fname=None):
	""" Serve report files
		SECURITY (ACL/ARM) has to be dealt with by the caller
		
		:param request: request object
		:type request: WSGIRequest
		:param rid: a Report id
		:type rid: int
		:param category: the category
		:type category: str
		:param report_inst: a Report class instance from db
		:type report_inst: Report
		:param fname: a specified file name (optional, default is report.html)
		:type fname: str
		:return: (local_path, path_to_file)
		:rtype: (str, str)
	"""
	from django.http import Http404
	# SAFETY FIRST
	assert isinstance(report_inst, Report)
	try:
		local_path, path_to_file = get_report_path(report_inst, fname)
		logger.debug('served: %s' % local_path)
	except Http404 as e:
		msg = ['The report file was not found.', 'This usually means that the pipeline'
			' did run, but failed to produce the report for some reason.',
			'Tis could be caused by the a script failing'
			' in an unexpected way that Breeze could not detect, or failed to detect.',
			'You can consider that this report has failed']
		return aux.fail_with404(request, msg, e.message)

	mime = MimeTypes()
	url = urllib.pathname2url(path_to_file)
	mime_type, encoding = mime.guess_type(url)
	mime_type = mime_type or c_t.OCTET_STREAM

	try:
		my_html = aux.html_auto_content_cache(path_to_file, False)

		response = HttpResponse(my_html, content_type=mime_type)
		folder, slash, a_file = local_path.rpartition('/')
		if category == 'get':
			response['Content-Disposition'] = 'attachment; filename=' + a_file
		else:
			response['Content-Disposition'] = 'filename=' + a_file
		return response
	except IOError:
		logger.exception('IOError %s' % path_to_file)
		return aux.fail_with404(request, 'File not found in expected location')


# Clem on 22/09/2015
@login_required(login_url='/')
def update_jobs_json(request, jid, item):
	if item == 'script':
		obj = Jobs.objects.get(id=jid)
		date = obj.created
		name = obj._name
	else:
		obj = Report.objects.get(id=jid)
		date = obj._created
		name = obj.name

	# sge_status = rshell.track_sge_job(obj)
	# request job instance again to be sure that the data is updated
	return dict(id=obj.id, name=name, staged=str(date), status=str(obj.status),
					progress=obj.progress, sge=obj.get_status(), md5=obj.md5), obj


@login_required(login_url='/')
def update_jobs(request, jid, item):
	response, _ = update_jobs_json(request, jid, item)
	return HttpResponse(simplejson.dumps(response), content_type=c_t.JSON)


@login_required(login_url='/')
def update_jobs_lp(request, jid, item, md5_t=None):
	if md5_t is None:
		return update_jobs(request, jid, item)
	from time import sleep
	refresh_time = 0.5

	if item == 'script':
		obj = Jobs.objects.get(id=jid)
	else:
		obj = Report.objects.get(id=jid)

	a_class = obj.instance_of

	last_sig = md5_t
	i = 0
	while last_sig == obj.md5:
		i += refresh_time
		if i > settings.LONG_POLL_TIME_OUT_REFRESH:
			break
		sleep(refresh_time)
		# forced refresh
		obj = a_class.objects.get(id=jid)

	return update_jobs(request, jid, item)


@login_required(login_url='/')
def send_dbcontent(request, content, iid=None):
	response = dict()
	# TODO ACL ?
	if content == "datasets":
		clist = DataSet.objects.all()
	elif content == "templates":
		clist = InputTemplate.objects.all()
	elif content == "description":
		script = Rscripts.objects.get(id=int(iid[1:]))
		response["description"] = script.details
		return HttpResponse(simplejson.dumps(response), content_type=c_t.JSON)
	else:
		# return empty dictionary if content was smth creepy
		return HttpResponse(simplejson.dumps(response), content_type=c_t.JSON)

	for item in clist:
		response[item.name] = item.description

	return HttpResponse(simplejson.dumps(response), content_type=c_t.JSON)


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
	
	sup = ''
	
	if form.is_valid():
		s_name = str(form.cleaned_data.get('name', None))
		s_inline = str(form.cleaned_data.get('inline', None))
		s_category = int(form.data.get('category', None))
		try:
			new_script = rshell.init_script(s_name, s_inline, request.user, s_category)
			if new_script:
				# go directly to the script editor view of the newly created script
				return script_editor(request, new_script.id)
			else:
				error_msg = 'Unable to create script "%s", unknown error' % s_name
				logger.error(error_msg)
				form.add_error('category', error_msg)
		except Exception as e:
			error_msg = 'Unable to create script %s : %s' % (s_name, str(e))
			logger.error(error_msg)
			form.add_error('category', error_msg)

	return render_to_response('forms/basic_form_dialog.html', RequestContext(request, {
		'form': form,
		# 'action': reverse(this_function_name()), # FIXME not working, possibly same issue with many others
		'action': '/scripts/new/', # FIXME not working, possibly same issue with many others
		'header': 'Create New Script' + sup,
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
		'action': '/new-rtype/', # FIXME hardcoded url
		'header': 'Create New Report Type',
		'layout': 'horizontal',
		'submit': 'Add'
	}))


@login_required(login_url='/')
def user_list(request):
	# user_lst = User.objects.all().order_by('username')
	user_lst = OrderedUser.objects.all()

	# lst = dict()
	lst = OrderedDict([])
	for each in user_lst:
		# lst[str(each)] = each.get_full_name()
		lst.update({str(each): each.get_full_name()})

	data = simplejson.dumps(lst)
	return HttpResponse(data, content_type=c_t.JSON)


# hardcoded url fixing done from bottom until here
@login_required(login_url='/')
def edit_rtype_dialog(request, pid=None, mod=None):
	"""
		This view provides a dialog to edit a report type in DB.
		@type request: django.db.models.query.QuerySet
		@type pid: int
	"""
	__self__ = this_function_name()  # instance to self
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
		'action': reverse(__self__),
		'header': 'Edit Report Type',
		'layout': 'horizontal',
		'submit': 'Save'
	}))


@login_required(login_url='/')
def new_project_dialog(request):
	"""
		This view provides a dialog to create a new Project in DB.
	"""
	__self__ = this_function_name()  # instance to self
	project_form = breezeForms.NewProjectForm(request.POST or None)

	if project_form.is_valid():
		aux.save_new_project(project_form, request.user)
		return HttpResponseRedirect(reverse(home, kwargs={ 'state': 'projects' }))

	return render_to_response('forms/basic_form_dialog.html', RequestContext(request, {
		'form': project_form,
		'action': reverse(__self__),
		'header': 'Create New Project',
		'layout': 'horizontal',
		'submit': 'Save'
	}))


@login_required(login_url='/')
def new_group_dialog(request):
	"""
		This view provides a dialog to create a new Group in DB.
	"""
	__self__ = this_function_name()  # instance to self
	group_form = breezeForms.GroupForm(request.POST or None, author=request.user)

	if group_form.is_valid():
		aux.save_new_group(group_form, request.user, request.POST)
		return HttpResponseRedirect(reverse(home, kwargs={ 'state': 'groups' }))

	return render_to_response('forms/basic_form_dialog.html', RequestContext(request, {
		'form': group_form,
		'action': reverse(__self__),
		'header': 'Create New Group',
		'layout': 'horizontal',
		'submit': 'Save'
	}))


@login_required(login_url='/')
def edit_project_dialog(request, pid):
	# TODO add user right management
	"""
		This view provides a dialog to create a new Project in DB.
	"""
	__self__ = this_function_name()  # instance to self
	project_data = Project.objects.get(id=pid)
	form_action = reverse(__self__, kwargs={'pid': pid})  # '/projects/edit/' + str(pid)
	form_title = 'Edit Project: ' + str(project_data.name)

	if request.method == 'POST':
		project_form = breezeForms.EditProjectForm(request.POST)
		if project_form.is_valid():
			aux.edit_project(project_form, project_data)
			# return HttpResponseRedirect('/home/projects')
			return HttpResponseRedirect(reverse(home, kwargs={'state': 'projects'}))
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
	__self__ = this_function_name()  # instance to self
	form_action = reverse(__self__, kwargs={'gid': gid})
	form_title = 'Edit Group: ' + str(group_data.name)

	if request.method == 'POST':
		group_form = breezeForms.EditGroupForm(request.POST, request=request)
		if group_form.is_valid():
			aux.edit_group(group_form, group_data, request.POST)
			return HttpResponseRedirect(reverse(home, kwargs={'state': 'groups'}))
	else:
		team = {}
		for arr in group_data.team.all():
			team[arr.id] = True

		group_form = breezeForms.EditGroupForm(initial={'group_team': team}, request=request)

	return render_to_response('forms/basic_form_dialog.html', RequestContext(request, {
		'form': group_form,
		'action': form_action,
		'header': form_title,
		'layout': 'horizontal',
		'submit': 'Save'
	}))


@login_required(login_url='/')
def update_user_info_dialog(request):
	__self__ = this_function_name()  # instance to self
	# user_info = User.objects.get(username=request.user)
	user_info = OrderedUser.objects.get(id=request.user.id)

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
				user_info.save()
				user_details.save()
			return HttpResponseRedirect('/home')  # FIXME hardcoded url

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
		'action': reverse(__self__),
		'header': 'Update Personal Info',
		'layout': 'horizontal',
		'submit': 'Save'
	}))


# FIXME no login ?
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
			if each_time <= each_group:
				count += 1
		response_data[idx] = [each_group, count]
	# response_data['message'] = ["Aug", "Sep", "Oct", "Nov"]

	return HttpResponse(simplejson.dumps(response_data), content_type=c_t.JSON)


@login_required(login_url='/')
def report_search(request):

	if not request.is_ajax():
		request.method = 'GET'
		return reports(request)  # Redirects to the default view (internally : no new HTTP request)
	
	request = legacy_request(request)

	search = request.REQUEST.get('filt_name', '') + request.REQUEST.get('filt_type', '') + \
		request.REQUEST.get('filt_author', '') + request.REQUEST.get('filt_project', '') + \
		request.REQUEST.get('access_filter1', '')
	entry_query = None
	page_index, entries_nb = aux.report_common(request)
	owned_filter = False

	if search.strip() != '' and not request.REQUEST.get('reset'):
		def query_concat(request, entry_query, rq_name, cols, user_name=False, exact=True):
			# like_a = '%' if like else ''
			query_type = (request.REQUEST.get(rq_name, '') if not user_name else request.user.id)
			tmp_query = aux.get_query(query_type, cols, exact)
			if not tmp_query:
				return entry_query
			return (entry_query & tmp_query) if entry_query else tmp_query

		# TODO make a sub function to reduce code duplication
		# filter by report name
		entry_query = query_concat(request, entry_query, 'filt_name', ['_name'], exact=False)
		# filter by type
		entry_query = query_concat(request, entry_query, 'filt_type', ['type_id'])
		# filter by author name
		entry_query = query_concat(request, entry_query, 'filt_author', ['author_id'])
		# filter by project name
		entry_query = query_concat(request, entry_query, 'filt_project', ['project_id'])
		# filter by owned reports
		if request.REQUEST.get('access_filter1'):
			owned_filter = True
			if request.REQUEST['access_filter1'] == 'owned':
				entry_query = query_concat(request, entry_query, 'access_filter1', ['author_id'], True)
			# filter by accessible reports
			elif request.REQUEST['access_filter1'] == 'accessible':
				entry_query = query_concat(request, entry_query, 'access_filter1', ['author_id', 'shared'], True)
	# Manage sorting
	if request.REQUEST.get('sort'):
		sorting = request.REQUEST.get('sort')
	else:
		sorting = '-_created'
	
	insti = UserProfile.get_institute(request.user)
	# Process the query
	if entry_query is None:
		found_entries = Report.objects.filter(status="succeed", institude=insti).order_by(sorting)  #
	# .distinct()
	else:
		found_entries = Report.objects.filter(entry_query, status="succeed", institude=insti).order_by(sorting).distinct()
	count = {'total': found_entries.count()}
	# apply pagination
	paginator = Paginator(found_entries, entries_nb)
	found_entries = paginator.page(page_index)
	# just a shortcut for the template
	for each in found_entries:
		each.user_is_owner = each.is_owner(request.user)
		each.user_has_access = each.has_access(request.user)
		# each.user_is_owner = each.author == request.user
		# each.user_has_access = request.user in each.shared.all() or each.user_is_owner
	# Copy the query for the paginator to work with filtering
	query_string = aux.make_http_query(request)
	# paginator counter
	count.update(aux.view_range(page_index, entries_nb, count['total']))

	return render_to_response('reports-paginator.html', RequestContext(request, {
		'reports': found_entries,
		'pagination_number': paginator.num_pages,
		'page': page_index,
		'url': 'search?',
		'search': query_string,
		'count': count,
		'sorting': sorting,
		'owned_filter': owned_filter
	}))


@csrf_exempt
@login_required(login_url='/')
def proxy_to(request, path, target_url, query_s=''):
	return aux.proxy_to(request, path, target_url, query_s)


def custom_404_view(request, message=None):
	if type(message) != list:
		message = [str(message)]
	t = loader.get_template('404.html')
	return http.HttpResponseNotFound(t.render({
		'request_path': request.path,
		'messages': message,
	}))

# DELETED on 08/09/2015 status_button(stat, text=['Online', 'Offline'], href=['#', '#']):


# clem on 24/08/2015
def status_button_json(stat, text, href=('#', '#'), c_type=('success', 'danger')):
	if type(stat) != bool:
		if type(stat) == HttpResponse:
			return stat
		return HttpResponse(str(stat), content_type=c_t.PLAIN)

	sel = 0 if stat else 1
	a_dict = { 'class': c_type[sel], 'text': text[sel], 'href': href[sel] }
	return HttpResponse(simplejson.dumps(a_dict), content_type=c_t.JSON)


# clem on 09/09/2015
# all the checker view in one proxy
@login_required(login_url='/')
def checker(request, what):
	try:
		test_obj = check.ui_get_object(what)
		return status_button_json(check.ui_checker_proxy(test_obj), test_obj.ui_text)
	except SystemCheckFailed:
		txt = test_obj.ex.__name__ if 'test_obj' in locals() and hasattr(test_obj, 'ex') else ObjectNotFound.__name__
		return status_button_json(False, ('', txt))
	except Exception as e:
		logger.exception(str(e))
	return status_button_json(False, ('', 'FAILED : %s' % str(e)))


# FIXME del DEPRECATED / STILL IN USE
@login_required(login_url='/')
def qstat_live(request):
	""" OLD AJAX qstat DEPRECATED

	:type request:
	:return: json
	:rtype: HttpResponse
	"""
	# return HttpResponse(Qstat().html, content_type='text/html')
	# TODO : fix
	return HttpResponse('', content_type=c_t.HTML)


# Clem 22/09/2015
@login_required(login_url='/')
def qstat_json(request):
	""" Returns a smart HTML view of qstat and associated md5,

	:type request:
	:return: json
	:rtype: HttpResponse
	"""
	# obj = Qstat()
	# return HttpResponse(simplejson.dumps({ 'md5': obj.md5, 'html': obj.html }), content_type=c_t.JSON)
	return HttpResponse(simplejson.dumps({ 'md5': '', 'html': '' }), content_type=c_t.JSON)


# Clem 22/09/2015
@login_required(login_url='/') # FIXME deprecated
def qstat_lp(request, md5_t=None):
	"""
	Long-Polling view for qstat
	Returns a smart HTML view of qstat and associated md5,
	Only upon changes from last client's known output.

	:type request:
	:type md5_t: str|None
	:return: json
	:rtype: HttpResponse
	"""
	# FIXME : CPU consumption really too high
	if False:
		if md5_t is None:
			return qstat_json(request)
		from time import sleep
		refresh_time = 0.5
		last_sig = md5_t
		i = 0
		while False: # last_sig == q.md5:
			i += refresh_time
			if i > settings.LONG_POLL_TIME_OUT_REFRESH:
				break
			sleep(refresh_time)
		return qstat_json(request)
	return aux.fail_with404(HttpRequest(), 'DISABLED')


# clem on 21/08/2015
@login_required(login_url='/')
def check_file_system_coherent(request):
	not_changed, not_broken, errors = check.check_is_file_system_unchanged()
	return status_button_json(not_broken, ['Valid', '%s error(s)' % errors], ['#', reverse(file_system_info)] )


# clem on 21/08/2015
@login_required(login_url='/')
def file_system_info(request):
	_, _, files_state, folders_state, _ = check.deep_fs_check()

	return render_to_response('fs_info.html', RequestContext(request, {
		'resources_status': 'active',
		'folders': folders_state,
		'files': files_state,
	}))


# clem on 08/10/2015
@login_required(login_url='/')
def view_log(request, show_all=False, num=0):
	DEFAULT_MAX = 250

	def no_withe_space(txt):
		return txt.replace('\t', '    ').replace(' ', '&nbsp;')

	if not request.user.is_superuser:
		# logger.warning(
		# 	'un-privileged user %s tried to trigger %s' % (request.user.get_full_name, utils.this_function_name()))
		raise PermissionDenied(request=request)
	grab_next = False
	last_pid = 0
	with open(settings.LOG_PATH) as f:
		log = f.readlines()
		out = list()
		for l in log:
			l = l.replace(">", "&gt;").replace("<", "&lt;")
			# l.encode('ascii', 'xmlcharrefreplace')
			# l.encode('ascii', 'ignore')
			# l = l.decode('utf-8') # .encode('utf-8', 'ignore')
			if l.replace('__breeze__started__', '') != l:
				out.append('<hr>') # add a separator to highlight reloads
			if l.strip() != '':
				if not l.startswith('20'):
					# reverse the order of Stack trace for them to be in-order
					# grab_next = True
					out[-1] += '<br />' + no_withe_space(l)

				# if l.startswith('20'):
				#	grab_next = False
				else:
					out.append(no_withe_space(l))
	out.append(no_withe_space(settings.USUAL_LOG_FORMAT_DESCRIPTOR))
	out.reverse()
	showing = 'whole (ie. <strong>%s</strong>) log since rotation' % len(out)
	if not show_all:
		if not num > 0:
			num = DEFAULT_MAX
		if num >= len(out):
			num = len(out)
		out = out[0:num]
		showing = 'last <strong>%s</strong> log entries' % num
	return render_to_response('log.html', RequestContext(request, {
		'resources_status': 'active',
		'log': out,
		'showing': showing
	}))


# clem on 08/10/2015
@login_required(login_url='/')
def fix_file_acl(request, fid):
	if not request.user.is_superuser:
		# logger.warning('un-privileged user %s tried to trigger %s' % (request.user.get_full_name,
		# utils.this_function_name()))
		raise PermissionDenied(request=request)

	try:
		utils.fix_file_acl_interface(fid)
	except OSError as e:
		# return custom_404_view(request, e)
		return aux.fail_with404(request, 'OSError', str(e.message))

	# return file_system_info(request)
	return HttpResponseRedirect(reverse(file_system_info))


# restart_breeze deleted on 19/10/2016
# restart_vm deleted on 19/10/2016
# restart_reboot_wrap deleted on 19/10/2016


@login_required(login_url='/')
def user_list_advanced(request):
	# user_lst = User.objects.all().order_by('username')
	if not (request.user.is_superuser or request.user.is_staff):
		raise PermissionDenied(request=request)
	user_lst = OrderedUser.objects.all()

	lst = list()
	lst2 = list()
	for each in user_lst:
		if each.email != '' and each.email is not None:
			lst.append(str(each.email))
		else:
			# lst2.append('%s (%s)' % (each.username, each.get_full_name()))
			lst2.append(str(each.username))

	data = ', '.join(lst) # simplejson.dumps(lst)
	data += '\n\n\nUsers with no registered email address :\n%s' % ', '.join(lst2)
	return HttpResponse(data, content_type=c_t.PLAIN)


@login_required(login_url='/')
def job_list(request):
	if not (request.user.is_superuser or request.user.is_staff):
		raise PermissionDenied(request=request)
	all_rt = ReportType.objects.all()
	resources = dict()
	for rt in all_rt:
		assert isinstance(rt, ReportType)
		last_y = Report.objects.filter(created__gt=datetime(2014, 12, 15)).filter(type_id=rt.id)
		new_l = list()
		for each in last_y:
			assert isinstance(each, Report)
			if each.sgeid != 0 and each.sgeid != '':
				new_l.append(each.sgeid)
		if len(new_l) > 0:
			resources.update({
				rt.type: new_l
			})

	all_jt = Rscripts.objects.all()
	resources2 = dict()
	for jt in all_jt:
		assert isinstance(jt, Rscripts)
		last_y = Jobs.objects.filter(staged__gt=datetime(2014, 12, 15)).filter(script_id=jt.id)
		new_l = list()
		for each in last_y:
			assert isinstance(each, Jobs)
			if each.sgeid != 0 and each.sgeid != '':
				new_l.append(each.sgeid)
		if len(new_l) > 0:
			resources2.update({
				jt.name: new_l
			})
	return HttpResponse(simplejson.dumps(resources) + '\n\n' + simplejson.dumps(resources2), content_type=c_t.JSON)


# clem 06/05/2016
def job_url_hook(request, i_type, rid, md5, status='', code=0):
	""" Endpoint of job feedback url.
	Instead of polling local jobs for completion, they will reach out to this url, upon termination

	:param request: usual request object
	:type request: int | str
	:param rid: id of the job
	:type rid: int | str
	:param md5: key identifying the job (a 32 chars md5 hash of the sh file for this job)
	:type md5: str
	:param status: string of the current status (starting | success | failed)
	:type status: str
	:param code: code of the exit status if not 0
	:type code: int
	:rtype: HttpResponse
	"""
	try:
		obj = Report if i_type == 'r' else Jobs
		a_runnable = obj.objects.f.get(pk=rid)
		if get_file_md5(a_runnable.rexec.path) == md5:
			# print 'OKAY GOOD' # TODO do stuff
			a_runnable.log.info('hook : %s (%s)' % (status, code))
	except ObjectDoesNotExist:
		pass
	return HttpResponse('ok', content_type=c_t.PLAIN)


# clem 17/05/2016
@login_required(login_url='/')
def invalidate_cache(request):
	if not request.user.is_superuser:
		raise PermissionDenied(request=request)
	ObjectCache.clear()
	return HttpResponse('ok', content_type=c_t.PLAIN)


# clem 17/05/2016
@login_required(login_url='/')
def invalidate_cache_view(request):
	if not request.user.is_superuser:
		raise PermissionDenied(request=request)
	ObjectCache.clear()
	destination = request.META.get('HTTP_REFERER', reverse(resources))
	return HttpResponseRedirect(destination)


@login_required(login_url='/')
def custom_list(request):
	assert is_admin(request)
	out = ''
	r_types = ReportType.objects.all() # all the types of reports

	for r_type in r_types:
		out += '\n\nAll users whom run at least one %s :\n' % r_type.type
		# users = r_type.get_all_users_ever()
		users = r_type.get_all_users_ever_with_count()
		# for user in users:

		names = list()
		emails = list()
		counts = list()

		for user, count in users.iteritems():
			counts.append('%s: %s' % (user.username, count))
			names.append(user.username)
			emails.append(user.email if user.email else 'N/A for %s' % user.username)

		out += 'Usernames : %s\n' % ', '.join(names)
		out += 'Emails : %s\n' % ', '.join(emails)
		out += 'Count : %s\n' % ', '.join(counts)

	return HttpResponse(out, content_type=c_t.PLAIN)
