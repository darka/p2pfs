from helpers import encrypt_file, decrypt_file
import hashlib
import os
import unittest
import random

class TestEncryptionFunctions(unittest.TestCase):
  def setUp(self):
    self.orig_filename = '.testEncryption'
    self.enc_filename = self.orig_filename + '.enc'
    self.dec_filename = self.orig_filename + '.dec'

    self.contents = ''.join([str(random.randint(0, 10000)) for x in xrange(1000)])
    with open(self.orig_filename, 'wb') as f:
      f.write(self.contents)

  def testEncryption(self):
    key = hashlib.sha256('test123').digest()
    encrypt_file(self.orig_filename, self.enc_filename, key)
    decrypt_file(self.enc_filename, self.dec_filename, key)

    decrypted_contents = open(self.dec_filename, 'rb').read()
    self.assertTrue(self.contents == decrypted_contents)

  def tearDown(self):
    for filename in [self.orig_filename, self.enc_filename, self.dec_filename]:
      if os.path.exists(filename):
        os.remove(filename)
