#!/usr/bin/env python3

import socket

import oursql
import requests

class TS3Client:
	def __init__(self):
		self.sock = None
		self.buf = None
		self.schid = None
		self.debug = False

	def connect(self):
		self.buf = b''
		self.schid = None
		self.sock = socket.create_connection(('localhost', 25639))
		while self.schid == None:
			for line in self.recv():
				if line.startswith('selected schandlerid='):
					self.schid = int(line[21:])

	def send(self, command, **kwargs):
		line = command
		for k, v in kwargs.items():
			line += ' %s=%s' % (k, v)
		if self.debug:
			print('->', line)
		self.sock.sendall(line.encode('utf-8') + b'\n')

	def recv(self):
		self.buf += self.sock.recv(1024)
		split = self.buf.split(b'\n\r')
		self.buf = split[-1]
		for line in split[:-1]:
			line = line.decode('utf-8') 
			if self.debug:
				print('<-', line)
			yield line

def parse_line(line):
	split = line.split()
	if split[0] != 'notifytextmessage':
		return
	args = {}
	for arg in split[1:]:
		k, v = arg.split('=', 1)
		args[k] = v.replace('\\s', ' ')
	if args['invokerid'] == args.get('target'): # echo of our own message
		return
	return args

rs = requests.Session()
rs.headers.update({'User-Agent': 'pbot'})
db = oursql.connect(db='eve', user='eve', passwd='eve', autoreconnect=True)
def price_check(msg):
	def get_prices(typeid, system=None, region=None):
		from xml.dom import minidom
		import xml.parsers.expat

		url = 'http://api.eve-central.com/api/marketstat'
		params = {'typeid': typeid}
		if system: params['usesystem'] = system
		if region: params['regionlimit'] = region
		try:
			xml = minidom.parseString(rs.get(url, params=params).text)
		except xml.parsers.expat.ExpatError:
			return None

		buy = xml.getElementsByTagName('buy')[0]
		buy_max = buy.getElementsByTagName('max')[0]
		bid = float(buy_max.childNodes[0].data)

		sell = xml.getElementsByTagName('sell')[0]
		sell_min = sell.getElementsByTagName('min')[0]
		ask = float(sell_min.childNodes[0].data)

		all_orders = xml.getElementsByTagName('all')[0]
		all_volume = all_orders.getElementsByTagName('volume')[0]
		volume = int(all_volume.childNodes[0].data)

		return bid, ask, volume
	def __item_info(curs, query):
		curs.execute('SELECT typeID, typeName FROM invTypes WHERE typeName LIKE ?', (query,))
		results = curs.fetchmany(3)
		if len(results) == 1:
			return results[0]
		if len(results) == 2 and \
				results[0][1].endswith('Blueprint') ^ results[1][1].endswith('Blueprint'):
			# an item and its blueprint; show the item
			if results[0][1].endswith('Blueprint'):
				return results[1]
			else:
				return results[0]
		if len(results) >= 2:
			return results
	def item_info(item_name):
		with db.cursor() as curs:
			# exact match
			curs.execute(
					'SELECT typeID, typeName FROM invTypes WHERE typeName LIKE ?',
					(item_name,)
					)
			result = curs.fetchone()
			if result:
				return result

			# start of string match
			results = __item_info(curs, item_name + '%')
			if isinstance(results, tuple):
				return results
			if results:
				names = map(lambda r: r[1], results)
				return 'Found items: ' + ', '.join(names)

			# substring match
			results = __item_info(curs, '%' + item_name + '%')
			if isinstance(results, tuple):
				return results
			if results:
				names = map(lambda r: r[1], results)
				return 'Found items: ' + ', '.join(names)
			return 'Item not found'
	def format_prices(prices):
		if prices is None:
			return 'n/a'
		if prices[1] < 1000.0:
			return 'bid {0:g} ask {1:g} vol {2:,d}'.format(*prices)
		prices = map(int, prices)
		return 'bid {0:,d} ask {1:,d} vol {2:,d}'.format(*prices)

	if msg.lower() == 'plex':
		msg = "30 Day Pilot's License Extension (PLEX)"
	result = item_info(msg)
	if not result:
		return
	if isinstance(result, str):
		return result
	typeid, item_name = result
	jita_system = 30000142
	amarr_system = 30002187
	jita_prices = get_prices(typeid, system=jita_system)
	amarr_prices = get_prices(typeid, system=amarr_system)
	jita = format_prices(jita_prices)
	amarr = format_prices(amarr_prices)
	return '%s\\nJita: %s\\nAmarr: %s' % (item_name, jita, amarr)

client = TS3Client()
client.connect()
client.send('clientnotifyregister', schandlerid=client.schid, event='notifytextmessage')
while True:
	for line in client.recv():
		args = parse_line(line)
		if args is None:
			continue

		if args['msg'].startswith('!pc '):
			response = price_check(args['msg'][4:])
			if response:
				response = response.replace(' ', '\\s')
				send_args = {'targetmode': args['targetmode']}
				if 'target' in args:
					send_args['target'] = args['invokerid']
				client.send('sendtextmessage', msg=response, **send_args)
