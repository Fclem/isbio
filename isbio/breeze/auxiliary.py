import breeze.models
import re
import copy
import urllib
import urllib2
import glob
import mimetypes
from django import http
from django.template.defaultfilters import slugify
from django.http import Http404, HttpResponse
from django.template import loader
from django.template.context import RequestContext
from django.core.handlers.wsgi import WSGIRequest
from utils import *

DASHED_LINE = '-' * 111


# system integrity checks moved to system_check.py on 31/08/2015


def update_server_routine():
	if False:
		from sge_interface import Qstat, SGEError
		try:
			server_info = object() # Qstat().queue_stat

			if server_info.total == server_info.cdsuE:
				server = 'bad'
			elif int(server_info.avail) == 0:
				server = 'full'
			elif int(server_info.avail) <= 3:
				server = 'busy'
			elif float(server_info.cqload) > 30:
				server = 'busy'
			else:
				server = 'idle'

			return server, server_info.__dict__
		except AttributeError, SGEError:
			pass
	return 'bad', dict()


###
# ## TODO	How about moving those shits to Models ?
###


def clean_up_dt_id(lst):
	""" Cleans up row ids that come from the DataTable plugin.

	Arguments:
	lst      -- list of ids
	"""
	cleaned = map(lambda line: int(line[4:]), lst)  # (trim firs 4 chars)

	return cleaned


def save_new_project(form, author):
	""" Saves New Project data from a valid form to DB model.

	Arguments:
	form        -- instance of NewProjectForm
	author      -- user name
	"""
	insti = breeze.models.UserProfile.objects.get(user=author).institute_info
	dbitem = breeze.models.Project(
		name=str(form.cleaned_data.get('project_name', None)),
		manager=str(form.cleaned_data.get('project_manager', None)),
		pi=str(form.cleaned_data.get('principal_investigator', None)),
		author=author,
		collaborative=form.cleaned_data.get('collaborative', None),
		wbs=str(form.cleaned_data.get('wbs', None)),
		external_id=str(form.cleaned_data.get('eid', None)),
		description=str(form.cleaned_data.get('description', None)),
		institute=insti
	)

	dbitem.save()

	return True


# moved save_new_group 12/05/2017 to breeze.models.Groups.new


def edit_project(form, project):
	""" Edit Project data.

	Arguments:
	form        -- instance of EditProjectForm
	project     -- db instance of existing Project
	"""
	project.wbs = str(form.cleaned_data.get('wbs', None))
	project.external_id = str(form.cleaned_data.get('eid', None))
	project.description = str(form.cleaned_data.get('description', None))
	project.save()

	return True


# FIXME
def edit_group(form, group, post):
	""" Edit Group data.

	Arguments:
	form        -- instance of EditGroupForm
	group       -- db instance of existing Group
	"""
	# clean up first
	group.team.clear()
	group.save()

	for chel in post.getlist('group_team'):
		group.team.add(breeze.models.User.objects.get(id=chel))

	group.save()

	return True


def delete_project(project):
	""" Remove a project from a DB model.

	Arguments:
	project     -- db instance of Project
	"""
	project.delete()

	return True


# deleted delete_group(group) 12/05/2017, using breeze.Group.delete() instead


def open_folder_permissions(path, permit=0770):
	""" Traverses a directory recursively and set permissions.

	Arguments:
	path        -- a path string ( default '' )
	permit      -- permissions to be set in oct
				( default 0770 ) - '?rwxrwx---'
	"""

	for dirname, dirnames, filenames in os.walk(path):
		for subdirname in dirnames:
			full_dir_path = os.path.join(dirname, subdirname)
			os.chmod(full_dir_path, permit)

		for filename in filenames:
			full_file_path = os.path.join(dirname, filename)
			os.chmod(full_file_path, permit)

	os.chmod(path, permit)

	return True


###
# ##	TODO	How about moving those shits to Managers ?
###


