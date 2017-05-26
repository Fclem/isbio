class Trans(object):
	"""
	Translate property names for Jobs and Reports to a unified model.
	Used in manager to access similar properties from both Jobs and Reports using the same name
	"""

	def __init__(self, *args, **kwargs):
		self._translate(*args, **kwargs)

	translation = {
		'name': '_name', 'jname': '_name',
		'description': '_description', 'jdetails': '_description',
		'author': '_author', 'juser': '_author',
		'type': '_type', 'script': '_type',
		'created': '_created', 'staged': '_created',
		'breeze_stat': '_breeze_stat', 'status': '_status',
		'rexec': '_rexec', 'rexecut': '_rexec',
		'dochtml': '_doc_ml', 'docxml': '_doc_ml', 'doc_ml': '_doc_ml',
		'institute': '_institute',
	}

	@staticmethod
	def swap(item):
		a = Trans.has(item)
		if a is not None:
			return a
		return item

	@staticmethod
	def has(item):
		if isinstance(item, str) and item != '':
			text = item
			if text.endswith('_id'): # for ForeignKeys
				text = text[:-3]
			for key in Trans.translation.keys():
				if text.startswith(key) or text.startswith('-' + key):
					item = item.replace(key, Trans.translation[key])
					return item
		return None

	def _translate(self, args, kwargs):
		new_arg = list(args)
		for pos, el in enumerate(new_arg):
			new_key = self.has(el)
			if new_key is not None:
				new_arg[pos] = new_key
		new_arg = tuple(new_arg)

		for key in kwargs.keys():
			new_key = self.has(key)
			if new_key is not None:
				kwargs[new_key] = kwargs[key]
				del kwargs[key]
		self.args, self.kwargs = new_arg, kwargs

	def get(self):
		return self.args, self.kwargs


def translate(args, kwargs):
	return Trans(args, kwargs).get()
