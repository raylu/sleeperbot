#!/usr/bin/env python

from __future__ import print_function

from os import path
import sys
sys.path.append(path.normpath(path.join(path.dirname(path.abspath(__file__)), 'pymumble')))

import thread
import time
import traceback
import wave
import wsgiref.simple_server

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

def webserver():
	httpd = wsgiref.simple_server.make_server('', 55555, app)
	httpd.serve_forever()

content = '''<!doctype html>
<html>
	<head>
		<title>green flame</title>
		<style>
			a {
				position: absolute;
				top: 0;
				bottom: 0;
				left: 0;
				right: 0;
				background-color: #111;
				text-align: center;
				font-size: 72px;
				color: #777;
			}
			a:hover {
				color: #7e7;
			}
		</style>
	</head>
	<body>
		<a href="/greenflame">green flame</a>
	</body>
</html>
'''
def app(environ, start_response):
	if environ['PATH_INFO'] == '/':
		headers = [('Content-Type', 'text/html')]
		start_response('200 OK', headers)
		return [content]
	elif environ['PATH_INFO'] == '/greenflame':
		green_flame()
		headers = [('Location', '/')]
		start_response('307 Temporary Redirect', headers)
	else:
		start_response('404 Not Found', [])
	return []

mumble = pymumble.Mumble(config.mumble_host, 64738, 'raylu-bot', config.mumble_password, debug=False)
mumble.callbacks.set_callback(PYMUMBLE_CLBK_TEXTMESSAGERECEIVED, message_received)

mumble.set_receive_sound(True)
mumble.start()
mumble.is_ready()
channel = mumble.channels.find_by_name(config.mumble_channel)
channel.move_in()

thread.start_new_thread(webserver, ())

while mumble.is_alive():
	time.sleep(1)
