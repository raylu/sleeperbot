#!/usr/bin/env python

from os import path
import sys
sys.path.append(path.normpath(path.join(path.dirname(path.abspath(__file__)), 'pymumble')))

import traceback

import pymumble
from pymumble.constants import PYMUMBLE_CLBK_TEXTMESSAGERECEIVED

import commands

def message_received(msg):
	command, text = msg.split(' ', 1)
	handler = commands.handlers.get(command[1:])
	if not handler:
		return
	try:
		response = handler(text)
	except:
		response = traceback.format_exc()
	if response:
		response = response.replace('\n', '<br>')
		channel.send_text_message(response)

mumble = pymumble.Mumble('voice.sc2gg.com', 64738, 'raylu-bot', '', debug=False)

mumble.callbacks.set_callback(PYMUMBLE_CLBK_TEXTMESSAGERECEIVED, message_received)

mumble.start()
mumble.is_ready()
mumble.users.myself.mute()
mumble.users.myself.deafen()
channel = mumble.channels.find_by_name('secret hiding room')
channel.move_in()
mumble.join()