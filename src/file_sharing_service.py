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
      db_path = os.path.join(self.file_dir, self.file_db.db_filename)
      reactor.callLater(7, self.download, os.path.basename(self.file_db.db_filename), db_path, self.key)
      reactor.callLater(11, self.file_db.ready, self)
      reactor.callLater(17, self.query_and_update_db_by_metadata)
    else:
      self.file_db.ready(self)
      reactor.callLater(17, self.query_and_update_db_by_metadata)
      #self.download(self.key, self.file_db.db_filename)

  def log(self, message):
    self.l.log('FileService', message)

  def query_and_update_db_by_metadata(self):
    df = self.get_metadata(self.file_db.db_filename, self.key)
    def handleMetadata(metadata):
      mtime = self.file_db.get_db_mtime(self.key)
      if mtime < metadata:
        self.log('will redownload: {} ({} < {})'.format(self.file_db.db_filename, mtime, metadata))
        db_path = os.path.join(self.file_dir, self.file_db.db_filename)
        self.download(os.path.basename(self.file_db.db_filename), db_path, self.key)
      else:
        self.log('{}: {} >= {}'.format(self.file_db.db_filename, mtime, metadata))
    def handleError(_):
      self.log('will update nothing')
    df.addCallback(handleMetadata)
    reactor.callLater(5, self.query_and_update_db_by_metadata)

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
  
  def publishFileWithUpload(self, path, local_file_path, m_time):
    key = sha_hash(path)
    self.log('publishing file {} ({})'.format(path, local_file_path))

    def uploadFile(protocol):
      if protocol != None:
        self.log("uploadFile {} {}".format(path, local_file_path))
        protocol.uploadFile(path, local_file_path, self.key, key, m_time)

    def uploadFileToPeers(contacts):
      outerDf = defer.Deferred()
      if not contacts:
        self.log("Could not reach any peers. ({})".format(str(contacts)))
      else:
        for contact in contacts:
          c = ClientCreator(reactor, UploadProtocol, self.l)
          df = c.connectTCP(contact.address, contact.port)
          df.addCallback(uploadFile)
          self.log("Will upload '{}' to: {}".format(local_file_path, contact))
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
    
    self.log('files: {}'.format(len(files)))

    for filename in files:
      full_file_path = os.path.join(self.file_dir, filename)
      shutil.copyfile(os.path.join(path, filename), full_file_path)
      
      size = os.path.getsize(full_file_path)
      file_path = os.path.join('/', filename)
      self.file_db.add_file(key, file_path, 0777, size)
      m_time = self.file_db.get_file_mtime(self.key, file_path)
      self.publish_file(key, file_path, full_file_path, m_time)

  def publish_file(self, key, path, full_file_path, m_time, add_to_database=False):
    self.log('--> {}'.format(path))
    hash = sha_hash(path)
    self.storage[hash] = {'key':key, 'filename':path, 'mtime':int(m_time)}
    df = self.publishFileWithUpload(path, full_file_path, m_time)
    return df

  def get_metadata(self, path, key):
    filename = os.path.basename(path)
    hash = sha_hash(filename)
    self.log('Getting metadata for: {}'.format(filename))
    
    def getTargetNode(result):
      #print result
      #print self.storage
      return result.pop()

    def getFile(protocol):
      if protocol != None:
        return protocol.request_metadata(filename, key, hash)

    def connectToPeer(contact):
      if contact == None:
        self.log("The host that published this file is no longer on-line.\n")
      else:
        c = ClientCreator(reactor, MetadataRequestProtocol, self.l)
        df = c.connectTCP(contact.address, contact.port)
        return df
    
    df = self.node.iterativeFindValue(hash)
    df.addCallback(getTargetNode)
    df.addCallback(connectToPeer)
    df.addCallback(getFile)
    return df
 
  def download(self, path, destination, key, update_time=False):
    hash = sha_hash(path)
    self.log('Downloading: {}'.format(path))
    
    def getTargetNode(result):
      return result.pop()

    def getFile(protocol):
      if protocol != None:
        return protocol.request_file(path, destination, key, hash)

    def connectToPeer(contact):
      if contact == None:
        self.log("File could not be retrieved.\nThe host that published this file is no longer on-line.\n")
      else:
        c = ClientCreator(reactor, UploadRequestProtocol, self.l)
        df = c.connectTCP(contact.address, contact.port)
        return df
    
    def updateTime(full_file_path):
      update_time = self.file_db.get_file_mtime(key, path)
      if update_time == 0: 
       return
      os.utime(full_file_path, (update_time, update_time))
      self.log('changed {} mtime to {}'.format(full_file_path, update_time))
      
    df = self.node.iterativeFindValue(hash)
    df.addCallback(getTargetNode)
    df.addCallback(connectToPeer)
    df.addCallback(getFile)
    if update_time:
      df.addCallback(updateTime)
    return df
 
