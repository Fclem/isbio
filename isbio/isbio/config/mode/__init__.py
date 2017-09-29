from .. import GENERATED_MODULE_NAME, conf_gen
from utilz import logger
import os

__path__ = os.path.realpath(__file__)
__dir_path__ = os.path.dirname(__path__)

conf_gen(__dir_path__, 'ConfigRunModesList')

try:
	from .generated import config_list
except (SyntaxError, ImportError, Exception) as e:
	logger.error('importing .generated: %s' % e)
	print('importing .generated: %s' % e)
	
try:
	from isbio.config.mode.generated import config_list
except (SyntaxError, ImportError, Exception) as e:
	logger.error('importing isbio.config.mode.generated: %s' % e)
	print('importing isbio.config.mode.generated: %s' % e)
	
try:
	from generated import config_list
except (SyntaxError, ImportError, Exception) as e:
	logger.error('importing generated: %s' % e)
	print('importing generated: %s' % e)
	import importlib
	
	generated = importlib.import_module(GENERATED_MODULE_NAME)
	config_list = generated.config_list
