#!/usr/bin/env python

from os import path
import sys
sys.path.append(path.normpath(path.join(path.dirname(path.abspath(__file__)), 'pymumble')))

import traceback

import pymumble
from pymumble.constants import PYMUMBLE_CLBK_TEXTMESSAGERECEIVED

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
		response = response.replace('\n', '<br>')
		channel_id = mumble.users.myself.get('channel_id')
		mumble.channels[channel_id].send_text_message(response)

mumble = pymumble.Mumble(config.mumble_host, 64738, 'raylu-bot', config.mumble_password, debug=False)

mumble.callbacks.set_callback(PYMUMBLE_CLBK_TEXTMESSAGERECEIVED, message_received)

mumble.start()
mumble.is_ready()
mumble.users.myself.unmute()
mumble.users.myself.deafen()
channel = mumble.channels.find_by_name(config.mumble_channel)
channel.move_in()
mumble.join()
