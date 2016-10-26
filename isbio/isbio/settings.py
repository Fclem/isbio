# Django settings for isbio project.
# from configurations import Settings
import logging
import os
import socket
import time
from datetime import datetime
from utilz import git, TermColoring, recur, recur_rec, get_key, import_env, file_content

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

DATABASES = {
	'default': {
		'ENGINE'  : 'django.db.backends.mysql', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
		'NAME'    : 'breezedb', # Or path to database file if using sqlite3.
		'USER'    : 'root', # Not used with sqlite3.
		'PASSWORD': get_key(MYSQL_SECRET_FILE), # Not used with sqlite3.
		'HOST'    : 'breeze-sql', # Set to empty string for localhost. Not used with sqlite3.
		'PORT'    : '3306', # Set to empty string for default. Not used with sqlite3.
		'OPTIONS' : {
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
				'django.core.context_processors.media',
				'django.core.context_processors.static',
				'breeze.context.user_context',
				'breeze.context.date_context',
				'django_auth0.context_processors.auth0',
				# "breeze.context.site",
			],
		},
	},
]


# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'Europe/Helsinki'

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
# STATIC_ROOT = ''

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
	# "/home/comrade/Projects/fimm/isbio/breeze/",
	# Put strings here, like "/home/html/static" or "C:/www/django/static".
	# Always use forward slashes, even on Windows.
	# Don't forget to use absolute paths, not relative paths.
	"/root/code/static_source",
)

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

AUTH_USER_MODEL = 'auth.User'
AUTH_USER_MODEL = 'breeze.models.OrderedUser'

INSTALLED_APPS = [
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
	'django_auth0',
	'hello_auth.apps.Config',
	'api.apps.Config',
	'webhooks.apps.Config',
	'utilz.apps.Config',
	'django_requestlogging',
	# Uncomment the next line to enable admin documentation:
	'django.contrib.admindocs',
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
	'django_requestlogging.middleware.LogSetupMiddleware',
	'breeze.middlewares.DataDog' if ENABLE_DATADOG else 'breeze.middlewares.Empty',
	'breeze.middlewares.RemoteFW' if ENABLE_REMOTE_FW else 'breeze.middlewares.Empty',
	'rollbar.contrib.django.middleware.RollbarNotifierMiddleware' if ENABLE_ROLLBAR else 'breeze.middlewares.Empty',
]

AUTHENTICATION_BACKENDS = (
	'django.contrib.auth.backends.ModelBackend',
	'django_auth0.auth_backend.Auth0Backend',
)

AUTH0_DOMAIN = 'breeze.eu.auth0.com'
AUTH0_TEST_URL = 'https://%s/test' % AUTH0_DOMAIN
AUTH0_ID_FILE_N = 'auth0_id'
AUTH0_CLIENT_ID = get_key(AUTH0_ID_FILE_N)
AUTH0_SECRET_FILE_N = 'auth0'
AUTH0_SECRET = get_key(AUTH0_SECRET_FILE_N)
# AUTH0_CALLBACK_URL = 'https://breeze-www.cloudapp.net/login/'
AUTH0_CALLBACK_URL = 'https://breeze.fimm.fi/login/'
AUTH0_SUCCESS_URL = '/home/'
AUTH0_LOGOUT_URL = 'https://breeze.eu.auth0.com/v2/logout'
AUTH0_LOGOUT_REDIRECT = 'https://www.fimm.fi'

SSH_TUNNEL_HOST = 'breeze-ssh'
SSH_TUNNEL_PORT = '2222'
# SSH_TUNNEL_TEST_URL = 'breeze-ssh'

# ROOT_URLCONF = 'isbio.urls'
APPEND_SLASH = True

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'isbio.wsgi.application'

# provide our profile model
AUTH_PROFILE_MODULE = 'breeze.UserProfile'

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

AUTH0_IP_LIST = ['52.169.124.164', '52.164.211.188', '52.28.56.226', '52.28.45.240', '52.16.224.164', '52.16.193.66']
ALLOWED_HOSTS = ['web-breeze.fimm.fi', 'breeze.fimm.fi'] + AUTH0_IP_LIST

DEBUG = True
VERBOSE = False
SQL_DUMP = False
# APPEND_SLASH = True

ADMINS = (
	('Clement FIERE', 'clement.fiere@helsinki.fi'),
)

# root of the Breeze django project folder, includes 'venv', 'static' folder copy, isbio, logs
SOURCE_ROOT = recur(3, os.path.dirname, os.path.realpath(__file__)) + '/'
DJANGO_ROOT = recur(2, os.path.dirname, os.path.realpath(__file__)) + '/'

# MANAGERS = ADMINS

# import_env()

Q_BIN = ''
QSTAT_BIN = ''
QDEL_BIN = ''
SGE_QUEUE = ''
os.environ['MAIL'] = '/var/mail/dbychkov' # FIXME obsolete

