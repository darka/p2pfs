from twisted.protocols.basic import LineReceiver

class UploadProtocol(LineReceiver):
  def __init__(self, logger):
    LineReceiver.__init__(self)
    self.l = logger

  def connectionMade(self):
    self.factory.l.log('Connection was made (UploadProtocol)')

  def uploadFile(self, filename, file_path, key, hash):
    self.factory.l.log("uploadFile protocol working")
    self.sendLine(','.join(['store', filename, key, hash]))
    upload_file(file_path, self.transport)
    self.transport.loseConnection()
    self.factory.l.log('finished uploading')


