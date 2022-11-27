import logging
import js
import os
import asyncio
import traceback
from pyodide import create_proxy
#from octopwn.common.screenhandler import ScreenHandlerBase


octopwnApp = None # Do not remove this!
octopwnExtra = None

class Dummy:
	def __init__(self):
		self.completer = None

class ExtraOperations:
	"""JS can't reach async functions directly, must be wrapped in a class.."""
	def __init__(self, octopwn):
		self.octopwn = octopwn
		self.pypykatz_cli = None

	async def localFileCreated(self, fpath):
		"""This function will be called each time a new file is uploaded to the browserFS"""
		#print('Python: newfile: %s' % fpath)
		ftype= None
		if fpath.lower().endswith('.dmp') or fpath.lower().endswith('.DMP'):
			ftype = 'dmp'
		if fpath.lower().endswith('.dit') or fpath.lower().endswith('.DIT'):
			ftype = 'dit'
		if fpath.lower().endswith('.reg') or fpath.lower().endswith('.reg'):
			ftype = 'reg'
		
		
		if ftype is not None and self.pypykatz_cli is None:
			for cli in self.octopwn.clients:
				config, client = self.octopwn.clients[cli]
				if config is None:
					continue
				if config.config_type == 'UTILS' and config.scanner_type == 'PYPYKATZ':
					self.pypykatz_cli = client
		
		if ftype == 'dmp':
			await client.do_lsass(fpath)


def createRegFileBrowser(filename):
	from octopwn.utils.extras.reghelper import RegHelper
	res = RegHelper(filename)
	return res


def gettb4exc(exc):
	# helping javascript to get the string representation of the traceback 
	# when a python exception happens
	if exc is None:
		return 'No additional info'
	return '\r\n'.join(traceback.format_tb(exc.__traceback__))

def criticalexception(msg, e = None):
	excstr = msg
	exctrace = 'There is no turning back now, please reload this browser tab.\r\n If you have any files stored in browserfs/volatile you might want to back them up!'
	if e is not None:
		exctrace += str(e) + '\r\n'
		exctrace += gettb4exc(e)
	js.showPythonError([excstr, exctrace], msg)



class RemoteComms:
	"""
	This class is here to emulate a python websockets connection over the javascript websockets interface
	"""
	def __init__(self, url):
		self.url = url
		self.internal_in_q = asyncio.Queue()
		self.in_q = asyncio.Queue()
		self.ws_open = asyncio.Event()
		self.ws_closed = asyncio.Event()
		self.connection_id = None
		self._open = False
		self.__read_task = None
		self.__monitor_task = None
	
	@property
	def open(self):
		if self.ws_open.is_set() and not self.ws_closed.is_set():
			return True
		return False

	def close(self):
		self.ws_closed.set()
		if self.__read_task is not None:
			self.__read_task.cancel()
		if self.__monitor_task is not None:
			self.__monitor_task.cancel()
		
		return
	
	async def send(self, data):
		js.sendWebSocketData(self.connection_id, data)
	
	async def recv(self):
		return await self.in_q.get()

	async def __reader(self):
		try:
			try:
				await asyncio.wait_for(self.ws_open.wait(), timeout=10)
			except asyncio.TimeoutError:
				criticalexception("Connection to server timed out!")
				return
			except Exception as e:
				raise e

			while self.open:
				data_memview = await self.internal_in_q.get()
				await self.in_q.put(data_memview.to_py())
		except Exception as e:
			traceback.print_exc()
		finally:
			await self.close()

	async def __connection_status_monitor(self):
		try:
			await self.ws_closed.wait()
			criticalexception("Server closed the connection")	
		except:
			pass
		finally:
			await self.close()

	async def run(self):
		try:
			self.connection_id = js.createNewWebSocket(
				self.url, 
				create_proxy(self.ws_open), 
				create_proxy(self.internal_in_q), 
				create_proxy(self.ws_closed), 
				False, 
			)
			self.__read_task = asyncio.create_task(self.__reader())
			self.__monitor_task = asyncio.create_task(self.__connection_status_monitor())
			await asyncio.wait_for(self.ws_open.wait(), timeout=10)
			return True, None
		except Exception as e:
			return None, e


