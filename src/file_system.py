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
    self.file_service = file_service

  def log(self, message):
    self.l.log('FileSystem', message)

  def __call__(self, op, *args):
    #self.log('-> {} {}'.format(op, (' '.join(str(arg) for arg in args) if args else '')))
    self.log('-> {} ...'.format(op))
    return getattr(self, op)(*args)

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

  getxattr = None
  listxattr = None

  def readdir(self, path, fh):
    contents = threads.blockingCallFromThread(reactor, self.file_db.list_directory, self.key, path)
    ret = ['.', '..'] 
    if contents:
      return ret + contents
    else:
      return ret

  def create(self, path, mode):
    threads.blockingCallFromThread(reactor, self.file_db.add_file, self.key, path, mode, 0)
    real_path = os.path.join(self.file_dir, path[1:])
    dir_path = os.path.dirname(real_path)
    if not os.path.exists(dir_path):
      self.log('create dir: {}'.format(dir_path))
      os.makedirs(dir_path)
    self.log('create file: {}'.format(real_path))
    return os.open(real_path, os.O_WRONLY | os.O_CREAT, mode)

  def mkdir(self, path, mode):
    threads.blockingCallFromThread(reactor, self.file_db.add_directory, self.key, path, mode)

  #access = None
  #opendir = None
  #release = None
  #releasedir = None

  def file_is_up_to_date(self, file_path):
    if not os.path.isfile(file_path):
      return False
    if os.stat(file_path).st_mtime < threads.blockingCallFromThread(reactor, self.file_db.get_file_mtime, self.key, os.path.basename(file_path)):
      return False
    return True
    
  def open(self, path, flags):
    if threads.blockingCallFromThread(reactor, self.file_db.file_exists, self.key, path):
      file_path = os.path.join(self.file_dir, path[1:])
      if not self.file_is_up_to_date(file_path):
        # we need to find this file on the dht
        threads.blockingCallFromThread(reactor, self.file_service.download, path, file_path, self.key, True)
      
    return os.open(os.path.join(self.file_dir, path[1:]), flags)

  def read(self, path, size, offset, fh):
    file_path = os.path.join(self.file_dir, path[1:])
    if not self.file_is_up_to_date(file_path):
      # we need to find this file on the dht
      threads.blockingCallFromThread(reactor, self.file_service.download, path, file_path, self.key, True)
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
    full_file_path = os.path.join(self.file_dir, path[1:])
    f = open(full_file_path, 'w')
    self.log('writing {}'.format(full_file_path))
    f.seek(offset, 0)
    f.write(data)
    f.close()
    mtime = threads.blockingCallFromThread(reactor, self.file_db.update_file_mtime, self.key, path)
    threads.blockingCallFromThread(reactor, self.file_db.update_size, self.key, path, len(data))
    reactor.callFromThread(self.file_service.publish_file, self.key, path, full_file_path, mtime)
    return len(data)