def normalize_query(query_string,
					find_terms=re.compile(r'"([^"]+)"|(\S+)').findall,
					norm_space=re.compile(r'\s{2,}').sub):
	""" Splits the query string in individual keywords, getting rid of unnecessary spaces
		and grouping quoted words together.
		Example:

		>>> normalize_query('  some random  words "with   quotes  " and   spaces')
		['some', 'random', 'words', 'with quotes', 'and', 'spaces']
	"""
	return [norm_space(' ', (t[0] or t[1]).strip()) for t in find_terms(str(query_string))]


def get_query(query_string, search_fields, exact=True):
	""" Returns a query, that is a combination of Q objects. That combination
		aims to search keywords within a model by testing the given search fields.
	"""
	from breeze.managers import Q
	query = None  # Query to search for every search term
	terms = normalize_query(query_string) if query_string else []
	for term in terms:
		or_query = None  # Query to search for a given term in each field
		for field_name in search_fields:
			q = Q(**{ "%s" % field_name: term }) if exact else Q(**{ "%s__icontains" % field_name: term })
			if or_query is None:
				or_query = q
			else:
				or_query |= q
		if query is None:
			query = or_query
		else:
			query = query & or_query
	return query


# DELETED extract_users 18/01/2017
# DELETED extract_groups 18/01/2017

# TODO get rid of that
def merge_job_history(jobs, reports, user=None):
	""" Merge reports and jobs in a unified object (list)
		So that reports and jobs can be processed similarly on the client side
	"""
	merged = list()
	pool = list(jobs) + list(reports)

	from breeze.models import Runnable

	for item in pool:
		assert isinstance(item, Runnable)
		el = dict()
		# TODO automatize this part
		if item.is_job:
			el['instance'] = 'script'
			el['id'] = item.id
			el['jname'] = item.jname
			el['status'] = item.status
			el['staged'] = item.staged

			el['rdownhref'] = '/jobs/download/%s-result'%str(item.id)  # results
			el['ddownhref'] = '/jobs/download/%s-code'%str(item.id)  # debug
			el['fdownhref'] = '/jobs/download/%s'%str(item.id)  # full folder
			
			el['home'] = item.home_folder_rel
			el['reschedhref'] = '/jobs/edit/%s-repl'%str(item.id)

			el['delhref'] = '/jobs/delete/%s'%str(item.id)
			el['abohref'] = '/abortjobs/%s'%str(item.id)

			el['progress'] = item.progress
			el['type'] = item.script
			el['r_error'] = item.r_error

			el['shiny_key'] = ''
			el['go_shiny'] = False

		else:                             # report
			el['instance'] = 'report'
			el['id'] = item.id
			el['jname'] = item.name
			el['status'] = item.status
			el['staged'] = item.created

			# el['rdownhref'] = '/get/report-%s'%str(item.id)  # results
			el['rdownhref'] = '/report/download/%s-result'%str(item.id)  # results
			el['ddownhref'] = '/report/download/%s-code' % str(item.id)  # debug
			el['fdownhref'] = '/report/download/%s' % str(item.id)  # full folder

			el['home'] = item.home_folder_rel
			el['reschedhref'] = '/reports/edit/%s'%str(item.id)

			el['delhref'] = '/reports/delete/%s-dash'%str(item.id)
			el['abohref'] = '/abortreports/%s'%str(item.id)

			el['progress'] = item.progress
			el['type'] = item.type
			el['r_error'] = item.r_error

			el['shiny_key'] = item.shiny_key
			el['go_shiny'] = item.is_shiny_enabled and item.has_access_to_shiny(user)

		merged.append(copy.deepcopy(el))

	# sort list according to creation daten and time
	merged.sort(key=lambda r: r['staged'])
	merged.reverse()

	return merged


