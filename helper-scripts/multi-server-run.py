import threading
import paramiko
import sys
import os

logs_folder = 'logs'
logs_err_folder = os.path.join(logs_folder, 'err')

def ssh_run(host):
  ssh = paramiko.SSHClient()
  ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
  ssh.connect(host)
  stdin, stdout, stderr = ssh.exec_command('ls')

  out = open(os.path.join(logs_err_folder, host + '.logerr'), 'w')
  out.write(stderr.read())
  out.close()

  out = open(os.path.join(logs_folder, host + '.log'), 'w')
  out.write(stdout.read())
  out.close()

def main():
  if len(sys.argv) != 2:
    print "Usage: multi-server-run.py [FILE]"
    sys.exit(1)

  if not os.path.exists(logs_folder):
    os.makedirs(logs_folder)

  if not os.path.exists(logs_err_folder):
    os.makedirs(logs_err_folder)

  hosts = []
  f = open(sys.argv[1], 'r')
  for host in f.readlines():
    hosts.append(host.strip())
  f.close()

  threads = []
  for host in hosts:
    print host
    t = threading.Thread(target=ssh_run, args=(host,))
    t.start()
    threads.append(t)

  for t in threads:
    t.join()

if __name__ == "__main__":
  main()

