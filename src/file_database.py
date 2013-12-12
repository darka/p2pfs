from stat import S_IFDIR, S_IFLNK, S_IFREG
import time
import os
import sqlite3

class FileDatabase(object):
  def __init__(self, logger, key, filename, new=False):
    self.key = key
    self.db_filename = filename
    self.new = new
    self.l = logger
    self.attr_fields = 'st_atime, st_ctime, st_mode, st_mtime, st_nlink, st_size'.split(', ')

  def ready(self, file_service):
    self.file_service = file_service
    self.conn = sqlite3.connect(self.db_filename)
    if self.new:
      self.create_tables()
    
  def execute(self, command):
    self.l.log('SQL', command)
    c = self.conn.cursor()
    c.execute(command)
    return c

  def commit(self):
    self.conn.commit()
    m_time = self.get_db_mtime(self.key)
    self.file_service.publish_file(self.key, os.path.basename(self.db_filename), self.db_filename, m_time)
    
  def create_tables(self):
    try:
      self.execute('''DROP TABLE files''')
    except sqlite3.OperationalError:
      self.l.log('DB', 'Could not drop table')
    self.execute(
          "CREATE TABLE files ("
          "pub_key text, "
          "filename text, "
          "path text, "
          "st_mode integer, "
          "st_uid integer, "
          "st_gid integer, "
          "st_atime integer DEFAULT 0, "
          "st_mtime integer DEFAULT 0, "
          "st_ctime integer DEFAULT 0, "
          "st_nlink integer DEFAULT 1, "
          "st_size integer DEFAULT 0, "
          "is_internal integer DEFAULT 0, "
          "PRIMARY KEY(path, filename, pub_key))")
    current_time = int(time.time())
    self.execute("INSERT INTO files"
                 "(pub_key, is_internal, filename, path, st_mode, st_atime, st_mtime, st_ctime, st_size) "
                 "VALUES('{}', 1, 'DB', 'DB', {}, {}, {}, {}, {})".format(
        self.key, 0, current_time, current_time, current_time, 0))

    self.commit()

  def chmod(self, public_key, path, mode):
    filename = os.path.basename(path)
    dirname = os.path.dirname(path)
    c = self.execute("SELECT st_mode FROM files WHERE pub_key='{}' AND path='{}' AND filename='{}'".format(public_key, dirname, filename))
    old_mode = c.fetchone()[0]
    old_mode &= 0770000
    mode = old_mode | mode
    self.execute("UPDATE files SET st_mode={} WHERE path='{}' AND filename='{}' AND pub_key='{}'".format(
        mode, dirname, filename, public_key))
    self.update_db_time()
    self.commit()

  def get_file_mtime(self, public_key, path):
    filename = os.path.basename(path)
    dirname = os.path.dirname(path)
    self.l.log('DB', 'Retrieving mtime for: {}'.format(filename))
    c = self.execute("SELECT st_mtime FROM files WHERE pub_key='{}' AND path='{}' AND filename='{}'".format(public_key, dirname, filename))
    ret = c.fetchone()
    self.l.log('DB', 'Result: {}'.format(str(ret)))
    if not ret: 
      return 0
    else: 
      return ret[0]
    
  def get_db_mtime(self, public_key):
    self.l.log('DB', 'Retrieving db mtime')
    c = self.execute("SELECT st_mtime FROM files WHERE pub_key='{}' AND path='DB' AND filename='DB' AND is_internal=1".format(public_key))
    ret = c.fetchone()
    self.l.log('DB', 'Result: {}'.format(str(ret)))
    if not ret: return 0
    else: return ret[0]
    
  def update_time(self, public_key, path, atime, mtime):
    filename = os.path.basename(path)
    dirname = os.path.dirname(path)
    self.execute("UPDATE files SET st_atime={}, st_mtime={} WHERE path='{}' AND filename='{}' AND pub_key='{}'".format(
        atime, mtime, dirname, filename, public_key))
    self.update_db_time()
    self.commit()

  def update_file_mtime(self, public_key, path):
    filename = os.path.basename(path)
    dirname = os.path.dirname(path)
    current_time = int(time.time())
    self.execute("UPDATE files SET st_mtime={} WHERE path='{}' AND filename='{}' AND pub_key='{}'".format(
        current_time, dirname, filename, public_key))
    self.update_db_time()
    self.commit()
    return current_time

  def update_size(self, public_key, path, size):
    filename = os.path.basename(path)
    dirname = os.path.dirname(path)
    self.execute("UPDATE files SET st_size={} WHERE path='{}' AND filename='{}' AND pub_key='{}'".format(
        size, dirname, filename, public_key))
    self.update_db_time()
    self.commit()
    
  def chown(self, public_key, path, uid, gid):
    filename = os.path.basename(path)
    dirname = os.path.dirname(path)
    self.execute("UPDATE files SET st_uid={}, st_gid={} WHERE path='{}' AND filename='{}' AND pub_key='{}'".format(
        uid, gid, dirname, filename, public_key))
    self.update_db_time()
    self.commit()
    
  def getattr(self, public_key, path):
    dirname = os.path.dirname(path)
    filename = os.path.basename(path)
    c = self.execute("SELECT st_atime, st_ctime, st_mode, st_mtime, st_nlink, st_size FROM files WHERE pub_key='{}' AND path='{}' AND filename='{}'".format(public_key, dirname, filename))
    attrs = c.fetchone()
    if not attrs: 
      return None
    return dict(zip(self.attr_fields, attrs))

  def rename(self, public_key, old_path, new_path):
    old_dirname = os.path.dirname(old_path)
    old_filename = os.path.basename(old_path)
    new_dirname = os.path.dirname(new_path)
    new_filename = os.path.basename(new_path)
    current_time = int(time.time())
    self.execute("UPDATE files SET path='{}', filename='{}' WHERE path='{}' AND filename='{}'".format(
        new_dirname, new_filename, old_dirname, old_filename))
    self.update_db_time()
    self.commit()

  def add_file(self, public_key, path, mode, size):
    dirname, filename = os.path.split(path)
    current_time = int(time.time())
    self.execute("INSERT INTO files"
                 "(pub_key, filename, path, st_mode, st_atime, st_mtime, st_ctime, st_size) "
                 "VALUES('{}', '{}', '{}', '{}', '{}', '{}', '{}', {})".format(
        public_key, filename, dirname, S_IFREG | mode, current_time, current_time, current_time, size))
    self.update_db_time()
    self.commit()

  def delete_file(self, public_key, path):
    dirname, filename = os.path.split(path)
    self.execute("DELETE FROM files WHERE "
                 "pub_key='{}' AND path='{}' AND filename='{}'".format(public_key, dirname, filename))
    self.update_db_time()
    self.commit()

  def delete_directory(self, public_key, path):
    dirname, filename = os.path.split(path)
    self.execute("DELETE FROM files WHERE "
                 "pub_key='{}' AND path='{}' AND filename='{}'".format(public_key, dirname, filename))
    self.update_db_time()
    self.commit()

  def update_db_time(self):
    current_time = int(time.time())
    self.execute("UPDATE files SET st_mtime={}, st_ctime={} WHERE filename='DB' AND path='DB' AND is_internal=1".format(current_time, current_time))

  def add_directory(self, public_key, path, mode):
    current_time = int(time.time())
    dirname = os.path.dirname(path)
    filename = os.path.basename(path)
    self.execute("INSERT INTO files"
                 "(pub_key, path, filename, st_mode, st_nlink, st_atime, st_mtime, st_ctime) "
                 "VALUES('{}', '{}', '{}', '{}', '{}', '{}', '{}', '{}')".format(
        public_key, dirname, filename, S_IFDIR | mode, 2, current_time, current_time, current_time))
    if path != '/':
      self.execute("UPDATE files SET st_nlink = st_nlink + 1 WHERE path='{}' AND pub_key='{}'".format(
        '/', public_key))
    self.update_db_time()
    self.commit()

  def list_directory(self, public_key, path):
    c = self.execute("SELECT filename FROM files WHERE pub_key='{}' AND path='{}'".format(public_key, path))
    rows = c.fetchall()
    return [row[0] for row in rows if row[0]]

  def file_exists(self, public_key, path):
    dirname = os.path.dirname(path)
    filename = os.path.basename(path)
    c = self.execute("SELECT filename FROM files WHERE pub_key='{}' AND path='{}' AND filename='{}'".format(public_key, dirname, filename))
    rows = c.fetchall()
    return len(rows) >= 1

