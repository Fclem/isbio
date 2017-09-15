import sys

IS_PY2 = sys.version_info.major == 2
IS_PY3 = sys.version_info.major == 3
if IS_PY3:
	# noinspection PyShadowingBuiltins
	str = bytes
	# noinspection PyShadowingBuiltins
	basestring = str
	# noinspection PyShadowingBuiltins
	unicode = str
if IS_PY2:
	try:
		# noinspection PyShadowingBuiltins,PyUnboundLocalVariable
		unicode = unicode
		# noinspection PyShadowingBuiltins,PyUnboundLocalVariable
		basestring = basestring
		# noinspection PyShadowingBuiltins,PyUnboundLocalVariable
		str = str
	finally:
		pass
