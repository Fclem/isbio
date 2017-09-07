# Django settings for isbio project.
# from configurations import Settings
import logging
import os
import socket
import time
from datetime import datetime
from utilz import git, TermColoring, recur, recur_rec, get_key, import_env, file_content, is_host_online,  test_url, \
	magic_const, get_md5

ENABLE_DATADOG = False
ENABLE_ROLLBAR = False
statsd = False
try:
	from datadog import statsd
	if ENABLE_DATADOG:
		ENABLE_DATADOG = True
except Exception:
	ENABLE_DATADOG = False
	
ENABLE_REMOTE_FW = False

# TODO : redesign

PID = os.getpid()

MAINTENANCE = False
USUAL_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
USUAL_LOG_FORMAT = \
	'%(asctime)s,%(msecs)03d  P%(process)05d %(levelname)-8s %(lineno)04d:%(module)-20s %(funcName)-25s %(message)s'
USUAL_LOG_LEN_BEFORE_MESSAGE = 93
USUAL_LOG_FORMAT_DESCRIPTOR =\
	'DATE       TIME,milisec  PID   LEVEL     LINE:MODULE               FUNCTION                  MESSAGE'
DB_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
LOG_FOLDER = '/var/log/breeze/'
# log_fname = 'breeze_%s.log' % datetime.now().strftime("%Y-%m-%d_%H-%M-%S%z")
log_fname = 'rotating.log'
log_hit_fname = 'access.log'
LOG_PATH = '%s%s' % (LOG_FOLDER, log_fname)
LOG_HIT_PATH = '%s%s' % (LOG_FOLDER, log_hit_fname)


# DEBUG = False
TEMPLATE_DEBUG = False

ADMINS = (
	('Clement FIERE', 'clement.fiere@helsinki.fi'),
)

MANAGERS = ADMINS

MYSQL_SECRET_FILE = 'mysql_root'

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'Europe/Helsinki'

DATABASES = {
	'default': {
		'ENGINE'	: 'django.db.backends.mysql', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
		'NAME'		: 'breezedb', # Or path to database file if using sqlite3.
		'USER'		: 'root', # Not used with sqlite3.
		'PASSWORD'	: get_key(MYSQL_SECRET_FILE), # Not used with sqlite3.
		'HOST'		: 'breeze-sql', # Set to empty string for localhost. Not used with sqlite3.
		'PORT'		: '3306', # Set to empty string for default. Not used with sqlite3.
		'OPTIONS'	: {
			"init_command": "SET default_storage_engine=INNODB; SET SESSION TRANSACTION ISOLATION LEVEL READ "
							"COMMITTED",
		}
		# "init_command": "SET transaction isolation level READ COMMITTED", }
	}
}

ROOT_URLCONF = 'isbio.urls'

TEMPLATES = [
	{
		'BACKEND' : 'django.template.backends.django.DjangoTemplates',
		'DIRS'    : [],
		'APP_DIRS': True,
		'OPTIONS' : {
			'context_processors': [
				'django.template.context_processors.debug',
				'django.template.context_processors.request',
				'django.contrib.auth.context_processors.auth',
				'django.contrib.messages.context_processors.messages',
				'django.template.context_processors.media',
				'django.template.context_processors.static',
				'breeze.context.user_context',
				'breeze.context.date_context',
				'breeze.context.run_mode_context',
				# 'django_auth0.context_processors.auth0', # moved to config/auth0.py
				"breeze.context.site",
				"breeze.context.__context_var_list",
			],
		},
	},
]

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = '/media/'

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
# STATIC_ROOT = '' # ** moved lower in this file

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# Additional locations of static files
# ** moved to configs/env/*
# STATICFILES_DIRS = (
# 	"/root/static_source",
# )

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
	'django.contrib.staticfiles.finders.FileSystemFinder',
	'django.contrib.staticfiles.finders.AppDirectoriesFinder',
	'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY_FN = 'django'
SECRET_KEY = get_key(SECRET_KEY_FN)

