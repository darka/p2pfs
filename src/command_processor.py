from twisted.internet import reactor
from cmd import Cmd

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


