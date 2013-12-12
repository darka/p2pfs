import datetime
import sys

class Logger(object):
  def __init__(self, where=None):
    self.set_output(where)
    self.DISABLED = True

  def set_output(self, where):
    if not where:
      self.out = sys.stdout
    else:
      self.out = where

  def log(self, *args):
    if self.DISABLED:
      return
    if len(args) == 1:
      cl = 'NULL'
      message = args[0]
    elif len(args) == 2:
      cl = args[0]
      message = args[1]
    tm = str(datetime.datetime.now())
    self.out.write('[{}] [{}] {}\n'.format(tm, cl, message))
    self.out.flush()
 
