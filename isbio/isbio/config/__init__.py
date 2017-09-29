"""
	Clem 15/12/2016
	
	This package provide and interface for multi-level configuration :
	_ run mode : PROD, DEV, PHARMA, ...
	_ run environment : FIMM, Azure_Cloud, ...
	_ execution system configurations : docker, sge, ... (TODO moved this to future exec modules setting class)
	_ auth backends : auth0, CAS, ...
	
	This module provide tools for the automatic configuration to happen
	Breeze settings depends on two files :
	MODE_FILE and ENV_FILE which defines respectively the RUN_MODE and the RUN_ENV modules to load
	(the path to these two file has to be defined there-after, and each file has to contain the name of the associated
	python module)
	Those modules then chain all other settings modules :
		_ mode/* shall only contain configuration relevant to the run mode,
		_ while env/* will import the desired auth/* and exec/* configuration modules
	
"""
# noinspection PyUnresolvedReferences
from isbio.settings import SOURCE_ROOT, TEMPLATE_FOLDER # TODO check if TEMPLATE_FOLDER actually used
# noinspection PyUnresolvedReferences
from utilz import file_content
from django.core.exceptions import ImproperlyConfigured
from conf_enum_generator import ConfigEnumGenerator, GENERATED_FN, GENERATED_MODULE_NAME, conf_gen
import mode
import execution
import env
import env.auth


class BreezeImproperlyConfigured(ImproperlyConfigured):
	pass


class SettingNotDefined(NameError):
	pass


class EmptyMandatorySetting(BreezeImproperlyConfigured):
	pass


class ProgramingError(RuntimeError):
	pass


def auto_conf_from_file(a_name, file_name, object_enum):
	""" check the content of a var file (which shall be one of named object_enum) and return the content if valid """
	file_path = SOURCE_ROOT + file_name
	content = file_content(file_path)
	if not content:
		raise BreezeImproperlyConfigured('%s not specified in %s or file not found' % (a_name, file_path))
	if content not in object_enum:
		raise BreezeImproperlyConfigured('%s "%s" not listed in %s' % (a_name, content, object_enum.__class__.__name__))
	return content


def assert_defined(*args):
	scope = globals().keys()
	for each in args:
		if each not in scope:
			raise SettingNotDefined('setting %s is not defined' % each)
	return True


def assert_filled(*args):
	if assert_defined(*args):
		for each in args:
			if not globals().get(each, None):
				raise EmptyMandatorySetting('setting %s is empty' % each)
	return True


# Static object describing available Auth Backends
ConfigAuthMethods = env.auth.config_list # ConfigAuthMethodsList()

# Static object describing available Environments
ConfigEnvironments = env.config_list # ConfigEnvironmentsList()

# Static object describing available Executions backends
ConfigExec = execution.config_list # ConfigExecList()

# Static object describing available Run Modes
ConfigRunModes = mode.config_list # ConfigRunModesList()


#################################
#  CONFIGURES RUN MODE SETTINGS #
#################################
RUN_MODE = auto_conf_from_file('Run mode', '.run_mode', ConfigRunModes)
RUN_MODE_CLASS = ConfigRunModes.get(RUN_MODE)
DEV_MODE = RUN_MODE == 'dev'
PHARMA_MODE = RUN_MODE == 'pharma' or RUN_MODE == 'pharma_dev'
MODE_PROD = RUN_MODE == 'prod'
#########################################
#  CONFIGURES RUN ENVIRONEMENT SETTINGS #
#########################################
RUN_ENV = auto_conf_from_file('Run env', '.run_env', ConfigEnvironments)
RUN_ENV_CLASS = ConfigEnvironments.get(RUN_ENV)

# TODO
# ## NOW import everything

AUTH_BACKEND = ConfigAuthMethods.undefined
# Commons
PROJECT_FOLDER_NAME = 'projects'
BREEZE_PROD_FOLDER = 'breeze'

# Settings
SET_SHOW_ALL_USERS = True

# checks
assert_filled('TEMPLATE_FOLDER', 'SOURCE_ROOT')

# run mode first

if RUN_MODE_CLASS is ConfigRunModes.prod:
	from mode.prod import *
	MODE_PROD = True
elif RUN_MODE_CLASS is ConfigRunModes.pharma:
	from mode.pharma import *
	PHARMA_MODE = True
elif RUN_MODE_CLASS is ConfigRunModes.dev:
	from mode.dev import *
	DEV_MODE = True
	assert_filled('ENABLE_NOTEBOOK')
elif RUN_MODE_CLASS is ConfigRunModes.pharma_dev:
	from mode.pharma_dev import *
	PHARMA_MODE = True
else: # FIXME debug
	raise ProgramingError('Impossible')

assert_defined('PROJECT_FOLDER_PREFIX')
assert_filled('PROJECT_FOLDER_NAME')
PROJECT_FOLDER = '%s/%s/' % (PROJECT_FOLDER_PREFIX, PROJECT_FOLDER_NAME)
# then environement

# if RUN_ENV == 'AzureCloud':
if RUN_ENV_CLASS is ConfigEnvironments.AzureCloud:
	from env.azure_cloud import *
	# RUN_ENV_CLASS = ConfigEnvironments.AzureCloud
elif RUN_ENV_CLASS is ConfigEnvironments.FIMM: # RUN_ENV == 'FIMM':
	from env.FIMM import *
	# RUN_ENV_CLASS = ConfigEnvironments.FIMM
elif RUN_ENV_CLASS is ConfigEnvironments.FIMM_cloud: # RUN_ENV == 'FIMM_cloud':
	from env.FIMM_cloud import *
	# RUN_ENV_CLASS = ConfigEnvironments.FIMM_cloud
else: # FIXME debug
	raise ProgramingError('Impossible')

assert_filled('BREEZE_FOLDER', 'ALLOWED_HOSTS', 'BREEZE_TITLE', 'BREEZE_TITLE_LONG',
	'AUTHENTICATION_BACKENDS', 'STATICFILES_DIRS', 'DOMAIN')
CURRENT_FQDN = DOMAIN[0]