class ScreenHandlerGoldenLayout:
	def __init__(self, remoting_support = False):
		self.multi_window_support = True
		self.octopwn = None
		self.targetstable_id = 'targetTable'
		self.proxytable_id = 'proxyTable'
		self.credentialtable_id = 'credentialTable'
		self.clienttable_id = 'clientTable'
		self.consoleoutput_base_id = 'consoleoutput-%s'
		self.input_handler = None
		self.credrefresh_task = None
		self.targetrefresh_task = None
		#this is to be removed...
		self.input_area = Dummy()

		self.remoting_support = remoting_support
	
	async def print_client_msg(self, clientid:int, msg:str, username = None):
		try:
			#print('print_client_msg %s %s' % (clientid, msg))
			window = js.document.getElementById(self.consoleoutput_base_id % clientid)
			if username is not None and username != '':
				msg = '[%s] %s\n' % (username, msg)
			else:
				msg = '%s\n' % msg
			window.innerHTML += msg
			window.scrollTop = window.scrollHeight
			if clientid != 0:
				js.signalClientMessage(clientid+1)
			
			return True, None
		except Exception as e:
			return None, e

	async def print_main_window(self, msg, username= None):
		await self.print_client_msg(0, msg, username=username)

	async def clear_main_window(self):
		window = js.document.getElementById(self.consoleoutput_base_id % '0')
		window.innerHTML = ''
	
	async def client_added(self, cid, client):
		# the create_client_window does everything for us
		return True, None

	async def refresh_clients(self):
		js.ClearDataTable('#' + self.clienttable_id)
		js.AddDataTableEntryP4(
			'#' + self.clienttable_id,
			'0',
			'MAIN',
			'MAIN CONSOLE',
			'',
		)
		js.AddDataTableEntryP4(
			'#' + self.clienttable_id,
			'-1',
			'PYTHON',
			'Python interpreter',
			'',
		)

		for cid in self.octopwn.clients:
			clientsettings, client = self.octopwn.clients[cid]
			if clientsettings is None:
				continue
			js.AddDataTableEntryP4(
				'#' + self.clienttable_id,
				str(cid),
				str(clientsettings.clientname),
				str(clientsettings.description) if clientsettings.description is not None else '',
				'',
			)

		return True, None
	
	async def target_added(self, tid, target):
		"""Called when a new target has been added"""
		try:
			if target.hidden is True:
				return
			js.AddDataTableEntryP6(
				'#' + self.targetstable_id, 
				str(tid), 
				str(target.to_compact()), 
				str(target.dcip), 
				str(target.realm),
				str(target.description) if target.description is not None else '',
				str(target.to_line())
			)
			return True, None
		except Exception as e:
			print(e)
			return None, e

	async def __refresh_targets(self, force = False):
		await asyncio.sleep(1)
		if force is False:
			js.RefreshDataTable('#' + self.targetstable_id)
		else:
			js.ClearDataTable('#' + self.targetstable_id)
			for tid in self.octopwn.targets:
				await self.target_added(tid, self.octopwn.targets[tid])
			js.RefreshDataTable('#' + self.targetstable_id)
		self.targetrefresh_task = None

	async def refresh_targets(self, force=False):
		try:
			if self.targetrefresh_task is None:
				self.targetrefresh_task = asyncio.create_task(self.__refresh_targets(force))	
			return True, None
		except Exception as e:
			print(e)
			return None, e

	async def refresh_proxies(self):
		try:
			js.ClearDataTable('#' + self.proxytable_id)
			for tid in self.octopwn.proxies:
				await self.proxy_added(tid, self.octopwn.proxies[tid])
			return True, None
		except Exception as e:
			print(e)
			return None, e
	
	async def proxy_added(self, pid, proxy):
		"""Add a proxy entry to the proxies window"""
		try:
			if proxy.ptype != 'CHAIN':
				js.AddDataTableEntryP5(
					'#' + self.proxytable_id, 
					str(pid), 
					str(proxy.ip) + ':' + str(proxy.port), 
					str(proxy.ptype),
					str(proxy.description) if proxy.description is not None else '',
					str(proxy.to_line())
				)
			else:
				js.AddDataTableEntryP5(
					'#' + self.proxytable_id, 
					str(pid), 
					str(','.join([str(x) for x in proxy.chain])),
					str(proxy.ptype),
					str(proxy.description) if proxy.description is not None else '',
					str(proxy.to_line())
				)
			
			return True, None
		except Exception as e:
			traceback.print_exc()
			return None, e

	async def __refresh_creds(self):
		await asyncio.sleep(1)
		js.ClearDataTable('#' + self.credentialtable_id)
		for tid in self.octopwn.credentials:
			await self.credential_added(tid, self.octopwn.credentials[tid])
		js.RefreshDataTable('#' + self.credentialtable_id)
		self.credrefresh_task = None

	async def refresh_credentials(self):
		try:
			if self.credrefresh_task is None:
				self.credrefresh_task = asyncio.create_task(self.__refresh_creds())	
			return True, None
		except Exception as e:
			return None, e

	async def credential_added(self, cid, credential):
		try:
			if credential.hidden is True:
				return
			js.AddDataTableEntryP8(
				'#' + self.credentialtable_id,
				str(cid),
				str(credential.to_line()),
				str(credential.domain),
				str(credential.username),
				str(credential.secret),
				str(credential.stype),
				str(credential.description) if credential.description is not None else '',
				str(credential.to_line(truncate=False))
			)
			return True, None
		except Exception as e:
			print(e)
			return None, e

	async def set_input_dialog_title(self, clientid, title):
		return
	
	async def set_message_dialog_title(self, clientid:int, title:str):
		return
	
	def abort(self, event = None):
		return
	
	async def create_client_window(self, clientid:int, cliname:str, client_settings, client):
		try:
			cproxy = create_proxy(client)
			if client is None:
				cproxy = None
			if client_settings is None:
				js.addNewClientWindow(
					int(clientid), 
					'????',
					'', 
					cproxy
				)
			else:
				js.addNewClientWindow(
					int(clientid), 
					client_settings.clientname,
					str(client_settings.description) if client_settings.description is not None else '', 
					cproxy
				)
			return True, None
		except Exception as e:
			print(e)
			return False, e
	
	async def create_rdp_canvas(self, client_id, cliname, width, height, mouse_cb, keyboard_cb, paste_cb):
		try:
			js.addNewRDPCanvasWindow(str(client_id), str(cliname), str(width), str(height), mouse_cb, keyboard_cb, paste_cb)
			return True, None
		except Exception as e:
			return None, e
	
	async def update_rdp_canvas(self, client_id, image, x, y, width, height):
		try:
			js.updateRDPCanvas(client_id, image, x, y, width, height)
			return True, None
		except Exception as e:
			print(e)
			return None, e

	async def create_graph_canvas(self, client_id, graphid, path_calc_cb, node_set_cb, node_search_cb):
		try:
			js.addNewGraphCanvasWindow(str(client_id), str(graphid), path_calc_cb, node_set_cb, node_search_cb)
			return True, None
		except Exception as e:
			return None, e

	async def update_graph_canvas(self, client_id, graphid, graphdata_json):
		try:
			js.updateGraphCanvas(str(client_id), str(graphid), graphdata_json)
			return True, None
		except Exception as e:
			return None, e

	async def runtask(self):
		while True:
			await asyncio.sleep(1000)
			
	async def run(self, octopwn, input_handler = None):
		self.octopwn = octopwn
		self.input_handler = input_handler
		return asyncio.create_task(self.runtask()), None

