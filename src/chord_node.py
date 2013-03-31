from twisted.protocols.basic import LineReceiver
from twisted.internet import reactor, protocol
import argparse
import md5

FILENAME = "to_send.test"
def hash(s):
	return long(md5.new(s).hexdigest(), 16)

def read_bytes_from_file(file, chunk_size = 8100):
	with open(file, 'rb') as file:
		while True:
			chunk = file.read(chunk_size)
			
			if chunk:
					yield chunk
			else:
				break

class ChordNodeProtocol(LineReceiver):
	delimiter = '\n'
	def __init__(self, factory, shared_data):
		self.factory = factory
		self.shared_data = shared_data
		self.hash = None
		self.file_handler = None

	def connectionMade(self):
		print('someone connected')
		#self.sendLine('requestHash')
		self.sendLine('requestFile\n')
		pass

	def lineReceived(self, line):
		print line
		if line.startswith('requestHash'):
			address = self.transport.getHost()
			address_hash = hash(address.host + ':' + str(address.port))
			self.sendLine('receiveHash ' + str(address_hash) +'\n')
		elif line.startswith('receiveHash'):
			self.hash = line.split()[1]
			print("got hash: " + self.hash)
		elif line.startswith('requestFile'):
			#if self.shared_data.receiver: return
			self.transport.write('receiveFile\n')
			print 'raw'
			self.setRawMode()
			print 'writing...'

			for bytes in read_bytes_from_file(FILENAME):
				self.transport.write(bytes)

			self.transport.write('\r\n')	
			self.setLineMode()
		elif line.startswith('receiveFile'):
			#if not self.shared_data.receiver:
			#	return
			print 'receiving file'
			self.setRawMode()

	def rawDataReceived(self, data):
		filename = self.shared_data.filename
		
		print 'Receiving file chunk (%d KB)' % (len(data))
		
		if not self.file_handler:
			self.file_handler = open(self.shared_data.filename, 'wb')
			
		if data.endswith('\r\n'):
			# Last chunk
			data = data[:-2]
			self.file_handler.write(data)
			self.setLineMode()
			
			self.file_handler.close()
			self.file_handler = None
		else:
			self.file_handler.write(data)

class NodeData(object):
	def __init__(self, filename):
		self.test = []
		self.filename = filename
		self.receiver = False

class ServerNodeFactory(protocol.ServerFactory):
	protocol = ChordNodeProtocol
	
	def __init__(self, shared_data):
		self.shared_data = shared_data

	def buildProtocol(self, addr):
		return ChordNodeProtocol(self, self.shared_data)

class ClientNodeFactory(protocol.ClientFactory):
	protocol = ChordNodeProtocol
	def __init__(self, server_node_factory):
		self.server_node_factory = server_node_factory

	def buildProtocol(self, addr):
		return ChordNodeProtocol(self, self.server_node_factory.shared_data)

def main():
	parser = argparse.ArgumentParser()
	parser.add_argument('--port')
	parser.add_argument('--filename', default="test.file")
	parser.add_argument('--connect', default=None)
	parser.add_argument('--receive', action='store_true')

	args = parser.parse_args()
	if args.receive:
		print 'i am a receiver'
	shared_data = NodeData(args.filename)
	shared_data.receiver = args.receive
	f = ServerNodeFactory(shared_data)
	port = int(args.port)
	reactor.listenTCP(port, f)
	if (args.connect):
		host, port = args.connect.split(':')
		port = int(port)
		f_client = ClientNodeFactory(f)
		
		reactor.connectTCP(host, port, f_client)
	reactor.run()

if __name__ == '__main__':
	main()
