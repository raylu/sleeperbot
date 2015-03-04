import codecs
try:
	import html.entities as htmlentitydefs # python 3
except ImportError:
	import htmlentitydefs # python 2
	chr = unichr
import json
import operator
import re
from xml.dom import minidom
import xml.parsers.expat

import oursql
import requests

rs = requests.Session()
rs.headers.update({'User-Agent': 'pbot'})
db = oursql.connect(db='eve', user='eve', passwd='eve', autoreconnect=True)
def price_check(text):
	def get_prices(typeid, system=None, region=None):

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

	if text.lower() == 'plex':
		text = "30 Day Pilot's License Extension (PLEX)"
	result = item_info(text)
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
	return '%s\nJita: %s\nAmarr: %s' % (item_name, jita, amarr)

def jumps(text):
	split = text.split()
	if len(split) != 2:
		return 'usage: !jumps [from] [to]'
	with db.cursor() as curs:
		curs.execute('''
				SELECT solarSystemName FROM mapSolarSystems
				WHERE solarSystemName LIKE ? or solarSystemName LIKE ?
				''', (split[0] + '%', split[1] + '%')
		)
		results = list(map(operator.itemgetter(0), curs.fetchmany(2)))
	query = [None, None]
	for i, s in enumerate(split):
		s = s.lower()
		for r in results:
			if r.lower().startswith(s):
				query[i] = r
				break
		else:
			return 'could not find system starting with ' + s
	if None in query:
		return
	r = rs.get('http://api.eve-central.com/api/route/from/%s/to/%s' % (query[0], query[1]))
	try:
		jumps = r.json()
	except ValueError:
		return 'error getting jumps'
	jumps_split = []
	for j in jumps:
		j_str = j['to']['name']
		from_sec = j['from']['security']
		to_sec = j['to']['security']
		if from_sec != to_sec:
			j_str += ' (%0.1g)' % to_sec
		jumps_split.append(j_str)
	return '%d jumps: %s' % (len(jumps), ', '.join(jumps_split))

entity_re = re.compile(r'&(#?)(x?)(\w+);')
def calc(text):
	def substitute_entity(match):
		ent = match.group(3)
		if match.group(1) == "#":
			if match.group(2) == '':
				return chr(int(ent))
			elif match.group(2) == 'x':
				return chr(int('0x'+ent, 16))
		else:
			cp = htmlentitydefs.name2codepoint.get(ent)
			if cp:
				return chr(cp)
			return match.group()
	def decode_htmlentities(string):
		return entity_re.subn(substitute_entity, string)[0]

	if not text:
		return
	response = rs.get('http://www.wolframalpha.com/input/', params={'i': text}).text
	matches = re.findall('context\.jsonArray\.popups\.pod_....\.push\((.*)\);', response)
	if len(matches) < 2:
		return 'error calculating'
	input_interpretation = json.loads(matches[0])['stringified']
	result = json.loads(matches[1])['stringified']
	output = '%s = %s' % (input_interpretation, result)
	output = output.replace('\u00a0', ' ') # replace nbsp with space
	output = codecs.getdecoder('unicode_escape')(output)[0]
	output = re.subn('<sup>(.*)</sup>', r'^(\1)', output)[0]
	output = decode_htmlentities(output)
	return output

handlers = {
	'pc': price_check,
	'jumps': jumps,
	'calc': calc,
}
