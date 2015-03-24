#!/usr/bin/env python

from os import path
import sys
sys.path.append(path.normpath(path.join(path.dirname(path.abspath(__file__)), 'pymumble')))

from collections import defaultdict
import cStringIO
from HTMLParser import HTMLParser
import time
import traceback
import urllib
import wave

import pymumble
from pymumble.constants import PYMUMBLE_CLBK_TEXTMESSAGERECEIVED
import requests
from wit.wit import Wit

import commands
import config

def message_received(msg):
	split = msg.split(' ', 1)
	if len(split) == 1:
		return
	command, text = split
	handler = commands.handlers.get(command[1:])
	if not handler:
		return
	try:
		response = handler(text)
	except:
		response = traceback.format_exc()
	if response:
		respond(response)

def respond(text):
	response = text.replace('\n', '<br>')
	channel_id = mumble.users.myself.get('channel_id')
	mumble.channels[channel_id].send_text_message(response)

class WikipediaParser(HTMLParser):
	NOT_STARTED = 0
	STARTED = 1
	DONE = 2

	def __init__(self):
		HTMLParser.__init__(self)
		self.state = self.NOT_STARTED
		self.text = ''

	def handle_starttag(self, tag, attrs):
		if tag == 'p' and self.state == self.NOT_STARTED:
			self.state = self.STARTED

	def handle_endtag(self, tag):
		if tag == 'p':
			self.state = self.DONE

	def handle_data(self, data):
		if self.state == self.STARTED:
			self.text += data

mumble = pymumble.Mumble(config.mumble_host, 64738, 'raylu-bot', config.mumble_password, debug=False)
mumble.callbacks.set_callback(PYMUMBLE_CLBK_TEXTMESSAGERECEIVED, message_received)
wit = Wit('EAW4ILIXTPSO57IIPLN7JYHMV2OUNXLQ')

mumble.set_receive_sound(True)
mumble.start()
mumble.is_ready()
channel = mumble.channels.find_by_name(config.mumble_channel)
channel.move_in()

user_states = defaultdict(bool)
user_bufs = {}
user_wavs = {}
while mumble.is_alive():
	for user in mumble.users.values():
		session = user['session']
		if user.sound.is_sound():
			pcm = user.sound.get_sound(0.01).pcm
			if session not in user_bufs:
				buf = cStringIO.StringIO()
				wav = wave.open(buf, 'w')
				wav.setparams((1, 2, 48000, 0, 'NONE', 'not compressed'))
				user_bufs[session] = buf
				user_wavs[session] = wav
			user_wavs[session].writeframes(pcm)
			user_states[session] = True
		else:
			if user_states[session]:
				user_wavs[session].close()
				buf = user_bufs[session]
				try:
					meaning = wit.post_speech(buf.getvalue())
					entities = meaning['outcome']['entities']
					wikipedia_search_query = entities.get('wikipedia_search_query')
					if wikipedia_search_query:
						query = urllib.urlencode({
							'action': 'parse',
							'page': wikipedia_search_query['value'],
							'format': 'json',
							'redirects': '1',
						})
						r = requests.get('https://en.wikipedia.org/w/api.php?' + query)
						json = r.json()
						if 'parse' in json:
							text = json['parse']['text']['*']
							parser = WikipediaParser()
							parser.feed(text)
							respond(parser.text)
				except:
					respond(traceback.format_exc())
				buf.close()
				del user_bufs[session]
			user_states[session] = False
	time.sleep(0.01)
