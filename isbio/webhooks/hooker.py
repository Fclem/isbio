from __future__ import print_function
from utilz import *
from django.core.handlers.wsgi import WSGIRequest
from django.core.exceptions import SuspiciousOperation

# from . import settings
# from django.conf import settings

CT_JSON = 'application/json'
CT_FORM = 'application/x-www-form-urlencoded'
CT_TEXT = 'text/plain'
empty_dict = dict()


# clem 17/10/2016
def get_key_magic(level=0):
	return get_key('api_' + this_function_caller_name(level))


# clem 04/10/2017
class BadRequest(SuspiciousOperation):
	pass


# clem 04/10/2017
class InvalidSignature(BadRequest):
	pass


# clem 04/10/2017
class WrongHTTPMethod(BadRequest):
	pass


# clem 04/10/2017
class POSTRequestWasExpected(WrongHTTPMethod):
	pass


# clem 04/10/2017
class GETRequestWasExpected(WrongHTTPMethod):
	pass


# clem 04/10/2017
class WrongContentType(BadRequest):
	pass


# clem 04/10/2017
class JSONContentTypeWasExpected(WrongContentType):
	pass


# clem 04/10/2017
class FormEncContentTypeWasExpected(WrongContentType):
	pass


# clem 04/10/2017
class NotFromAuthorizedHost(BadRequest):
	pass


