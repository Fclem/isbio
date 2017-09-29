from utilz import magic_const, MagicAutoConstEnum

# __all__ = ['config_list']
# modules = 'dev pharma prod'


# Static object describing available Run Modes
# noinspection PyMethodParameters
class ConfigRunModesList(MagicAutoConstEnum):
	@magic_const
	def dev(): pass
	
	@magic_const
	def prod(): pass
	
	@magic_const
	def pharma(): pass

	@magic_const
	def pharma_dev(): pass


config_list = ConfigRunModesList()
