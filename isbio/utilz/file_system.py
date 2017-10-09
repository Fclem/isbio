import hashlib
from sys import stdout
from multipledispatch import dispatch # enables method overloading
from os.path import isfile, isdir, islink, exists, getsize, join, basename
from os import symlink, readlink, listdir, makedirs, access, R_OK, chmod
from . import get_logger

__version__ = '0.1'
__author__ = 'clem'
__date__ = '27/05/2016'


class ACL(enumerate):
	__R = 4
	__RX = 5
	__W = 6
	__X = 7
	__OTHER = 1
	__GROUP = 10
	__OWNER = 100

	R__ = 0o400
	RW__ = 0o600
	RWX__ = 0o700
	RW_RW_R = 0o664
	RW_RW_ = 0o660
	RW_R_ = 0o640
	R_R_ = 0o440
	RWX_RWX_R = 0o774
	RWX_RWX_ = 0o770
	RWX_RX_ = 0o750
	RX_RX_ = 0o550


# clem on 21/08/2015
def get_md5(content):
	""" Return md5 checksum of content argument

	:type content: list|str
	:rtype: str
	"""
	m = hashlib.md5()
	if type(content) == list:
		for eachLine in content:
			m.update(eachLine)
	else:
		m.update(content)
	return m.hexdigest()


# clem on 29/03/2017
def get_sha2(content):
	""" Return the sha512 checksum of content argument

	:type content: list|str
	:rtype: str
	"""
	m = hashlib.sha512()
	if type(content) == list:
		for eachLine in content:
			m.update(eachLine)
	else:
		m.update(content)
	return m.hexdigest()


# clem on 21/08/2015
def get_file_md5(file_path):
	""" Return md5 checksum of file

	:param file_path: location of the file
	:type file_path: str
	:rtype: str
	"""
	try:
		fd = open(file_path, "rb")
		content = fd.readlines()
		fd.close()
		return get_md5(content)
	except IOError:
		return ''


# Shortcut for handling path ( TEST DESIGN )
class Path(object):
	import os
	SEP = os.path.sep

	def __init__(self, path_str):
		""" Path object always return the path string with a trailing slash ( / ) for folders

		:param path_str: the path to use
		:type path_str: str
		"""
		self.__path_str = ''
		self.set_path(path_str)

	def get_path(self):
		return self.__path_str

	def set_path(self, path_str):
		if path_str is not None and path_str != '':
			if path_str[-1] != self.SEP and isdir(path_str + self.SEP):
				path_str += self.SEP
		self.__path_str = path_str

	path_str = property(get_path, set_path)

	def __str__(self): # Python 3: def __str__(self):
		return '%s' % self.path_str

	def is_dir(self):
		return isdir(self.path_str)

	def is_file(self):
		return isfile(self.path_str)

	def is_link(self):
		return islink(self.path_str)

	def exists(self):
		return exists(self.path_str)

	def get_size(self):
		return getsize(self.path_str)

	def is_non_empty_file(self):
		"""
		Return if the path is pointing to an non empty file
		:return: is path pointing to an non empty file
		:rtype: bool
		"""
		return isfile(self.path_str) and getsize(self.path_str) > 0

	def remove_file_safe(self):
		"""
		Remove a file or link if it exists
		:return: True or False
		:rtype: bool
		"""
		from os import remove
		try:
			if isfile(self.path_str) or islink(self.path_str):
				get_logger().debug("removing %s" % self.path_str)
				set_file_acl(self.path_str, ACL.RW_RW_, True)
				remove(self.path_str)
				return True
		except OSError:
			return self.remove_lnk_safe()
		return False

	def remove_lnk_safe(self):
		"""
		Remove a link file or a dir and all sub content (to use for links only)
		"""
		from os import unlink

		path = self.path_str
		if self.is_dir() and self.path_str.endswith(self.SEP):
			path = path[:-1]

		try:
			get_logger().debug("unlinking %s" % path)
			unlink(path)
			return True
		except OSError as e:
			get_logger().debug("unable to unlink : %s" % e)
		return False

	def auto_symlink(self, holder):
		"""
		Make a soft-link and overwrite any previously existing file (be careful !) or link with the same name
		:param holder: path of the link holder
		:type holder: str
		"""
		log_obj = get_logger()
		Path(holder).remove_lnk_safe()

		log_obj.debug("symlink to %s @ %s" % (self.path_str, holder))
		symlink(self.path_str, holder)
		return True


