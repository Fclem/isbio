from django.conf.urls import url, include
from . import views as api_views

urlpatterns = [
	url(r'^$', api_views.api_home, name='api.home'),
	url(r'^auth/check/?$', api_views.is_authenticated, name='api.is_authenticated'),
	url(r'^auth/test/?$', api_views.has_auth, name='api.has_auth'),
	url(r'^auth/shiny/?.*$', api_views.shiny_auth, name='api.shiny_auth'),
	url(r'^legacy/', include('api.urls_legacy')),
	url(r'^v1/', include('api.urls_v1')),
	url(r'^.*/?', api_views.handler404, name='api.not_found'),
]
