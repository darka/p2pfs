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

  def ready(self, file_service):
    self.file_service = file_service
    self.conn = sqlite3.connect(self.db_filename)
    if self.new:
      self.create_tables()
    
  def execute(self, command):
    self.l.log(command)
    c = self.conn.cursor()
    c.execute(command)
    return c

  def commit(self):
    self.conn.commit()
    self.file_service.publish_file(self.key, os.path.basename(self.db_filename), self.db_filename)
    
  def create_tables(self):
    try:
      self.execute('''DROP TABLE files''')
    except sqlite3.OperationalError:
      self.l.log('Could not drop table')
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
          "st_size integer DEFAULT 0)")
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
    self.commit()

  def update_time(self, public_key, path, atime, mtime):
    filename = os.path.basename(path)
    dirname = os.path.dirname(path)
    self.execute("UPDATE files SET st_atime={}, st_mtime={} WHERE path='{}' AND filename='{}' AND pub_key='{}'".format(
        atime, mtime, dirname, filename, public_key))
    self.commit()

  def update_size(self, public_key, path, size):
    filename = os.path.basename(path)
    dirname = os.path.dirname(path)
    self.execute("UPDATE files SET st_size={} WHERE path='{}' AND filename='{}' AND pub_key='{}'".format(
        size, dirname, filename, public_key))
    self.commit()
    
  def chown(self, public_key, path, uid, gid):
    filename = os.path.basename(path)
    dirname = os.path.dirname(path)
    self.execute("UPDATE files SET st_uid={}, st_gid={} WHERE path='{}' AND filename='{}' AND pub_key='{}'".format(
        uid, gid, dirname, filename, public_key))
    self.commit()
    
  def getattr(self, public_key, path):
    dirname = os.path.dirname(path)
    filename = os.path.basename(path)
    fields = 'st_atime, st_ctime, st_mode, st_mtime, st_nlink, st_size'.split(', ')
    c = self.execute("SELECT {} FROM files WHERE pub_key='{}' AND path='{}' AND filename='{}'".format(', '.join(fields), public_key, dirname, filename))
    attrs = c.fetchone()
    if not attrs: 
      return None
    result = dict(zip(fields, attrs))
    return result

  def rename(self, public_key, old_path, new_path):
    old_dirname = os.path.dirname(old_path)
    old_filename = os.path.basename(old_path)
    new_dirname = os.path.dirname(new_path)
    new_filename = os.path.basename(new_path)
    current_time = int(time.time())
    self.execute("UPDATE files SET path='{}', filename='{}' WHERE path='{}' AND filename='{}'".format(
        new_dirname, new_filename, old_dirname, old_filename))
    self.commit()

  def add_file(self, public_key, filename, path, mode, size):
    current_time = int(time.time())
    self.execute("INSERT INTO files"
                 "(pub_key, filename, path, st_mode, st_atime, st_mtime, st_ctime, st_size) "
                 "VALUES('{}', '{}', '{}', '{}', '{}', '{}', '{}', {})".format(
        public_key, filename, path, S_IFREG | mode, current_time, current_time, current_time, size))
    self.commit()

  def delete_directory(self, public_key, path):
    dirname = os.path.dirname(path)
    filename = os.path.basename(path)
    self.execute("DELETE FROM files WHERE "
                 "pub_key='{}' AND path='{}' AND filename='{}'".format(public_key, dirname, filename))
    self.commit()

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
    self.commit()

  def list_directory(self, public_key, path):
    c = self.execute("SELECT filename FROM files WHERE pub_key='{}' AND path='{}'".format(public_key, path))
    rows = c.fetchall()
    return [row[0] for row in rows if row[0]]