def merge_job_lst(item1, item2):
	""" Merge reports with reports or jobs with jobs in a unified object (list) """
	merged = list() + list(item1) + list(item2)

	# sort list according to creation date and time
	merged.sort(key=lambda r: r['staged'])
	merged.reverse()

	return merged


###
# ##	*** END ***
###

# 02/06/2015 Clem # FIXME merge into a class with rest of related code
def view_range(page_index, entries_nb, total):
	""" Calculate and return a dict with the number of the first and last elements in the current view of the paginator

	:param page_index: number of the current page in the paginator (1 to x)
	:type page_index: int
	:param entries_nb: number of elements to be disaplayed in the view
	:type entries_nb: int
	:param total: total number of elements
	:type total: int
	:return: dict(first, last, total)
	:rtype: dict
	"""
	return dict(first=(page_index - 1)*entries_nb + 1, last=min(page_index*entries_nb, total), total=total)


# 28/04/2015 Clem
def make_http_query(request):
	""" serialize GET or POST data from a query into a dict string

	:param request: Django Http request object
	:type request: http.HttpRequest
	:return: QueryString
	:rtype: str
	"""
	if request.method == 'POST':
		args = request.POST.copy()
	else:
		args = request.GET.copy()

	if args.get('page'):
		del args['page']
	if args.get('csrfmiddlewaretoken'):
		del args['csrfmiddlewaretoken']

	query_string = ''
	for each in args:
		if args[each] != '':
			query_string = query_string + each + ': "' + args[each] + '", '

	if len(query_string) > 0:
		query_string = query_string[:-2]

	return query_string


# clem 23/06/2016 # FIXME merge into a class with rest of related code
def get_argument(req, arg_name):
	g = req.GET.get(arg_name, None)
	p = req.POST.get(arg_name, None)

	if g and not p:
		return g
	elif p and not g:
		return p
	elif not p and not g:
		return None
	else:
		raise AttributeError('argument %s is both in both GET and POST' % arg_name)


# 10/03/2015 Clem updated 23/06/2016 # FIXME merge into a class with rest of related code
def report_common(request, v_max=15):
	"""
	:type request: django.core.handlers.wsgi.WSGIRequest
	:type v_max: int
	:return: page_index, entries_nb
		page_index: int
			current page number to display
		entries_nb: int
			number of item to display in a page
	"""
	return int(get_argument(request, 'page') or 1), int(get_argument(request, 'entries') or v_max)

# DELETED get_job_safe(request, job_id) 19/02/2016 replaced by manager.owner_get
# DELETED get_report_safe(request, job_id, owner=True) 19/02/2016 replaced by manager.owner_get
# DELETED  get_worker_safe_abstract(request, obj_id, model) 19/02/2016 replaced by manager.owner_get


# 10/03/2015 Clem / ShinyProxy
def u_print(request, url, code=None, size=None, date_f=None):
	print u_print_sub(request, url, code, size, date_f)


def u_print_sub(request, url, code=None, size=None, date_f=None):
	proto = request.META['SERVER_PROTOCOL'] if request.META.has_key('SERVER_PROTOCOL') else ''
	return console_print_sub("\"PROX %s   %s %s\" %s %s" % (request.method, url, proto, code, size), date_f=date_f)


# DELETED get_report_path(f_item, fname=None) 19/02/2016 moved to comp.py
# DELETED get_report_path_test(f_item, fname=None, no_fail=False): 19/02/2016 moved to comp.py


def fail_with404(request, error_msg=None, log_message=''):
	"""
	custom 404 method that enable 404 template even in debug mode (discriminate from real 404),
	Raise no exception so call it with return

	:param request: Django request object
	:type request: http.HttpRequest
	:param error_msg: The message to display on the 404 page, defaults to ''
	:type error_msg: str | list
	:param log_message: The message to write in the logs, defaults to error_msg
	:type log_message: str | None
	:return: custom 404 page
	:rtype: http.HttpResponseNotFound
	"""

	t = loader.get_template('404.html')

	if type(error_msg) is not list:
		error_msg = [error_msg]

	rq_path = request.path if request is not None else ''
	
	if not log_message:
		log_message = error_msg
	logger.warning('404 @ %s from %s : %s' % (rq_path, this_function_caller_name(), log_message))

	return http.HttpResponseNotFound(t.render({
		'request_path': rq_path,
		'messages': error_msg,
	}))