CONSOLE_DATE_F = "%d/%b/%Y %H:%M:%S"
# auto-sensing if running on dev or prod, for dynamic environment configuration
FULL_HOST_NAME = socket.gethostname()
HOST_NAME = str.split(FULL_HOST_NAME, '.')[0]
# automatically setting RUN_MODE depending on the host name
MODE_FILE = SOURCE_ROOT + '.run_mode'
MODE_FILE_CONTENT = file_content(MODE_FILE)
RUN_MODE = 'dev' if MODE_FILE_CONTENT == 'dev' else 'prod'
DEV_MODE = RUN_MODE == 'dev'
MODE_PROD = RUN_MODE == 'prod'
PHARMA_MODE = False

# Super User on breeze can Access all data
SU_ACCESS_OVERRIDE = True

# contains everything else (including breeze generated content) than the breeze web source code and static files
PROJECT_FOLDER_NAME = 'projects'
# PROJECT_FOLDER_PREFIX = '/fs'
PROJECT_FOLDER_PREFIX = ''
PROJECT_FOLDER = '%s/%s/' % (PROJECT_FOLDER_PREFIX, PROJECT_FOLDER_NAME)
BREEZE_PROD_FOLDER = 'breeze'
# BREEZE_DEV_FOLDER = '%s-dev' % BREEZE_PROD_FOLDER
# BREEZE_FOLDER = '%s/' % BREEZE_DEV_FOLDER if DEV_MODE else BREEZE_PROD_FOLDER
BREEZE_FOLDER = '%s/' % BREEZE_PROD_FOLDER

PROJECT_PATH = PROJECT_FOLDER + BREEZE_FOLDER
if not os.path.isdir(PROJECT_PATH):
	PROJECT_FOLDER = '/%s/' % PROJECT_FOLDER_NAME
PROD_PATH = '%s%s/' % (PROJECT_FOLDER, BREEZE_PROD_FOLDER)
R_ENGINE_SUB_PATH = 'R/bin/R ' # FIXME LEGACY ONLY
R_ENGINE_PATH = PROD_PATH + R_ENGINE_SUB_PATH
if not os.path.isfile( R_ENGINE_PATH.strip()):
	PROJECT_FOLDER = '/%s/' % PROJECT_FOLDER_NAME
	PROJECT_PATH = PROJECT_FOLDER + BREEZE_FOLDER
	R_ENGINE_PATH = PROD_PATH + R_ENGINE_SUB_PATH # FIXME Legacy

PROJECT_PATH = PROJECT_PATH + '/' if not PROJECT_PATH.endswith('/') else PROD_PATH

PROJECT_FHRB_PM_PATH = '/%s/fhrb_pm/' % PROJECT_FOLDER_NAME
JDBC_BRIDGE_PATH = PROJECT_FHRB_PM_PATH + 'bin/start-jdbc-bridge' # Every other path has a trailing /

TEMP_FOLDER = SOURCE_ROOT + 'tmp/' # /homes/dbychkov/dev/isbio/tmp/
####
# 'db' folder, containing : reports, scripts, jobs, datasets, pipelines, upload_temp
####
DATA_TEMPLATES_FN = 'mould/'

RE_RUN_SH = SOURCE_ROOT + 're_run.sh'

MEDIA_ROOT = PROJECT_PATH + 'db/'  # '/project/breeze[-dev]/db/'
RORA_LIB = PROJECT_PATH + 'RORALib/'
UPLOAD_FOLDER = MEDIA_ROOT + 'upload_temp/'
DATASETS_FOLDER = MEDIA_ROOT + 'datasets/'
STATIC_ROOT = SOURCE_ROOT + 'static_source/' # static files for the website
DJANGO_CONFIG_FOLDER = SOURCE_ROOT + 'config/' # Where to store secrets and deployment conf
TEMPLATE_FOLDER = DJANGO_ROOT + 'templates/' # source templates (not HTML ones)
MOULD_FOLDER = MEDIA_ROOT + DATA_TEMPLATES_FN
NO_TAG_XML = TEMPLATE_FOLDER + 'notag.xml'

SH_LOG_FOLDER = '.log'
GENERAL_SH_BASE_NAME = 'run_job'
GENERAL_SH_NAME = '%s.sh' % GENERAL_SH_BASE_NAME
GENERAL_SH_CONF_NAME = '%s_conf.sh' % GENERAL_SH_BASE_NAME
DOCKER_SH_NAME = 'run.sh'
SGE_REQUEST_FN = '.sge_request'
INCOMPLETE_RUN_FN = '.INCOMPLETE_RUN'
FAILED_FN = '.failed'
SUCCESS_FN = '.done'
R_DONE_FN = '.sub_done'
# SGE_QUEUE_NAME = 'breeze.q' # monitoring only
DOCKER_HUB_PASS_FILE = SOURCE_ROOT + 'docker_repo'
AZURE_PASS_FILE = SOURCE_ROOT + 'azure_pwd'

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
ALLQ_TARGET_ID = 2
BREEZE_TARGET_ID = 1
DEFAULT_TARGET_ID = ALLQ_TARGET_ID
# 13/05/2016
EXEC_CONFIG_FN = 'exec/'
EXEC_CONFIG_PATH = CONFIG_PATH + EXEC_CONFIG_FN
# 13/05/2016
ENGINE_CONFIG_FN = 'engine/'
ENGINE_CONFIG_PATH = CONFIG_PATH + ENGINE_CONFIG_FN
# 23/05/2016
SWAP_FN = 'swap/'
SWAP_PATH = MEDIA_ROOT + SWAP_FN

