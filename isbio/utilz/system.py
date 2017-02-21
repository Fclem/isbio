from threading import Thread, Lock
import json
import os
import copy
import abc
import subprocess as sp

__version__ = '0.1.2'
__author__ = 'clem'
__date__ = '27/05/2016'


class TermColoring(enumerate):
	HEADER = '\033[95m'
	OK_BLUE = '\033[94m'
	OK_GREEN = '\033[92m'
	WARNING = '\033[93m'
	FAIL = '\033[91m'
	END_C = '\033[0m'
	BOLD = '\033[1m'
	UNDERLINE = '\033[4m'

	@classmethod
	def ok_blue(cls, text):
		return cls.OK_BLUE + text + cls.END_C

	@classmethod
	def ok_green(cls, text):
		return cls.OK_GREEN + text + cls.END_C

	@classmethod
	def fail(cls, text):
		return cls.FAIL + text + cls.END_C

	@classmethod
	def warning(cls, text):
		return cls.WARNING + text + cls.END_C

	@classmethod
	def header(cls, text):
		return cls.HEADER + text + cls.END_C

	@classmethod
	def bold(cls, text):
		return cls.BOLD + text + cls.END_C

	@classmethod
	def underlined(cls, text):
		return cls.UNDERLINE + text + cls.END_C


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
def compute_enc_session_id(session_id_clear_or_enc, shared_key):
	import base64
	return base64.b64encode(xor_strings(session_id_clear_or_enc, shared_key))