# clem 17/10/2016
class HookWSGIReq(WSGIRequest):
	import hashlib
	_not = "Class %s doesn't implement %s()"
	H_SIG = '' # optional HTTP HEADER name container the signature
	H_DELIVERY_ID = '' # optional HTTP HEADER name container the delivery id
	H_REQ_METHOD = 'REQUEST_METHOD'
	H_C_T = 'CONTENT_TYPE'
	H_HOST = 'HTTP_X_Forwarded_For' # X-Forwarded-For # HTTP_HOST
	H_REMOTE_IP = 'HTTP_X_Real_IP' # X-Real-IP # might be proxy IP, do not trust
	H_USER_AGENT = 'HTTP_USER_AGENT'
	DEF_SOURCE_NET = '0.0.0.0/0'
	DEF_HASH_ALGORITHM = hashlib.sha1
	AVAILABLE_HASH = hashlib.algorithms
	VERBOSITY = True
	
	def __init__(self, request, call_depth=0, restrict_source_network=DEF_SOURCE_NET, hash_algorithm=DEF_HASH_ALGORITHM):
		assert isinstance(request, WSGIRequest)
		super(HookWSGIReq, self).__init__(request.environ)
		self._call_depth = call_depth
		self._allowed_source_net = restrict_source_network
		if self._is_hash_algorithm_valid(hash_algorithm):
			self._hash_algorithm = hash_algorithm
		else:
			logger.warning('hash algorithm %s not available from hashlib' % hash_algorithm.__name__)
			self._hash_algorithm = self.DEF_HASH_ALGORITHM
	
	#############
	# ACCESSORS #
	#############
	
	def get_meta(self, key, default=''):
		return str(self.META.get(key.upper(), default))
	
	def get_meta_low(self, key, default=''):
		return self.get_meta(key, default).lower()
	
	def get_meta_up(self, key, default=''):
		return self.get_meta(key, default).upper()
	
	#########################
	# HTTP HEADER shortcuts #
	#########################
	
	# clem 18/10/2016
	@property
	def http_remote_ip(self):
		remote_ip = self.get_meta(self.H_REMOTE_IP)
		host_list = self.http_remote_host_list
		if len(host_list) > 1: # and remote_ip in host_list:
			# host_list.remove(remote_ip)
			return host_list[0]
		return remote_ip
	
	# clem 04/10/2017
	@property
	def http_remote_host_list(self):
		# host_line = self.get_meta(self.H_HOST)
		# return [x.strip() for x in host_line.split(',')]
		host_line = self.get_meta(self.H_HOST).replace(' ', '').replace('\t', '')
		return host_line.split(',')
	
	# clem 18/10/2016
	@property
	def http_remote_host_deprecated(self):
		""" legacy version of http_remote_host_list, that omits the fact that this value may contain multiple IPs"""
		# return self.http_remote_host_list[0]
		return self.get_meta(self.H_HOST)
	
	# clem 18/10/2016
	@property
	def http_user_agent(self):
		return self.get_meta(self.H_USER_AGENT)
	
	# clem 18/10/2016
	@property
	def http_content_type(self):
		return self.get_meta(self.H_C_T)
	
	# clem 18/10/2016
	@property
	def http_request_method(self):
		return self.get_meta(self.H_REQ_METHOD)
	
	#############
	# FUNCTIONS #
	#############
	
	# clem 18/10/2016
	def _is_hash_algorithm_valid(self, hash_algorithm):
		""" If hash_algorithm is part of available hashlib algorithm
		
		:param hash_algorithm: a hash algorithm from hashlib
		:type hash_algorithm: callable
		:rtype: bool
		"""
		return callable(hash_algorithm) and hash_algorithm().name in self.AVAILABLE_HASH
	
	def _hmac(self, key, algorithm=None):
		""" Compute the digest of the request body, provided the key to use and the optional hash algorithm
		
		:type key: str
		:type algorithm: object | None
		:rtype: str
		"""
		import hmac
		if not algorithm or not self._is_hash_algorithm_valid(algorithm):
			self._hash_algorithm = self.DEF_HASH_ALGORITHM
		return hmac.new(key, self.body, self._hash_algorithm).hexdigest()
	
	@property
	def signature(self):
		""" Return the signature found in H_SIG HTTP header if H_SIG is defined, '' otherwise

		:rtype: str
		"""
		return self.get_meta(self.H_SIG) if self.H_SIG else ''
	
	@property
	def delivery_id(self):
		""" Return the delivery id found in H_DELIVERY_ID HTTP header if H_DELIVERY_ID is defined, '' otherwise

		:rtype: str
		"""
		return self.get_meta(self.H_DELIVERY_ID) if self.H_DELIVERY_ID else ''
	
	@property
	def has_sig(self):
		""" Wether or not this request has a signature as defined in HTTP header H_SIG or
		
		as returned by your own implementation of self.signature \n
		the signature must start by the name of the hash algorithm self._sign_type i.e. "sha1:" or "md5=", etc \n
		if not then overload this function

		:rtype: bool
		"""
		try:
			return self.signature.startswith(self._hash_algorithm().name)
		except Exception as e:
			logger.exception(str(e))
		return False
	
	# clem 18/10/2016
	@property
	def check_source_address(self):
		""" Wether the source address of the client lies in the expected network, if specified during init, True
		
		otherwise
		
		:rtype: bool
		"""
		return self._allowed_source_net == self.DEF_SOURCE_NET or \
			is_ip_in_network(self.http_remote_ip, self._allowed_source_net)
	
	# clem 04/10/2016
	@property
	def enforce_source_address(self):
		""" Check if the source address of the client lies in the expected network, if specified during init, True
		
		otherwise
		
		:rtype: bool
		"""
		if self.check_source_address:
			return True
		raise NotFromAuthorizedHost('Address %s not in network %s' % (self.http_remote_ip, self._allowed_source_net))
	
	@property
	def is_post_hook(self):
		""" Wether or not the request if of POST type
		
		:return: Wether or not the request if of POST type
		:rtype: bool
		"""
		return self.http_request_method == 'POST' and self.check_source_address
	
	# clem 04/10/2017
	@property
	def enforce_post_hook(self):
		""" Check if the request if of POST type and form authorized source network
		
		:return: True iff request is of POST type and form authorized source network
		:raise: if not POST, or not from authorized source network
		:raises: NotPostRequest, NotFromAuthorizedHost
		:rtype: bool
		"""
		if self.http_request_method != 'POST':
			raise POSTRequestWasExpected('Instead method was %s' % self.http_request_method)
		return self.enforce_source_address
	
	# clem 18/10/2016
	@property
	def is_get_hook(self):
		""" Wether or not the request if of GET type

		:return: Wether or not the request if of GET type
		:rtype: bool
		"""
		return self.http_request_method == 'GET' and self.check_source_address
	
	# clem 04/10/2017
	@property
	def enforce_get_hook(self):
		""" Wether or not the request if of GET type

		:return: Wether or not the request if of GET type
		:rtype: bool
		"""
		if self.http_request_method != 'GET':
			raise GETRequestWasExpected('Instead method was %s' % self.http_request_method)
		return self.enforce_source_address
	
	@property
	def is_json_post(self):
		""" Wether the HTTP content type header is application/json and HTTP method is POST
		
		:rtype: bool
		"""
		return self.is_post_hook and self.http_content_type == CT_JSON
	
	# clem 04/10/2017
	@property
	def enforce_json_post(self):
		""" Wether the HTTP content type header is application/json and HTTP method is POST
		
		:rtype: bool
		"""
		if self.enforce_post_hook:
			if self.http_content_type != CT_JSON:
				raise JSONContentTypeWasExpected('Instead content type was %s' % self.http_content_type)
		return True
	
	# clem 18/10/2016
	@property
	def is_form_post(self):
		""" Wether the HTTP content type header is application/x-www-form-urlencoded and HTTP method is POST
		
		:rtype: bool
		"""
		return self.is_post_hook and self.http_content_type == CT_FORM
	
	# clem 04/10/2017
	@property
	def enforce_form_post(self):
		""" Wether the HTTP content type header is application/x-www-form-urlencoded and HTTP method is POST
		
		:rtype: bool
		"""
		if self.enforce_post_hook:
			if self.http_content_type != CT_FORM:
				raise JSONContentTypeWasExpected('Instead content type was %s' % self.http_content_type)
		return True
	
	@property
	def client_id(self):
		""" Return a client identification line as "http_remote_host (http_remote_ip) / http_user_agent" if
		
		http_remote_host is different form http_remote_ip, "http_remote_ip / http_user_agent" otherwise
		
		:rtype: str
		"""
		host = self.http_remote_host_deprecated
		ip = self.http_remote_ip
		host_bloc = host if host == ip else '%s (%s)' % (host, ip)
		return '%s / %s' % (host_bloc, self.http_user_agent)
	
	# noinspection PyUnboundLocalVariable
	def check_sig(self, key=None, call_depth=0):
		""" check if the signature of the request body is valid (return False if no signature present)
		
		The signature is provided as "*sig" in the HTTP header of name H_SIG \n
		It is checked against a HMAC digest of the request.body using key \n
		c.f. https://pubsubhubbub.github.io/PubSubHubbub/pubsubhubbub-core-0.4.html#authednotify
		
		:type key: str  | None
		:param call_depth: 0 if calling this function directly, 1 if calling for another function
		:type call_depth: int  | None
		:rtype: bool
		"""
		if self.has_sig and self.body:
			if self.VERBOSITY:
				args = (this_function_caller_name(self._call_depth + call_depth), self.client_id, self.delivery_id)
				msg = ' SIG_CHECK for %s FROM %s (delivery %s)' % args
			if self.signature.endswith(self._hmac(key or get_key_magic(self._call_depth + 1 + call_depth))):
				if self.VERBOSITY:
					success_msg = 'VERIFIED' + msg
					logger.info(success_msg)
					print(TermColoring.ok_green(success_msg))
				return True
			else:
				if self.VERBOSITY:
					error_msg = 'FAILED' + msg
					logger.warning(error_msg)
					print(TermColoring.fail(error_msg))
		return False
	
	# clem 04/10/2017
	def enforce_sig(self, key=None, call_depth=0):
		if not self.check_sig(key, ++call_depth):
			raise InvalidSignature
		return True
	
	# clem 18/10/2016
	def get_json(self, key=None, call_depth=0):
		""" grab the json object from request.content, checks the signature if there is one, fails if its invalid
		
		:param key: the optional signature key
		:type key: str | None
		:param call_depth: 0 if calling this function directly, 1 if calling for another function
		:type call_depth: int  | None
		:return: A json object
		:rtype: object | None
		"""
		if self.is_json_post and self.body and\
			(not self.has_sig or self.check_sig(key or get_key_magic(self._call_depth + 1 + call_depth), 1)):
			return json.loads(self.body)
		return None


# clem 18/10/2016
class GitHubWSGIReq(HookWSGIReq):
	H_SIG = 'HTTP_X_HUB_SIGNATURE'
	H_DELIVERY_ID = 'HTTP_X_GitHub_Delivery'
	H_EVENT = 'HTTP_X_GitHub_Event'
	
	def __init__(self, request, call_depth=0, restrict_source_network=HookWSGIReq.DEF_SOURCE_NET,
		sign_type=HookWSGIReq.DEF_HASH_ALGORITHM):
		super(GitHubWSGIReq, self).__init__(request, call_depth, restrict_source_network, sign_type)
	
	@property
	def event_name(self):
		return self.get_meta(self.H_EVENT)
