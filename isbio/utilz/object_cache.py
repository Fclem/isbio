from . import new_thread, get_logger, time, Lock

__version__ = '0.1.1'
__author__ = 'clem'
__date__ = '27/05/2016'

GENERAL_CACHE_TIME_OUT = 60 * 60 # 60 minutes


# clem 16/05/2016
class ExpiredCacheObject(RuntimeWarning):
	pass


# clem 16/05/2016
class IdleExpiredCacheObject(ExpiredCacheObject):
	pass


# clem 16/05/2016
class CachedObject(object):
	__created = 0.
	__last_access = 0.
	access_counter = 0
	__stored_object = None
	__time_out = -1
	__idle_time_out = -1

	def __init__(self, an_object, invalidate_after=GENERAL_CACHE_TIME_OUT, idle_expiry=0):
		""" This class is a caching mechanism to store an object, managing expiration, and idle expiration.
		if no invalidate_after is provided, it will be assigned default_time_out (120 sec).
		if no idle_expiry is provided, it will be disabled.

		:param an_object: The object to store
		:type an_object: object
		:param invalidate_after: number of second after which the object will be deleted (0 to disable)
		:type invalidate_after: int | float
		:param idle_expiry: number of second since last access after which the object will be deleted (0 to disable)
		:type idle_expiry: int | float
		"""
		self.__stored_object = an_object
		self.__created = time()
		self.__last_access = time()
		self.__time_out = invalidate_after
		self.__idle_time_out = idle_expiry

	@property
	def is_expired(self):
		""" returns whether or not this object has expired

		:rtype: bool
		"""
		if self.__time_out and self.age >= self.__time_out:
			return True
		return False

	@property
	def is_idle_time_out(self):
		""" returns whether or not this object has exceeded its idle time-out

		:rtype: bool
		"""
		if self.__idle_time_out and self.idle_time >= self.__idle_time_out:
			return True
		return False

	def __accessed(self):
		""" Updates the last access time of the object, and the access counter. Also manages expiration.

		:raise: IdleExpiredCacheObject | ExpiredCacheObject
		:rtype: None
		"""
		if self.is_expired or self.is_idle_time_out:
			self.__stored_object = None
			raise IdleExpiredCacheObject if self.is_idle_time_out else ExpiredCacheObject
		self.__last_access = time()
		self.access_counter += 1

	def get_object(self):
		""" Returns the stored object. will update the last access time, and thus reset the idle_time."""
		self.__accessed()
		return self.__stored_object

	@property
	def age(self):
		""" return the number of seconds since this object was created

		:rtype: float
		"""
		return time() - self.__created

	@property
	def idle_time(self):
		""" return the number of seconds since this object was last accessed directly

		:rtype: float
		"""
		return time() - self.__last_access

	@property
	def last_access(self):
		""" return the time stamp (i.e. as time.time() ) of the last direct access to the stored object

		:rtype: float
		"""
		return self.__last_access

	@property
	def object(self):
		""" Returns the stored object. will update the last access time, and thus reset the idle_time alias
			of get_object().

		:raise: IdleExpiredCacheObject | ExpiredCacheObject
		"""
		return self.get_object()

	# clem 24/03/2017
	def to_json(self):
		print(type(self.get_object()))
		return self.get_object()

	def __str__(self):
		return '<cached %s (idle %s sec / %s sec old)>' % (
			repr(self.__stored_object), int(self.idle_time), int(self.age))

	def __repr__(self):
		return '<cached %s>' % repr(self.__stored_object)


