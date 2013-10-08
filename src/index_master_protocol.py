from twisted.protocols.basic import LineReceiver
from helpers import *
import os
import binascii

class IndexMasterProtocol(LineReceiver):
  def connectionMade(self):
    self.setLineMode()
    self.factory.l.log('Index Master Running')
    self.buffer = ''

  def lineReceived(self, data):
    self.command = data.split(',')
    self.factory.l.log('Received: {}'.format(self.command[0]))
    if self.command[0] == 'store':
      self.filename = self.command[1]
      self.key = self.command[2]
      self.hash = binascii.unhexlify(self.command[3])
      self.mtime = self.command[4]
      self.factory.l.log("Index Master received: {}".format(self.filename))
      self.destination = os.path.join(self.factory.file_dir, self.filename)
      self.setRawMode()
    elif self.command[0] == 'tell_metadata':
      path = self.command[1]
      self.hash = binascii.unhexlify(self.command[2])
      if self.factory.file_service.storage.has_key(self.hash):
        print self.factory.file_service.storage
        self.sendLine(self.factory.file_service.storage[self.hash]['mtime'])
        self.transport.loseConnection()
      else:
        self.factory.l.log('Cannot send metadata: no such key')
    elif self.command[0] == 'upload':
      self.factory.l.log('upload: {}'.format(self.command[1]))
      self.hash = binascii.unhexlify(self.command[3])
      if self.factory.file_service.storage.has_key(self.hash):
        self.setRawMode()
        file_path = os.path.join(self.factory.file_dir, self.command[1])
        upload_file(file_path, self.transport)
        self.transport.loseConnection()
      else:
        self.factory.l.log('Cannot upload: no such key')
      
  def rawDataReceived(self, data):
    self.buffer += data

  def connectionLost(self, reason):
    if self.command[0] == 'store':
      if len(self.buffer) == 0:
        self.factory.l.log("Error! Connection lost :(\n")
        return
      else:
        save_buffer(self.buffer, self.destination)
        self.factory.file_service.storage[self.hash] = {'key':self.key, 'filename':self.filename, 'mtime':self.mtime}
        #self.factory.l.log('Stored({}): {}, {}'.format(self.hash, self.key, self.filename))
        self.factory.l.log('Stored: {}'.format(self.filename))
    elif self.command[0] == 'tell_metadata':
      self.factory.l.log('Metadata sent')
    elif self.command[0] == 'upload':
      self.factory.l.log('Upload finished')
 
