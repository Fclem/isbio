from isbio.settings import DomainList
from isbio.config import DEV_MODE
DomainList.selected_domain = DomainList.FIMM_CLOUD
# noinspection PyUnresolvedReferences
from base_cloud import *

ALLOWED_HOSTS += ['192.168.4.135']
BREEZE_TITLE = 'C-BREEZE2' + ('-DEV' if DEV_MODE else '')
BREEZE_TITLE_LONG = 'Cloud Breeze2' + (' (dev)' if DEV_MODE else '')

