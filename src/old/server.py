import socket
import sys
import os
import struct
import SocketServer


class NodeHandler(SocketServer.BaseRequestHandler):

	netstring_max_header_size = 5

	def handle(self):
		data = self.request.recv(NodeHandler.netstring_max_header_size)
		if data == '':
			raise RuntimeError("connection broken")

		try:
			header, data = data.split(':')
		except ValueError:
			raise RuntimeError("incorrect header received")

		try:
			expected_size = int(header)
		except ValueError:
			raise("failed to determine expected packet length")

		expected_size -= len(data)
		received = False
		while not received:
			data_new = self.request.recv(expected_size)
			expected_size -= len(data_new)
			data = "{}{}".format(data, data_new)
			if (expected_size == 0):
				received = True
		print(data)

class NodeServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
	daemon_threads = True
	allow_reused_address = True

	def __init__(self, server_address, RequestHandlerClass):
		SocketServer.TCPServer.__init__(self, server_address, RequestHandlerClass)
		
def main():
	server = NodeServer(('localhost', 6000), NodeHandler)
	try:
		server.serve_forever()
	except KeyboardInterrupt:
		sys.exit(0)

if __name__ == "__main__":
	main()
