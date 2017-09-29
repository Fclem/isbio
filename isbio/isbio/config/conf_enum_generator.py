from __future__ import print_function
from utilz import logger
from datetime import datetime
import os

generated = None
GENERATED_MODULE_NAME = 'generated'
GENERATED_FN = '%s.py' % GENERATED_MODULE_NAME


ONLY_EXT = ['py']
EXCLUDE_FILES = ['__init__.py', GENERATED_FN]
IGNORE_START_WITH = '__'
MODULE_TEMPLATE = """# Automatically generated by Breeze on %s
# Any change WILL BE OVERWRITTEN by Breeze
from utilz import magic_const, MagicAutoConstEnum


# Static object describing available Environments
# noinspection PyMethodParameters,PyPep8Naming
class %s(MagicAutoConstEnum):
%s
config_list = %s()
"""
PROPERTY_TEMPLATE = "	@magic_const\n	def %s(): pass\n\n"


def nop():
	pass


class FilterableList(list):
	def filter_func(self, filt_func):
		assert callable(filt_func)
		return FilterableList(filter(filt_func, self))
	
	def __repr__(self):
		return '*%s' % str(super(FilterableList, self).__repr__())
	
	def __str__(self):
		return str(self.__repr__())


class WalkObject(object):
	path = ''
	dir_list = list
	file_list = FilterableList
	
	def __init__(self, walk_object):
		assert isinstance(walk_object, tuple) and len(walk_object) == 3
		self.path = walk_object[0]
		self.dir_list = walk_object[1]
		self.file_list = FilterableList(walk_object[2])
	
	def filter_files(self, filter_func):
		self.file_list = self.file_list.filter_func(filter_func)
	
	@property
	def data(self):
		return self.path, self.dir_list, self.file_list
	
	def __str__(self):
		return '<WO:%s>' % str(self.data)


class ConfigEnumGenerator(object):
	__walker_list = list()  # type: list[WalkObject, ]
	filter_ext = list()
	exclude = list()
	recursive = False
	class_name = ''
	a_path = ''
	
	def __init__(self, class_name, a_path, filter_ext=list(), exclude=list(), recursive=False, verbose=False):
		self.a_path = a_path
		self.verbose = verbose
		self.class_name = class_name
		self.filter_ext = filter_ext or ONLY_EXT
		self.exclude = exclude or EXCLUDE_FILES
		self.recursive = recursive
	
	def __str__(self):
		return str(self.__walker_list)
	
	@property
	def walker_list(self):
		if not self.__walker_list:
			self.__walker_list = self.__walker()
		return self.__walker_list
	
	def filter_function(self, file_name):
		""" Return True for file to keep in the results
		
		:param file_name: file name to test against conditions
		:type file_name: str
		:rtype: bool
		"""
		val = not file_name.startswith(IGNORE_START_WITH) and (
			'.' not in file_name or file_name.split('.')[-1] in ONLY_EXT) and file_name not in EXCLUDE_FILES
		print('ignored %s' % file_name) if self.verbose and not val else nop()
		return val
	
	def __walker(self):
		"""
		
		:return:
		:rtype: list[WalkObject]
		"""
		if self.verbose:
			print('walking dir %s%s' % (self.a_path, '' if not self.recursive else ' with recursion'))
		walking = [i for i in os.walk(self.a_path)]
		result = list()
		walk_list = walking if self.recursive else filter(lambda w: w[0] == self.a_path, walking)
		print('walk_list: %s' % walk_list) if self.verbose else nop()
		for walk_item in [WalkObject(x) for x in walk_list]:
			print('walk_item: %s' % walk_item) if self.verbose else nop()
			walk_item.filter_files(self.filter_function)
			result.append(walk_item)
		return result
	
	@staticmethod
	def reloader(package='.'):
		import importlib
		return importlib.import_module(GENERATED_MODULE_NAME, package=package)
	
	def gen(self, target_path, do_reload=False):
		"""
		
		:param target_path: path of the python file to write
		:type target_path: str
		:param do_reload: should the written file be loaded as a module afterwards
		:type do_reload: bool
		:return: is success
		:rtype: bool
		"""
		try:
			with open(target_path, 'w') as a_file:
				sup = ''
				for each1 in self.walker_list:
					for each2 in each1.file_list:
						sup += PROPERTY_TEMPLATE % each2.replace('.py', '')
				a_file.write(MODULE_TEMPLATE %
					(datetime.now().isoformat(), self.class_name, sup if sup else '	pass', self.class_name))
			if do_reload:
				print('generated? %s' % generated) if self.verbose else nop()
				self.reloader()
				print('generated? %s' % generated) if self.verbose else nop()
			return True
		except Exception as e:
			logger.warning('While generating %s : %s' % (self.a_path, e))
		return False


def conf_gen(a_path, class_name):
	gen = ConfigEnumGenerator(class_name, a_path)
	gen.gen('%s/%s' % (a_path, GENERATED_FN))
