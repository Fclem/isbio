import sys
# imports from sub-modules (the order is CRITICAL)
from system import *
from pythonic import *
from my_logging import *
from file_system import *
from networking import *
import git
from object_cache import ObjectCache
# noinspection PyUnresolvedReferences
from time import sleep

# DO NOT HAVE ANY BREEZE NOR DJANGO RELATED CODE IN THIS MODULE
# this module is intended to have utilities function used in breeze, but must remain self-contained
# i.e. NO Breeze related code, no Django-specific code, no imports from Breeze nor Django

IS_PY2 = sys.version_info.major == 2
IS_PY3 = sys.version_info.major == 3
if IS_PY3:
	# noinspection PyShadowingBuiltins
	str = bytes
	# noinspection PyShadowingBuiltins
	basestring = str
	# noinspection PyShadowingBuiltins
	unicode = str
else:
	try:
		# noinspection PyShadowingBuiltins,PyUnboundLocalVariable
		unicode = unicode
	finally:
		pass
	# noinspection PyShadowingBuiltins,PyCompatibility
	basestring = basestring
	# noinspection PyShadowingBuiltins
	str = str


# TODO rewrite, as a class maybe ?
# clem 09/03/2016 contains code from from http://stackoverflow.com/a/3229493/5094389
def advanced_pretty_print(d, indent=0, open_obj=False, get_output=False):
	""" Prints a tree from a nested dict

	:type d: dict | list | basestring
	:type indent: int
	:type open_obj: bool
	:type get_output: bool
	:rtype: None | basestring
	"""

	buff = ''

	# clem 10/03/2016
	def get_iter(obj):
		if isinstance(obj, basestring):
			return obj
		if type(obj) in [dict, list] or hasattr(obj, 'iteritems') or hasattr(obj, '__iter__'):
			return obj
		if hasattr(obj, '__dict__'):
			if open_obj:
				return obj.__dict__
			else:
				return repr(obj)
		return list()

	# clem 10/03/2016
	def get_type(obj):
		res = str(type(obj)).partition("'")[2].partition("'")[0]
		return res if not res == 'instance' else ''

	# clem 10/03/2016
	def get_size(obj):
		try:
			return len(obj)
		except (TypeError, AttributeError):
			if hasattr(obj, 'bit_length'):
				return obj.bit_length()
		return '?'

	# clem 10/03/2016
	def extra_info(obj):
		a_type = get_type(obj)
		return ' <%s:%s>' % (a_type, get_size(obj)) if a_type else ''

	# clem 14/03/2016
	def out(content):
		if get_output:
			return content
		else:
			print(content)
			return ''

	def multi_line_indent(txt):
		return txt.replace('\n', '\n' + '\t' * (indent + 1))

	iterable = get_iter(d)

	if type(d) is list: # source element is a list, that may contain dicts
		i = 0
		for el in iterable:
			buff += out('\t' * indent + '_#%s :' % i)
			buff += str(advanced_pretty_print(el, indent + 1, open_obj, get_output))
			i += 1
	elif type(d) is dict or type(iterable) is dict:
		for key, value in iterable.items():
			buff += out('\t' * indent + str(key) + extra_info(value))
			if isinstance(value, (dict, list)):
				buff += str(advanced_pretty_print(value, indent + 1, open_obj, get_output))
			else:
				buff += out('\t' * (indent + 1) + multi_line_indent(str(repr(value))))
	else:
		buff += out(u'\t' * (indent + 1) + multi_line_indent(unicode(iterable)))

	# if get_output:
	return buff


# clem 01/04/2016
def pp(data, unfold_objects=False, return_output=False):
	return advanced_pretty_print(data, open_obj=unfold_objects, get_output=return_output)


# clem 06/04/2016
# deleted password_from_file 22/09/2016


# clem 06/05/2016, moved here on 16/05/2016
def gen_file_from_template(template_path, sub_dict, output_path=None, safe=True):
	""" generates a content from a template

	:param template_path: the path of the template file to use
		(c.f. https://docs.python.org/2.7/library/string.html#string.Template )
	:type template_path: str or unicode
	:param sub_dict: the substitution dictionary to use. Keys are used to match the $-var in the template
	:type sub_dict: dict
	:param output_path: the full path (including file name) where to save the output to. If None, then the
		result is returned
	:type output_path: basestring or None
	:param safe: If True, the sub-engine will not raise error for non-matched $-keys
	:type safe: bool
	:return: Either a success flag is output_path was provided, or the result of the replacement if successful,
	or False
	:rtype: bool or basestring
	"""
	from os.path import exists, expanduser
	assert isinstance(template_path, basestring)
	try:
		assert exists(template_path)
	except AssertionError:
		logger.error('Not found: %s' % template_path)
	assert output_path is None or isinstance(output_path, basestring)
	assert isinstance(sub_dict, dict)

	from string import Template

	# load the template
	with open(template_path) as template_fd:
		src = Template(template_fd.read())

	# do the substitution
	result = src.safe_substitute(sub_dict) if safe else src.substitute(sub_dict)

	if output_path:
		output_path = expanduser(output_path)
		with open(output_path, 'w') as output_fd:
			# writes the result to the output file
			while output_fd.write(result):
				pass
		return True
	return result


# moved from settings on 19/05/2016
# TODO make a generator
# FIXME Django Specific ?
def get_key(name='', caching=True):
	config_root = recur(3, os.path.dirname, os.path.realpath(__file__)) + '/configs/' # FIXME hardcoded setting string
	if name.endswith('_secret'):
		name = name[:-7]
	if name.startswith('.'):
		name = name[1:]
	full_path = '%s.%s_secret' % (config_root, name)
	
	def read_key():
		with open(full_path) as f:
			logger.debug('Read key %s from %s' % (full_path, this_function_caller_name(2)))
			return str(f.read())[:-1]
	
	try: # FIXME caching seems not to work with docker_if
		key_id = '%s:%s' % ('SecretKey', name)
		return ObjectCache.get_or_add(key_id, read_key, 10*60) if caching else read_key()
	except Exception as e:
		logger.exception(str(e))
		pass
	msg = 'could not read key %s from %s' % (name, config_root)
	print('WARNING: %s' % msg)
	logger.warning(msg)
	return ''


# FIXME misplace as it's Django specific
from django.contrib.auth.decorators import login_required as login_rq, user_passes_test as user_p_test
from django.core.exceptions import PermissionDenied


# clem 01/06/2016 # FIXME not working
@login_rq(login_url='/')
def admin_only(func):
	""" Wrapper to check that user has admin rights

	:type func: Callable
	"""

	actual_decorator = user_p_test(
		lambda u: u.is_superuser or u.is_staff,
		login_url='/'
	)
	return actual_decorator if not func else actual_decorator(func)


# clem 01/06/2016
def is_admin(request):
	""" check that user has admin rights

	:type request:
	:rtype:
	"""

	if not (request.user.is_superuser or request.user.is_staff):
		raise PermissionDenied
	return True


# clem 28/03/2017
context = dict()
