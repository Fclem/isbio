# -*- coding: utf-8 -*-
# from __future__ import unicode_literals
from django.contrib.auth import get_user_model
from django.utils.translation import ugettext as _
from utilz import logger
from django.core.exceptions import PermissionDenied

UserModel = get_user_model()

# user profile keys that are always present as specified by
# https://auth0.com/docs/user-profile/normalized#normalized-user-profile-schema
AUTH0_USER_INFO_KEYS = [
	'name',
	'nickname',
	'picture',
	'user_id',
]


# clem 12/04/2017
class Auth0IdMismatch(PermissionDenied):
	def __init__(self, msg):
		logger.warning(msg)
		super(Auth0IdMismatch, self).__init__(msg)


class Auth0Backend(object):
	@staticmethod
	def authenticate(**kwargs): # code duplicated from original Auth0 backend
		"""
		Auth0 return a dict which contains the following fields
		:param kwargs: user information provided by auth0
		:return: user
		"""
		# check that each auth0 key is present in kwargs
		for key in AUTH0_USER_INFO_KEYS:
			if key not in kwargs:
				return None
		
		user_id = kwargs.get('user_id', None)
		user_nick = kwargs.get('nickname', None)
		user_email = kwargs.get('email', None)
		
		if user_id is None:
			raise ValueError(_('user_id can\'t be blank!'))
		
		# The format of user_id is
		# {identity provider id}|{unique id in the provider}
		# The pipe character is invalid for the django username field (FIXME is it ?)
		# The solution is to replace the pipe with a dash
		# user_id = user_id.replace('|', '-')
		
		try:
			user = UserModel.objects.get(username__iexact=user_nick)
			user = user if user.is_active else None
			if user.password != user_id: # check for eventual hijack attempt
				raise Auth0IdMismatch('Recorded user\'s Auth0 id does not match the id retrieved from Auth0')
		except UserModel.DoesNotExist:
			user = UserModel.objects.create_user(username=user_nick, email=user_email, password=user_id)
			logger.info('USER signup %s' % user)
		
		return user
	
	# noinspection PyProtectedMember
	@staticmethod
	def get_user(user_id):
		"""
		Primary key identifier
		It is better to raise UserModel.DoesNotExist
		:param user_id:
		:return: UserModel instance
		"""
		return UserModel._default_manager.get(pk=user_id)
