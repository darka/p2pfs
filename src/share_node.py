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
import time
import entangled.node
  
from threading import Lock
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
  def __init__(self, key, filename, new=False):
    self.key = key
    self.db_filename = filename
    self.new = new

  def ready(self, file_service):
    self.file_service = file_service
    if self.new:
      self.conn = sqlite3.connect(self.db_filename)
      self.create_tables()
    
  def execute(self, command):
    l.log(command)
    c = self.conn.cursor()
    c.execute(command)
    return c

  def commit(self):
    self.conn.commit()
    self.file_service.publish_file(self.key, os.path.basename(self.db_filename), self.db_filename)
    
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
    filename = os.path.basename(path)
    dirname = os.path.dirname(path)
    c = self.execute("SELECT st_mode FROM files WHERE pub_key='{}' AND path='{}' AND filename='{}'".format(public_key, dirname, filename))
    old_mode = c.fetchone()[0]
    old_mode &= 0770000
    mode = old_mode | mode
    self.execute("UPDATE files SET st_mode={} WHERE path='{}' AND filename='{}' AND pub_key='{}'".format(
        mode, dirname, filename, public_key))
    self.commit()

  def update_time(self, public_key, path, atime, mtime):
    filename = os.path.basename(path)
    dirname = os.path.dirname(path)
    self.execute("UPDATE files SET st_atime={}, st_mtime={} WHERE path='{}' AND filename='{}' AND pub_key='{}'".format(
        atime, mtime, dirname, filename, public_key))
    self.commit()

  def update_size(self, public_key, path, size):
    filename = os.path.basename(path)
    dirname = os.path.dirname(path)
    self.execute("UPDATE files SET st_size={} WHERE path='{}' AND filename='{}' AND pub_key='{}'".format(
        size, dirname, filename, public_key))
    self.commit()
    
  def chown(self, public_key, path, uid, gid):
    filename = os.path.basename(path)
    dirname = os.path.dirname(path)
    self.execute("UPDATE files SET st_uid={}, st_gid={} WHERE path='{}' AND filename='{}' AND pub_key='{}'".format(
        uid, gid, dirname, filename, public_key))
    self.commit()
    
  def getattr(self, public_key, path):
    dirname = os.path.dirname(path)
    filename = os.path.basename(path)
    fields = 'st_atime, st_ctime, st_mode, st_mtime, st_nlink, st_size'.split(', ')
    c = self.execute("SELECT {} FROM files WHERE pub_key='{}' AND path='{}' AND filename='{}'".format(', '.join(fields), public_key, dirname, filename))
    attrs = c.fetchone()
    if not attrs: 
      return None
    result = dict(zip(fields, attrs))
    return result

  def rename(self, public_key, old_path, new_path):
    old_dirname = os.path.dirname(old_path)
    old_filename = os.path.basename(old_path)
    new_dirname = os.path.dirname(new_path)
    new_filename = os.path.basename(new_path)
    current_time = int(time.time())
    self.execute("UPDATE files SET path='{}', filename='{}' WHERE path='{}' AND filename='{}'".format(
        new_dirname, new_filename, old_dirname, old_filename))
    self.commit()

  def add_file(self, public_key, filename, path, mode):
    current_time = int(time.time())
    self.execute("INSERT INTO files"
                 "(pub_key, filename, path, st_mode, st_atime, st_mtime, st_ctime) "
                 "VALUES('{}', '{}', '{}', '{}', '{}', '{}', '{}')".format(
        public_key, filename, path, S_IFREG | mode, current_time, current_time, current_time))
    self.commit()

  def delete_directory(self, public_key, path):
    dirname = os.path.dirname(path)
    filename = os.path.basename(path)
    self.execute("DELETE FROM files WHERE "
                 "pub_key='{}' AND path='{}' AND filename='{}'".format(public_key, dirname, filename))
    self.commit()

  def add_directory(self, public_key, path, mode):
    current_time = int(time.time())
    dirname = os.path.dirname(path)
    filename = os.path.basename(path)
    self.execute("INSERT INTO files"
                 "(pub_key, path, filename, st_mode, st_nlink, st_atime, st_mtime, st_ctime) "
                 "VALUES('{}', '{}', '{}', '{}', '{}', '{}', '{}', '{}')".format(
        public_key, dirname, filename, S_IFDIR | mode, 2, current_time, current_time, current_time))
    if path != '/':
      self.execute("UPDATE files SET st_nlink = st_nlink + 1 WHERE path='{}' AND pub_key='{}'".format(
        '/', public_key))
    self.commit()

  def list_directory(self, public_key, path):
    c = self.execute("SELECT filename FROM files WHERE pub_key='{}' AND path='{}'".format(public_key, path))
    rows = c.fetchall()
    return [row[0] for row in rows if row[0]]