def custom_copytree(src, dst, symlinks=False, ignore=None, verbose=True, sub=False):
	from shutil import copy2, Error, copystat, WindowsError

	if not sub and verbose:
		print 'copy %s => %s' % (src, dst)
	files_count, folders_count = 0, 0

	names = listdir(src)
	if ignore is not None:
		ignored_names = ignore(src, names)
	else:
		ignored_names = set()

	def dot():
		stdout.write('.')
		stdout.flush()

	try:
		makedirs(dst)
	except OSError:
		pass

	errors = []
	for name in names:
		if name in ignored_names:
			continue
		src_name = join(src, name)
		dst_name = join(dst, name)
		try:
			if symlinks and islink(src_name):
				linkto = readlink(src_name)
				symlink(linkto, dst_name)
				if verbose:
					if isdir(linkto):
						folders_count += 1
					elif isfile(linkto):
						files_count += 1
					dot()
			elif isdir(src_name):
				c1, c2 = custom_copytree(src_name, dst_name, symlinks, ignore, verbose=verbose, sub=True)
				files_count += c1
				folders_count += c2 + 1
			else:
				# Will raise a SpecialFileError for unsupported file types
				copy2(src_name, dst_name)
				if verbose:
					dot()
					files_count += 1

		# catch the Error from the recursive copytree so that we can
		# continue with other files
		except Error as err:
			errors.extend(err.args[0])
		except EnvironmentError as why:
			errors.append((src_name, dst_name, str(why)))
	try:
		copystat(src, dst)
	except OSError as why:
		if WindowsError is not None and isinstance(why, WindowsError):
			# Copying file access times may fail on Windows
			pass
		else:
			errors.extend((src, dst, str(why)))
	if errors:
		raise Error(errors)
	if not sub and verbose:
		print 'done (%s files and %s folders)' % (files_count, folders_count)
	return files_count, folders_count


def is_non_empty_file(file_path):
	return Path(file_path).is_non_empty_file()


def remove_file_safe(fname):
	""" Remove a file or link if it exists

	:param fname: the path of the file/link to delete
	:type fname: str
	:return: True or False
	:rtype: bool
	"""
	return Path(fname).remove_file_safe()


def auto_symlink(target, holder):
	""" Make a soft-link and overwrite any previously existing file (be careful !) or link with the same name

	:param target: target path of the link
	:type target: str
	:param holder: path of the link holder
	:type holder: str
	"""
	return Path(target).auto_symlink(holder)


def get_folder_size(folder):
	""" Return the total size of a folder located at <i>folder</i>, recursively
	:type folder: str
	:rtype: int
	"""
	total_size = getsize(folder)
	for item in listdir(folder):
		item_path = join(folder, item)
		if not islink(item_path):
			if isfile(item_path):
				total_size += getsize(item_path)
			elif isdir(item_path):
				total_size += get_folder_size(item_path)
	return total_size


# clem 07/10/2015
def is_readable(file_path):
	""" Return if a file located at <i>file_path</i> is readable
	:type file_path: str
	:rtype: bool
	"""
	return access(file_path, R_OK)


# clem 09/10/2015
def set_file_acl(path, perm=ACL.RW_R_, silent_fail=False):
	""" Change file permission to <i>perm</i> (default is RW_R_)
	:type path: str
	:type perm: int
	:type silent_fail: bool
	:rtype: bool
	"""
	if not is_readable(path):
		try:
			chmod(path, perm)
			get_logger().info('changed {0} to {1:#o}'.format(path, perm))
			return True
		except OSError as e:
			get_logger().exception(str(e))
			if not silent_fail:
				raise OSError(e)
	return False


# moved here on 19/05/2016
# TODO : Review
@dispatch(basestring)
def file_mod_time(path):
	from os.path import getmtime # , join

	return getmtime(path)


# moved here on 19/05/2016
@dispatch(basestring, basestring)
def file_mod_time(dir_name, fname):
	from os.path import join

	return file_mod_time(join(dir_name, fname))


# clem 20/04/2016 moved from compute_interface_module on 24/05/2016
def make_tarfile(output_filename, source_dir, do_raise=True):
	""" makes a tar.bz2 archive from source_dir, and stores it in output_filename

	:param output_filename: the name/path of the resulting archive
	:type output_filename: basestring
	:param source_dir: the path of the source folder
	:type source_dir: basestring
	:param do_raise: indicate wether to raise the error (in case of),
		if not it will be logged instead
	:type do_raise: bool
	:return: if success
	:rtype: bool
	"""
	try:
		import tarfile
		with tarfile.open(output_filename, 'w:bz2') as tar:
			tar.add(source_dir, arcname=basename(source_dir))
		return True
	except Exception as e:
		if do_raise:
			raise
		get_logger().exception('Error creating %s : %s' % (output_filename, str(e)))
	return False


