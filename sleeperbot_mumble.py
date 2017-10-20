#!/usr/bin/env python

from os import path
import sys
sys.path.append(path.normpath(path.join(path.dirname(path.abspath(__file__)), 'pymumble')))

from collections import defaultdict
import cStringIO
from HTMLParser import HTMLParser
import subprocess
import thread
import time
import traceback
import urllib
import wave

import pymumble
from pymumble.constants import PYMUMBLE_CLBK_TEXTMESSAGERECEIVED
import requests
from wit.wit import Wit

import config

def message_received(msg):
	print(msg)

def respond(text):
	response = text.replace('\n', '<br>')
	channel_id = mumble.users.myself.get('channel_id')
	mumble.channels[channel_id].send_text_message(response)

def encode_mp3(pcm):
	lame = subprocess.Popen(['lame', '--silent', '-f', '-V9', '-', '-'],
			stdin=subprocess.PIPE, stdout=subprocess.PIPE)
	lame.stdin.write(pcm)
	mp3, _ = lame.communicate()
	return mp3

def query_wit(audio):
	meaning = wit.post_speech(audio, content_type='mpeg3')
	outcomes = meaning['outcomes']
	for outcome in outcomes:
		if outcome['intent'] == 'green_flame' and outcome['confidence'] >= 0.49:
			break
	else: # not green_flame
		return
	try:
		wav = wave.open('green_flame.wav', 'r')
		mumble.sound_output.add_sound(wav.readframes(wav.getnframes()))
	finally:
		wav.close()

mumble = pymumble.Mumble(config.mumble_host, 64738, 'raylu-bot', config.mumble_password, debug=False)
mumble.callbacks.set_callback(PYMUMBLE_CLBK_TEXTMESSAGERECEIVED, message_received)
wit = Wit(config.wit_token)

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
					mp3 = encode_mp3(buf.getvalue())
					thread.start_new_thread(query_wit, (mp3,))
				except:
					respond(traceback.format_exc())
				buf.close()
				del user_bufs[session]
			user_states[session] = False
	time.sleep(0.01)
