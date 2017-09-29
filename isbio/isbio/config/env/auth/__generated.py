from utilz import magic_const, MagicAutoConstEnum


# Static object describing available Auth Backends
# noinspection PyMethodParameters,PyPep8Naming
class ConfigAuthMethodsList(MagicAutoConstEnum):
	@magic_const
	def CAS_NG(): pass
	
	@magic_const
	def AUTH0(): pass


config_list = ConfigAuthMethodsList()
