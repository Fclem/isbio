from .common import *

# from django.views.decorators.csrf import csrf_exempt
# from django.utils import timezone
# from breeze.utils import pp
# from django.conf import settings
# from django import http
# from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
# from django.http import HttpResponseRedirect, HttpResponsePermanentRedirect
# from django.template.context import RequestContext
# from django.core.urlresolvers import reverse


# clem 17/10/2016
def get_response(data=empty_dict, version='', result=''):
	return HttpResponse(json.dumps(data), content_type=CT_JSON)


# clem 17/10/2016
# copied from breeze
@allow_guest
def show_templates(_, content, iid=None):
	from breeze.models import DataSet, InputTemplate, Rscripts
	response = dict()
	c_list = list()
	# TODO ACL ?
	if content == "datasets":
		c_list = DataSet.objects.all()
	elif content == "templates":
		c_list = InputTemplate.objects.all()
	elif content == "description":
		script = Rscripts.objects.get(id=int(iid[1:]))
		response["description"] = script.details
	
	if c_list:
		for item in c_list:
			response[item.name] = item.description
		
	return get_response(response, version='legacy')