# clem 16/05/2016
class ObjectCache(object):
	_cache = dict()
	_DEBUG = False
	data_mutex = Lock()
	
	# clem 24/03/2017
	@classmethod
	def dump(cls): # TODO : dump as serializable dict
		result = dict()
		for each in cls._cache.keys():
			if not each.lower().startswith('secret'):
				value = cls._cache.get(each)
			else:
				value = '***REDACTED***'
				
			result.update({each: value})
		return result
	
	@classmethod
	def dump_list(cls):
		return cls._cache.keys()

	@classmethod
	def get_cached(cls, key, default=None):
		""" Retrieves the CachedObject containing the object if it exists (Thread Safe)

		:param key: the key to identify the object
		:type key: basestring
		:param default: default object to return if object is not found in the cache
		:type default: Any
		:return: The corresponding CacheObject or None
		:rtype: CachedObject | None
		"""
		key = cls._key_getter(key)
		with cls.data_mutex:
			val = cls._cache.get(key, default)
		return val

	@classmethod
	def get(cls, key, default=None):
		""" Retrieves the stored object if it exists (Thread Safe)

		:param key: the key to identify the object
		:type key: basestring
		:param default: default object to return if object is not found in the cache
		:type default: Any
		:return: The stored object or None
		"""
		key = cls._key_getter(key)
		cached = cls.get_cached(key, default)
		if cached:
			text = str(cached)
			try:
				return cached.object
			except ExpiredCacheObject as e:
				cls.expire(key, text, str(e.__class__.__name__))
		return default

	@classmethod
	def get_or_add(cls, key, callback, invalidate_after=GENERAL_CACHE_TIME_OUT, idle_expiry=0):
		""" Retrieves the stored object if it exists, else creates it and store it using the callback (Thread Safe)

		:param key: the key to identify the object
		:type key: basestring
		:param callback: a function returning the object to cache if not found
		:type callback: callable
		:param invalidate_after: number of second after which the object will be deleted (0 to disable)
		:type invalidate_after: int | float
		:param idle_expiry: number of second since last access after which the object will be deleted (0 to disable)
		:type idle_expiry: int | float
		:return: The stored object or None
		:raise: AssertionError if callback is not a callable object
		"""
		assert callable(callback)
		key = cls._key_getter(key)
		obj = cls.get(key)
		if not obj:
			obj = callback()
			cls.add(obj, key, invalidate_after, idle_expiry)
		return obj

	@classmethod
	@new_thread
	def expire(cls, key, text, exception_txt):
		""" Removes an object from the cache (Thread Safe)

		:param key: the key to identify the object
		:type key: basestring
		:param text: a message to be added to the log upon removal if cls._DEBUG is True
		:type text: str
		:param exception_txt: a message to be added to the log upon removal failure
		:type exception_txt: str
		:return: is success
		:rtype: bool
		"""
		key = cls._key_getter(key)
		try:
			with cls.data_mutex:
				del cls._cache[key]
			if cls._DEBUG:
				get_logger().debug('Cache : removed %s:%s : %s' % (key, text, exception_txt))
			return True
		except KeyError:
			return False

	@classmethod
	def _key_getter(cls, the_object):
		""" Get the key from the object if stored in cache

		:param the_object: the object to get the key of
		:type the_object: object
		:return: is success
		:rtype: object | basestring
		"""
		if not isinstance(the_object, basestring):
			with cls.data_mutex:
				if the_object in cls._cache.values():
					return cls._cache.keys()[cls._cache.values().index(the_object)]
		return the_object

	@classmethod
	def add(cls, some_object, key, invalidate_after=GENERAL_CACHE_TIME_OUT, idle_expiry=0):
		""" store some object in the cache using key as a reference (Thread Safe)

		:param some_object: the object to store
		:param key: the key to identify the object
		:type key: basestring
		:param invalidate_after: number of second after which the object will be deleted (0 to disable)
		:type invalidate_after: int | float
		:param idle_expiry: number of second since last access after which the object will be deleted (0 to disable)
		:type idle_expiry: int | float
		"""
		cls.garbage_collection()
		if not cls.get_cached(key):
			with cls.data_mutex:
				cls._cache[key] = CachedObject(some_object, invalidate_after, idle_expiry)
			if cls._DEBUG:
				get_logger().debug('Cache : added %s:%s' % (key, repr(cls.get_cached(key))))

	@classmethod
	def clear(cls):
		""" Removes everything from the cache (Thread Safe) """
		with cls.data_mutex:
			num = len(cls._cache)
			cls._cache = dict()
		if cls._DEBUG:
			get_logger().debug('Cache : cleared (%s objects removed)' % num)

	@classmethod
	@new_thread
	def garbage_collection(cls):
		""" Process to the removal of any expired object (due to idle, or general expiration) (Thread Safe) """
		with cls.data_mutex:
			for k, v in cls._cache.items():
				if v.is_idle_time_out or v.is_expired:
					cls.expire(k, str(v), 'ExpiredGarbageCollection')
