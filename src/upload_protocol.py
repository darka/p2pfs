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

    self.infile = open(file_path, 'r')
    d = upload_file(self.infile, self.transport)
    d.addCallback(self.transferCompleted)

    self.l.log('started uploading')

  def transferCompleted(self, lastsent):
    self.l.log('finished uploading')
    self.infile.close()
    self.transport.loseConnection()


