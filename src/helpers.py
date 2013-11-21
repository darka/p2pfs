from twisted.protocols.basic import FileSender
import os
import hashlib

def sha_hash(name):
  h = hashlib.sha1()
  h.update(name)
  return h.digest()

def upload_file(f, transport):
  sender = FileSender()
  sender.CHUNK_SIZE = 2 ** 16
  d = sender.beginFileTransfer(f, transport, lambda data: data)
  return d

def save_buffer(buffer, destination):
  real_file_path = os.path.dirname(destination)
  if not os.path.exists(real_file_path):
    os.makedirs(real_file_path)
  f = open(destination, 'w')
  f.write(buffer)
  f.close()
 
