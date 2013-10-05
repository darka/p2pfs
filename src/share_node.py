#! /usr/bin/env python
##
## This library is free software, distributed under the terms of
## the GNU Lesser General Public License Version 3, or any later version.
## See the COPYING file included in this archive
##

import argparse
import os
import sys
import hashlib
import sqlite3
import shutil
import entangled.node

from cmd import Cmd
from stat import S_IFDIR, S_IFLNK, S_IFREG

from twisted.internet import reactor
from twisted.internet import task
from twisted.internet import defer
from twisted.internet import threads

from twisted.internet.protocol import Protocol, ServerFactory, ClientCreator
from twisted.protocols.basic import LineReceiver

from entangled.kademlia.datastore import SQLiteDataStore

from Crypto.Cipher import PKCS1_OAEP
from Crypto.PublicKey import RSA
from errno import ENOENT
from stat import S_IFDIR, S_IFREG
from sys import argv, exit
from time import time

from fuse import FUSE, FuseOSError, Operations, LoggingMixIn, fuse_get_context

def sha_hash(name):
  h = hashlib.sha1()
  h.update(name)
  return h.digest()

class Logger(object):
  def __init__(self, where=None):
    self.set_output(where)

  def set_output(self, where):
    if not where:
      self.out = sys.stdout
    else:
      self.out = where

  def log(self, message):
    self.out.write(message + '\n')
    self.out.flush()
  

l = Logger()

class FileDatabase(object):
  def __init__(self, filename):
    self.conn = sqlite3.connect(filename)
    self.create_tables()

  def execute(self, command):
    l.log(command)
    c = self.conn.cursor()
    c.execute(command)
    return c

  def commit(self):
    self.conn.commit()
    
  def create_tables(self):
    try:
      self.execute('''DROP TABLE files''')
    except sqlite3.OperationalError:
      l.log('Could not drop table')
    self.execute(
          "CREATE TABLE files ("
          "pub_key text, "
          "filename text, "
          "path text, "
          "st_mode integer, "
          "st_uid integer, "
          "st_gid integer, "
          "st_atime integer DEFAULT 0, "
          "st_mtime integer DEFAULT 0, "
          "st_ctime integer DEFAULT 0, "
          "st_nlink integer DEFAULT 1, "
          "st_size integer DEFAULT 0)")
    self.commit()

  def chmod(self, public_key, path, mode):
    c = self.execute("SELECT st_mode FROM files WHERE pub_key='{}' AND path='{}'".format(public_key, path))
    old_mode = c.fetchone()[0]
    old_mode &= 0770000
    mode = old_mode | mode
    self.execute("UPDATE files SET st_mode={} WHERE path='{}' AND pub_key='{}'".format(
        mode, path, public_key))
    self.commit()
    
  def chown(self, public_key, path, uid, gid):
    self.execute("UPDATE files SET st_uid={}, st_gid={} WHERE path='{}' AND pub_key='{}'".format(
        uid, gid, path, public_key))
    self.commit()
    
  def getattr(self, public_key, path):
    fields = 'st_atime, st_ctime, st_mode, st_mtime, st_nlink, st_size'.split(', ')
    c = self.execute("SELECT {} FROM files WHERE pub_key='{}' AND path='{}'".format(', '.join(fields), public_key, path))
    attrs = c.fetchone()
    if not attrs: 
      return None
    result = dict(zip(fields, attrs))
    return result

  def add_file(self, public_key, filename, path, mode):
    self.execute("INSERT INTO files"
                 "(pub_key, filename, path, st_mode) "
                 "VALUES('{}', '{}', '{}', '{}')".format(
        public_key, filename, path, S_IFREG | mode))
    self.commit()

  def add_directory(self, public_key, path, mode):
    self.execute("INSERT INTO files"
                 "(pub_key, path, st_mode, st_nlink) "
                 "VALUES('{}', '{}', '{}', '{}')".format(
        public_key, path, S_IFDIR | mode, 2))
    if path != '/':
      self.execute("UPDATE files SET st_nlink = st_nlink + 1 WHERE path='{}' AND pub_key='{}'".format(
        '/', public_key))
    self.commit()

  def list_directory(self, public_key, path):
    c = self.execute("SELECT filename FROM files WHERE pub_key='{}' AND path='{}'".format(public_key, path))
    rows = c.fetchall()
    return [row[0] for row in rows]


