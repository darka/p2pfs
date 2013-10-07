from twisted.protocols.basic import LineReceiver

class UploadProtocol(LineReceiver):
  def connectionMade(self):
    l.log('Connection was made (UploadProtocol)')

  def uploadFile(self, filename, file_path, key, hash):
    l.log("uploadFile protocol working")
    self.sendLine(','.join(['store', filename, key, hash]))
    upload_file(file_path, self.transport)
    self.transport.loseConnection()
    l.log('finished uploading')


