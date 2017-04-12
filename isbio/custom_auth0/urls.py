# -*- coding: utf-8 -*-
from django.conf.urls import url
from .views import auth_callback, process_login


urlpatterns = [
    url(r'callback/?$', auth_callback, name='auth_callback'),
    url(r'login/?$', process_login, name='process_login'),
]
