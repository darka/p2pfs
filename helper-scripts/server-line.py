#!/usr/bin/env python
import sys
import os

def main():
  if len(sys.argv) != 2:
    print 'Usage: server-line.py FILENAME'
    sys.exit(1)
  f = open(sys.argv[1])
  hosts = []
  for l in f.readlines():
    l = l.strip()
    if l.startswith('#'): 
      continue
    host = l.split()[0]
    hosts.append(host)
  f.close()
  print ','.join(hosts)

if __name__ == '__main__':
  main()