class FileSystem(LoggingMixIn, Operations):
  def __init__(self, key, file_db):
    self.fd = 0
    self.file_db = file_db
    #self.root = root
    self.key = key

  def chown(self, path, uid, gid):
    threads.blockingCallFromThread(reactor, self.file_db.chown, self.key, path, uid, gid)

  def chmod(self, path, mode):
    threads.blockingCallFromThread(reactor, self.file_db.chmod, self.key, path, mode)

  def getattr(self, path, fh=None):
    result = threads.blockingCallFromThread(
        reactor, self.file_db.getattr, self.key, path)
    if result:
      return result
    else:
      raise FuseOSError(ENOENT)

  getxattr = None
  listxattr = None

  def readdir(self, path, fh):
    return ['.', '..']# + self.file_db.list_directory(self.key, path)

  #def create(self, path, mode):
  #  self.file_db.add_file(self.key, os.path.basename(path), path, mode)
  #  self.fd += 1
  #  return self.fd

  #def mkdir(self, path, mode):
  #  self.file_db.add_directory(self.key, path, mode)

  access = None
  flush = None
  open = None
  opendir = None
  release = None
  releasedir = None
  statfs = None
  #def open(self, path, flags):
  #  self.fd += 1
  #  return self.fd

  def read(self, path, size, offset, fh):
    return ''

  #def symlink(self, target, source):
  #  print 'symlink'

  #def utimens(self, path, times=None):
  #  print 'utimens'

  #def write(self, path, data, offset, fh):
  #  print 'write'

  #def readlink(self, path):
  #  print 'readlink'

  #def rename(self, old, new):
  #  print 'rename'
  #
  #def rmdir(self, path):
  #  print 'rmdir'

  #def unlink(self, path):
  #  print 'unlink'

  #def truncate(self, path, length, fh=None):
  #  print 'truncate'

  #def statfs(self, path):
  #  return dict(f_bsize=512, f_blocks=4096, f_bavail=2048)
  
  symlink = None
  truncate = None
  unlink = None
  utimens = None
  write = None


class CommandProcessor(Cmd):
  def __init__(self, file_service):
    self.prompt = ''
    Cmd.__init__(self)
    self.file_service = file_service

  def do_EOF(self, line):
    return True 

  def do_download(self, args):
    reactor.callFromThread(perform_download, self.file_service, *args.split())

  def do_search(self, keyword):
    reactor.callFromThread(perform_keyword_search, self.file_service, keyword)

class IndexMasterProtocol(LineReceiver):
  def __init__(self):
    self.setLineMode()
    l.log('Index Master Running')

  def lineReceived(self, data):
    self.buffer = ''
    self.filename = data
    l.log("Index Master received: {}".format(self.filename))
    self.destination = os.path.join('/tmp', self.filename)
    self.setRawMode()

  def rawDataReceived(self, data):
    self.buffer += data

  def connectionLost(self, reason):
    if len(self.buffer) == 0:
       l.log("Error! Connection lost :(\n")
       return
   
    f = open(self.destination, 'w')
    f.write(self.buffer)
    f.close()

class UploaderProtocol(LineReceiver):
  def uploadFile(filename, file_path):
    self.transport.sendLine(filename)
    l.log("uploadFile: {} {}".format(filename, file_path))
    f = open(file_path, 'r')
    buf = f.read()
    self.transport.write(buf)
    f.close()
    self.transport.loseConnection()

#class FileServer(Protocol):
#  def dataReceived(self, data):
#    request = data.strip()
#    for entry in os.walk(self.factory.sharePath):
#      for filename in entry[2]:
#        if filename == request:
#          fullPath = '%s/%s' % (entry[0], filename)
#          f = open(fullPath, 'r')
#          buf = f.read()
#          self.transport.write(buf)
#          f.close()
#          break
#    self.transport.loseConnection()
#
#class FileGetter(Protocol):
#  def connectionMade(self):
#    self.buffer = ''
#    self.filename = ''
#    self.destination = ''
#    
#  def requestFile(self, filename, destination):
#    self.filename = filename
#    self.destination = destination
#    self.transport.write('%s\r\n' % filename)
#
#  def dataReceived(self, data):
#    self.buffer += data
#  
#  def connectionLost(self, reason):
#    if len(self.buffer) == 0:
#       l.log("Error! Connection lost :(\n")
#       return
#   
#    f = open(self.destination, 'w')
#    f.write(self.buffer)
#    f.close()