# clem 23/05/2016  moved from compute_interface_module on 24/05/2016
def extract_tarfile(input_filename, destination_dir, do_raise=True):
	""" extract an tar.* to a destination folder

	:param input_filename: the name/path of the source archive
	:type input_filename: basestring
	:param destination_dir: the path of the destination folder
	:type destination_dir: basestring
	:param do_raise: indicate wether to raise the error (in case of),
		if not it will be logged instead
	:type do_raise: bool
	:return: if success
	:rtype: bool
	"""
	try:
		import tarfile
		with tarfile.open(input_filename, 'r:*') as tar:
			tar.extractall(destination_dir)
		return True
	except Exception as e:
		if do_raise:
			raise
		get_logger().log.exception('Error creating %s : %s' % (input_filename, str(e)))
	return False


# moved from Filesize module 27/05/2016
# clem 31/03/2016
# adapted from https://pypi.python.org/pypi/hurry.filesize


class UnitSystem(object):
	traditional = [
		(1024 ** 5, 'P'),
		(1024 ** 4, 'T'),
		(1024 ** 3, 'G'),
		(1024 ** 2, 'M'),
		(1024 ** 1, 'K'),
		(1024 ** 0, 'B'),
	]

	alternative = [
		(1024 ** 5, ' PB'),
		(1024 ** 4, ' TB'),
		(1024 ** 3, ' GB'),
		(1024 ** 2, ' MB'),
		(1024 ** 1, ' KB'),
		(1024 ** 0, (' byte', ' bytes')),
	]

	verbose = [
		(1024 ** 5, (' petabyte', ' petabytes')),
		(1024 ** 4, (' terabyte', ' terabytes')),
		(1024 ** 3, (' gigabyte', ' gigabytes')),
		(1024 ** 2, (' megabyte', ' megabytes')),
		(1024 ** 1, (' kilobyte', ' kilobytes')),
		(1024 ** 0, (' byte', ' bytes')),
	]

	iec = [
		(1024 ** 5, 'Pi'),
		(1024 ** 4, 'Ti'),
		(1024 ** 3, 'Gi'),
		(1024 ** 2, 'Mi'),
		(1024 ** 1, 'Ki'),
		(1024 ** 0, ''),
	]

	si = [
		(1000 ** 5, 'P'),
		(1000 ** 4, 'T'),
		(1000 ** 3, 'G'),
		(1000 ** 2, 'M'),
		(1000 ** 1, 'K'),
		(1000 ** 0, 'B'),
	]


def _file_size2human(bytes_count, system=UnitSystem.traditional, digit=0):
	"""Human-readable file size.

	Using the traditional system, where a factor of 1024 is used::

	>>> _file_size2human(10)
	'10B'
	>>> _file_size2human(100)
	'100B'
	>>> _file_size2human(1000)
	'1000B'
	>>> _file_size2human(2000)
	'1K'
	>>> _file_size2human(10000)
	'9K'
	>>> _file_size2human(20000)
	'19K'
	>>> _file_size2human(100000)
	'97K'
	>>> _file_size2human(200000)
	'195K'
	>>> _file_size2human(1000000)
	'976K'
	>>> _file_size2human(2000000)
	'1M'

	Using the SI system, with a factor 1000::

	>>> _file_size2human(10, system=UnitSystem.si)
	'10B'
	>>> _file_size2human(100, system=UnitSystem.si)
	'100B'
	>>> _file_size2human(1000, system=UnitSystem.si)
	'1K'
	>>> _file_size2human(2000, system=UnitSystem.si)
	'2K'
	>>> _file_size2human(10000, system=UnitSystem.si)
	'10K'
	>>> _file_size2human(20000, system=UnitSystem.si)
	'20K'
	>>> _file_size2human(100000, system=UnitSystem.si)
	'100K'
	>>> _file_size2human(200000, system=UnitSystem.si)
	'200K'
	>>> _file_size2human(1000000, system=UnitSystem.si)
	'1M'
	>>> _file_size2human(2000000, system=UnitSystem.si)
	'2M'

	:type bytes_count: int
	:type system: Systems
	:type digit: int
	:rtype str
	"""
	factor, suffix = 1, '' # ONLY for the IDE not to complain about reference before assignment
	for factor, suffix in system:
		if bytes_count >= factor:
			break
	amount = float(bytes_count) / factor
	if isinstance(suffix, tuple):
		singular, multiple = suffix
		if int(amount) == 1:
			suffix = singular
		else:
			suffix = multiple
	return (('%%.0%sf' % digit) % amount) + suffix


# clem 09/10/2015
def human_readable_byte_size(size_value, unit=None, digit=2):
	""" Human-readable file size.

	:type size_value: int
	:type unit: filesize.UnitSystem
	:type digit: int
	:rtype: str
	"""
	return _file_size2human(size_value, system=UnitSystem.traditional if not unit else unit, digit=digit)