##
# Report config
##
BOOTSTRAP_SH_TEMPLATE = TEMPLATE_FOLDER + GENERAL_SH_NAME
BOOTSTRAP_SH_CONF_TEMPLATE = TEMPLATE_FOLDER + GENERAL_SH_CONF_NAME
DOCKER_BOOTSTRAP_SH_TEMPLATE = TEMPLATE_FOLDER + DOCKER_SH_NAME
SGE_REQUEST_TEMPLATE = TEMPLATE_FOLDER + SGE_REQUEST_FN

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
WATCHER_DB_REFRESH = 2 # number of seconds to wait before refreshing reports from DB
WATCHER_PROC_REFRESH = 2 # number of seconds to wait before refreshing processes

#
# SHINY RELATED CONFIG
#
from shiny.settings import *

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
SGE_MASTER_FILE = '/var/lib/gridengine/default/common/act_qmaster' # FIXME obsolete
SGE_MASTER_IP = '192.168.67.2' # FIXME obsolete
DOTM_SERVER_IP = '128.214.64.5' # FIXME obsolete
RORA_SERVER_IP = '192.168.0.219' # FIXME obsolete
FILE_SERVER_IP = '192.168.0.107' # FIXME obsolete
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

TMP_CSC_TAITO_MOUNT = '/mnt/csc-taito/'
TMP_CSC_TAITO_REPORT_PATH = 'breeze/'
TMP_CSC_TAITO_REMOTE_CHROOT = '/homeappl/home/clement/'

# mail config
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_HOST_USER = 'breeze.fimm@gmail.com'
EMAIL_HOST_PASSWORD = 'mult24mult24'
EMAIL_PORT = '587'
EMAIL_SUBJECT_PREFIX = '[' + FULL_HOST_NAME + '] '
EMAIL_USE_TLS = True

#
# END OF CONFIG
# RUN-MODE SPECIFICS FOLLOWING

# ** NO CONFIGURATION CONST BEYOND THIS POINT **
#

# if prod mode then auto disable DEBUG, for safety
if MODE_PROD:
	SHINY_MODE = 'remote'
	SHINY_LOCAL_ENABLE = False
	DEBUG = False
	VERBOSE = False

if DEBUG:
	import sys
	LOGGING = {
		'version': 1,
		'disable_existing_loggers': False,
		'formatters': {
			'verbose': {
				'datefmt': USUAL_DATE_FORMAT,
				'format': USUAL_LOG_FORMAT,
			},
			'standard': {
				'format': USUAL_LOG_FORMAT,
				'datefmt': USUAL_DATE_FORMAT,
			},
			'request_format': {
				'format': '%(remote_addr)s %(username)s "%(request_method)s '
				'%(path_info)s %(server_protocol)s" %(http_user_agent)s '
				'%(message)s %(asctime)s',
			},
		},
		'filters': {
			'request': {
				'()': 'django_requestlogging.logging_filters.RequestFilter',
			},
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
			'console': {
				'level': 'INFO',
				'class': 'logging.StreamHandler',
				'stream': sys.stdout,
				'formatter': 'verbose',
			},
			'access_log': {
				'class': 'logging.handlers.RotatingFileHandler',
				'filename': LOG_HIT_PATH,
				'maxBytes': 1024 * 1024 * 10, # 5 MB
				'backupCount': 900,
				'filters': ['request'],
				'formatter': 'request_format',
			},
		},
		'loggers': {
			'isbio': {
				'handlers': ['console'],
				'level': 'DEBUG',
				'propagate': True,
			},
			'breeze': {
				'handlers': ['console', 'access_log'],
				'level': 'DEBUG',
				'propagate': True,
			},
			'breeze2': {
				'handlers': ['access_log'],
				'filters': ['request'],
			},
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
	import logging.config
	logging.config.dictConfig(LOGGING)
else:
	VERBOSE = False

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
# FIXME obsolete
if SHINY_MODE == 'remote':
	SHINY_TARGET_URL = SHINY_REMOTE_TARGET_URL
	SHINY_LIBS_TARGET_URL = SHINY_REMOTE_LIBS_TARGET_URL
	SHINY_LIBS_BREEZE_URL = SHINY_REMOTE_LIBS_BREEZE_URL
else:
	SHINY_TARGET_URL = SHINY_LOCAL_TARGET_URL
	SHINY_LIBS_TARGET_URL = SHINY_LOCAL_LIBS_TARGET_URL
	SHINY_LIBS_BREEZE_URL = SHINY_LOCAL_LIBS_BREEZE_URL


def make_run_file():
	f = open('running', 'w+')
	f.write(str(datetime.now().strftime(USUAL_DATE_FORMAT)))
	f.close()

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
print('debug mode is %s' % ('ON' if DEBUG else 'OFF'))


def project_folder_path(breeze_folder=BREEZE_FOLDER):
	return PROJECT_FOLDER + breeze_folder
