from isbio.settings import DomainList
from isbio.config import DEV_MODE
DOMAIN = DomainList.CLOUD_DEV if DEV_MODE else DomainList.CLOUD_PROD
# noinspection PyUnresolvedReferences
from base_cloud import *

AZURE_PASS_FILE = SOURCE_ROOT + 'azure_pwd' # FIXME unused
