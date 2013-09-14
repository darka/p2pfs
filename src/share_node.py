#! /usr/bin/env python
#
# This library is free software, distributed under the terms of
# the GNU Lesser General Public License Version 3, or any later version.
# See the COPYING file included in this archive
#

import argparse
import os, sys 

import twisted.internet.reactor
from twisted.internet import task

from twisted.internet import defer
from twisted.internet.protocol import Protocol, ServerFactory, ClientCreator

import hashlib

import entangled.node
from entangled.kademlia.datastore import SQLiteDataStore

DEST_FILENAME = "downloaded.data"

class FileServer(Protocol):
    def dataReceived(self, data):
        request = data.strip()
        for entry in os.walk(self.factory.sharePath):
            for filename in entry[2]:
                if filename == request:
                    fullPath = '%s/%s' % (entry[0], filename)
                    f = open(fullPath, 'r')
                    buf = f.read()
                    self.transport.write(buf)
                    f.close()
                    break
        self.transport.loseConnection()

class FileGetter(Protocol):
    def connectionMade(self):
        self.buffer = ''
        self.filename = ''
        
    def requestFile(self, filename):
        self.filename = filename
        self.transport.write('%s\r\n' % filename)

    def dataReceived(self, data):
        self.buffer += data
    
    def connectionLost(self, reason):
        if len(self.buffer) == 0:
             sys.stderr.write("Error! Connection lost :(\n")
             return
     
        f = open(DEST_FILENAME, 'w')
        f.write(self.buffer)
        f.close()


class FileSharingService():
    def __init__(self, node, listen_port):
        self.node = node
        self.listen_port = listen_port
        
        self._setupTCPNetworking()

    def _setupTCPNetworking(self):
        # Next lines are magic:
        self.factory = ServerFactory()
        self.factory.protocol = FileServer
        self.factory.sharePath = '.'
        twisted.internet.reactor.listenTCP(self.listen_port, self.factory)

    def search(self, keyword):
        return self.node.searchForKeywords(keyword)
    
    def publishDirectory(self, path):
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
        
        print 'files: ', len(files)
        def publishNextFile(result=None):
            if len(files) > 0:
                #twisted.internet.reactor.iterate()
                filename = files.pop()
                print '-->',filename
                df = self.node.publishData(filename, self.node.id)
                df.addCallback(publishNextFile)
            else:
                print '** done **'
                outerDf.callback(None)
        publishNextFile()
    
    def downloadFile(self, path):
        filename = path
        h = hashlib.sha1()
        h.update(filename)
        key = h.digest()
        
        def getTargetNode(result):
            targetNodeID = result[key]
            #print targetNodeID
            df = self.node.findContact(targetNodeID)
            return df
        def getFile(protocol):
            if protocol != None:
                protocol.requestFile(filename)
        def connectToPeer(contact):
            if contact == None:
                sys.stderr.write("File could not be retrieved.\nThe host that published this file is no longer on-line.\n")
            else:
                c = ClientCreator(twisted.internet.reactor, FileGetter)
                df = c.connectTCP(contact.address, contact.port)
                return df
        
        df = self.node.iterativeFindValue(key)
        df.addCallback(getTargetNode)
        df.addCallback(connectToPeer)
        df.addCallback(getFile)
        
    
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', required=True, type=int)
    parser.add_argument('--connect', dest='address', default=None)
    parser.add_argument('--share', dest='shared', default=[], nargs='*')
    parser.add_argument('--dest', dest='destination_folder', default=DEST_FILENAME)
    parser.add_argument('--search', dest='search_keywords', default=[], nargs='*')
    args = parser.parse_args()
    
    if args.address:
        ip, port = args.address.split(':')
        port = int(port)
        knownNodes = [(ip, port)]
#    elif len(sys.argv) == 3:
#        knownNodes = []
#        f = open(sys.argv[2], 'r')
#        lines = f.readlines()
#        f.close()
#        for line in lines:
#            ipAddress, udpPort = line.split()
#            knownNodes.append((ipAddress, int(udpPort)))
    else:
        knownNodes = None

    try:
        os.makedirs(os.path.expanduser('~')+'/.entangled')
    except OSError:
        pass
    dataStore = None#SQLiteDataStore(os.path.expanduser('~')+'/.entangled/fileshare.sqlite')
    node = entangled.node.EntangledNode(udpPort=args.port, dataStore=dataStore)
    node.invalidKeywords.extend(('mp3', 'png', 'jpg', 'txt', 'ogg'))
    node.keywordSplitters.extend(('-', '!'))
    file_service = FileSharingService(node, args.port)
    for directory in args.shared:
        file_service.publishDirectory(directory)
 
    node.joinNetwork(knownNodes)

    def perform_keyword_search():
        print("performing search...")
        for keyword in args.search_keywords:
          df = file_service.search(keyword)
          def printKeyword(result):
              print("keyword: {}".format(keyword))
              print("  {}".format(result))
          df.addCallback(printKeyword)

    if args.search_keywords:
      task.deferLater(twisted.internet.reactor, 10, perform_keyword_search)
    twisted.internet.reactor.run()


if __name__ == '__main__':
    main()
