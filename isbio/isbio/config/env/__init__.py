from utilz import magic_const, MagicAutoConstEnum


# Static object describing available Environments
# noinspection PyMethodParameters,PyPep8Naming
class ConfigEnvironmentsList(MagicAutoConstEnum):
	@magic_const
	def AzureCloud(): pass
	
	@magic_const
	def FIMM(): pass
	
	@magic_const
	def FIMM_cloud(): pass


config_list = ConfigEnvironmentsList()
