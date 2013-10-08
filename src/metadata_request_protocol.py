from twisted.internet import defer
from twisted.protocols.basic import LineReceiver
from helpers import *
import binascii

class MetadataRequestProtocol(LineReceiver):
  def __init__(self, logger):
    self.l = logger
    self.buffer = ''

  def connectionMade(self):
    self.l.log('Connection was made (MetadataRequestProtocol)')

  def lineReceived(self, line):
    self.buffer = line

  def request_metadata(self, filename, key, hash):
    self.sendLine(str(','.join(['tell_metadata', filename, binascii.hexlify(hash), key])))
    self.l.log('metadata request finished')
    self.df = defer.Deferred()
    return self.df

  def connectionLost(self, reason):
    if len(self.buffer) == 0:
      self.l.log("Metadata request failed! Got nothing.\n")
      return
    self.df.callback(int(self.buffer))

