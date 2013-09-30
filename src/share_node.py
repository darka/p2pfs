#! /usr/bin/env python
#
# This library is free software, distributed under the terms of
# the GNU Lesser General Public License Version 3, or any later version.
# See the COPYING file included in this archive
#

import argparse
import os
import sys
import hashlib
import sqlite3

import entangled.node

from cmd import Cmd
from twisted.internet import reactor
from twisted.internet import task

from twisted.internet import defer
from twisted.internet.protocol import Protocol, ServerFactory, ClientCreator

from entangled.kademlia.datastore import SQLiteDataStore

from Crypto.Cipher import PKCS1_OAEP
from Crypto.PublicKey import RSA

DEST_FILENAME = "downloaded.data"
    
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
    

l = Logger()

class FileDatabase(object):
    def __init__(self, filename):
        self.conn = sqlite3.connect(filename)
        self.create_tables()

    def execute(self, command):
        l.log(command)
        c = self.conn.cursor()
        c.execute(command)
        self.conn.commit()
      
    def create_tables(self):
        try:
            self.execute('''DROP TABLE files''')
        except sqlite3.OperationalError:
            l.log('Could not drop table')
        self.execute(
            '''CREATE TABLE files (date text, pub_key text, path text)''')

    def add_file(self, public_key, filename):
        self.execute(
            '''INSERT INTO files VALUES (datetime('now'), '{}', '{}')'''.format(
                public_key, filename))
        
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
        self.destination = ''
        
    def requestFile(self, filename, destination):
        self.filename = filename
        self.destination = destination
        self.transport.write('%s\r\n' % filename)

    def dataReceived(self, data):
        self.buffer += data
    
    def connectionLost(self, reason):
        if len(self.buffer) == 0:
             l.log("Error! Connection lost :(\n")
             return
     
        f = open(self.destination, 'w')
        f.write(self.buffer)
        f.close()


class FileSharingService():
    def __init__(self, node, listen_port, file_db):
        self.node = node
        self.listen_port = listen_port
        self.file_db = file_db
        
        self._setupTCPNetworking()

    def _setupTCPNetworking(self):
        # Next lines are magic:
        self.factory = ServerFactory()
        self.factory.protocol = FileServer
        self.factory.sharePath = '.'
        reactor.listenTCP(self.listen_port, self.factory)

    def search(self, keyword):
        return self.node.searchForKeywords(keyword)
    
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
                df = self.node.publishData(filename, self.node.id)
                self.file_db.add_file(key, path)
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


def perform_keyword_search(file_service, keyword):
    l.log("performing search...")
    df = file_service.search(keyword)
    def printKeyword(result):
        l.log("keyword: {}".format(keyword))
        l.log("  {}".format(result))
    df.addCallback(printKeyword)
    
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--key', required=True)
    parser.add_argument('--port', required=True, type=int)
    parser.add_argument('--connect', dest='address', default=None)
    parser.add_argument('--share', dest='shared', default=[], nargs='*')
    parser.add_argument('--dir', dest='content_directory', required=True)
    parser.add_argument('--db', dest='db_filename', required=True)
    parser.add_argument('--log', dest='log_filename', default=None)
    args = parser.parse_args()

    l.set_output(open(args.log_filename, 'w'))
    
    file_db = FileDatabase(args.db_filename)
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

    #key = RSA.importKey(open(args.key + '.pub').read())

    sha = hashlib.sha1()
    public_key = open(args.key + '.pub').read().strip()
    sha.update(public_key)
    node_id = sha.digest()

    node = entangled.node.EntangledNode(id=node_id, udpPort=args.port, dataStore=dataStore)
    node.invalidKeywords.extend(('mp3', 'png', 'jpg', 'txt', 'ogg'))
    node.keywordSplitters.extend(('-', '!'))

    file_service = FileSharingService(node, args.port, file_db)

    for directory in args.shared:
        file_service.publishDirectory(public_key, directory)
 
    node.joinNetwork(knownNodes)

    l.log('Node running.')
    processor = CommandProcessor(file_service)

    reactor.callInThread(processor.cmdloop)
    reactor.run()


if __name__ == '__main__':
    main()
