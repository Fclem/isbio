# noinspection PyUnresolvedReferences
from isbio.config.execution.docker import * # !important, do not delete
# noinspection PyUnresolvedReferences
from isbio.settings import DomainList, SOURCE_ROOT
from isbio.config import DEV_MODE, BREEZE_PROD_FOLDER
from auth.auth0 import *

DOMAIN = DomainList.selected_domain
ALLOWED_HOSTS = DOMAIN + AUTH0_IP_LIST
# FIXME : replace with Site.objects.get(pk=0)
AUTH0_CALLBACK_URL = AUTH0_CALLBACK_URL_BASE % DOMAIN[0]

# override the dev config
BREEZE_FOLDER = '%s/' % BREEZE_PROD_FOLDER

# DOCKER_HUB_PASS_FILE = SOURCE_ROOT + 'docker_repo' # Moved to docker config
# override Shiny mode (may be on if run mode is dev)
SHINY_MODE = 'remote'
SHINY_LOCAL_ENABLE = False
BREEZE_TITLE = 'C-BREEZE' + ('-DEV' if DEV_MODE else '')
BREEZE_TITLE_LONG = 'Cloud Breeze' + (' (dev)' if DEV_MODE else '')

STATICFILES_DIRS = (
	# Put strings here, like "/home/html/static" or "C:/www/django/static".
	# Always use forward slashes, even on Windows.
	# Don't forget to use absolute paths, not relative paths.
	"/root/static_source",
)

SET_SHOW_ALL_USERS = False

AUTH_ALLOW_GUEST = True

BREEZE_TARGET_ID = 1
