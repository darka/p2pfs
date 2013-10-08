from twisted.protocols.basic import LineReceiver
from helpers import *
import binascii

class UploadProtocol(LineReceiver):
  def __init__(self, logger):
    self.l = logger

  def connectionMade(self):
    self.l.log('Connection was made (UploadProtocol)')

  def uploadFile(self, filename, file_path, key, hash):
    self.l.log("uploadFile protocol working")
    self.sendLine(','.join(['store', filename, key, binascii.hexlify(hash)]))
    upload_file(file_path, self.transport)
    self.transport.loseConnection()
    self.l.log('finished uploading')