class FileSharingService():
  def __init__(self, node, listen_port, file_db, file_dir):
    self.node = node
    self.listen_port = listen_port
    self.file_db = file_db
    self.file_dir = file_dir
    
    self._setupTCPNetworking()

    self.REPLICA_COUNT = 2

  def _setupTCPNetworking(self):
    # Next lines are magic:
    self.factory = ServerFactory()
    self.factory.protocol = IndexMasterProtocol
    self.factory.sharePath = '.'
    reactor.listenTCP(self.listen_port, self.factory)

  def search(self, keyword):
    return self.node.searchForKeywords(keyword)
  
  def publishFileWithUpload(self, filename, file_path):
    key = sha_hash(filename)
    l.log('publishing file {} ({})'.format(filename, file_path))

    def uploadFile(protocol):
      if protocol != None:
        protocol.uploadFile(filename, file_path)

    def uploadFileToPeers(contacts):
      outerDf = defer.Deferred()
      if not contacts:
        l.log("Could not reach any peers.")
      else:
        for contact in contacts:
          c = ClientCreator(reactor, UploaderProtocol)
          df = c.connectTCP(contact.address, contact.port)
          df.addCallback(uploadFile)
          l.log("Will upload '{}' to: {}".format(file_path, contact))
          outerDf.chainDeferred(df)
      return outerDf
    

    df = self.node.iterativeFindNode(key)
    df.addCallback(uploadFileToPeers)
    return df

  def publishDirectory(self, key, path):
    files = []
    paths = []

    outerDf = defer.Deferred()

    self.factory.sharePath = path

    for entry in os.walk(path):
      for file in entry[2]:
        if file not in files and file not in ('.directory'):
          files.append(file)
          paths.append(entry[0])
    files.sort()
    
    l.log('files: {}'.format(len(files)))

    def publishNextFile(result=None):
      if len(files) > 0:
        filename = files.pop()
        l.log('--> {}'.format(filename))
        full_file_path = os.path.join(self.file_dir, filename)
        shutil.copyfile(os.path.join(path, filename), full_file_path)
        df = self.publishFileWithUpload(filename, full_file_path)
        self.file_db.add_file(key, filename)
        df.addCallback(publishNextFile)
      else:
        l.log('** done **')
        outerDf.callback(None)

    publishNextFile()


  def downloadFile(self, filename, destination):
    key = sha_hash(filename)
    
    def getTargetNode(result):
      targetNodeID = result[key]
      df = self.node.findContact(targetNodeID)
      return df
    def getFile(protocol):
      if protocol != None:
        protocol.requestFile(filename, destination)
    def connectToPeer(contact):
      if contact == None:
        l.log("File could not be retrieved.\nThe host that published this file is no longer on-line.\n")
      else:
        c = ClientCreator(reactor, FileGetter)
        df = c.connectTCP(contact.address, contact.port)
        return df
    
    df = self.node.iterativeFindValue(key)
    df.addCallback(getTargetNode)
    df.addCallback(connectToPeer)
    df.addCallback(getFile)
    

def perform_download(file_service, filename, destination):
  l.log("downloading {} to {}...".format(filename, destination))
  file_service.downloadFile(filename, destination)

def publish_file(file_service, filename, destination):
  l.log("downloading {} to {}...".format(filename, destination))
  file_service.downloadFile(filename, destination)


def perform_keyword_search(file_service, keyword):
  l.log("performing search...")
  df = file_service.search(keyword)
  def printKeyword(result):
    l.log("keyword: {}".format(keyword))
    l.log("  {}".format(result))
  df.addCallback(printKeyword)
  

if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument('--key', required=True)
  parser.add_argument('--port', required=True, type=int)
  parser.add_argument('--connect', dest='address', default=None)
  parser.add_argument('--share', dest='shared', default=[], nargs='*')
  parser.add_argument('--dir', dest='content_directory', required=True)
  parser.add_argument('--db', dest='db_filename', required=True)
  parser.add_argument('--log', dest='log_filename', default=None)
  parser.add_argument('--fs', default=None)
  args = parser.parse_args()

  print('> opening log file')
  l.set_output(open(args.log_filename, 'w'))
  
  file_db = FileDatabase(args.db_filename)
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

  file_service = FileSharingService(node, args.port, file_db, args.content_directory)

  for directory in args.shared:
    reactor.callLater(10, file_service.publishDirectory, public_key, directory)
 
  print('> joining network')
  node.joinNetwork(knownNodes)

  file_db.add_directory(public_key, '/', 0755)
  l.log('Node running.')
  if args.fs:
    #fuse = FUSE(FileSystem(public_key, file_db), args.fs, foreground=True)
    reactor.callInThread(FUSE, FileSystem(public_key, file_db), args.fs, foreground=True)
  #processor = CommandProcessor(file_service)
  #reactor.callInThread(processor.cmdloop)
  print('> running')
  reactor.run()

