import code_v1 as code
from common import *

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
def show_cache(request):
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
	# sorting = aux.get_argument(request, 'sort') or '-created' # FIXME legacy
	# get the user's institute
	# institute = UserProfile.get_institute(request.user)
	# all_reports = Report.objects.filter(status="succeed", _institute=institute).order_by(sorting)
	all_reports = Report.objects.get_accessible(request.user)
	print 'api report len : ', len(all_reports)
	
	return code.default_object_json_dump(Report, all_reports)


# clem 24/03/2017
@login_required
def projects(request):
	from breeze.models import Project
	return code.default_object_json_dump(Project)


# clem 24/03/2017
@login_required
def rtypes(request):
	from breeze.models import ReportType
	return code.default_object_json_dump(ReportType)


# clem 27/03/2017
@login_required
def users(request):
	from breeze.models import UserProfile
	return code.default_object_json_dump(UserProfile)


# clem 28/02/2016
def news(request):
	data = json.load(open(settings.settings.DJANGO_ROOT + 'news.json'))
	# return code.get_response(data=data, raw=True)
	return code.get_response(data=data)
