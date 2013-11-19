from twisted.protocols.basic import LineReceiver
from helpers import *
import os
import json
import binascii

class IndexMasterProtocol(LineReceiver):
  def log(self, message):
    self.factory.l.log('IndexMaster', message)

  def connectionMade(self):
    self.setLineMode()
    self.log('Index Master Running')
    self.buffer = ''

  def lineReceived(self, data):
    data = json.loads(data)
    self.command_name = data['command']
    self.log('Received: {}'.format(self.command_name))

    if self.command_name == 'store':
      self.filename = data['path']
      self.key = data['key']
      self.hash = binascii.unhexlify(data['hash'])
      self.mtime = data['time']
      self.log("Index Master received: {}".format(self.filename))
      # hack
      if self.filename[0] == '/':
        self.destination = os.path.join(self.factory.file_dir, self.filename[1:])
      else:
        self.destination = os.path.join(self.factory.file_dir, self.filename)
      self.setRawMode()

    elif self.command_name == 'tell_metadata':
      path = data['path']
      self.hash = binascii.unhexlify(data['hash'])

      if self.factory.file_service.storage.has_key(self.hash):
        #print self.factory.file_service.storage
        self.sendLine(str(self.factory.file_service.storage[self.hash]['mtime']))
        self.transport.loseConnection()
      else:
        self.log('Cannot send metadata: no such key')

    elif self.command_name == 'upload':
      self.log('upload: {}'.format(self.command_name))
      self.hash = binascii.unhexlify(data['hash'])

      if self.factory.file_service.storage.has_key(self.hash):
        self.setRawMode()
        # hack
        if data['path'][0] == '/':
          file_path = os.path.join(self.factory.file_dir, data['path'][1:])
        else:
          file_path = os.path.join(self.factory.file_dir, data['path'])
        upload_file(file_path, self.transport)
        self.transport.loseConnection()
      else:
        self.log('Cannot upload: no such key')
      
  def rawDataReceived(self, data):
    self.buffer += data

  def connectionLost(self, reason):
    if self.command_name == 'store':

      if len(self.buffer) == 0:
        self.log("Error! Connection lost :(\n")
        return
      else:
        save_buffer(self.buffer, self.destination)
        self.factory.file_service.storage[self.hash] = {'key':self.key, 'filename':self.filename, 'mtime':int(self.mtime)}
        self.log('Stored: {}'.format(self.filename))

    elif self.command_name == 'tell_metadata':
      self.log('Metadata sent')

    elif self.command_name == 'upload':
      self.log('Upload finished')
 
