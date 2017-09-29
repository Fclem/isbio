from .. import GENERATED_MODULE_NAME, conf_gen
import os

__path__ = os.path.realpath(__file__)
__dir_path__ = os.path.dirname(__path__)

conf_gen(__dir_path__, 'ConfigEnvironmentsList')

try:
	from __generated import config_list
except (SyntaxError, ImportError, Exception):
	import importlib
	generated = importlib.import_module(GENERATED_MODULE_NAME, package='isbio.config.env')
	config_list = generated.config_list
