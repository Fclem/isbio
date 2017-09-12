from local_storage_module import * # import interface, already has os, sys and abc

__date__ = '04/05/2016'
__version__ = '0.1'
__author__ = 'clem'


# general config
__DEV__ = True
__path__ = os.path.realpath(__file__)
__dir_path__ = os.path.dirname(__path__)
__file_name__ = os.path.basename(__file__)


class ProjectStorage(StorageModule):
	pass


def back_end_initiator(_):
	return ProjectStorage()
