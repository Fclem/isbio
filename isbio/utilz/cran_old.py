# clement@fiere.fr 03/02/2016
class InvalidArgument(BaseException):
	pass


def human_readable_byte_size(num, suffix='B'):
	for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
		if abs(num) < 1024.0:
			return "%3.1f%s%s" % (num, unit, suffix)
		num /= 1024.0
	return "%.1f%s%s" % (num, 'Yi', suffix)


class CranArchiveDownloader(object): # special purpose light FTP downloader
	name = str
	# http_url = 'http://cran.r-project.org/src/contrib/Archive/'
	ftp_server = 'cran.r-project.org'
	ftp_path = '/pub/R/src/contrib/Archive/'
	ftp_home_url = 'ftp://%s' % ftp_server
	verbose = True # display or not information on console
	alt_logger = None
	login = 'anonymous'
	password = ''

	# ftp_url = '%s%s' % (ftp_home_url, ftp_path)

	def __init__(self, name=str, logger=None):
		""" name is the name of the requested library, logger is a callable logging function with txt argument
		:type name: str
		:type logger: callable
		"""
		if type(name) == str and name:
			self.name = name
		else:
			raise InvalidArgument
		self._searched = False		# 01 search has been done
		self._found = False			# 02 searched item has been found
		self._downloaded = False	# 03 found item has been downloaded
		self._extracted = False		# 04 downloaded item has been extracted
		from ftplib import FTP
		self.ftp = FTP(self.ftp_server)
		from os.path import dirname, realpath
		self._self_path = dirname(realpath(__file__))
		self._extract_path = '%s/%s' % (self._self_path, self.name)
		self.v = False
		self._nlst = dict()
		self.save_path = ''
		self.alt_logger = logger

	def _out(self, msg):
		"""
		Print msg if verbose is True, and alternatively log msg if alternative logger is present
		:type msg: str
		:rtype: None
		"""
		if self.alt_logger:
			self.alt_logger(msg)
		if self.verbose:
			print msg

	def find(self, suggest=True):
		"""
		Try to cd to the target library dir directly,
		and if not found call self.guess
		:type suggest: bool
		:rtype: bool|str
		"""
		if not self._searched: # don't do it twice
			self.ftp.login(self.login, self.password)
			if self.name:
				try:
					self.ftp.cwd("%s%s" % (self.ftp_path, self.name))
					# No error, means folder exists == FOUND !
					self._found = True
					self._out('found, last version : %s, %s' %
						(self._last_version_file_name, human_readable_byte_size(self._size)))
				# url = '%s%s%s' % (self.ftp_home_url, pwd(), the_file)
				except Exception as e:
					if str(e).startswith('550'):
						if suggest:
							self._out('%s not found!' % self.name)
							self._find_similar()
					elif self.verbose:
						self._out('Error : %s' % e)
			self._searched = True
		return self._found

	def download(self):
		""" Download the latest version of the found package
		:rtype: bool|str
		"""
		if self._found or self.find(False):
			path = self._download_and_save()
			if not path:
				self._out('Download failed !')
			return path
		return False

	def extract_to(self, path=None, rm_archive=True):
		if not path:
			path = self._extract_path
		if not self._extracted and (self._downloaded or self.download()):
			try:
				import tarfile
				import time
				tar = tarfile.open(self.save_path)
				self._out('extracting %s to %s ...' % (self._last_version_file_name, path))
				start_time = time.time()
				tar.extractall(path)
				interval = time.time() - start_time
				self._extracted = True
				tar.close()
				# if self.verbose:
				speed = human_readable_byte_size(self._size / interval)
				self._out('done in %s sec (%s/s) !' % (round(interval, 2), speed))
				if rm_archive:
					from os import remove
					remove(self.save_path)
					self._downloaded = False
				return path
			except Exception as e:
				self._out('Extraction failed : %s ' % e)
		return False

	@property
	def _file_list(self):
		""" Returns file list of cwd with caching (don't ask twice for the same path)
		:rtype: str
		"""
		pwd = self._pwd
		if pwd not in self._nlst:
			self._nlst[pwd] = self.ftp.nlst()
		return self._nlst[pwd]

	@property
	def _pwd(self):
		""" Returns current working directory with trailing slash
		:rtype: str
		"""
		return '%s/' % self.ftp.pwd()

	@property
	def _last_version_file_name(self):
		return self._file_list[-1]

	@property
	def _size(self):
		""" Return the size of self._last_version_file_name
		:rtype: float
		"""
		return self.ftp.size(self._last_version_file_name)

	def _downloader(self, filename, save_to):
		""" Download the file name filename from the CWD and save it to save_to
		:type filename: str
		:type save_to: str
		:rtype: bool
		"""
		with open(save_to, 'wb') as save_file:
			def _write_f(data):
				save_file.write(data)
				if self.verbose:
					import sys
					sys.stdout.write('.')
			try:
				import time
				size = self.ftp.size(filename)
				self._out('Downloading %s bytes...' % size)
				start_time = time.time()
				self.ftp.retrbinary("RETR " + filename, _write_f)
				interval = time.time() - start_time
				speed = human_readable_byte_size(size / interval)
				self._out(' done in %s sec (%s/s) !\nsaved to % s' % (round(interval, 2), speed, save_to))
				return True
			except Exception as e:
				self._out('Error %s' % e)
		return False

	def _download_and_save(self):
		""" Actually download and save the last legacy version of the package
		:rtype: bool|str
		"""
		filename = self._last_version_file_name
		self.save_path = '%s/%s' % (self._self_path, filename)
		if self._downloader(filename, self.save_path):
			self._downloaded = True
			return self.save_path
		return False

	def _guess(self):
		""" Go through the list of package and try to find matching package name (case insensitive and including self.name)
		:rtype: list
		"""
		new_l = list()
		if self.name:
			self.name = self.name.lower()
			for e in self._file_list:
				l = str(e).lower()
				if l == self.name or self.name in l or l in self.name:
					new_l.append(str(e))
		return new_l

	def _find_similar(self):
		""" Suggest on console similar package (case insensitive and including self.name) if verbose is enable
		:rtype: None
		"""
		self.ftp.cwd(self.ftp_path)
		real_name = self._guess()
		if self.verbose and real_name:
			for e in real_name:
				self._out('Did you meant "%s" ?' % e)