# List of callable that know how to import templates from various sources.
# TEMPLATE_LOADERS = (
# 	'django.template.loaders.filesystem.Loader',
# 	'django.template.loaders.app_directories.Loader',
# )

# AUTH_USER_MODEL = 'breeze.OrderedUser'
# AUTH_USER_MODEL = 'breeze.CustomUser' # FIXME

INSTALLED_APPS = [
	'suit',
	'django.contrib.admin',
	'django.contrib.auth',
	'django.contrib.contenttypes',
	'django.contrib.sessions',
	'django.contrib.sites',
	'django.contrib.messages',
	'django.contrib.staticfiles',
	'bootstrap_toolkit',
	'breeze.apps.Config',
	'shiny.apps.Config',
	'dbviewer.apps.Config',
	'compute.apps.Config',
	'down.apps.Config',
	# 'south',
	'gunicorn',
	'mathfilters',
	# 'django_auth0', # moved to config/auth0.py
	'hello_auth.apps.Config',
	'api.apps.Config',
	'webhooks.apps.Config',
	'utilz.apps.Config',
	'django_requestlogging',
	'django.contrib.admindocs',
	'django_extensions'
]

MIDDLEWARE_CLASSES = [
	'breeze.middlewares.BreezeAwake',
	'django.middleware.security.SecurityMiddleware',
	'django.contrib.sessions.middleware.SessionMiddleware',
	'django.middleware.common.CommonMiddleware',
	'django.middleware.csrf.CsrfViewMiddleware',
	'django.contrib.auth.middleware.AuthenticationMiddleware',
	'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
	'django.contrib.messages.middleware.MessageMiddleware',
	'django.middleware.clickjacking.XFrameOptionsMiddleware',
	# 'django.middleware.doc.XViewMiddleware',
	'breeze.middlewares.JobKeeper',
	'breeze.middlewares.CheckUserProfile',
	'breeze.middlewares.ContextualRequest',
	'django_requestlogging.middleware.LogSetupMiddleware',
	'breeze.middlewares.DataDog' if ENABLE_DATADOG else 'breeze.middlewares.Empty',
	'breeze.middlewares.RemoteFW' if ENABLE_REMOTE_FW else 'breeze.middlewares.Empty',
	'rollbar.contrib.django.middleware.RollbarNotifierMiddleware' if ENABLE_ROLLBAR else 'breeze.middlewares.Empty',
]

# ** AUTHENTICATION_BACKENDS moved to specific auth config files (config/env/auth/*)

# ** AUTH0_* moved to config/env/auth/auth0.py

SSH_TUNNEL_HOST = 'breeze-ssh'
SSH_TUNNEL_PORT = '2222'
# SSH_TUNNEL_TEST_URL = 'breeze-ssh'

# ROOT_URLCONF = 'isbio.urls'
APPEND_SLASH = True

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'isbio.wsgi.application'

# provide our profile model
AUTH_PROFILE_MODULE = 'breeze.UserProfile'

# allow on the fly creation of guest user accounts
AUTH_ALLOW_GUEST = False		# allow anonymous visitor to login as disposable guests
GUEST_INSTITUTE_ID = 3			# guest institute
GUEST_EXPIRATION_TIME = 24 * 60	# expiration time of inactive guests in minutes
GUEST_FIRST_NAME = 'guest'
GUEST_GROUP_NAME = GUEST_FIRST_NAME.capitalize() + 's'
ALL_GROUP_NAME = 'Registered users'
RESTRICT_GUEST_TO_SPECIFIC_VIEWS = True
DEFAULT_LOGIN_URL = '/login_page'
FORCE_DEFAULT_LOGIN_URL = True

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
	'version': 1,
	'disable_existing_loggers': False,
	'formatters': {
		'standard': {
			'format': USUAL_LOG_FORMAT,
			'datefmt': USUAL_DATE_FORMAT,
		},
	},
	'filters': {
		'require_debug_false': {
			'()': 'django.utils.log.RequireDebugFalse'
		}
	},
	'handlers': {
		'default': {
			'level': 'DEBUG',
			'class': 'logging.handlers.RotatingFileHandler',
			'filename': LOG_PATH,
			'maxBytes': 1024 * 1024 * 5, # 5 MB
			'backupCount': 10,
			'formatter': 'standard',
		},
		'mail_admins': {
			'level': 'ERROR',
			'filters': ['require_debug_false'],
			'class': 'django.utils.log.AdminEmailHandler'
		},
	},
	'loggers': {
		'': {
			'handlers': ['default'],
			'level': logging.INFO,
			'propagate': True
		},
		'django.request': {
			'handlers': ['mail_admins'],
			'level': 'ERROR',
			'propagate': True,
		},

	}
}


