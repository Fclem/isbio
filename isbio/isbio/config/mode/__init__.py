from .. import GENERATED_MODULE_NAME, conf_gen
from utilz import logger
import os

__path__ = os.path.realpath(__file__)
__dir_path__ = os.path.dirname(__path__)

conf_gen(__dir_path__, 'ConfigRunModesList')

try:
	from __generated import config_list
except (SyntaxError, ImportError, Exception) as e:
	logger.error('importing __generated: %s' % e)
	print('importing __generated: %s' % e)
	import importlib
	
	generated = importlib.import_module(GENERATED_MODULE_NAME, package='isbio.config.mode')
	config_list = generated.config_list
