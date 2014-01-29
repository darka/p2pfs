from twisted.protocols.basic import FileSender
from Crypto.Cipher import AES
import struct
import random
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

def encrypt_file(source, destination, key):
  chunk_size = 64*1024

  iv = ''.join(chr(random.randint(0, 0xFF)) for i in range(16))
  encryptor = AES.new(key, AES.MODE_CBC, iv)

  f_in = open(source, 'rb')
  f_out = open(destination, 'wb')

  file_size = os.path.getsize(source)

  f_out.write(struct.pack('<Q', file_size))
  f_out.write(iv)

  chunk = f_in.read(chunk_size)

  while len(chunk) > 0:
    if len(chunk) % 16 != 0:
      chunk += ' ' * (16 - len(chunk) % 16)
    f_out.write(encryptor.encrypt(chunk))
    chunk = f_in.read(chunk_size)
  f_in.close()
  f_out.close()

def decrypt_file(source, destination, key):
  chunk_size = 64*1024

  f_in = open(source, 'rb')
  f_out = open(destination, 'wb')

  orig_size = struct.unpack('<Q', f_in.read(struct.calcsize('Q')))[0]

  iv = f_in.read(16)
  decryptor = AES.new(key, AES.MODE_CBC, iv)

  chunk = f_in.read(chunk_size)

  while len(chunk) > 0:
    f_out.write(decryptor.decrypt(chunk))
    chunk = f_in.read(chunk_size)

  f_out.truncate(orig_size)
  f_in.close()
  f_out.close()
    
    
def save_buffer(buffer, destination):
  real_file_path = os.path.dirname(destination)
  if not os.path.exists(real_file_path):
    os.makedirs(real_file_path)
  f = open(destination, 'w')
  f.write(buffer)
  f.close()
 
