import os
import hashlib

def sha_hash(name):
  h = hashlib.sha1()
  h.update(name)
  return h.digest()

def upload_file(file_path, transport):
  f = open(file_path, 'r')
  buf = f.read()
  transport.write(buf)
  f.close()

def save_buffer(buffer, destination):
  real_file_path = os.path.dirname(destination)
  if not os.path.exists(real_file_path):
    os.makedirs(real_file_path)
  f = open(destination, 'w')
  f.write(buffer)
  f.close()
 
