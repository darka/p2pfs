from stat import S_IFDIR, S_IFLNK, S_IFREG
import pickle
import time
import os
import sqlite3

class FileObject(object):
  attr_fields = 'st_atime, st_ctime, st_mode, st_mtime, st_nlink, st_size'.split(', ')
  def __init__(self):
    self.attrs = {}
    self.contents = {}

class FileDatabase(object):
  def __init__(self, logger, key, filename, new=False):
    self.key = key
    self.db_filename = filename
    self.new = new
    self.l = logger
    self.data = {'current_time' : 0}

  def ready(self):
    if self.new or not os.path.exists(self.db_filename):
      self.update_db_time()
    else:
      self.load_data(self.db_filename)
    self.l.log('DB', 'READY')

  def save_data(self):
    self.l.log('DB', 'SAVING DB')
    f = open(self.db_filename, 'w')
    pickle.dump(self.data, f)
    f.close()

  def publish(self):
    self.save_data()
    m_time = self.get_db_mtime(self.key)
    self.file_service.publish_file(self.key, os.path.basename(self.db_filename), self.db_filename, m_time) 

  def load_data(self, filename):
    self.data = pickle.load(open(filename))
    
  def get_file_object(self, public_key, path, create_parents=False):
    path = path.split('/')
    result = self.data.get(public_key)

    if create_parents and not result:
      result = FileObject()
      current_time = int(time.time())
      result.attrs['st_mode'] = S_IFDIR | 0755
      result.attrs['st_nlink'] = 2
      result.attrs['st_atime'] = current_time
      result.attrs['st_mtime'] = current_time
      result.attrs['st_ctime'] = current_time
      result.attrs['st_size'] = 0
      self.data[public_key] = result

    for dir_name in path:
      if dir_name:
        new_result = result.contents.get(dir_name)
        if new_result:
          result = new_result
        else:
          return None
    return result
      
  def chmod(self, public_key, path, mode):
    fobj = self.get_file_object(public_key, path)
    fobj.attrs['st_mode'] &= 0770000
    fobj.attrs['st_mode'] |= mode
    self.update_db_time()
    self.publish()

  def get_file_mtime(self, public_key, path):
    #self.l.log('DB', 'Retrieving mtime for: {}'.format(filename))
    fobj = self.get_file_object(public_key, path)
    if not fobj:
      return 0
    else:
      return fobj.attrs['st_mtime']
    
  def get_db_mtime(self, public_key):
    return self.data['current_time']
    
  def update_time(self, public_key, path, atime, mtime):
    fobj = self.get_file_object(public_key, path)
    fobj.attrs['st_atime'] = atime
    fobj.attrs['st_mtime'] = mtime
    self.update_db_time()
    self.publish()

  def update_file_mtime(self, public_key, path):
    fobj = self.get_file_object(public_key, path)
    current_time = int(time.time())
    fobj.attrs['st_mtime'] = current_time
    self.update_db_time()
    self.publish()
    return current_time

  def update_size(self, public_key, path, size):
    fobj = self.get_file_object(public_key, path)
    fobj.attrs['st_size'] = size
    self.update_db_time()
    self.publish()
    
  def chown(self, public_key, path, uid, gid):
    fobj = self.get_file_object(public_key, path)
    fobj.attrs['st_uid'] = uid
    fobj.attrs['st_gid'] = gid
    self.update_db_time()
    self.publish()
    
  def getattr(self, public_key, path):
    fobj = self.get_file_object(public_key, path)
    return fobj.attrs if fobj else None 

  def rename(self, public_key, old_path, new_path):
    old_dirname, old_filename = os.path.split(old_path)
    new_dirname, new_filename = os.path.split(new_path)
    old_location = self.get_file_object(public_key, old_dirname)
    destination = self.get_file_object(public_key, new_dirname)
    destination.contents[new_filename] = old_location.contents[old_filename]
    del old_location.contents[old_filename]
    self.update_db_time()
    self.publish()

  def add_file(self, public_key, path, mode, size):
    new_file = FileObject()
    current_time = int(time.time())
    new_file.attrs['st_mode'] = S_IFREG | mode
    new_file.attrs['st_atime'] = current_time
    new_file.attrs['st_mtime'] = current_time
    new_file.attrs['st_ctime'] = current_time
    new_file.attrs['st_size'] = size
    new_file.attrs['st_nlink'] = 1
    dirname, filename = os.path.split(path)
    fobj = self.get_file_object(public_key, dirname, True)
    fobj.contents[filename] = new_file
    self.update_db_time()
    self.publish()

  def delete_file(self, public_key, path):
    dirname, filename = os.path.split(path)
    fobj = self.get_file_object(public_key, dirname)
    del fobj.contents[filename]
    self.update_db_time()
    self.publish()

  def delete_directory(self, public_key, path):
    delete_file(public_key, path)

  def update_db_time(self):
    self.data['current_time'] = int(time.time())

  def add_directory(self, public_key, path, mode):
    # hack to create top folder, this shouldn't be done at all ever!
    self.l.log('adding directory {}'.format(path))
    if path == '/':
      self.get_file_object(public_key, '/', True)
      self.update_db_time()
      self.publish()
      return
    current_time = int(time.time())
    dirname, filename = os.path.split(path)
    new_dir = FileObject()
    new_dir.attrs['st_mode'] = S_IFDIR | mode
    new_dir.attrs['st_nlink'] = 2
    new_dir.attrs['st_size'] = 0
    new_dir.attrs['st_atime'] = current_time
    new_dir.attrs['st_mtime'] = current_time
    new_dir.attrs['st_ctime'] = current_time
    fobj = self.get_file_object(public_key, dirname, True)
    fobj.contents[filename] = new_dir

    self.update_db_time()
    self.publish()

  def list_directory(self, public_key, path):
    fobj = self.get_file_object(public_key, path)
    return fobj.contents.keys()

  def file_exists(self, public_key, path):
    dirname, filename = os.path.split(path)
    fobj = self.get_file_object(public_key, dirname)
    return fobj.contents.has_key(filename)

