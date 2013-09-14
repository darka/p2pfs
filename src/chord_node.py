from twisted.protocols.basic import LineReceiver
from twisted.internet import reactor, protocol
from twisted.internet.address import IPv4Address
from twisted.internet.defer import Deferred, succeed
from twisted.internet.protocol import Protocol, ClientFactory, ServerFactory
from twisted.protocols import amp
import argparse
import md5
import collections
import math


M = 10

def Echo(s):
  print(s)

def Hash(s):
  return int(long(md5.new(s).hexdigest(), 16) % M)


class ChordServerProtocol(NetstringReceiver):

  def connectionMade(self):
    print("Someone connected.")

  def stringReceived(self, request):
    print("Received a request: {}.".format(request))

    if '.' not in request: # bad request
        self.transport.loseConnection()
        return

    req, arg = request.split('.', 1)

    d = self.factory.HandleRequest(req)
    d.addCallback(lambda ret: self.sendString(str(ret)))
    d.addCallback(lambda _: self.transport.loseConnection)
    d.callback(int(arg))


class ChordServerFactory(ServerFactory):

  protocol = ChordServerProtocol

  def __init__(self, service):
    self.service = service

  def HandleRequest(self, req):
    if req == 'retrieve_value':
      d = Deferred()
      d.addCallback(self.service.GetValue)
      return d


class ChordClientProtocol(amp.AMP):
  pass

class ChordClientFactory(ClientFactory):

  protocol = ChordClientProtocol

  def __init__(self, key, deferred):
    self.key = key
    self.deferred = deferred


def HashAddress(address):
  return Hash(str(address.host) + str(address.port))
  

class ChordService(object):
  
  def __init__(self):
    self.data = {}
    self.routing_table = {}

  def AddToRoutingTable(self, address):
    h = HashAddress(address)
    self.routing_table[h] = address
    print("Added {} to routing table (hash: {}).".format(address, h))

  def StoreValue(self, key, value):
    self.data[int(key)] = value
    print("Stored key: {}, value: {}.".format(key, value))
    
  def GetValue(self, key):
    print('Retrieving value with key: {}.'.format(key))
    # check if value is among the values you hold
    if key in self.data:
      return succeed(self.data[key])

    # if it is not, look at your routing table
    deferred = Deferred()
    factory = ChordClientFactory(key, deferred)
    #address_hash = int(math.floor(math.log(int(key), 2)))
    #print("address hash: {}".format(address_hash)
    #address = self.routing_table[address_hash]
    address = self.routing_table[int(key)]
    reactor.connectTCP(address.host, address.port, factory)
    return factory.deferred


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('--port')
  parser.add_argument('--store')
  parser.add_argument('--retrieve')
  parser.add_argument('--connect', default=None)

  args = parser.parse_args()
  port = int(args.port)

  service = ChordService()

  if (args.connect):
    dst = args.connect.split(':')
    service.AddToRoutingTable(IPv4Address('TCP', dst[0], int(dst[1])))

  if (args.store):
    key, value = args.store.split(':')
    service.StoreValue(key, value)
    
  if (args.retrieve):
    def EchoValue(value):
      print('Retrieved value: {}.'.format(value))
    d = service.GetValue(args.retrieve)
    d.addCallback(EchoValue)

  f = ChordServerFactory(service)
  reactor.listenTCP(port, f)
    
  reactor.run()

if __name__ == '__main__':
  main()

  
