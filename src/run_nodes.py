import sys
import os
import time
import subprocess

port_range = (4000, 4008)

retriever = 5

data = {12:100, 17:200}

def main():
  # start first node
  procs = []
  command = ['python', 'chord_node.py', '--port', str(port_range[0])]
  print(' '.join(command))
  procs.append(subprocess.Popen(command))

  data_items = data.items()
  for port in range(port_range[0]+1, port_range[1]):
    command = ['python', 'chord_node.py', '--port', str(port)]
    command += ['--connect', 'localhost:{}'.format(str(port_range[0]))]
    if len(data_items) > 0:
      item = data_items.pop()
      command.append('--store')
      command.append('{}:{}'.format(item[0], item[1]))
    print(' '.join(command))
    procs.append(subprocess.Popen(command))
  time.sleep(10)
  for p in procs:
    p.terminate()

  # call the rest of servers

if __name__ == '__main__':
  main()
