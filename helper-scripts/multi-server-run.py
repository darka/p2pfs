#!/usr/bin/env python
import threading
import paramiko
import sys
import os
import argparse

logs_folder = 'logs'
logs_err_folder = os.path.join(logs_folder, 'err')

def perform_host(host, filenames, commands):
  ssh = paramiko.SSHClient()
  ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
  ssh.connect(host)

  out = open(os.path.join(logs_folder, host + '.log'), 'w')
  out_err = open(os.path.join(logs_err_folder, host + '.logerr'), 'w')

  if filenames:
    sftp = ssh.open_sftp()
  
    for filename in filenames:
      sftp.put(os.path.join(os.getcwd(), filename), os.path.join('.', filename))
      out.write('>> Uploaded: {0}\n'.format(filename))

  for command in commands:
    command = command.strip()
    if command.startswith('#'):
      continue
    stdin, stdout, stderr = ssh.exec_command(command)
  
    out.write(stdout.read())
    out_err.write(stderr.read())

    out.flush()
    out_err.flush()

  out_err.close()
  out.close()

def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('--hosts', required=True)
  parser.add_argument('--commands', required=False)
  parser.add_argument('--files', required=False, nargs='*')
  args = parser.parse_args()

  if not os.path.exists(logs_folder):
    os.makedirs(logs_folder)

  if not os.path.exists(logs_err_folder):
    os.makedirs(logs_err_folder)

  hosts = []
  f = open(args.hosts, 'r')
  for host in f.readlines():
    hosts.append(host.strip())
  f.close()

  threads = []
  commands = open(args.commands, 'r').readlines() if args.commands else []

  for host in hosts:
    print host
    t = threading.Thread(target=perform_host, args=(host, args.files, commands))
    t.start()
    threads.append(t)

  for t in threads:
    t.join()

if __name__ == "__main__":
  main()

