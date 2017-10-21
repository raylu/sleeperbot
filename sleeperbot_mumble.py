#!/usr/bin/env python

from __future__ import print_function

from os import path
import sys
sys.path.append(path.normpath(path.join(path.dirname(path.abspath(__file__)), 'pymumble')))

import thread
import time
import traceback
import wave

import pymumble
from pymumble.constants import PYMUMBLE_CLBK_TEXTMESSAGERECEIVED

import config

def message_received(msg):
	if msg == 'green flame':
		green_flame()

def respond(text):
	response = text.replace('\n', '<br>')
	channel_id = mumble.users.myself.get('channel_id')
	mumble.channels[channel_id].send_text_message(response)

def green_flame():
	try:
		wav = wave.open('green_flame.wav', 'r')
		mumble.sound_output.add_sound(wav.readframes(wav.getnframes()))
	finally:
		wav.close()

mumble = pymumble.Mumble(config.mumble_host, 64738, 'raylu-bot', config.mumble_password, debug=False)
mumble.callbacks.set_callback(PYMUMBLE_CLBK_TEXTMESSAGERECEIVED, message_received)

mumble.set_receive_sound(True)
mumble.start()
mumble.is_ready()
channel = mumble.channels.find_by_name(config.mumble_channel)
channel.move_in()
while mumble.is_alive():
	time.sleep(1)
