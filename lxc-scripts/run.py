#!/usr/bin/python

import os
import time
import random
import sys
import netaddr
import subprocess
import argparse

prec = "cont"
directory = "lxc_config"
location = "/home/ubuntu/p2pfs"
keys_location = "/home/ubuntu/p2pfs/src/keys/"
dbs_location = "/home/ubuntu/p2pfs/src/dbs/"
logs_location = "/home/ubuntu/p2pfs/src/logs/"
resources_location = "/home/ubuntu/p2pfs/src/res/"
node_location = os.path.join(location, 'src', 'share_node.py')
base_command = node_location + " --port 2000"

#python_command = sys.executable
python_command = "/usr/bin/pypy"

parser = argparse.ArgumentParser()
parser.add_argument('--count', '-c', type=int, dest='container_count', required=True)
parser.add_argument('--simulate', default=False, action='store_true')
args = parser.parse_args()

total = args.container_count

#starting_address = netaddr.IPAddress("192.168.1.10")
starting_address = netaddr.IPAddress("10.0.3.2")

new_address = starting_address
addresses = [('{}000'.format(prec), starting_address)]

for i in xrange(0, total-1):
    new_address = new_address + 1
    name = "{}{:03d}".format(prec, i+1)
    addresses.append( (name, new_address) )

print [a for a in addresses]

current = 0
shares = { 1 : os.path.join('/home/ubuntu/test_pics') }

def run_subprocess(address, command, fake=False):
    time.sleep(0.5)
    command_parts = ['lxc-execute', '-n', address[0], '--', python_command] + command.split()
    print(' '.join(command_parts))
    if not fake:
      subprocess.Popen(command_parts, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=location)

def with_default_args(command, current):
    ret = command
    key_location = os.path.join(keys_location, 'key' + str(current))
    db_location = os.path.join(dbs_location, 'db' + str(current))
    log_location = os.path.join(logs_location, 'log' + str(current))
    resource_location = os.path.join(resources_location, 'res' + str(current))
    try:
        os.makedirs(resource_location)
    except:
        pass
    ret += " --key {}".format(key_location)
    ret += " --db {}".format(db_location)
    ret += " --log {}".format(log_location)
    ret += " --dir {}".format(resource_location)
    ret += " --newdb"
    return ret
  
def run_nodes(addresses, simulate=False):
      
    current = 0
    # run the first container 
    a = addresses.pop(random.randint(0, len(addresses) - 1))

    command = with_default_args(base_command, current)

    # add share if needed
    if current in shares:
        command = '{} {} {}'.format(command, '--share', shares[current])
    run_subprocess(a, command, simulate)

    # run the rest of containers:

    current += 1
    while len(addresses) > 0:
        if len(addresses) == 0: 
            break
        b = addresses.pop(random.randint(0, len(addresses) - 1))
        
        command = "{} --connect {}:2000".format(base_command, a[1])

        command = with_default_args(command, current)

        if current in shares:
            command = '{} {} {}'.format(command, '--share', shares[current])
         
        run_subprocess(b, command, simulate)
        current += 1

def main():
    run_nodes(addresses, args.simulate)

if __name__=='__main__':
    main()
