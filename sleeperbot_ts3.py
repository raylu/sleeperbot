#!/usr/bin/env python3

import socket
import traceback

import config
import commands

class TS3Client:
	def __init__(self):
		self.sock = None
		self.buf = None
		self.schid = None
		self.debug = False

	def connect(self):
		self.buf = b''
		self.schid = None
		self.sock = socket.create_connection((config.clientquery_host, 25639))
		self.sock.settimeout(30)
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

def handle_message(client, args):
	if not args['msg'].startswith('!'):
		return
	command, text = args['msg'].split(' ', 1)
	handler = commands.handlers.get(command[1:])
	if not handler:
		return
	try:
		response = handler(text)
	except:
		response = traceback.format_exc()
	if response:
		response = response.replace(' ', '\\s')
		response = response.replace('\n', '\\n')
		send_args = {'targetmode': args['targetmode']}
		if 'target' in args:
			send_args['target'] = args['invokerid']
		client.send('sendtextmessage', msg=response, **send_args)

def main():
	client = TS3Client()
	client.connect()
	client.send('clientnotifyregister', schandlerid=client.schid, event='notifytextmessage')
	while True:
		try:
			for line in client.recv():
				args = parse_line(line)
				if args is None:
					continue
				handle_message(client, args)
		except socket.timeout:
			client.send('') # keepalive

if __name__ == '__main__':
	main()