# FIXME old and nasty code (STILL IN USE, for Shiny and to check CAS connection)
def proxy_to(request, path, target_url, query_s='', silent=False, timeout=None):
	import fileinput
	console_date_f = settings.CONSOLE_DATE_F

	qs = ''
	url = '%s%s' % (target_url, path)
	if query_s and query_s != '':
		qs = '?' + query_s
		url += qs
	elif 'QUERY_STRING' in request.META and request.META['QUERY_STRING'] != "":
		qs = '?' + request.META['QUERY_STRING']
		url += qs
	opener = urllib2.build_opener()
	data = ''
	if request.method == 'POST':

		from urllib import quote_plus

		print 'POST:', str(request.POST)

		def encode_obj(in_obj):

			def encode_list(in_list):
				out_list = []
				for el in in_list:
					out_list.append(encode_obj(el))
				return out_list

			def encode_dict(in_dict):
				out_dict = { }
				for k, v in in_dict.iteritems():
					out_dict[k.encode('utf-8')] = encode_obj(v)
				return out_dict

			if isinstance(in_obj, unicode):
				return in_obj.encode('utf-8')
			elif isinstance(in_obj, list):
				return encode_list(in_obj)
			elif isinstance(in_obj, tuple):
				return tuple(encode_list(in_obj))
			elif isinstance(in_obj, dict):
				return encode_dict(in_obj)

			return in_obj
		#import requests
		#payload_str = "&".join("%s=%s" % (k, v) for k, v in dict(request.POST.iteritems()))
		## req = requests.post(url, params=payload_str)
		#req = requests.get(url, params=payload_str)
		#return HttpResponse(req.content, status=req.status_code, mimetype=req.apparent_encoding)

		tmp = encode_obj(dict(request.POST.iteritems()))
		#from cStringIO import StringIO
		#buf = StringIO()
		#for k, v in tmp.iteritems():
		#	buf.write(k + '=' + v + '&')

		# data = buf.getvalue()[:-1]
		data = '&'.join(k + '=' + v for k, v in tmp.iteritems())  # data should be bytes
		#print '#' * 56 + ' DATA : ' + '#' * 56 + '\n' + data[:1024] + '\n' + '#' * 120

	log = '/var/log/shiny-server.log'
	log_size = os.stat(log).st_size
	proxied_request = None
	msg = ''
	reason = ''
	more = ''
	rep = HttpResponse(status=599, mimetype=HttpResponse)
	try:
		if not silent:
			get_logger().debug(u_print_sub(request, path + str(qs)))
		if settings.VERBOSE:
			u_print(request, path + str(qs), date_f=console_date_f)
		if timeout:
			proxied_request = opener.open(url, data or None, timeout=timeout)
		else:
			proxied_request = opener.open(url, data or None)
	except urllib2.HTTPError as e:
		# add the shiny-server log tail
		if log_size < os.stat(log).st_size:
			more = "%s :\n" % log
			try:
				with open(log) as f:
					logger.debug('read: %s' % log)
					f.seek(log_size)
					for line in f.readlines():
						more += line + '\n'
			except Exception as e:
				pass
			more = more[:-1] + DASHED_LINE + '\n'

		# try to read the shiny app log :
		p = '/var/log/shiny-server/' + path[:-1] + '-shiny-*'
		for fileName in glob.glob(p):
			# more += os.path.basename(fileName) + ' : \n'
			more += fileName + ' :\n'
			for line in fileinput.input(fileName, openhook=fileinput.hook_encoded("utf8")):
				more += line + '\n'
			fileinput.close()
			try:
				os.remove(fileName)
			except Exception as e:
				pass
			more = more[:-1] + DASHED_LINE + '\n'

		try:
			content = e.read()
		except Exception as e:
			if hasattr(e, 'msg'):
				msg = e.msg
			if hasattr(e, 'reason'):
				reason = e.reason
			content = 'SHINY SERVER : %s\nReason : %s\n%s\n%s' % (msg, reason, DASHED_LINE, more)

		msg, reason, code, mime = '', '', '', ''
		if hasattr(e, 'code'):
			code = e.code
		if hasattr(e, 'headers'):
			mime = e.headers.typeheader
		print "'%s' '%s'" % (url, data)
		print proxied_request
		logger.getChild('shiny_server').warning('%s : %s %s%s\n%s' % (e, request.method, path, str(qs), more))
		rep = HttpResponse(content, status=code, mimetype=mime)
	except urllib2.URLError as e:
		get_logger().error(e)
		pass
	else:
		status_code = proxied_request.code
		mime_type = proxied_request.headers.typeheader or mimetypes.guess_type(url)
		content = proxied_request.read()
		if proxied_request.code != 200:
			print 'PROX::', proxied_request.code
		if not silent:
			get_logger().debug(u_print_sub(request, path + str(qs), proxied_request.code, str(len(content))))
		if settings.DEBUG and not silent:
			u_print(request, path + str(qs), proxied_request.code, str(len(content)), date_f=console_date_f)
		rep = HttpResponse(content, status=status_code, mimetype=mime_type)
	return rep

