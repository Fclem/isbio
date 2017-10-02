from isbio.settings import DomainList
from isbio.config import DEV_MODE
DomainList.selected_domain = DomainList.CLOUD_DEV if DEV_MODE else DomainList.CLOUD_PROD
# noinspection PyUnresolvedReferences
from base_cloud import *

AZURE_PASS_FILE = SOURCE_ROOT + 'azure_pwd' # FIXME unused
BREEZE_TITLE = 'C-BREEZE' + ('-DEV' if DEV_MODE else '')
BREEZE_TITLE_LONG = 'Cloud Breeze' + (' (dev)' if DEV_MODE else '')
