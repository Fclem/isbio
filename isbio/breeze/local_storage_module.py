from utils import TermColoring
import os
import abc
from b_exceptions import ObjectNotFound as MissingResException

__version__ = '0.1'
__author__ = 'clem'
__date__ = '04/05/2016'


# clem 06/04/2016
def password_from_file(the_path):
	from os.path import exists, expanduser
	if not exists(the_path):
		temp = expanduser(the_path)
		if exists(temp):
			the_path = temp
		else:
			return False
	return open(the_path).read().replace('\n', '')


# TODO set this configs :
__DEV__ = True
__path__ = os.path.realpath(__file__)
__dir_path__ = os.path.dirname(__path__)
__file_name__ = os.path.basename(__file__)


class StorageModule(object):
	__metaclass__ = abc.ABCMeta
	_not = "Class %s doesn't implement %s()"
	_interface = None # as to be defined as a BlobStorageObject that support argument list : (account_name=self
	missing_res_exception = MissingResException

	def __init__(self):
		pass

	def _print_call(self, fun_name, args):
		arg_list = ''
		if isinstance(args, basestring):
			args = [args]
		for each in args:
			arg_list += "'%s', " % TermColoring.warning(each)
		print TermColoring.bold(fun_name) + "(%s)" % arg_list[:-2]