class FileSystem(LoggingMixIn, Operations):
  def __init__(self, key, file_db, file_service, file_dir):
    self.file_db = file_db
    self.file_dir = file_dir
    self.key = key

  def __call__(self, op, *args):
    print '->', op, (' '.join(str(arg) for arg in args) if args else '')
    ret = getattr(self, op)(*args)
    return ret

  def chown(self, path, uid, gid):
    threads.blockingCallFromThread(reactor, self.file_db.chown, self.key, path, uid, gid)

  def chmod(self, path, mode):
    threads.blockingCallFromThread(reactor, self.file_db.chmod, self.key, path, mode)
    return 0

  def getattr(self, path, fh=None):
    result = threads.blockingCallFromThread(
        reactor, self.file_db.getattr, self.key, path)
    if result:
      return result
    else:
      raise FuseOSError(ENOENT)

  #getxattr = None
  #listxattr = None

  def readdir(self, path, fh):
    contents = threads.blockingCallFromThread(reactor, self.file_db.list_directory, self.key, path)
    ret = ['.', '..'] 
    if contents:
      return ret + contents
    else:
      return ret

  def create(self, path, mode):
    threads.blockingCallFromThread(reactor, self.file_db.add_file, self.key, os.path.basename(path), os.path.dirname(path), mode)
    return os.open(os.path.join(self.file_dir, path[1:]), os.O_WRONLY | os.O_CREAT, mode)

  def mkdir(self, path, mode):
    threads.blockingCallFromThread(reactor, self.file_db.add_directory, self.key, path, mode)

  #access = None
  #opendir = None
  #release = None
  #releasedir = None

  def open(self, path, flags):
    return os.open(os.path.join(self.file_dir, path[1:]), flags)

  def read(self, path, size, offset, fh):
    file_path = os.path.join(self.file_dir, path[1:])
    if not os.path.isfile(file_path):
      # we need to find this file on the dht
      self.file_service.download(path)
    f = open(file_path, 'r')
    f.seek(offset, 0)
    buf = f.read(size)
    f.close()
    return buf

  #def symlink(self, target, source):
  #  print 'symlink'
  def flush(self, path, fh):
    return 0

  def fsync(self, path, datasync, fh):
    return 0

  def utimens(self, path, times=None):
    atime, mtime = times if times else (now, now)
    threads.blockingCallFromThread(reactor, self.file_db.update_time, self.key, path, atime, mtime)

  #def readlink(self, path):
  #  print 'readlink'

  def rename(self, old, new):
    threads.blockingCallFromThread(reactor, self.file_db.rename, self.key, old, new)
  
  def rmdir(self, path):
    threads.blockingCallFromThread(reactor, self.file_db.delete_directory, self.key, path)

  #def unlink(self, path):
  #  print 'unlink'

  def truncate(self, path, length, fh=None):
    with open(os.path.join(self.file_dir, path[1:]), 'r+') as f:
      f.truncate(length)

  def statfs(self, path):
    return dict(f_bsize=512, f_blocks=4096, f_bavail=2048)
  
  symlink = None
  unlink = None

  def write(self, path, data, offset, fh):
    f = open(os.path.join(self.file_dir, path[1:]), 'w')
    f.seek(offset, 0)
    f.write(data)
    f.close()
    threads.blockingCallFromThread(reactor, self.file_db.update_size, self.key, path, len(data))
    return len(data)

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

def upload_file(file_path, transport):
  f = open(file_path, 'r')
  buf = f.read()
  transport.write(buf)
  f.close()

def save_buffer(buffer, destination):
  f = open(destination, 'w')
  f.write(buffer)
  f.close()
 
class IndexMasterProtocol(LineReceiver):
  def connectionMade(self):
    self.setLineMode()
    l.log('Index Master Running')
    self.buffer = ''

  def lineReceived(self, data):
    self.command = data.split(',')
    l.log('Received: {}'.format(self.command[0]))
    if self.command[0] == 'store':
      self.filename = self.command[1]
      self.key = self.command[2]
      self.hash = self.command[3]
      l.log("Index Master received: {}".format(self.filename))
      self.destination = os.path.join(self.factory.file_dir, self.filename)
      self.setRawMode()
    elif command[0] == 'upload':
      if self.factory.file_service.storage.has_key(command[3]):
        self.setRawMode()
        file_path = os.path.join(self.file_dir, command[1])
        upload_file(file_path, self.transport)
        self.transport.loseConnection()
      
  def rawDataReceived(self, data):
    self.buffer += data

  def connectionLost(self, reason):
    if self.command[0] == 'store':
      if len(self.buffer) == 0:
        l.log("Error! Connection lost :(\n")
        return
      else:
        save_buffer(self.buffer, self.destination)
        self.factory.file_service.storage[self.hash] = (self.key, self.filename)
        #l.log('Stored({}): {}, {}'.format(self.hash, self.key, self.filename))
        l.log('Stored({}): {}, {}'.format('...', '##', self.filename))

    if self.command[0] == 'upload':
      l.log('Upload finished')
 
