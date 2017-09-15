from utilz import *
from django.conf import settings as settings

# Django settings for isbio project.
# from configurations import Settings

# override default 404
handler404 = 'api.common.handler404'
settings.handler404 = handler404

API_VERSION = '1.0'
API_SERVE_DEFAULT = 'api.urls_v1'

GIT_HUB_IP_NETWORK = '192.30.252.0/22'
GIT_COMMAND = 'git pull --verify-signatures'
GIT_BASE_PATH = 'refs/heads/%s'
GIT_DEV_BRANCH = 'dev'
GIT_DEV_REF = GIT_BASE_PATH % GIT_DEV_BRANCH
GIT_PROD_BRANCH = 'master'
GIT_PROD_REF = GIT_BASE_PATH % GIT_PROD_BRANCH
GIT_PHARMA_BRANCH = 'pharma'
GIT_PHARMA_REF = GIT_BASE_PATH % GIT_PHARMA_BRANCH
GIT_CURRENT_BRANCH = git.get_branch_from_fs()
GIT_CURRENT_REF = GIT_BASE_PATH % GIT_CURRENT_BRANCH

GIT_REMOTE_NAME = 'origin'
GIT_PULL_FROM = GIT_CURRENT_BRANCH
GIT_AUTO_REF = GIT_CURRENT_REF

API_PULL_COMMAND = '%s %s %s' % (GIT_COMMAND, GIT_REMOTE_NAME, GIT_PULL_FROM)
