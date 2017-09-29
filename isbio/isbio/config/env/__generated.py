from utilz import magic_const, MagicAutoConstEnum


# Static object describing available Environments
# noinspection PyMethodParameters,PyPep8Naming
class ConfigEnvironmentsList(MagicAutoConstEnum):
	@magic_const
	def AzureCloud(): pass
	
	@magic_const
	def FIMM(): pass


config_list = ConfigEnvironmentsList()
