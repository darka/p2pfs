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
    ip = self.transport.getPeer().host
    self.l.log('Connection was made (UploadRequestProtocol) to {}'.format(ip))

  def rawDataReceived(self, data):
    self.tmp_destination_file.write(data)
    self.outfile_size += len(data)

  def request_file(self, path, file_path, key, hash):
    self.destination = file_path
    hexhash = binascii.hexlify(hash)
    self.l.log("upload request protocol working ({}, {}, {}, {})".format(path, file_path, key, hexhash))

    contents = json.dumps({'command' : 'upload', 'path' : path, 'key' : key, 'hash' : hexhash})

    dirs = os.path.dirname(self.destination)
    if dirs and not os.path.exists(dirs):
      os.makedirs(dirs)

    self.tmp_destination_file = NamedTemporaryFile(delete=False)
    self.outfile_size = 0
    self.sendLine(contents)
    self.setRawMode()
    self.df = defer.Deferred()
    self.l.log('file request finished')
    return self.df

  def connectionLost(self, reason):
    if self.outfile_size == 0:
      self.l.log("Upload request failed! Downloaded nothing.")
      return
    self.l.log('Saved download to {}'.format(self.destination))
    self.tmp_destination_file.close()
    decrypt_file(self.tmp_destination_file.name, self.destination, ENCRYPT_KEY)
    self.df.callback(self.destination)

