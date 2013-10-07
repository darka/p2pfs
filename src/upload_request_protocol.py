from twisted.protocols.basic import LineReceiver

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


