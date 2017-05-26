from paramiko.client import SSHClient, MissingHostKeyPolicy
from base64 import b64encode
from utils import Timer
import time
import datetime
# from paramiko.sftp_client import SFTPClient

SERVER = 'breeze.northeurope.cloudapp.azure.com'
REMOTE_KEY = "AAAAB3NzaC1yc2EAAAADAQABAAABAQC/RWm8040HWNOr/B0CfXgr3ZxXZPbwhrpxumvUskut/003gNFAEne2TmZGxAZ1Y4knLM81FfI" \
	"bkxjmMWI+Oz+VQ1hA3XEz0yRPJMFBzchOviF2g0MFMjpADc9ovuILrjpDtD7BzAv40rQRZugLo7Pz6M1JJeL7lFe+hMFVKlglEafAxiG1IlRLtcJ" \
	"JKa5efcvVTBstmXkIHq5N3L1Fb1LQY+GDY/EiZApNlaf++f5UzyyfCCQzcV/J9eWyUxrL2ak1hxnX/404tWvrJSuASr4+gja9ZfjOi9oOhNgoHUR" \
	"f9tWGHjzpepb8I2q6d+mXNJhcPDxNT85DXbin7i1VuCM97"
# clem 08/03/2016 module
# small experiment with paramiko API to execute remote shell command through SSH


# clem 08/03/2016
class CommandOut(object):
	_output = None

	def __init__(self, (stdin, stdout, stderr), command, exec_time):
		self.stdin = stdin
		self.stdout = stdout
		self.stderr = stderr
		self._output = self.stdout.readlines()
		self._err_output = self.stderr.readlines()
		self.time = time.time()
		self._exec_time = exec_time
		self.command = command

	@property
	def show_date_time(self):
		return datetime.datetime.fromtimestamp(self.time).strftime('%Y-%m-%d %H:%M:%S')

	@staticmethod
	def _str_format(tab):
		out = ''
		for e in tab:
			out += '%s%s' % (e, '\n' if not str(e).endswith('\n') else '')
		return out

	@property
	def raw_output(self):
		return self._output

	@property
	def raw_err_output(self):
		return self._err_output

	@property
	def display_output(self):
		return self._str_format(self._output)

	@property
	def display_err_output(self):
		return self._str_format(self._err_output)

	@property
	def exec_time_ms(self):
		return int(self._exec_time * 1000)

	@property
	def output_size(self):
		return self._size(self.raw_output)

	@property
	def err_output_size(self):
		return self._size(self.raw_err_output)

	def _size(self, obj):
		s1 = len(obj)
		s2 = len(self._str_format(obj))
		return "%sL:%s" % (s1, s2) if s1 > 0 else '0'

	def __str__(self):
		return "<CommandOut [%s] '%s' : %s>" % (self.show_date_time, self.command, self.raw_output)

	def __repr__(self):
		return "<CommandOut '%s' : out %s, err %s>" % \
			(self.time, self.output_size, self.err_output_size)


# clem 08/03/2016
class Server(object):
	_server_url = None
	_server_pub_key = None
	_ssh_client = None
	_my_host_key_policy = None
	_cmd_history = list()

	@staticmethod
	def __server_auth(_, hostname, key):
		key = b64encode(str(key))
		if key == REMOTE_KEY:
			return
		raise Exception('Received key for %s, was not the one expected' % hostname)

	def __connect(self):
		assert self._server_pub_key and self._server_url and isinstance(self._my_host_key_policy, MissingHostKeyPolicy)
		client = SSHClient()
		client.set_missing_host_key_policy(self._my_host_key_policy)
		client.connect(self._server_url) # host alias from .ssh/config #
		self._ssh_client = client
		return True

	@property
	def client(self):
		if not self._ssh_client:
			self.__connect()
		return self._ssh_client

	def __init__(self, url, key):
		self._my_host_key_policy = MissingHostKeyPolicy()
		self._my_host_key_policy.missing_host_key = self.__server_auth
		self._server_url = url
		self._server_pub_key = key

	def exec_cmd(self, cmd):
		with Timer() as t:
			a = self.client.exec_command(cmd)
		last = CommandOut(a, cmd, t.interval)
		self._cmd_history.append(last)
		return last

	def print_cmd(self, cmd):
		last = self.exec_cmd(cmd)
		print "read %s in %s ms :\n%s" % (last.output_size, last.exec_time_ms, last.display_output)
		return last

	@property
	def command_history(self):
		return self._cmd_history

	@property
	def las_command(self):
		return self.command_history[-1]

	def __enter__(self):
		self.__connect()

	def __exit__(self, *_):
		self._ssh_client.close()


def main():
	target = Server(SERVER, REMOTE_KEY)
	# md = target.exec_cmd('ls -l')
	return target
