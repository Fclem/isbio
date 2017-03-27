from . import code_v1 as code
from .common import *

# import json # included in common
# import time # included in common
# from django.http import HttpResponse # included in common
# from django.core.handlers.wsgi import WSGIRequest # included in common
# from django.core.exceptions import SuspiciousOperation # included in common
# from breeze.utilities import * # included in common
# from breeze.utils import pp
# from django.core.urlresolvers import reverse
# from django.conf import settings
# from django import http
# from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
# from django.template.context import RequestContext
# from django.contrib.auth.decorators import login_required
# from django.http import HttpResponseRedirect, HttpResponsePermanentRedirect


#########
# VIEWS #
#########


# clem 17/10/2016
def hook(_):
	return code.get_response()


# clem 17/10/2016
@csrf_exempt
def reload_sys(request):
	payload, rq = code.get_git_hub_json(request)
	if not (payload and rq.is_json_post):
		raise default_suspicious(request)
	
	allow_filter = {
		'ref'                 : settings.GIT_AUTO_REF,
		'repository.id'       : "70237993",
		'repository.full_name': 'Fclem/isbio2',
		'pusher.name'         : 'Fclem',
		'sender.id'           : "6617239",
	}
	if rq.event_name == 'push' and match_filter(payload, allow_filter):
		logger.info(
			'Received system reload from GitHub, pulling (django should reload itself if any change occurs) ...')
		result = code.do_self_git_pull()
		return get_response(result, payload)

	return HttpResponseNotModified()
	
	
# clem 17/10/2016
@csrf_exempt
def git_hook(request):
	payload, rq = code.get_git_hub_json(request)
	if not (payload and rq.is_json_post):
		raise default_suspicious(request)

	allow_filter = {
		'ref'                 : "refs/heads/master",
		'repository.id'       : "70131764", # "DSRT-v2"
	}
	if rq.event_name == 'push' and match_filter(payload, allow_filter):
		logger.info('Received git push event for R code')
		result = code.do_r_source_git_pull()
		return get_response(data=payload) if result else get_response_opt(http_code=HTTP_NOT_IMPLEMENTED)

	return HttpResponseNotModified()


# clem 22/10/2016
@login_required
def show_cache(_):
	from utilz.object_cache import ObjectCache
	# data = { 'cache': dict(ObjectCache.dump()) }
	data = {'cache': ObjectCache.dump_list()}
	return code.get_response(data=data)


# clem 24/03/2017
@login_required
def reports(request):
	from breeze.models import UserProfile, Report
	from breeze import auxiliary as aux
	
	# Manage sorting
	sorting = aux.get_argument(request, 'sort') or '-created'
	# get the user's institute
	institute = UserProfile.get_institute(request.user)
	all_reports = Report.objects.filter(status="succeed", _institute=institute).order_by(sorting)
	
	data = {'data': Report.json_dump(all_reports)}
	return code.get_response(data=data)


# clem 24/03/2017
@login_required
def projects(request):
	from breeze.models import Project, UserProfile
	
	institute = UserProfile.get_institute(request.user)
	all_projects = Project.objects.filter(institute=institute)
	
	data = {'data': Project.json_dump(all_projects)}
	return code.get_response(data=data)


# clem 24/03/2017
@login_required
def rtypes(request):
	from breeze.models import ReportType, UserProfile
	
	institute = UserProfile.get_institute(request.user)
	all_rtypes = ReportType.objects.filter(institute=institute)
	
	data = {'data': ReportType.json_dump(all_rtypes)}
	return code.get_response(data=data)


# clem 27/03/2017
@login_required
def users(request):
	from breeze.models import User, UserProfile
	
	institute = UserProfile.get_institute(request.user)
	all_users = UserProfile.objects.filter(institute_info=institute)
	
	data = {'data': UserProfile.json_dump(all_users)}
	return code.get_response(data=data)


# clem 28/02/2016
def news(_):
	data = json.load(file(settings.settings.DJANGO_ROOT + 'news.json'))
	# return code.get_response(data=data, raw=True)
	return code.get_response(data=data)



"""

@login_required(login_url='/')
def reports(request, _all=False):

	page_index, entries_nb = aux.report_common(request)
	# Manage sorting
	sorting = aux.get_argument(request, 'sort') or '-created'
	# get the user's institute
	# insti = UserProfile.objects.get(user=request.user).institute_info
	insti = UserProfile.get_institute(request.user)
	all_reports = Report.objects.filter(status="succeed", _institute=insti).order_by(sorting)
	user_rtypes = request.user.pipeline_access.all()
	# later all_users will be changed to all users from the same institute
	# all_users = UserProfile.objects.filter(institute_info=insti).order_by('user__username')
	all_users = UserProfile.objects.all().order_by('user__username')
	# first find all the users from the same institute, then find their accessible report types
	
	# report_type_lst = ReportType.objects.filter(access=request.user)
	# all_projects = Project.objects.filter(institute=insti)
	all_projects = Project.objects.all()
	
	request = legacy_request(request)
	# filtering accessible reports (DO NOT DISPLAY OTHERS REPORTS ANYMORE; EXCEPT ADMIN OVERRIDE)
	all_reports = _report_filtering(all_reports, request.user, 'all' in request.REQUEST or _all)
	
	a_user_list = dict()
	for each in all_reports:
		a_user_list.update({each.author: UserProfile.objects.get(user=each.author)})
	all_users = a_user_list.values()
	all_users.sort()
	
	reptypelst = list()
	for each in all_users:
		rtypes = each.user.pipeline_access.all()
		# rtypes = each.pipeline_access.all()
		if rtypes:
			for each_type in rtypes:
				if each_type not in reptypelst:
					reptypelst.append(each_type)
	
	count = {'total': len(all_reports)}
	paginator = Paginator(all_reports, entries_nb)  # show 18 items per page

	# If AJAX - use the search view
	# Otherwise return the first page
	if request.is_ajax() and request.method == 'GET':
		return report_search(request, _all)
	else:
		page_index = 1
		reports_list = paginator.page(page_index)
		
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
			'url_lst': url_lst,
			'show_author_filter': not _report_filtering_show_limited_predicate(request.user, _all)
		}))
		
		
		
		
		
		
		
		
		
@login_required(login_url='/')
def report_search(request, all=False):

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
		found_entries = Report.objects.filter(status="succeed", _institute=insti).order_by(sorting)  #
	# .distinct()
	else:
		found_entries = Report.objects.filter(entry_query, status="succeed", _institute=insti).order_by(
			sorting).distinct()
		
	# filtering accessible reports (DO NOT DISPLAY OTHERS REPORTS ANYMORE; EXCEPT ADMIN OVERRIDE)
	found_entries = _report_filtering(found_entries, request.user, 'all' in request.REQUEST or all)
	
	count = {'total': len(found_entries)}
	# apply pagination
	paginator = Paginator(found_entries, entries_nb)
	found_entries = paginator.page(page_index)
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
		'owned_filter': owned_filter #,
		# 'show_author_filter': settings.SET_SHOW_ALL_USERS
	}))




"""
