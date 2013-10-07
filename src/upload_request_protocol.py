from twisted.internet import defer
from twisted.protocols.basic import LineReceiver
from helpers import *
import binascii

class UploadRequestProtocol(LineReceiver):
  def __init__(self, logger):
    self.l = logger
    self.buffer = ''

  def connectionMade(self):
    self.l.log('Connection was made (UploadRequestProtocol)')

  def rawDataReceived(self, data):
    self.buffer += data

  def request_file(self, filename, file_path, key, hash):
    self.filename = filename
    self.destination = file_path
    hexhash = binascii.hexlify(hash)
    self.l.log("uploadFile protocol working ({}, {}, {}, {})".format(filename, file_path, key, hexhash))
    self.sendLine(str(','.join(['upload', filename, key, hexhash])))
    self.l.log('file request finished')
    self.setRawMode()
    self.df = defer.Deferred()
    return self.df

  def connectionLost(self, reason):
    if len(self.buffer) == 0:
      self.l.log("Upload request failed! Downloaded nothing.\n")
      return
    save_buffer(self.buffer, self.destination)
    self.l.log('Saved buffer to {}'.format(self.destination))
    self.df.callback(None)

