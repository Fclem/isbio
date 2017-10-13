from isbio.settings import DomainList, PROJECT_FOLDER
from isbio.config import DEV_MODE
DomainList.selected_domain = DomainList.FIMM_CLOUD
# noinspection PyUnresolvedReferences
from base_cloud import *

ALLOWED_HOSTS += ['192.168.4.135', 'breeze-cloud.fimm.fi']
BREEZE_TITLE = 'C-BREEZE2' + ('-DEV' if DEV_MODE else '')
BREEZE_TITLE_LONG = 'Cloud Breeze2' + (' (dev)' if DEV_MODE else '')

STORAGE_FOLDER_NAME = 'storage'
STORAGE_FOLDER = '%s%s/' % (PROJECT_FOLDER, STORAGE_FOLDER_NAME)
STORAGE_PLACE = '%s/' % STORAGE_FOLDER_NAME

