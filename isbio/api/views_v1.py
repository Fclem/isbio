import code_v1 as code
from common import *
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponseNotModified

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
	if not (payload and rq.enforce_json_post):
		raise default_suspicious(request, 'Request had no payload')
	
	allow_filter = {
		'ref':                  settings.GIT_AUTO_REF,
		'repository.id':        "70237993",
		'repository.full_name': 'Fclem/isbio2',
		'pusher.name':          'Fclem',
		'sender.id':            "6617239",
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
	if not (payload and rq.enforce_json_post):
		raise default_suspicious(request)
	
	allow_filter = {
		'ref':           "refs/heads/master",
		'repository.id': "70131764", # "DSRT-v2"
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
	data = {'cache': ObjectCache.dump_list()}
	return code.get_response(data=data)


# clem 24/03/2017
@allow_guest
def reports(request):
	from breeze.models import Report
	return code.default_object_json_dump(Report, Report.objects.get_accessible(request.user))


# clem 24/03/2017
@allow_guest
def projects(_):
	from breeze.models import Project
	return code.default_object_json_dump(Project)


# clem 24/03/2017
@allow_guest
def report_types(_):
	from breeze.models import ReportType
	return code.default_object_json_dump(ReportType)


# clem 27/03/2017
@allow_guest
def users(_):
	from breeze.models import UserProfile
	return code.default_object_json_dump(UserProfile)


# clem 28/02/2016
def news(_):
	data = json.load(open(settings.settings.DJANGO_ROOT + 'news.json'))
	return code.get_response(data=data)


# clem 26/05/2017
@login_required
def report_info(request, jid, md5_t=''):
	from breeze.models import Report
	return code.get_response(data={'data': Report.objects.secure_get(id=jid, user=request.user).json_info})


# clem 26/05/2017
@login_required
def reports_active(_):
	from breeze.models import Report
	return code.default_object_json_dump(Report, Report.objects.f.get_active())