# 29/05/2015 TOOOOOOOO SLOW
# DELETED update_all_jobs_sub on 30/06/2015


# clem 02/10/2015
def html_auto_content_cache(path_to_file, convert_img=True):
	""" Figure out if an HTML file has been cached or not, and return file content.
	
	If file was not cached, checks for image content and return <i>image_embedding()</i> processed markup
	<i>image_embedding()</i> transform images link in embedded images and save a cache file.
	<i>Experimental results shows browser <u>loading time decrease by <b>factor 10+</b></u> (2000+ images)</i>

	:param path_to_file: path to the HTML file
	:type path_to_file: str
	:param convert_img: wether to convert img from HTML file to embedded base64 images
		(WARNING : currently breaks <img> attributes)
	:type convert_img: bool
	:rtype: str
	"""
	from os.path import splitext, dirname, basename, isfile

	file_name, file_ext = splitext(basename(path_to_file))
	file_ext = slugify(file_ext)

	if not convert_img or file_ext != 'html' and file_ext != 'htm':
		f = open(path_to_file)
		logger.debug('read: %s' % path_to_file)
		return f.read()

	dir_path = dirname(path_to_file) + '/'
	cached_path = dir_path + file_name + '_cached.' + file_ext

	if isfile(cached_path): # and getsize(cached_path) > pow(1024, 2): # 1 Mibi
		f = open(cached_path)
		logger.debug('read: %s' % cached_path)
		return f.read()
	
	return image_embedding(path_to_file, cached_path)


# clem 30/09/2015
def image_embedding(path_to_file, cached_path=None):
	"""
	Replace <img> links in HTML's <i>path_to_file</i> content by corresponding base64_encoded embedded images
	Save the generated file to [<i>original_file_name</i>]_cached.[extension]
	<u>images files's urls have to be a path inside path_to_file's containing folder</u>

	:param path_to_file: path to the HTML file
	:type path_to_file: str
	:param cached_path:
	:type cached_path: str
	:rtype: str
	"""
	from os.path import splitext, dirname
	from bs4 import BeautifulSoup
	changed = False

	f = open(path_to_file)
	# soup = BeautifulSoup(f.read(), 'lxml')
	dir_path = dirname(path_to_file) + '/'
	soup = BeautifulSoup(f.read(), 'html.parser')
	all_imgs = soup.findAll('img')
	for each in all_imgs:
		if not str(each['src']).startswith('data:'):
			ext = slugify(splitext(each['src'])[1])
			if ext in ['jpg', 'jpeg', 'png', 'gif']:
				changed = True
				data_uri = open(dir_path + each['src'], 'rb').read().encode('base64').replace('\n', '')
				img_tag = BeautifulSoup('<img src="data:image/{0};base64,{1}">'.format(ext, data_uri), 'html.parser')
				each.replace_with(img_tag)

	if cached_path and changed:
		f2 = open(cached_path, 'w')
		f2.write(str(soup))

	return str(soup)


