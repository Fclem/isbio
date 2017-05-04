from django.conf.urls import url
from .views import *


urlpatterns = [
    url(r'^$', index, name='index'),
    url(r'^old_login_page/?$', index, name='old_login_page', kwargs={'landing': False}),
    url(r'^login_page/?$', index, name='login_page'),
    url(r'^guest_login/?$', guest_login, name='guest_login'),
    url(r'^login/?$', process_login, name='process_login'),
    url(r'^logout/?$', trigger_logout, name='trigger_logout'),
    url(r'^logout/login/?$', logout_login, name='logout_login'),
]
