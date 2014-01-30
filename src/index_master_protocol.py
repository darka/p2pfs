from twisted.protocols.basic import LineReceiver
from tempfile import NamedTemporaryFile
from helpers import *
import os
import json
import binascii

class IndexMasterProtocol(LineReceiver):
  def log(self, message):
    self.factory.l.log('IndexMaster', message)

  def connectionMade(self):
    self.setLineMode()
    ip = self.transport.getPeer().host
    self.log('New Connection from {}'.format(ip))

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

      dirs = os.path.dirname(self.destination)
      if dirs and not os.path.exists(dirs):
        os.makedirs(dirs)

      self.tmp_destination_file = NamedTemporaryFile(delete=False)
      self.outfile_size = 0
      self.setRawMode()

    elif self.command_name == 'tell_metadata':
      path = data['path']
      self.hash = binascii.unhexlify(data['hash'])

      if self.factory.file_service.storage.has_key(self.hash):
        #print self.factory.file_service.storage
        self.sendLine(str(self.factory.file_service.storage[self.hash]['mtime']))
        self.transport.loseConnection()
        self.log('Metadata sent and transport connection terminated')
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
        self.log('Uploading: {}'.format(file_path))
        d = upload_file_with_encryption(file_path, self.transport)
        d.addCallback(self.transferCompleted)
      else:
        self.log('Cannot upload: no such key')
    else:
      self.log('Unrecognised command: {}'.format(self.command_name))

  def transferCompleted(self, last_sent):
    self.log('finished uploading')
    self.transport.loseConnection()
      
  def rawDataReceived(self, data):
    self.log('raw data received ({})'.format(len(data)))
    self.tmp_destination_file.write(data)
    self.outfile_size += len(data)

  def addStorage(self, hash, key, filename, mtime):
    #self.factory.file_service.storage[self.hash] = {'key':self.key, 'filename':self.filename, 'mtime':int(self.mtime)}
    self.factory.file_service.storage[hash] = {
        'key': key, 
        'filename': filename, 
        'mtime': int(mtime)
    }
    
  def connectionLost(self, reason):
    self.log('Index master lost connection.')
    if self.command_name == 'store':
      self.setLineMode()
      if self.outfile_size == 0:
        self.log("Error! Connection lost :(\n")
        return
      else:
        self.tmp_destination_file.close()
        d = threads.deferToThread(
            decrypt_file, 
            open(self.tmp_destination_file.name, 'rb'), 
            open(self.destination, 'wb'),
            ENCRYPT_KEY)
        d.addCallback(lambda _ : addStorage(self.hash, self.key, self.filename, self.mtime))
        self.log('Stored: {} ({} bytes)'.format(self.filename, self.outfile_size))

    elif self.command_name == 'tell_metadata':
      self.log('Metadata sent')

    elif self.command_name == 'upload':
      self.setLineMode()
      self.log('Upload finished')
 
