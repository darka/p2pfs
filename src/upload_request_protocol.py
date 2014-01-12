from twisted.internet import defer
from twisted.protocols.basic import LineReceiver
from helpers import *
import binascii
import json

class UploadRequestProtocol(LineReceiver):
  def __init__(self, logger):
    self.l = logger
    self.outfile_size = 0

  def connectionMade(self):
    self.l.log('Connection was made (UploadRequestProtocol)')

  def rawDataReceived(self, data):
    self.outfile.write(data)
    self.outfile_size += len(data)

  def request_file(self, path, file_path, key, hash):
    self.destination = file_path
    hexhash = binascii.hexlify(hash)
    self.l.log("upload request protocol working ({}, {}, {}, {})".format(path, file_path, key, hexhash))

    contents = json.dumps({'command' : 'upload', 'path' : path, 'key' : key, 'hash' : hexhash})

    self.l.log('file request finished')

    dirs = os.path.dirname(self.destination)
    if not os.path.exists(dirs):
      os.makedirs(dirs)

    self.outfile = open(self.destination, 'wb')
    self.outfile_size = 0
    self.setRawMode()
    self.sendLine(contents)
    self.df = defer.Deferred()
    return self.df

  def connectionLost(self, reason):
    if self.outfile_size == 0:
      self.l.log("Upload request failed! Downloaded nothing.\n")
      return
    self.l.log('Saved download to {}'.format(self.destination))
    self.outfile.close()
    self.df.callback(self.destination)

