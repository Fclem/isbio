"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""
from django.test import TestCase
from breeze.models import *


# FIXME broken
class TestUserOverride(TestCase):
    def setUp(self):
        pass
    
    def test_animals_can_speak(self):
        user = User.objects.get(pk=1)
        user = BreezeUser.get(user)
        self.assertEqual(user, user.user_profile.user)