class UploadRequestProtocol(LineReceiver):
  def connectionMade(self):
    l.log('Connection was made (UploadRequestProtocol)')
    self.buffer = ''

  def rawDataReceived(self, data):
    self.buffer += data

  def request_file(self, filename, file_path, key, hash):
    self.filename = filename
    self.file_path = file_path
    l.log("uploadFile protocol working")
    self.sendLine(','.join(['upload', filename, key, hash]))
    l.log('file request finished')
    self.setRawMode()

  def connectionLost(self, reason):
    if len(self.buffer) == 0:
      l.log("Upload request failed! Downloaded nothing.\n")
      return
    save_buffer(self.buffer, self.destination)
    l.log('Saved buffer to {}'.format(self.destination))

class UploaderProtocol(LineReceiver):
  def connectionMade(self):
    l.log('Connection was made (UploaderProtocol)')

  def uploadFile(self, filename, file_path, key, hash):
    l.log("uploadFile protocol working")
    self.sendLine(','.join(['store', filename, key, hash]))
    upload_file(file_path, self.transport)
    self.transport.loseConnection()
    l.log('finished uploading')

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
  def __init__(self, node, listen_port, key, file_db, file_dir):
    self.node = node
    self.listen_port = listen_port
    self.file_dir = file_dir

    self.storage = {}
    self.key = key
    
    self.file_db = file_db

    if not self.file_db.new:
      reactor.callLater(20, self.download, self.key, self.file_db.db_filename)
      #self.download(self.key, self.file_db.db_filename)

    self._setupTCPNetworking()
    self.file_db.ready(self)

    #self.REPLICA_COUNT = 2

  def _setupTCPNetworking(self):
    # Next lines are magic:
    self.factory = ServerFactory()
    self.factory.protocol = IndexMasterProtocol
    self.factory.file_service = self
    self.factory.file_dir = self.file_dir 
    self.factory.file_db = self.file_db 
    self.factory.key = self.key 
    reactor.listenTCP(self.listen_port, self.factory)

  def search(self, keyword):
    return self.node.searchForKeywords(keyword)
  
  def publishFileWithUpload(self, filename, file_path):
    key = sha_hash(filename)
    l.log('publishing file {} ({})'.format(filename, file_path))

    def uploadFile(protocol):
      if protocol != None:
        l.log("uploadFile {} {}".format(filename, file_path))
        protocol.uploadFile(filename, file_path, self.key, key)

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

    for filename in files:
      full_file_path = os.path.join(self.file_dir, filename)
      shutil.copyfile(os.path.join(path, filename), full_file_path)
      self.publish_file(key, filename, full_file_path, add_to_database=True)

  def publish_file(self, key, filename, full_file_path, add_to_database=False):
    l.log('--> {}'.format(filename))
    df = self.publishFileWithUpload(filename, full_file_path)
    if add_to_database:
      self.file_db.add_file(key, filename, '/', 0777)
    return df

  def download(self, path, key):
    filename = os.path.basename(path)
    hash = sha_hash(filename)
    
    def getTargetNode(result):
      targetNodeID = result[hash]
      df = self.node.findContact(targetNodeID)
      return df

    def getFile(protocol):
      if protocol != None:
        protocol.request_file(filename, destination, key, hash)

    def connectToPeer(contact):
      if contact == None:
        l.log("File could not be retrieved.\nThe host that published this file is no longer on-line.\n")
      else:
        c = ClientCreator(reactor, UploadRequestProtocol)
        df = c.connectTCP(contact.address, contact.port)
        return df
    
    df = self.node.iterativeFindValue(hash)
    df.addCallback(getTargetNode)
    df.addCallback(connectToPeer)
    df.addCallback(getFile)
    

#def perform_keyword_search(file_service, keyword):
#  l.log("performing search...")
#  df = file_service.search(keyword)
#  def printKeyword(result):
#    l.log("keyword: {}".format(keyword))
#    l.log("  {}".format(result))
#  df.addCallback(printKeyword)
  

if __name__ == '__main__':
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

  print('> opening log file')
  l.set_output(open(args.log_filename, 'w'))
  
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

  file_db = FileDatabase(public_key, args.db_filename, args.newdb)
  file_service = FileSharingService(node, args.port, public_key, file_db, args.content_directory)

  for directory in args.shared:
    reactor.callLater(6, file_service.publishDirectory, public_key, directory)
 
  print('> joining network')
  node.joinNetwork(knownNodes)

  if args.newdb:
    print('> adding \'/\'')
    file_db.add_directory(public_key, '/', 0755)
  l.log('Node running.')

  def fuse_call():
    fuse = FUSE(FileSystem(public_key, file_db, file_service, args.content_directory), args.fs, foreground=True)

  if args.fs:
    reactor.callInThread(fuse_call)

  #processor = CommandProcessor(file_service)
  #reactor.callInThread(processor.cmdloop)

  print('> running')
  reactor.run()