class DomainList(object):
	CLOUD_PROD = ['breeze.fimm.fi', '13.79.158.135', ]
	CLOUD_DEV = ['breeze-dev.northeurope.cloudapp.azure.com', '52.164.209.61', ]
	FIMM_PH = ['breeze-newph.fimm.fi', 'breeze-ph.fimm.fi', ]
	FIMM_DEV = ['breeze-dev.fimm.fi', ]
	FIMM_PROD = ['breeze-fimm.fimm.fi', 'breeze-new.fimm.fi', ]
	
	@classmethod
	def get_current_domain(cls):
		from isbio.config import RUN_ENV_CLASS, ConfigEnvironments, MODE_PROD, DEV_MODE, PHARMA_MODE
		if RUN_ENV_CLASS is ConfigEnvironments.AzureCloud:
			domain = cls.CLOUD_DEV if DEV_MODE else cls.CLOUD_PROD
		elif RUN_ENV_CLASS is ConfigEnvironments.FIMM:
			domain = cls.FIMM_PROD if MODE_PROD else cls.FIMM_PH if PHARMA_MODE else cls.FIMM_DEV
		return domain[0]

DEBUG = False
VERBOSE = False
SQL_DUMP = False
# APPEND_SLASH = True

ADMINS = (
	('Clement FIERE', 'clement.fiere@helsinki.fi'),
)

# root of the Breeze django project folder, includes 'venv', 'static' folder copy, isbio, logs
SOURCE_ROOT = recur(3, os.path.dirname, os.path.realpath(__file__)) + '/'
DJANGO_ROOT = recur(2, os.path.dirname, os.path.realpath(__file__)) + '/'
TEMPLATE_FOLDER = DJANGO_ROOT + 'templates/' # source templates (not HTML ones)

DJANGO_AUTH_MODEL_BACKEND_PY_PATH = 'django.contrib.auth.backends.ModelBackend'
# CAS_NG_BACKEND_PY_PATH = 'my_django.cas_ng_custom.CASBackend'
AUTH0_BACKEND_PY_PATH = 'django_auth0.auth_backend.Auth0Backend'
AUTH0_CUSTOM_BACKEND_PY_PATH = 'custom_auth0.auth_backend.Auth0Backend'

os.environ['MAIL'] = '/var/mail/dbychkov' # FIXME obsolete

CONSOLE_DATE_F = "%d/%b/%Y %H:%M:%S"
# auto-sensing if running on dev or prod, for dynamic environment configuration
# FIXME broken in docker container
FULL_HOST_NAME = socket.gethostname()
HOST_NAME = str.split(FULL_HOST_NAME, '.')[0]

# do not move. here because some utils function useses it
FIMM_NETWORK = '128.214.0.0/16'

from config import *

# Super User on breeze can Access all data
SU_ACCESS_OVERRIDE = True

PROJECT_PATH = PROJECT_FOLDER + BREEZE_FOLDER
if not os.path.isdir(PROJECT_PATH):
	PROJECT_FOLDER = '/%s/' % PROJECT_FOLDER_NAME
PROD_PATH = '%s%s' % (PROJECT_FOLDER, BREEZE_FOLDER)
R_ENGINE_SUB_PATH = 'R/bin/R ' # FIXME LEGACY ONLY
R_ENGINE_PATH = PROD_PATH + R_ENGINE_SUB_PATH
if not os.path.isfile( R_ENGINE_PATH.strip()):
	PROJECT_FOLDER = '/%s/' % PROJECT_FOLDER_NAME
	R_ENGINE_PATH = PROD_PATH + R_ENGINE_SUB_PATH # FIXME Legacy

