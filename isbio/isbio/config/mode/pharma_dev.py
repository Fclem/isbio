from isbio.config import BREEZE_PROD_FOLDER

TEMPLATE_DEBUG = False
DEBUG = True

# contains everything else (including breeze generated content) than the breeze web source code and static files
PROJECT_FOLDER_PREFIX = '/fs'
BREEZE_FOLDER = '%s-ph2/' % BREEZE_PROD_FOLDER

SHINY_MODE = 'remote'
SHINY_LOCAL_ENABLE = False

ENABLE_NOTEBOOK = True

import sys
from isbio.settings import USUAL_DATE_FORMAT, USUAL_LOG_FORMAT, LOG_PATH, LOG_HIT_PATH, logging

LOGGING = {
	'version'                 : 1,
	'disable_existing_loggers': False,
	'formatters'              : {
		'verbose'       : {
			'datefmt': USUAL_DATE_FORMAT,
			'format' : USUAL_LOG_FORMAT,
		},
		'standard'      : {
			'format' : USUAL_LOG_FORMAT,
			'datefmt': USUAL_DATE_FORMAT,
		},
		'request_format': {
			'format': '%(remote_addr)s %(username)s "%(request_method)s %(path_info)s %(server_protocol)s" '
			'%(http_user_agent)s %(message)s %(asctime)s',
		},
	},
	'filters'                 : {
		'request'            : {
			'()': 'django_requestlogging.logging_filters.RequestFilter',
		},
		'require_debug_false': {
			'()': 'django.utils.log.RequireDebugFalse'
		}
	},
	'handlers'                : {
		'default'    : {
			'level'      : 'DEBUG',
			'class'      : 'logging.handlers.RotatingFileHandler',
			'filename'   : LOG_PATH,
			'maxBytes'   : 1024 * 1024 * 5, # 5 MB
			'backupCount': 10,
			'formatter'  : 'standard',
		},
		'mail_admins': {
			'level'  : 'ERROR',
			'filters': ['require_debug_false'],
			'class'  : 'django.utils.log.AdminEmailHandler'
		},
		'console'    : {
			'level'    : 'INFO',
			'class'    : 'logging.StreamHandler',
			'stream'   : sys.stdout,
			'formatter': 'verbose',
		},
		'access_log' : {
			'class'      : 'logging.handlers.RotatingFileHandler',
			'filename'   : LOG_HIT_PATH,
			'maxBytes'   : 1024 * 1024 * 10, # 5 MB
			'backupCount': 900,
			'filters'    : ['request'],
			'formatter'  : 'request_format',
		},
	},
	'loggers'                 : {
		'isbio'         : {
			'handlers' : ['console'],
			'level'    : 'DEBUG',
			'propagate': True,
		},
		'breeze'        : {
			'handlers' : ['console', 'access_log'],
			'level'    : 'DEBUG',
			'propagate': True,
		},
		'breeze2'       : {
			'handlers': ['access_log'],
			'filters' : ['request'],
		},
		''              : {
			'handlers' : ['default'],
			'level'    : logging.INFO if not DEBUG else logging.DEBUG,
			'propagate': True
		},
		'django.request': {
			'handlers' : ['mail_admins'],
			'level'    : 'ERROR',
			'propagate': True,
		},
	}
}
import logging.config

logging.config.dictConfig(LOGGING)
