#! /usr/bin/env python
##
## This library is free software, distributed under the terms of
## the GNU Lesser General Public License Version 3, or any later version.
## See the COPYING file included in this archive
##

import argparse
import cProfile
import os
import sys
import shutil
import time
  
from threading import Lock

from file_database import *
from file_system import *
from file_sharing_service import *
from helpers import *
from logger import *

from twisted.internet import task
from twisted.internet import defer

import entangled.node

from entangled.kademlia.datastore import SQLiteDataStore

from Crypto.Cipher import PKCS1_OAEP
from Crypto.PublicKey import RSA

def main():
  l = Logger()
  parser = argparse.ArgumentParser()
  parser.add_argument('--key', required=True)
  parser.add_argument('--port', required=True, type=int)
  parser.add_argument('--connect', dest='address', default=None)
  parser.add_argument('--share', dest='shared', default=[], nargs='*')
  parser.add_argument('--dir', dest='content_directory', required=True)
  parser.add_argument('--db', dest='db_filename', required=True)
  parser.add_argument('--newdb', default=False, action='store_true')
  parser.add_argument('--log', dest='log_filename', default=None)
  parser.add_argument('--fs', default=None)
  args = parser.parse_args()

  l.set_output(open(args.log_filename, 'w'))
  print('> logging to: {}'.format(args.log_filename))
  
  if args.address:
    ip, port = args.address.split(':')
    port = int(port)
    knownNodes = [(ip, port)]
  # elif len(sys.argv) == 3:
  #   knownNodes = []
  #   f = open(sys.argv[2], 'r')
  #   lines = f.readlines()
  #   f.close()
  #   for line in lines:
  #     ipAddress, udpPort = line.split()
  #     knownNodes.append((ipAddress, int(udpPort)))
  else:
    knownNodes = None

  try:
    os.makedirs(os.path.expanduser('~')+'/.entangled')
  except OSError:
    pass
  dataStore = None#SQLiteDataStore(os.path.expanduser('~')+'/.entangled/fileshare.sqlite')

  ##key = RSA.importKey(open(args.key + '.pub').read())

  print('> reading key')
  sha = hashlib.sha1()
  public_key = open(args.key + '.pub').read().strip()
  sha.update(public_key)
  node_id = sha.digest()

  node = entangled.node.EntangledNode(id=node_id, udpPort=args.port, dataStore=dataStore)
  node.invalidKeywords.extend(('mp3', 'png', 'jpg', 'txt', 'ogg'))
  node.keywordSplitters.extend(('-', '!'))

  print('> joining network')
  node.joinNetwork(knownNodes)

  def prepare():
    file_db = FileDatabase(l, public_key, args.db_filename, args.newdb)
    file_service = FileSharingService(l, node, args.port, public_key, file_db, args.content_directory)
  
    for directory in args.shared:
      reactor.callLater(6, file_service.publish_directory, public_key, directory)
   
  
    # just for informational purposes
    if args.newdb:
      print('> adding \'/\'')

    l.log('Main', 'Node running.')
  
    def fuse_call():
      time.sleep(20)
      print('> filesystem running')
      debug = True
      fsobj = FileSystem(l, public_key, file_db, file_service, args.content_directory)
      fuse = FUSE(fsobj, args.fs, foreground=True, debug=debug)
  
    if args.fs:
      reactor.callInThread(fuse_call)

  #processor = CommandProcessor(file_service)
  #reactor.callInThread(processor.cmdloop)

  print('> reactor running')
  reactor.callLater(2, prepare)

  reactor.run()

if __name__ == '__main__':
  #cProfile.run('main()')
  main()