PROJECT_FHRB_PM_PATH = '/%s/fhrb_pm/' % PROJECT_FOLDER_NAME
JDBC_BRIDGE_PATH = PROJECT_FHRB_PM_PATH + 'bin/start-jdbc-bridge' # Every other path has a trailing /

TEMP_FOLDER = SOURCE_ROOT + 'tmp/'
####
# 'db' folder, containing : reports, scripts, jobs, datasets, pipelines, upload_temp
####
DATA_TEMPLATES_FN = 'mould/'

RE_RUN_SH = SOURCE_ROOT + 're_run.sh'

MEDIA_ROOT = PROJECT_PATH + 'db/'
RORA_LIB = PROJECT_PATH + 'RORALib/'
UPLOAD_FOLDER = MEDIA_ROOT + 'upload_temp/'
DATASETS_FOLDER = MEDIA_ROOT + 'datasets/'
STATIC_ROOT = SOURCE_ROOT + 'static_source/' # static files for the website
DJANGO_CONFIG_FOLDER = SOURCE_ROOT + 'config/' # Where to store secrets and deployment conf
MOULD_FOLDER = MEDIA_ROOT + DATA_TEMPLATES_FN
NO_TAG_XML = TEMPLATE_FOLDER + 'notag.xml'

SH_LOG_FOLDER = '.log'
GENERAL_SH_BASE_NAME = 'run_job'
GENERAL_SH_NAME = '%s.sh' % GENERAL_SH_BASE_NAME
GENERAL_SH_CONF_NAME = '%s_conf.sh' % GENERAL_SH_BASE_NAME
DOCKER_SH_NAME = 'run.sh'

REPORTS_CACHE_INTERNAL_URL = '/cached/reports/'

INCOMPLETE_RUN_FN = '.INCOMPLETE_RUN'
FAILED_FN = '.failed'
SUCCESS_FN = '.done'
R_DONE_FN = '.sub_done'
# ** moved to config/execution/sge.py
# SGE_QUEUE_NAME = 'breeze.q' # monitoring only
# ** moved to config/env/azure_cloud.py
# DOCKER_HUB_PASS_FILE = SOURCE_ROOT + 'docker_repo'
# AZURE_PASS_FILE = SOURCE_ROOT + 'azure_pwd' # moved to config/env/azure_cloud.py

#
# ComputeTarget configs
#
# TODO config
# 13/05/2016
CONFIG_FN = 'configs/'
CONFIG_PATH = MEDIA_ROOT + CONFIG_FN
# 19/04/2016
TARGET_CONFIG_FN = 'target/'
TARGET_CONFIG_PATH = CONFIG_PATH + TARGET_CONFIG_FN
# 08/06/2016
DEFAULT_TARGET_ID = BREEZE_TARGET_ID
# 13/05/2016
EXEC_CONFIG_FN = 'exec/'
EXEC_CONFIG_PATH = CONFIG_PATH + EXEC_CONFIG_FN
# 13/05/2016
ENGINE_CONFIG_FN = 'engine/'
ENGINE_CONFIG_PATH = CONFIG_PATH + ENGINE_CONFIG_FN
# 23/05/2016
SWAP_FN = 'swap/'
SWAP_PATH = MEDIA_ROOT + SWAP_FN
# 21/02/2017
SHINY_SECRET_KEY_FN = 'shiny'
SHINY_SECRET = get_key(SHINY_SECRET_KEY_FN) # Warning : shiny_secret must be at least 32 char long.
ENC_SESSION_ID_COOKIE_NAME = get_md5('seed')


##
# Report config
##
BOOTSTRAP_SH_TEMPLATE = TEMPLATE_FOLDER + GENERAL_SH_NAME
BOOTSTRAP_SH_CONF_TEMPLATE = TEMPLATE_FOLDER + GENERAL_SH_CONF_NAME
DOCKER_BOOTSTRAP_SH_TEMPLATE = TEMPLATE_FOLDER + DOCKER_SH_NAME