async def start():
	try:
		global octopwnApp
		global octopwnExtra
		# setting the current directory
		os.chdir("/volatile/")
		
		# mode of operation switch. This looks a bit dumb here, but later down the line
		# this will be extended with other features
		MOO = js.getOctoPwnModeOfOperation()
		if MOO == 'OFFLINE':
			remote = False
		elif MOO == 'STANDALONE':
			remote = False
		elif MOO == 'REMOTE':
			remote = True

		screen = ScreenHandlerGoldenLayout(remote)

		if remote is False:
			from octopwn.core import OctoPwn
			# checking if a session file exists
			sessionfile = '/static/octopwn.session'
			sessionfile_temp = '/static/octopwn.session.temp'

			newsession = True
			for filename in [sessionfile, sessionfile_temp]:
				try:
					js.loadingScreenMessage("Trying to load session file %s" % filename)
					with open(filename, 'rb') as f:
						a = 1
					js.loadingScreenMessage("It seems there is already a session file here. Trying to load it!")
					octopwnApp = OctoPwn.load(filename, screen, work_dir = '/static/', periodic_save = True)
					js.loadingScreenMessage("Session restore ok!")
					newsession = False
					break
				except Exception as e:
					js.loadingScreenMessage("Loading session file failed! Reason: %s" % str(e))
			else:
				js.loadingScreenMessage("Either no session file or it is corrupt, let the past die kill it if you have to...")
				octopwnApp = OctoPwn(screen, work_dir = '/static/', periodic_save = True)
		
			apprunner, err = await octopwnApp.run()
			if err is not None:
				raise err

			if newsession is True:
				# the ip/port doesnt matter, those params are not used in this protocol
				_,_,err = await octopwnApp.do_addproxy('WSNET', '127.0.0.1', 8700)
				if err is not None:
					raise err
				await octopwnApp.do_createutil('PYPYKATZ')
		
		
		else:
			from octopwn.remote.client.core import OctoPwnRemoteClient
			from octopwn.remote.client import logger as remclilogger

			js.loadingScreenMessage("Determining authentication type...")
			def get_val_or_none(x):
				res = js.document.getElementById(x)
				if res is None:
					return None	
				if res.value == '':
					return None
				return res.value

			def get_authmethod():
				return js.getRemoteServerAuthType()

			username = get_val_or_none("remoteserverusername")
			password = get_val_or_none("remoteserverpassword")
			authmethod = get_authmethod()

			js.loadingScreenMessage("Authentication type %s will be used" % authmethod)
			remclilogger.setLevel(logging.DEBUG)
			
			url = js.document.getElementById('remoteserverurl').value
			js.loadingScreenMessage("Creating websockets connection to %s" % url)
			comms = RemoteComms(url)
			_, err = await comms.run()
			if err is not None:
				js.stopLoadingScreenError("Server connection error!")
				raise err
			js.loadingScreenMessage("Connected to remote server!")
			
			octopwnApp = OctoPwnRemoteClient(
				None, 
				None, 
				screen, 
				username=username, 
				password=password, 
				authmethod=authmethod
			)
			js.loadingScreenMessage("Authenticating...")
			try:
				_, err = await asyncio.wait_for(octopwnApp.authenticate(comms), timeout=5)
			except asyncio.TimeoutError:
				criticalexception('Authentication timed out!')
				raise Exception('Authentication timed out!')
			if err is not None:
				criticalexception('Authentication error!', err)
				raise err
			js.loadingScreenMessage("Authentication OK!")
			apprunner = asyncio.create_task(octopwnApp.run_generic(comms))
		
		octopwnExtra = ExtraOperations(octopwnApp)
			
		await asyncio.sleep(0)
		return True, None
	except Exception as e:
		traceback.print_exc()
		return False, e

await start()

