from . import Thread
import gc
import inspect
from collections import OrderedDict

__version__ = '0.1.3'
__author__ = 'clem'
__date__ = '27/05/2016'


# clem 05/04/2016
def new_thread(func):
	""" Wrapper to run functions in a new Thread (use as a @decorator)

	:type func:
	:rtype:
	"""

	# assert callable(func)

	def decorated(*args):
		Thread(target=func, args=args).start()

	return None if not func else decorated


# clem 08/04/2016
def is_from_cli():
	""" Tells if the caller was called from command line or not

	:rtype: bool
	"""
	return this_function_caller_name(1) == '<module>'


# clem 08/04/2016
def get_named_tuple(class_name, a_dict):
	# noinspection PyCompatibility
	assert isinstance(class_name, basestring) and isinstance(a_dict, dict)
	from collections import namedtuple
	return namedtuple(class_name, ' '.join(a_dict.keys()))(**a_dict)


# moved from settings on 19/05/2016
def recur_rec(nb, func, args):
	if nb > 0:
		return recur_rec(nb - 1, func, func(args))
	return args


# moved from settings on 19/05/2016
def recur(nb, func, args):
	while nb > 0:
		args = func(args)
		nb -= 1
	return args


# moved in utils on 19/05/2016
def not_imp(self): # writing shortcut for abstract classes
	raise NotImplementedError("%s was not implemented in concrete class %s." % (
		this_function_caller_name(), self.__class__.__name__))

##############################################################
# DISCLAIMER :                                               #
# If you don't want to bleed from the eyes, look no further. #
##############################################################


# clem 27/05/2016
class ClassProperty(property):
	def __get__(self, cls, owner=None):
		# noinspection PyCallingNonCallable
		return classmethod(self.fget).__get__(None, owner)()
	

# clem 30/11/2016
class StaticPropertyBase(property):
	def __get__(self, cls, owner=None):
		return staticmethod(self.fget).__get__(None, owner)


# clem 30/11/2016
class MagicConst(StaticPropertyBase):
	@StaticPropertyBase
	def over(self):
		return self.__name__


magic_const = MagicConst
classproperty = ClassProperty


# clem 15/12/2016
class MagicAutoConstEnum(object):
	""" type that enables iteration of MagicConst list of static class """
	@classmethod
	def __iter__(cls):
		for k, v in cls.__dict__.items():
			if type(v) is MagicConst:
				yield k
	
	@classmethod
	def __contains__(cls, item):
		""" provides case insensitive filtering amongst the class properties names """
		# return item in cls.__dict__
		# for each in cls.__dict__.keys():
		for each in cls.__iter__():
			if str(item).lower() == each.lower():
				return True
		return False
	
	def get(self, item):
		for key in self.__iter__():
			if key.lower() == str(item).lower():
				item = key
		return self.__getattribute__(item)
	
	def __call__(self):
		return self
	
	@magic_const
	def undefined(*args):
		pass


# clem 15/12/2016
class Struct(object):
	def __init__(self, **entries):
		self.__dict__.update(entries)


# clem 15/12/2016
# noinspection PyTypeChecker
def magic_const_object_from_list(a_list):
	magic_dict = dict()
	for each in a_list:
		magic_dict.update({each: magic_const(property())})
	return Struct(**magic_dict)


MODULE_EXTENSIONS = ('.py', '.pyc', '.pyo')


# Clem 15/12/2016 from StackOverflow
def package_contents(package_name):
	import imp
	import os
	a_file, pathname, description = imp.find_module(package_name)
	if a_file:
		raise ImportError('Not a package: %r', package_name)
	# Use a set because some may be both source and compiled.
	return set([os.path.splitext(a_module)[0]
		for a_module in os.listdir(pathname)
		if a_module.endswith(MODULE_EXTENSIONS)])


# clem 10/10/2016 from http://stackoverflow.com/a/4506081/5094389
def this_function_own_object_old():
	""" Return the function object of the caller
	
	:rtype: function
	"""
	frame = inspect.currentframe(1)
	code = frame.f_code
	globs = frame.f_globals
	functype = type(lambda: 0)
	funcs = []
	for func in gc.get_referrers(code):
		if type(func) is functype:
			if getattr(func, "func_code", None) is code:
				if getattr(func, "func_globals", None) is globs:
					funcs.append(func)
					if len(funcs) > 1:
						return None
	return funcs[0] if funcs else None


lambda_cache = dict()


# clem 14/10/2016 from http://metapython.blogspot.fi/2010/11/recursive-lambda-functions.html
# http://stackoverflow.com/a/4492828
def this_function_own_object():
	from types import FunctionType
	caller_frame = inspect.currentframe(1)
	code = caller_frame.f_code
	if code not in lambda_cache:
		# noinspection PyArgumentList
		lambda_cache[code] = FunctionType(code, caller_frame.f_globals)
	return lambda_cache[code]


# clem 08/04/2016
def this_function_name(delta=0):
	""" Return the name of the calling function
	
	:param delta: change the depth of the call stack inspection
	:type delta: int
	
	:rtype: str
	"""
	return this_function_caller_name(delta)


# clem 08/04/2016 + 10/10/2016
def this_function_caller_name(delta=0):
	""" Return the name of the calling function's caller
	
	:param delta: change the depth of the call stack inspection
	:type delta: int
	
	:rtype: str
	"""
	return inspect.currentframe(2 + delta).f_code.co_name


