import sys

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
    self.out.flush()
 
