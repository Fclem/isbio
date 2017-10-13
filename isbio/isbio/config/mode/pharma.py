from isbio.config import BREEZE_PROD_FOLDER
TEMPLATE_DEBUG = False
DEBUG = False

# contains everything else (including breeze generated content) than the breeze web source code and static files
PROJECT_FOLDER_PREFIX = ''
BREEZE_FOLDER = '%s-ph2/' % BREEZE_PROD_FOLDER

SHINY_MODE = 'remote'
SHINY_LOCAL_ENABLE = False

ENABLE_NOTEBOOK = False