# clem 06/06/2017
def list_functions_from_module(a_module):
	import types
	
	return [a_module.__dict__.get(a) for a in dir(a_module)
		if isinstance(a_module.__dict__.get(a), types.FunctionType)]


####################
# CUSTOMIZED TYPES #
####################
class SupStr(str):
	""" string that supports minus operation """
	_empty = ''
	
	def __init__(self, string=_empty):
		super(SupStr, self).__init__(string)
	
	def __sub__(self, other):
		""" minus operation as remove substring """
		assert isinstance(other, str)
		return self.replace(other, self._empty)


class EnsDict(dict):
	""" dict that supports ensembles (like in set) operations on its keys"""
	_empty = iter(())
	
	def __init__(self, iterable=_empty, **kwargs):
		super(EnsDict, self).__init__(iterable=iterable, **kwargs)
	
	@property
	def sd(self):
		return self.__data()
	
	def __data(self, obj=None):
		"""
		:type obj: dict |  EnsDict
		:rtype: dict
		"""
		if not obj:
			obj = self
		if type(obj) is dict:
			return obj
		elif type(obj) is EnsDict:
			return obj.get('iterable')
		else:
			raise TypeError
	
	def __sub__(self, other): # A / B (everything in A that is not in B)
		assert isinstance(other, dict)
		sd, od = self.sd, self.__data(other)
		a, b = set(sd.keys()), set(od.keys())
		c = a - b
		new_dict = dict()
		for each in c:
			new_dict.update({each: sd.get(each, None)})
		return new_dict
	
	def __and__(self, other): # A inter B (everything that is both in A and B)
		assert isinstance(other, dict)
		sd, od = self.sd, self.__data(other)
		a, b = set(sd.keys()), set(od.keys())
		c = a & b
		new_dict = dict()
		for each in c:
			new_dict.update({each: (sd.get(each, None), od.get(each, None))})
		return new_dict
	
	def __or__(self, other): # A union B (A union B, everything from A, and everything from B) i.e. (A / B) + A inter
		#  B + (B / A)
		assert isinstance(other, dict)
		sd, od = self.sd, self.__data(other)
		a, b = set(sd.keys()), set(od.keys())
		c = a | b
		new_dict = dict()
		for each in c:
			new_dict.update({each: (sd.get(each, None), od.get(each, None))})
		return new_dict
	
	def __xor__(self, other): # (A + B) / (A inter B) (everything in A and not in B, and everything in B and not in A)
		sd, od = self.sd, self.__data(other)
		myself, other = EnsDict(sd), EnsDict(od)
		return EnsDict(myself - other) + EnsDict(other - myself)
	
	def weired(self, other): # ???
		assert isinstance(other, dict)
		sd, od = self.sd, self.__data(other)
		a, b = set(sd.keys()), set(od.keys())
		c = a - b
		d = b - a
		new_dict = dict()
		for each in c:
			new_dict.update({each: (sd.get(each, None), od.get(each, None))})
		for each in d:
			new_dict.update({each: (sd.get(each, None), od.get(each, None))})
		return new_dict
	
	def __add__(self, other): # ???
		assert isinstance(other, dict)
		sd, od = self.sd, self.__data(other)
		new_dict = dict()
		for each in sd.keys():
			new_dict.update({each: (sd.get(each, None), od.get(each, None))})
		for each in od.keys():
			new_dict.update({each: (sd.get(each, None), od.get(each, None))})
		return new_dict
	
	def __repr__(self):
		return self.sd.__repr__()


class EnsList(list): # FIXME should use set instead of manual parsing
	""" list that supports minus and plus operations as in ensemble deprived and union """
	_empty = iter(())
	
	def __init__(self, iterable=_empty):
		super(EnsList, self).__init__(iterable)
	
	def __sub__(self, other):
		""" as deprived ensemble operation """
		res = self.__class__(self._empty)
		assert isinstance(other, list)
		for each in self:
			if each not in other:
				res.append(each)
		return res
	
	def __add__(self, other):
		""" as union ensemble operation """
		res = self.__class__(self._empty)
		assert isinstance(other, list)
		for each in self:
			if each not in other:
				res.append(each)
		for each in other:
			if each not in self:
				res.append(each)
		return res
	
	def filter(self, contains):
		""" returns only items of the list that contains a specific string """
		res = self.__class__(self._empty)
		for each in self:
			if contains in each:
				res.append(each)
		return res


class AutoOrderedDict(OrderedDict):
	""" Store items in the order the keys were last added, and create sorted dicts, from dicts and key order list """
	
	def __init__(self, a_dict=None, order_list=list()):
		super(AutoOrderedDict, self).__init__()
		a_dict = a_dict or dict()
		if a_dict and order_list: # values in same order as the list of keys
			for each in order_list:
				if each in a_dict:
					self[each] = a_dict[each]
		elif a_dict and not order_list: # values in same "order" as the original dict
			for k, v in a_dict.items():
				self[k] = v
		elif order_list and not a_dict: # order without values, save the order, init all value to None
			for each in order_list:
				self[each] = None
	
	def __setitem__(self, key, value, _=dict.__setitem__):
		if key in self:
			del self[key]
		OrderedDict.__setitem__(self, key, value)
