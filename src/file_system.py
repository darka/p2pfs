import os
from twisted.internet import reactor
from twisted.internet import threads
from fuse import FUSE, FuseOSError, Operations, LoggingMixIn, fuse_get_context
from errno import ENOENT
from stat import S_IFDIR, S_IFLNK, S_IFREG


class FileSystem(LoggingMixIn, Operations):
  def __init__(self, logger, key, file_db, file_service, file_dir):
    self.file_db = file_db
    self.file_dir = file_dir
    self.key = key
    self.l = logger

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
    threads.blockingCallFromThread(reactor, self.file_db.add_file, self.key, os.path.basename(path), os.path.dirname(path), mode, 0)
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



