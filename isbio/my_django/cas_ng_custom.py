"""CAS authentication backend override"""
from django_cas_ng.backends import CASBackend as org_CASBackend
# from django.contrib.auth.backends import ModelBackend


class CASBackend(org_CASBackend):
	"""CAS authentication backend override"""
	
	def user_can_authenticate(self, user):
		"""
		Reject users with is_active=False. Custom user models that don't have
		that attribute are allowed.
		note : duplicated code from django.contrib.auth.backends.ModelBackend
			since "user_can_authenticate = ModelBackend.user_can_authenticate" was not working
		"""
		print 'HelloAuth'
		is_active = getattr(user, 'is_active', None)
		return is_active or is_active is None

