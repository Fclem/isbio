from isbio.settings import DomainList
from isbio.config import DEV_MODE
DOMAIN = DomainList.FIMM_CLOUD
# noinspection PyUnresolvedReferences
from base_cloud import *

BREEZE_TITLE = 'C-BREEZE2' + ('-DEV' if DEV_MODE else '')
BREEZE_TITLE_LONG = 'Cloud Breeze2' + (' (dev)' if DEV_MODE else '')

