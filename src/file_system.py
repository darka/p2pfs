import os
from twisted.internet import reactor
from twisted.internet import threads
from fuse import FUSE, FuseOSError, Operations, LoggingMixIn, fuse_get_context
from errno import ENOENT
from stat import S_IFDIR, S_IFLNK, S_IFREG


class FileSystem(LoggingMixIn, Operations):
  """FUSE Interface Class"""

  def __init__(self, logger, key, file_db, file_service, file_dir):
    self.file_db = file_db
    self.file_dir = file_dir
    self.key = key
    self.l = logger
    self.file_service = file_service

    # Files which will be repropagated after flushing
    self.updateables = set([])

  def log(self, message):
    self.l.log('FileSystem', message)

  def __call__(self, op, *args):
    # Insert debugging messages here
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
      # Could not get attributes
      raise FuseOSError(ENOENT)

  # No support for extended file attributes
  getxattr = None
  listxattr = None

  def readdir(self, path, fh):
    contents = threads.blockingCallFromThread(reactor, self.file_db.list_directory, self.key, path)
    ret = ['.', '..'] 
    if contents:
      ret += contents
    return ret

  def unlink(self, path):
    threads.blockingCallFromThread(reactor, self.file_db.delete_file, self.key, path)
    real_path = os.path.join(self.file_dir, path[1:])
    os.unlink(real_path)

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

  def access(self, path, mode):
    real_path = os.path.join(self.file_dir, path[1:])
    if os.path.exists(real_path) and not os.access(real_path, mode):
      raise FuseOSError(EACCES)

  opendir = None
  releasedir = None

  def file_is_up_to_date(self, file_path_on_disk, path):
    self.log('Is file up to date? {}'.format(file_path_on_disk))
    if not os.path.isfile(file_path_on_disk):
      return False
    if os.stat(file_path_on_disk).st_mtime < threads.blockingCallFromThread(reactor, self.file_db.get_file_mtime, self.key, path):
      return False
    return True
    
  def open(self, path, flags):
    if threads.blockingCallFromThread(reactor, self.file_db.file_exists, self.key, path):
      file_path = os.path.join(self.file_dir, path[1:])
      if not self.file_is_up_to_date(file_path, path):
        # We need to find this file on the dht
        threads.blockingCallFromThread(reactor, self.file_service.download, path, file_path, self.key, True)
      
    return os.open(os.path.join(self.file_dir, path[1:]), flags)

  def read(self, path, size, offset, fh):
    file_path = os.path.join(self.file_dir, path[1:])
    os.lseek(fh, offset, 0)
    return os.read(fh, size)

  def flush(self, path, fh):
    os.fsync(fh)
    if fh in self.updateables:
      full_file_path = os.path.join(self.file_dir, path[1:])
      mtime = threads.blockingCallFromThread(reactor, self.file_db.update_file_mtime, self.key, path)
      threads.blockingCallFromThread(reactor, self.file_db.update_size, self.key, path, os.path.getsize(full_file_path))
      reactor.callFromThread(self.file_service.publish_file, self.key, path, full_file_path, mtime)
      self.updateables.remove(fh)
    return 0

  def release(self, path, fh):
    return os.close(fh)

  def fsync(self, path, datasync, fh):
    os.fsync(fh)
    return 0

  def utimens(self, path, times=None):
    atime, mtime = times if times else (now, now)
    threads.blockingCallFromThread(reactor, self.file_db.update_time, self.key, path, atime, mtime)

  def rename(self, old, new):
    threads.blockingCallFromThread(reactor, self.file_db.rename, self.key, old, new)
  
  def rmdir(self, path):
    threads.blockingCallFromThread(reactor, self.file_db.delete_directory, self.key, path)

  def truncate(self, path, length, fh=None):
    with open(os.path.join(self.file_dir, path[1:]), 'r+') as f:
      f.truncate(length)

  def statfs(self, path):
    # Hard coded values
    return dict(f_bsize=512, f_blocks=4096, f_bavail=2048)
  
  symlink = None

  def write(self, path, data, offset, fh):
    self.log('handle {}'.format(str(fh)))
    self.log('writing {}'.format(path))
    os.lseek(fh, offset, 0)
    self.updateables.add(fh)
    return os.write(fh, data)

