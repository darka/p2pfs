from twisted.protocols.basic import LineReceiver
from twisted.internet import reactor, protocol
from twisted.internet.defer import Deferred, succeed
from twisted.internet.protocol import Protocol, ClientFactory, ServerFactory
from twisted.protocols.basic import NetstringReceiver
import argparse
import md5
import collections

FILENAME = "to_send.test"

def Hash(s):
  return int(long(md5.new(s).hexdigest(), 16) % 160)

class ChordClientProtocol(NetstringReceiver):

  value = ''

  def connectionMade(self):
    self.sendString("retrieve_value" + '.' + self.factory.key)

  def dataReceived(self, data):
    self.value += data 

  def connectionLost(self, reason):
    self.factory.ValueReceived(self.value)


class ChordServerFactory(ServerFactory):

    protocol = Protocol

    def __init__(self, service):
        self.service = service


class ChordClientFactory(ClientFactory):

  protocol = ChordClientProtocol

  def __init__(self, key, deferred):
    self.key = key
    self.deferred = deferred

  def ValueReceived(self, value):
    if self.deferred is not None:
      d, self.deferred = self.deferred, None
      d.callback(value)


Address = collections.namedtuple('Address', ['host', 'port'])


def HashAddress(address):
  return hash(str(address.host) + str(address.port))
  

class ChordService(object):
  
  def __init__(self):
    self.data = {}
    self.routing_table = {}

  def AddToRoutingTable(address):
    h = HashAddress(address)
    self.routing_table[h] = address
    print("Added {} to routing table.".format(address))

  def StoreValue(self, key, value):
    self.data[key] = value
    print("Stored key: {}, value: {}.".format(key, value))
    
  def GetValue(self, key):
    # check if value is among the values you hold
    if key in self.data:
      return succeed(self.data[key])

    # if it is not, look at your routing table
    deferred = Deferred()
    factory = ChordClientFactory(key, deferred)
    address = routing_table[int(floor(log(key, 2)))]
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

  f = ChordServerFactory(service)
  reactor.listenTCP(port, f)
  if (args.connect):
    host, port = args.connect.split(':')
    service.AddToRoutingTable(Address(host, int(port)))

  if (args.store):
    key, value = args.store.split(':')
    service.StoreValue(key, value)
    
  if (args.retrieve):
    def EchoValue(value):
      print('Retrieved value: {}'.format(value))
    d = service.GetValue(args.retrieve)
    d.addCallback(EchoValue)
    
  reactor.run()

if __name__ == '__main__':
  main()

  
