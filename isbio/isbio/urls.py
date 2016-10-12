"""isbio URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
	https://docs.djangoproject.com/en/1.9/topics/http/urls/
Examples:
Function views
	1. Add an import:  from my_app import views
	2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
	1. Add an import:  from other_app.views import Home
	2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
	1. Import the include() function: from django.conf.urls import url, include
	2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url, include
from django.conf import settings
from django.contrib.staticfiles.views import serve
from breeze.middlewares import is_on

if not is_on():
	from down import views

	urlpatterns = [url(r'^.*$', views.down)]
else:
	from django.contrib.staticfiles.urls import staticfiles_urlpatterns
	from breeze import views
	# Uncomment/comment the next two lines to enable/disable the admin:
	from django.contrib import admin
	admin.autodiscover()

	email_pattern = r'\b[\w.\'-]+@(?:(?:[^_+,!@#$%^&*();\/\\|<>"\'\n -][-\w]+[^_+,!@#$%^&*();\/\\|<>"\' ' \
		r'\n-]|\w+)\.)+\w{2,63}\b'

	urlpatterns = [
		url(r'^', include('hello_auth.urls')),
		url(r'^auth/', include('django_auth0.urls')),
		url(r'^user_list/?$', views.user_list),
		url(r'^test1/?', views.job_list),
		url(r'^mail_list/?$', views.user_list_advanced),
		url(r'^custom_list/?$', views.custom_list),
		# url(r'^$', django_cas_login),  # views.breeze),
		url(r'^breeze/?$', views.breeze),
		# url(r'^logout/?$', django_cas_logout),  # views.logout),
		url(r'^stat/?$', views.ajax_user_stat),
		# Special system checks
		# url(r'^resources/restart/?$', views.restart_breeze),
		# url(r'^resources/restart-vm/?$', views.restart_vm),
		url(r'^status/fs_info/?$', views.file_system_info),
		url(r'^status/fs_info/fix_file/(?P<fid>\d+)$', views.fix_file_acl),
		url(r'^status/log/?$', views.view_log),
		url(r'^status/log/all/?$', views.view_log, { 'show_all': True }),
		url(r'^status/log/(?P<num>\d+)/?$', views.view_log),
		url(r'^status/fs_ok/?$', views.check_file_system_coherent),
		url(r'^status/qstat/?$', views.qstat_live),
		url(r'^status_lp/qstat/(?P<md5_t>[a-z0-9_]{32})?$', views.qstat_lp),
		# All others system check in a wrapper
		url(r'^status/(?P<what>[a-z_]+)?/?$', views.checker),
		url(r'^home/(?P<state>[a-z]+)?$', views.home, name='home'),
		url(r'^ajax-rora-patients/(?P<which>[a-z]+)?$', views.ajax_patients_data),
		url(r'^ajax-rora/action/?$', views.ajax_rora_action),
		url(r'^ajax-rora-plain-screens/(?P<gid>\d+)$', views.ajax_rora_screens),
		url(r'^ajax-rora-groupname/?$', views.group_name),
		url(r'^update-user-info/?$', views.update_user_info_dialog),
		url(r'^update-server/?$', views.update_server),
		url(r'^help/?$', views.dochelp),
		# url(r'^db-policy/?$', views.db_policy),
		url(r'^store/?$', views.store, name='store'),
		url(r'^store/deletefree/?$', views.deletefree),
		url(r'^installscripts/(?P<sid>\d+)$', views.install),
		url(r'^installreport/(?P<sid>\d+)$', views.installreport),
		url(r'^mycart/?$', views.my_cart),
		url(r'^updatecart/?$', views.update_cart),
		url(r'^addtocart/(?P<sid>\d+)$', views.add_to_cart),
		url(r'^abortreports/(?P<rid>\d+)$', views.abort_report),
		url(r'^abortjobs/(?P<jid>\d+)$', views.abort_job),
		url(r'^search/(?P<what>[a-z]+)?$', views.search),
		url(r'^patient-data/(?P<which>\d+)?$', views.ajax_patients),
		url(r'^patient-new/?$', views.ajax_patients_new),
		url(r'^screen-data/(?P<which>\d+)?$', views.screen_data),
		url(r'^showdetails/(?P<sid>\d+)$', views.showdetails),
		url(r'^deletecart/(?P<sid>\d+)$', views.deletecart),
		url(r'^reports/?$', views.reports),
		url(r'^reports/search$', views.report_search),
		url(r'^reports/view/(?P<rid>\d+)/(?P<fname>.+)?$', views.report_file_view, name='report.view'),
		url(r'^reports/get/(?P<rid>\d+)/(?P<fname>.+)?$', views.report_file_get),
		url(r'^media/reports/(?P<rid>\d+)_(?P<rest>[^/]+)/(?P<fname>.+)?$', views.report_file_wrap),
		url(r'^media/reports/(?P<rid>\d+)/(?P<fname>.+)?$', views.report_file_wrap2),
		url(r'^reports/delete/(?P<rid>\d+)(?P<redir>-[a-z]+)?$', views.delete_report),
		url(r'^reports/edit_access/(?P<rid>\d+)$', views.edit_report_access),
		url(r'^reports/overview/(?P<rtype>\w+)-(?P<iname>[^/-]+)-(?P<iid>[^/-]+)$', views.report_overview),
		url(r'^reports/edit/(?P<jid>\d+)?$', views.edit_report),  # Re Run report
		url(r'^reports/check/?$', views.check_reports),  # Re Run report
		url(r'^reports/send/(?P<rid>\d+)$', views.send_report),
		url(r'^off_user/add/?$', views.add_offsite_user_dialog),
		url(r'^off_user/add/(?P<rid>\d*)$', views.add_offsite_user_dialog),
		url(r'^off_user/add/form/(?P<email>' + email_pattern + ')$', views.add_offsite_user),
		url(r'^off_user/add/form/?$', views.add_offsite_user),
		url(r'^off_user/edit/(?P<uid>\d*)$', views.edit_offsite_user),
		url(r'^off_user/del/(?P<uid>\d*)$', views.delete_off_site_user),
		# Shiny page in
		# url(r'^reports/shiny-tab/(?P<rid>\d+)/?$', views.report_shiny_view_tab),
		url(r'^runnable/delete/?', views.runnable_del),
		url(r'^jobs/(?P<page>\d+)?(/)?(?P<state>[a-z]+)?(/)?$', views.jobs, name='jobs'),
		url(r'^jobs/delete/(?P<jid>\d+)(?P<state>[a-z]+)?$', views.delete_job), # FIXME DEPRECATED
		url(r'^jobs/(?P<page>\d+)?(/)?(?P<state>[a-z]+)?(/)?delete/(?P<jid>\d+)$', views.delete_job),
		url(r'^jobs/(?P<page>\d+)?(/)?(?P<state>[a-z]+)?(/)?group-delete/?$', views.runnable_del),
		url(r'^jobs/run/(?P<jid>\d+)$', views.run_script), # FIXME DEPRECATED
		url(r'^jobs/(?P<page>\d+)?(/)?(?P<state>[a-z]+)?(/)?run/(?P<jid>\d+)$', views.run_script),
		url(r'^jobs/edit/jobs/(?P<jid>\d+)(?P<mod>-[a-z]+)?$', views.edit_job), # FIXME DEPRECATED
		url(r'^jobs/(?P<page>\d+)?(/)?(?P<state>[a-z]+)?(/)?edit/jobs/(?P<jid>\d+)(?P<mod>-[a-z]+)?$', views.edit_job),
		url(r'^jobs/edit/(?P<jid>\d+)(?P<mod>-[a-z]+)?$', views.edit_job), # FIXME DEPRECATED
		url(r'^jobs/(?P<page>\d+)?(/)?(?P<state>[a-z]+)?(/)?edit/(?P<jid>\d+)(?P<mod>-[a-z]+)?$', views.edit_job),
		url(r'^jobs/show-code/(?P<jid>\d+)$', views.show_rcode),
		url(r'^jobs/download/(?P<jid>\d+)(?P<mod>-[a-z]+)?$', views.send_zipfile_j),
		url(r'^report/download/(?P<jid>\d+)(?P<mod>-[a-z]+)?$', views.send_zipfile_r),
		# url(r'^update-jobs/(?P<jid>\d+)-(?P<item>[a-z]+)$', views.update_jobs), # FIXME DEPRECATED
		url(r'^jobs/info/(?P<jid>\d+)-(?P<item>[a-z]+)$', views.update_jobs), # FIXME DEPRECATED
		url(r'^jobs/info/(?P<item>[a-z]+)/(?P<jid>\d+)$', views.update_jobs),
		url(r'^jobs/info/(?P<jid>\d+)$', views.update_jobs, { 'item': 'script' }),
		url(r'^reports/info/(?P<jid>\d+)$', views.update_jobs, { 'item': 'report' }),
		# new
		url(r'^jobs/info_lp/(?P<jid>\d+)/(?P<md5_t>[a-z0-9_]{32})?$', views.update_jobs_lp, { 'item': 'script' }),
		url(r'^reports/info_lp/(?P<jid>\d+)/(?P<md5_t>[a-z0-9_]{32})?$', views.update_jobs_lp, { 'item': 'report' }),
		url(r'^hook/(?P<i_type>r|j)(?P<rid>\d+)/(?P<md5>[a-z0-9_]{32})/(?P<status>\w+)?$', views.job_url_hook),
		url(r'^hook/(?P<i_type>r|j)(?P<rid>\d+)/(?P<md5>[a-z0-9_]{32})/(?P<status>\w+)/(?P<code>\w+)?$', views.job_url_hook),
		# url(r'^update-all-jobs/$', views.update_all_jobs), # DO NOT USE : TOOOOOOOO SLOW
		url(r'^scripts/new/?$', views.new_script_dialog, name='scripts.new'),
		url(r'^scripts/delete/(?P<sid>\d+)$', views.delete_script),
		url(r'^scripts/apply-script/(?P<sid>\d+)$', views.create_job, name="scripts.apply"),
		url(r'^scripts/read-descr/(?P<sid>\d+)$', views.read_descr, name='scripts.read_desc'),
		url(r'^scripts/(?P<layout>[a-z]+)?$', views.scripts),
		url(r'^new/append/(?P<which>[A-Z]+)$', views.append_param),
		url(r'^new/delete/(?P<which>.+)$', views.delete_param),
		url(r'^new/?$', views.create_script),
		url(r'^pipelines/new/?$', views.new_rtype_dialog), # TODO
		url(r'^new-rtype/?$', views.new_rtype_dialog),
		url(r'^projects/create/?$', views.new_project_dialog),
		url(r'^projects/edit/(?P<pid>\d+)$', views.edit_project_dialog),
		url(r'^projects/view/(?P<pid>\d+)$', views.veiw_project),
		url(r'^projects/delete/(?P<pid>\d+)$', views.delete_project),
		url(r'^groups/create/?$', views.new_group_dialog),
		url(r'^groups/edit/(?P<gid>\d+)$', views.edit_group_dialog),
		url(r'^groups/view/(?P<gid>\d+)$', views.view_group),
		url(r'^groups/delete/(?P<gid>\d+)$', views.delete_group),
		url(r'^submit/?$', views.save),
		url(r'^get/template/(?P<name>[^/]+)$', views.send_template, name='get.template'),
		url(r'^get/(?P<ftype>[a-z]+)-(?P<fname>[^/-]+)$', views.send_file),
		url(r'^builder/?$', views.builder),
		url(r'^invalidate/??$', views.invalidate_cache),
		url(r'^resources/?$', views.resources, name='res'),
		url(r'^resources/invalidate_cache/?$', views.invalidate_cache_view, name='cache.invalidate'),
		url(r'^resources/scripts/(?P<page>\d+)?$', views.manage_scripts, name='res.scripts'),
		url(r'^resources/scripts/all/(?P<page>\d+)?$', views.manage_scripts, { 'view_all': True }, name='res.scripts.all'),
		url(r'^resources/scripts/(all/)?script-editor/(?P<sid>\d+)(?P<tab>-[a-z_]+)?$', views.script_editor),
		url(r'^resources/scripts/(all/)?script-editor/update/(?P<sid>\d+)$', views.script_editor_update),
		url(r'^resources/scripts/(all/)?script-editor/get-content/(?P<content>[^/-]+)(?P<iid>-\d+)?$', views.send_dbcontent),
		url(r'^resources/scripts/(all/)?script-editor/get-code/(?P<sid>\d+)/(?P<sfile>[^/-]+)$', views.get_rcode),
		url(r'^resources/scripts/(all/)?script-editor/get-form/(?P<sid>\d+)$', views.get_form),
		url(r'^resources/pipes/?$', views.manage_pipes),
		url(r'^resources/pipes/pipe-editor/(?P<pid>\d+)$', views.edit_rtype_dialog),
		url(r'^resources/pipes/delete/(?P<pid>\d+)$', views.delete_pipe),
		url(r'^resources/datasets/?$', views.manage_scripts),
		url(r'^resources/files/?$', views.manage_scripts),
		url(r'^resources/integration/?$', views.manage_scripts),
		url(r'^media/scripts/(?P<path>[^.]*(\.(jpg|jpeg|gif|png)))?$', serve,
			{'document_root': settings.MEDIA_ROOT + 'scripts/'}),
		url(r'^media/pipelines/(?P<path>[^.]*(\.(pdf)))$', serve,
			{'document_root': settings.MEDIA_ROOT + 'pipelines/'}),
		url(r'^media/mould/(?P<path>.*)$', serve,
			{'document_root': settings.MEDIA_ROOT + 'mould/'}),

		# url(r'^media/(?P<path>.*)$', 'django.views.static.serve',
		# 			{'document_root': settings.MEDIA_ROOT}),
		# Examples:
		# url(r'^$', 'isbio.views.home', name='home'),
		# url(r'^isbio/', include('isbio.foo.urls')),

		# Uncomment the admin/doc line below to enable admin documentation:
		# url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

		# Uncomment/comment the next line to enable/disable the admin:
		url(r'^admin/?', include(admin.site.urls)),
	]

	if settings.DEBUG and settings.DEV_MODE:

		urlpatterns += [
			url(r'^closed$', serve, { 'path': '', }),
			# url(r'^static/(?P<path>.*)$', serve)
		]
	# print staticfiles_urlpatterns()
	urlpatterns += staticfiles_urlpatterns()