def legacy_request(request):
	""" Adds back the REQUEST property as dict(self.GET + self.POST) that seems to be missing
	
	:type request: WSGIRequest
	:rtype: WSGIRequest
	"""
	
	assert isinstance(request, WSGIRequest)
	if not hasattr(request, 'REQUEST'):
		request.REQUEST = copy.copy(request.GET)
		request.REQUEST.update(request.POST)
	return request


# clem 10/05/2017 # FIXME merge into a class with rest of related code
def report_filtering(request, _all):
	from models import Report
	request = legacy_request(request)
	
	search = request.REQUEST.get('filt_name', '') + request.REQUEST.get('filt_type', '') + \
		request.REQUEST.get('filt_author', '') + request.REQUEST.get('filt_project', '') + \
		request.REQUEST.get('access_filter1', '')
	
	entry_query = None
	page_index, entries_nb = report_common(request)
	owned_filter = False
	
	# Manage sorting
	if request.REQUEST.get('sort'):
		sorting = request.REQUEST.get('sort')
	else:
		sorting = '-_created'
	
	# initial the query
	found_entries = Report.objects.f.get_done(False, False).order_by(sorting)
	
	if search.strip() != '' and not request.REQUEST.get('reset'):
		def query_concat(request, entry_query, rq_name, cols, user_name=False, exact=True):
			# like_a = '%' if like else ''
			query_type = (request.REQUEST.get(rq_name, '') if not user_name else request.user.id)
			tmp_query = get_query(query_type, cols, exact)
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
		if request.REQUEST.get('access_filter1', None) not in ['all', '', None]:
			owned_filter = True
			if request.REQUEST['access_filter1'] == 'owned':
				entry_query = query_concat(request, entry_query, 'access_filter1', ['author_id'], True)
			# filter by accessible reports
			elif request.REQUEST['access_filter1'] == 'accessible':
				entry_query = query_concat(request, entry_query, 'access_filter1', ['author_id', 'shared'], True)
			elif request.REQUEST['access_filter1'] == 'shared':
				# entry_query = query_concat(request, entry_query, 'access_filter1', ['shared'], True)
				found_entries = Report.objects.get_shared_with_user_all(request.user, found_entries)

	# if some filters apply, filter the original query
	if entry_query and found_entries:
		found_entries = found_entries.filter(entry_query)
	found_entries = found_entries.distinct()
	
	response = {
		'page':              page_index,
		'sorting':           sorting,
		'entries_nb':        entries_nb,
		'owned_filter':      owned_filter
	}
	
	# filtering accessible reports (DO NOT DISPLAY OTHERS REPORTS ANYMORE; EXCEPT ADMIN OVERRIDE)
	return Report.objects.get_accessible(request.user, 'all' in request.REQUEST or _all, query=found_entries), response
	# return found_entries, response


# clem 10/05/2017 # FIXME merge into a class with rest of related code
def reports_links(_all):
	return { # TODO remove static url mappings
		'Edit': '/reports/edit_access/',
		'Add':  '/off_user/add/',
		'Send': '/reports/send/',
		'less': '/reports/',
		'self': '/reports/%s' % ('all/' if _all else ''),
		'all':  '/reports/all/'
	}
