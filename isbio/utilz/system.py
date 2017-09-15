from threading import Thread, Lock
import json
import os
import copy
import abc
import base64
import subprocess as sp

__version__ = '0.1.2'
__author__ = 'clem'
__date__ = '27/05/2016'


class TermColoring(enumerate):
	HEADER = '\033[95m'
	OK_BLUE = '\033[94m'
	DARK_BLUE = '\033[34m'
	OK_GREEN = '\033[92m'
	WARNING = '\033[93m'
	FAIL = '\033[91m'
	END_C = '\033[0m'
	BOLD = '\033[1m'
	UNDERLINE = '\033[4m'

	@classmethod
	def ok_blue(cls, text, print_func=None):
		"""  blue coloring

		:param text: a string to be colored in blue
		:type text: basestring
		:param print_func: an optional output function (like print())
		:type print_func: function
		"""
		return cls.__text_gen(text, cls.OK_BLUE, print_func)

	@classmethod
	def ok_green(cls, text, print_func=None):
		"""  green coloring

		:param text: a string to be colored in green
		:type text: basestring
		:param print_func: an optional output function (like print())
		:type print_func: function
		"""
		return cls.__text_gen(text, cls.OK_GREEN, print_func)

	@classmethod
	def fail(cls, text, print_func=None):
		"""  red coloring

		:param text: a string to be colored in red
		:type text: basestring
		:param print_func: an optional output function (like print())
		:type print_func: function
		"""
		return cls.__text_gen(text, cls.FAIL, print_func)

	@classmethod
	def warning(cls, text, print_func=None):
		"""  Yellow coloring

		:param text: a string to be colored in yellow
		:type text: basestring
		:param print_func: an optional output function (like print())
		:type print_func: function
		"""
		return cls.__text_gen(text, cls.WARNING, print_func)

	@classmethod
	def header(cls, text, print_func=None):
		"""  ?

		:param text: a string to be ?
		:type text: basestring
		:param print_func: an optional output function (like print())
		:type print_func: function
		"""
		return cls.__text_gen(text, cls.HEADER, print_func)

	@classmethod
	def bold(cls, text, print_func=None):
		"""  font weight bold

		:param text: a string to put into bold
		:type text: basestring
		:param print_func: an optional output function (like print())
		:type print_func: function
		"""
		return cls.__text_gen(text, cls.BOLD, print_func)

	@classmethod
	def underlined(cls, text, print_func=None):
		"""  underlining of text

		:param text: a string to be underlined
		:type text: basestring
		:param print_func: an optional output function (like print())
		:type print_func: function
		"""
		return cls.__text_gen(text, cls.UNDERLINE, print_func)
	
	# clem 15/09/2017
	@classmethod
	def dark_blue(cls, text, print_func=None):
		"""  dark blue coloring
		
		:param text: a string to be colored in dark blue
		:type text: basestring
		:param print_func: an optional output function (like print())
		:type print_func: function
		"""
		return cls.__text_gen(text, cls.DARK_BLUE, print_func)
	
	# clem 15/09/2017
	@classmethod
	def no_color(cls, text, print_func=None):
		""" no coloring
		
		:param text: a string not to be colored
		:type text: basestring
		:param print_func: an optional output function (like print())
		:type print_func: function
		"""
		return cls.__printer_router(text, print_func)
	
	# clem 15/09/2017
	@classmethod
	def __text_gen(cls, text, head, print_func):
		""" writing shortcut that use head color string adds text and the trailing ENC_C
		
		:param text: a string to be colored
		:type text: basestring
		:param head: the color code to use
		:type head: str
		:param print_func: an optional output function (like print())
		:type print_func: function
		"""
		return cls.__printer_router(head + text + cls.END_C, print_func)
	
	# clem 15/09/2017
	@classmethod
	def __printer_router(cls, value, print_func=None):
		""" return value or return print_func(value)
		
		:type value: basestring
		:type print_func: function
		:rtype: basestring | (print_func)
		"""
		if print_func:
			return print_func(value)
		else:
			return value
	
	# clem 15/09/2017
	@classmethod
	def command(cls, command, color=None, print_func=None):
		""" format a string like a shell input (add a leading green $)
		
		:param command: a string to be colored as a shell command
		:type command: basestring
		:param color: an optional coloring function for the command line (defaults to DEFAULT_COLOR)
		:type color: function
		:param print_func: an optional output function (like print())
		:type print_func: function
		"""
		color = cls.DEFAULT_COLOR if not color else color
		value = cls.ok_green('$ ') + color(command)
		return cls.__printer_router(value, print_func)
	
	DEFAULT_COLOR = dark_blue


# clem 19/02/2016
# FIXME deprecated 18/10/2016
def do_restart():
	return False


# clem 19/02/2016
# FIXME deprecated 18/10/2016
def do_reboot():
	return False


# clem 10/10/2016 moved this_function_* to pythonic

# clem 20/06/2016
def is_command_available(cmd_str):
	return get_term_cmd_stdout(['which', cmd_str], False) not in ['', [''], []]


# clem 18/04/2016
def get_term_cmd_stdout(cmd_list_with_args, check_if_command_is_available=True):
	assert isinstance(cmd_list_with_args, list)
	ret = ''
	try:
		if not check_if_command_is_available or is_command_available(cmd_list_with_args[0]):
			a = sp.Popen(cmd_list_with_args, stdout=sp.PIPE)
			b = a.communicate()
			if b:
				s = b[0].split('\n')
				return s
		return ret
	except OSError as e:
		print 'EXCEPTION (UNLOGGED) while running cmd %s : %s' % (str(cmd_list_with_args), str(e))
		return ''


# moved from settings on 19/05/2016 # FIXME Django specific ?
def import_env():
	""" dynamically change the environement """
	source = 'source ~/.sge_profile'
	dump = 'python -c "import os, json;print json.dumps(dict(os.environ))"'
	pipe = sp.Popen(['/bin/bash', '-c', '%s && %s' % (source, dump)], stdout=sp.PIPE)
	env = json.loads(pipe.stdout.read())
	os.environ = env


# Clem 18/10/2016
def file_content(file_path):
	""" Return the content of a single line file stripped from any space
	
	:param file_path: the full file path to read from
	:type file_path: str
	:return: the content
	:rtype: str
	"""
	try:
		return open(file_path).read().lower().replace('\n', '').replace('\r', '').replace('\f', '').replace(' ',
			'')
	except IOError: # HACK
		return ''


# Clem 21/02/2017 c.f. https://en.wikipedia.org/wiki/XOR_cipher
def u_ord(c):
	"""Adapt `ord(c)` for Python 2 or 3"""
	return ord(str(c)[0:1])


# Clem 21/02/2017 c.f. https://en.wikipedia.org/wiki/XOR_cipher
def xor_strings(s, t):
	"""xor two strings together"""
	return "".join(chr(u_ord(a) ^ u_ord(b)) for a, b in zip(s, t))


# clem 21/02/2017
def compute_enc_session_id(session_id_clear, shared_key):
	return base64.b64encode(xor_strings(session_id_clear, shared_key))


# clem 21/02/2017
def compute_dec_session_id(session_id_encoded, shared_key):
	return xor_strings(base64.b64decode(session_id_encoded), shared_key)