NOZZLE_TEMPLATE_FOLDER = TEMPLATE_FOLDER + 'nozzle_templates/'
TAGS_TEMPLATE_PATH = NOZZLE_TEMPLATE_FOLDER + 'tag.R'
NOZZLE_REPORT_TEMPLATE_PATH = NOZZLE_TEMPLATE_FOLDER + 'report.R'
NOZZLE_REPORT_FN = 'report'

RSCRIPTS_FN = 'scripts/'
RSCRIPTS_PATH = MEDIA_ROOT + RSCRIPTS_FN

REPORT_TYPE_FN = 'pipelines/'
REPORT_TYPE_PATH = MEDIA_ROOT + REPORT_TYPE_FN

REPORTS_FN = 'reports/'
REPORTS_PATH = '%s%s' % (MEDIA_ROOT, REPORTS_FN)
REPORTS_SH = GENERAL_SH_NAME
REPORTS_FM_FN = 'transfer_to_fm.txt'

R_FILE_NAME_BASE = 'script'
R_FILE_NAME = R_FILE_NAME_BASE + '.r'
R_OUT_EXT = '.Rout'
##
# Jobs configs
##
SCRIPT_CODE_HEADER_FN = 'header.R'
SCRIPT_HEADER_DEF_CONTENT = '# write your header here...'
SCRIPT_CODE_BODY_FN = 'body.R'
SCRIPT_BODY_DEF_CONTENT = '# copy and paste main code here...'
SCRIPT_FORM_FN = 'form.xml'
SCRIPT_TEMPLATE_FOLDER = TEMPLATE_FOLDER + 'script_templates/'
SCRIPT_TEMPLATE_PATH = SCRIPT_TEMPLATE_FOLDER + 'script.R'
JOBS_FN = 'jobs/'
JOBS_PATH = '%s%s' % (MEDIA_ROOT, JOBS_FN)
JOBS_SH = '_config.sh'

#
# WATCHER RELATED CONFIG
#
# FIXME make this target_config specific
WATCHER_DB_REFRESH = 2 # number of seconds to wait before refreshing reports from DB
WATCHER_PROC_REFRESH = 2 # number of seconds to wait before refreshing processes

#
# SHINY RELATED CONFIG
#
from shiny.settings import * # FIXME obsolete

FOLDERS_LST = [TEMPLATE_FOLDER, SHINY_REPORT_TEMPLATE_PATH, SHINY_REPORTS, SHINY_TAGS,
	NOZZLE_TEMPLATE_FOLDER, SCRIPT_TEMPLATE_FOLDER, JOBS_PATH, REPORT_TYPE_PATH, REPORTS_PATH, RSCRIPTS_PATH, MEDIA_ROOT,
	STATIC_ROOT, TARGET_CONFIG_PATH, EXEC_CONFIG_PATH, ENGINE_CONFIG_PATH]

##
# System Autocheck config
##
# this is used to avoid 504 Gateway time-out from ngnix with is currently set to 600 sec = 10 min
# LONG_POLL_TIME_OUT_REFRESH = 540 # 9 minutes
# set to 50 sec to avoid time-out on breeze.fimm.fi
LONG_POLL_TIME_OUT_REFRESH = 50 # FIXME obsolete
# SGE_MASTER_FILE = '/var/lib/gridengine/default/common/act_qmaster' # FIXME obsolete
# SGE_MASTER_IP = '192.168.67.2' # FIXME obsolete
# DOTM_SERVER_IP = '128.214.64.5' # FIXME obsolete
# RORA_SERVER_IP = '192.168.0.219' # FIXME obsolete
# FILE_SERVER_IP = '192.168.0.107' # FIXME obsolete
SPECIAL_CODE_FOLDER = PROJECT_PATH + 'code/'
FS_SIG_FILE = PROJECT_PATH + 'fs_sig.md5'
FS_LIST_FILE = PROJECT_PATH + 'fs_checksums.json'
FOLDERS_TO_CHECK = [TEMPLATE_FOLDER, SHINY_TAGS, REPORT_TYPE_PATH, # SHINY_REPORTS,SPECIAL_CODE_FOLDER  ,
	RSCRIPTS_PATH, MOULD_FOLDER, STATIC_ROOT, DATASETS_FOLDER]

