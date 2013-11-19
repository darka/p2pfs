from twisted.protocols.basic import LineReceiver
from helpers import *
import binascii
import json

class UploadProtocol(LineReceiver):
  def __init__(self, logger):
    self.l = logger

  def connectionMade(self):
    self.l.log('Connection was made (UploadProtocol)')

  def uploadFile(self, path, file_path, key, hash, mtime):
    self.l.log("uploadFile protocol working, mtime: {}".format(mtime))

    contents = json.dumps({'command' : 'store', 'path' : path, 'key' : key, 'hash' : binascii.hexlify(hash), 'time' : str(mtime)})
    self.sendLine(contents)

    upload_file(file_path, self.transport)
    self.transport.loseConnection()
    self.l.log('finished uploading')


