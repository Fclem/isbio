from breeze.utilities import *
from django.conf import settings as settings
# from isbio.settings import *

# Django settings for isbio project.
# from configurations import Settings

# override default 404
handler404 = 'api.common.handler404'
settings.handler404 = handler404
# settings.settings
# settings.settings.DATABASES['default']['handler404'] = handler404

API_VERSION = '1.0'

GIT_HUB_IP_NETWORK = '192.30.252.0/22'
GIT_COMMAND = 'git pull'
GIT_DEV_BRANCH = 'dev'
GIT_DEV_REF = 'refs/heads/dev'
GIT_PROD_BRANCH = 'master'
GIT_PROD_REF = 'refs/heads/master'

GIT_REMOTE_NAME = 'origin'
GIT_PULL_FROM = GIT_DEV_BRANCH if settings.DEV_MODE else GIT_PROD_BRANCH
GIT_AUTO_REF = GIT_DEV_REF if settings.DEV_MODE else GIT_PROD_REF

API_PULL_COMMAND = '%s %s %s' % (GIT_COMMAND, GIT_REMOTE_NAME, GIT_PULL_FROM)
