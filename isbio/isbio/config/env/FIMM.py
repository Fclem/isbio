from isbio.config.execution.sge import * # !important, do not delete
from isbio.config.execution.docker import * # !important, do not delete
from isbio.settings import DomainList
from isbio.config import PROJECT_FOLDER, DEV_MODE, PHARMA_MODE
DOMAIN = DomainList.FIMM_DEV if DEV_MODE else DomainList.FIMM_PH if PHARMA_MODE else DomainList.FIMM_PROD
from auth.CAS import *

ALLOWED_HOSTS = DOMAIN + [CAS_SERVER_IP, '192.168.4.135']

BREEZE_TITLE = 'BREEZE-PH'
BREEZE_TITLE_LONG = 'Breeze Pharma'

if not PHARMA_MODE:
	BREEZE_TITLE = 'BREEZE' + ('-DEV' if DEV_MODE else '')
	BREEZE_TITLE_LONG = 'Cloud Breeze' + (' (dev)' if DEV_MODE else '')
else:
	BREEZE_TITLE = 'BREEZE-PH'
	BREEZE_TITLE_LONG = 'Breeze Pharma'

STATICFILES_DIRS = (
	# Put strings here, like "/home/html/static" or "C:/www/django/static".
	# Always use forward slashes, even on Windows.
	# Don't forget to use absolute paths, not relative paths.
	"%s/static_source" % PROJECT_FOLDER,
)

BREEZE_TARGET_ID = 3
