#!/usr/bin/env python
import sys
import os

def make_server_line(filename):
  f = open(filename)
  hosts = []
  for l in f.readlines():
    l = l.strip()
    if l.startswith('#'): 
      continue
    host = l.split()[0]
    hosts.append(host)
  f.close()
  return ','.join(hosts)

def main():
  if len(sys.argv) != 2:
    print 'Usage: server-line.py FILENAME'
    sys.exit(1)
  filename = sys.argv[1]
  print make_server_line(filename)

if __name__ == '__main__':
  main()
