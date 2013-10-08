import os
import shutil
from twisted.internet import defer
from twisted.internet import reactor
from twisted.internet.protocol import Protocol, ServerFactory, ClientCreator
from index_master_protocol import *
from upload_protocol import *
from metadata_request_protocol import *
from upload_request_protocol import *

class FileSharingService():
  def __init__(self, logger, node, listen_port, key, file_db, file_dir):
    self.node = node
    self.listen_port = listen_port
    self.file_dir = file_dir
    self.l = logger

    self.storage = {}
    self.key = key
    
    self.file_db = file_db

    self._setupTCPNetworking()
    if not self.file_db.new:
      reactor.callLater(7, self.download, self.file_db.db_filename, self.key)
      reactor.callLater(14, self.file_db.ready, self)
      reactor.callLater(25, self.query_and_update_db_by_metadata)
    else:
      self.file_db.ready(self)
      #self.download(self.key, self.file_db.db_filename)

  def query_and_update_db_by_metadata(self):
    df = self.get_metadata(self.file_db.db_filename, self.key)
    def printMetadata(metadata):
      print 'Got: {}'.format(metadata)
    df.addCallback(printMetadata)
    reactor.callLater(20, self.query_and_update_db_by_metadata)

  def _setupTCPNetworking(self):
    # Next lines are magic:
    self.factory = ServerFactory()
    self.factory.protocol = IndexMasterProtocol
    self.factory.file_service = self
    self.factory.file_dir = self.file_dir 
    self.factory.file_db = self.file_db 
    self.factory.key = self.key 
    self.factory.l = self.l
    reactor.listenTCP(self.listen_port, self.factory)

  def search(self, keyword):
    return self.node.searchForKeywords(keyword)
  
  def publishFileWithUpload(self, filename, file_path, m_time):
    key = sha_hash(filename)
    self.l.log('publishing file {} ({})'.format(filename, file_path))

    def uploadFile(protocol):
      if protocol != None:
        self.l.log("uploadFile {} {}".format(filename, file_path))
        protocol.uploadFile(filename, file_path, self.key, key, m_time)

    def uploadFileToPeers(contacts):
      outerDf = defer.Deferred()
      if not contacts:
        self.l.log("Could not reach any peers. ({})".format(str(contacts)))
      else:
        for contact in contacts:
          c = ClientCreator(reactor, UploadProtocol, self.l)
          df = c.connectTCP(contact.address, contact.port)
          df.addCallback(uploadFile)
          self.l.log("Will upload '{}' to: {}".format(file_path, contact))
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
    self.factory.l = self.l

    for entry in os.walk(path):
      for file in entry[2]:
        if file not in files and file not in ('.directory'):
          files.append(file)
          paths.append(entry[0])
    files.sort()
    
    self.l.log('files: {}'.format(len(files)))

    for filename in files:
      full_file_path = os.path.join(self.file_dir, filename)
      shutil.copyfile(os.path.join(path, filename), full_file_path)
      
      size = os.path.getsize(full_file_path)
      self.file_db.add_file(key, filename, '/', 0777, size)
      m_time = self.file_db.get_file_mtime(self.key, filename)
      self.publish_file(key, filename, full_file_path, m_time)

  def publish_file(self, key, filename, full_file_path, m_time, add_to_database=False):
    self.l.log('--> {}'.format(filename))
    df = self.publishFileWithUpload(filename, full_file_path, m_time)
    return df

  def get_metadata(self, path, key):
    filename = os.path.basename(path)
    hash = sha_hash(filename)
    self.l.log('Getting metadata for: {}'.format(filename))
    
    def getTargetNode(result):
      return result.pop()

    def getFile(protocol):
      if protocol != None:
        return protocol.request_metadata(filename, key, hash)

    def connectToPeer(contact):
      if contact == None:
        self.l.log("The host that published this file is no longer on-line.\n")
      else:
        c = ClientCreator(reactor, MetadataRequestProtocol, self.l)
        df = c.connectTCP(contact.address, contact.port)
        return df
    
    df = self.node.iterativeFindValue(hash)
    df.addCallback(getTargetNode)
    df.addCallback(connectToPeer)
    df.addCallback(getFile)
    return df
 
  def download(self, path, key):
    filename = os.path.basename(path)
    hash = sha_hash(filename)
    self.l.log('Downloading: {}'.format(filename))
    
    def getTargetNode(result):
      return result.pop()

    def getFile(protocol):
      if protocol != None:
        return protocol.request_file(filename, path, key, hash)

    def connectToPeer(contact):
      if contact == None:
        self.l.log("File could not be retrieved.\nThe host that published this file is no longer on-line.\n")
      else:
        c = ClientCreator(reactor, UploadRequestProtocol, self.l)
        df = c.connectTCP(contact.address, contact.port)
        return df
    
    df = self.node.iterativeFindValue(hash)
    df.addCallback(getTargetNode)
    df.addCallback(connectToPeer)
    df.addCallback(getFile)
    return df
 
