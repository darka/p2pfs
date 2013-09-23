#!/usr/bin/python

import os
import time
import random
import sys
import netaddr
import subprocess

prec = "cont"
directory = "lxc_config"
location = "/home/ubuntu/p2pfs"
keys_location = "/home/ubuntu/p2pfs/src/keys/"
node_location = os.path.join(location, 'src', 'share_node.py')
base_command = node_location + " --port 2000"

total = 10
starting_address = netaddr.IPAddress("192.168.1.10")

new_address = starting_address
addresses = [('{}000'.format(prec), starting_address)]

for i in xrange(0, total-1):
    new_address = new_address + 1
    name = "{}{:03d}".format(prec, i+1)
    addresses.append( (name, new_address) )

print [a for a in addresses]

current = 0
shares = { 1 : 'pngs', 
           2 : 'more_pngs' }

def run_subprocess(address, command):
    time.sleep(1)
    command_parts = ['lxc-execute', '-n', address[0], '--', sys.executable] + command.split()
    print 'Running: {}'.format(' '.join(command_parts))
    subprocess.Popen(command_parts, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=location)
  
def run_nodes(addresses):
    def add_key_arg(command, current):
      key_location = os.path.join(keys_location, 'key' + str(current))
      return command + " --key {}".format(key_location)
      
    current = 0
    # run the first container 
    a = addresses.pop(random.randint(0, len(addresses) - 1))

    command = add_key_arg(base_command, current)

    # add share if needed
    if current in shares:
      command = '{} {} {}'.format(command, '--share', shares[current])
    run_subprocess(a, command)

    # run the rest of containers:

    current += 1
    while len(addresses) > 0:
        if len(addresses) == 0: 
            break
        b = addresses.pop(random.randint(0, len(addresses) - 1))
        
        command = "{} --connect {}:2000".format(base_command, a[1])

        command = add_key_arg(command, current)

        if current in shares:
            command = '{} {} {}'.format(command, '--share', shares[current])
         
        run_subprocess(b, command)
        current += 1

def main():
    run_nodes(addresses)

if __name__=='__main__':
  main()
