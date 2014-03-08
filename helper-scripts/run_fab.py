#!/usr/bin/env python
import sys
import subprocess
import os
import server_line

def main():
  if len(sys.argv) < 3:
    print 'Usage: run_fab.py FILENAME COMMAND [REST]'
    sys.exit(1)
  filename = sys.argv[1]
  command = sys.argv[2]

  fab_command = 'fab'
  if len(sys.argv) > 3:
    rest = ' '.join(sys.argv[3:])
    fab_command += ' {}'.format(rest)

  hosts = server_line.make_server_line(filename)
  
  fab_command += ' -H {} {}'.format(hosts, command)

  print fab_command
  subprocess.call(fab_command, shell=True, cwd='.')
  print 'done'

if __name__ == '__main__':
  main()