# STATIC URL MAPPINGS

# STATIC_URL = '/static/'
# MEDIA_URL = '/media/'
MOULD_URL = MEDIA_URL + DATA_TEMPLATES_FN

# number of seconds after witch a job that has not received a sgeid should be marked as aborted or re-run
NO_SGEID_EXPIRY = 30

# FIXME obsolete
TMP_CSC_TAITO_MOUNT = '/mnt/csc-taito/'
TMP_CSC_TAITO_REPORT_PATH = 'breeze/'
TMP_CSC_TAITO_REMOTE_CHROOT = '/homeappl/home/clement/'

# mail config
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_HOST_USER = 'breeze.fimm@gmail.com'
EMAIL_HOST_PASSWORD = get_key('gmail')
EMAIL_PORT = '587'
# EMAIL_SUBJECT_PREFIX = '[' + FULL_HOST_NAME + '] '
EMAIL_SUBJECT_PREFIX = '[' + BREEZE_TITLE + '] '
EMAIL_USE_TLS = True
EMAIL_SENDER = 'Breeze PMS'

#
# END OF CONFIG
# RUN-MODE SPECIFICS FOLLOWING

# ** NO CONFIGURATION CONST BEYOND THIS POINT **
#

# ** moved to config/env/*
# if prod mode then auto disable DEBUG, for safety
# if MODE_PROD or PHARMA_MODE:
# 	SHINY_MODE = 'remote'
# 	SHINY_LOCAL_ENABLE = False
# 	DEBUG = False
# 	VERBOSE = False

# ** DEV logging config moved to config/env/dev.py

# FIXME obsolete
if ENABLE_ROLLBAR:
	try:
		import rollbar
		BASE_DIR = SOURCE_ROOT
		ROLLBAR = {
			'access_token': '00f2bf2c84ce40aa96842622c6ffe97d',
			'environment': 'development' if DEBUG else 'production',
			'root': BASE_DIR,
		}
	
		rollbar.init(**ROLLBAR)
	except Exception:
		ENABLE_ROLLBAR = False
		logging.getLogger().error('Unable to init rollbar')
		pass


def make_run_file():
	f = open('running', 'w+')
	f.write(str(datetime.now().strftime(USUAL_DATE_FORMAT)))
	f.close()

# FIXME obsolete
if os.path.isfile('running'):
	# First time
	print '__breeze__started__'
	logging.info('__breeze__started__')

	os.remove('running')
else:
	make_run_file()
	# Second time
	time.sleep(1)
	print '__breeze__load/reload__'
	logging.info('__breeze__load/reload__')
	print 'source home : ' + SOURCE_ROOT
	logging.debug('source home : ' + SOURCE_ROOT)
	print 'project home : ' + PROJECT_PATH
	logging.debug('project home : ' + PROJECT_PATH)
	print 'Logging on %s\nSettings loaded. Running branch %s, mode %s on %s' % \
		(TermColoring.bold(LOG_PATH), TermColoring.ok_blue(git.get_branch_from_fs(SOURCE_ROOT)), TermColoring.ok_blue(
			TermColoring.bold(RUN_MODE)), TermColoring.ok_blue(FULL_HOST_NAME))
	git_stat = git.get_status()
	print git_stat
	logging.info('Settings loaded. Running %s on %s' % (RUN_MODE, FULL_HOST_NAME))
	logging.info(git_stat)
	from api import code_v1
	code_v1.do_self_git_pull()
	if PHARMA_MODE:
		print TermColoring.bold('RUNNING WITH PHARMA')
print('debug mode is %s' % ('ON' if DEBUG else 'OFF'))


# FIXME obsolete
def project_folder_path(breeze_folder=BREEZE_FOLDER):
	return PROJECT_FOLDER + breeze_folder
