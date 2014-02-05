from twisted.protocols.basic import LineReceiver
from helpers import *
from tempfile import NamedTemporaryFile
import binascii
import json

class UploadProtocol(LineReceiver):
  def __init__(self, logger):
    self.l = logger

  def connectionMade(self):
    self.l.log('Connection was made (UploadProtocol)')

  def upload_file(self, path, file_path, key, hash, mtime):
    self.l.log("uploadFile protocol working, mtime: {}".format(mtime))

    contents = json.dumps({'command' : 'store', 'path' : path, 'key' : key, 'hash' : binascii.hexlify(hash), 'time' : str(mtime)})
    self.sendLine(contents)

    d = upload_file_with_encryption(file_path, self.transport)
    d.addCallback(self.transferCompleted)

    self.l.log('started uploading')

  def transferCompleted(self, lastsent):
    self.l.log('finished uploading')
    self.transport.loseConnection()
    self.l.log('connection closed')

