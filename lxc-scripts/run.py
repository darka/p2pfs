import random
import sys
import netaddr
import subprocess

prec = "cont"
directory = "lxc_config"

total = 10
starting_address = netaddr.IPAddress("10.0.2.50")

new_address = starting_address
prec = "cont"
addresses = [('{}000'.format(prec), starting_address)]

for i in xrange(0, total-1):
	new_address = new_address + 1
	name = "{}{:03d}".format(prec, i+1)
	addresses.append( (name, new_address))

print [a for a in addresses]

while len(addresses) > 0:
	a = addresses.pop(random.randint(0, len(addresses) - 1))
	if len(addresses) == 0: 
		break
	b = addresses.pop(random.randint(0, len(addresses) - 1))

	location = "/home/ubuntu/src/p2pfs/src"
	server_command = "chord_node.py --port 2000 --filename a{}".format(a[0])
	client_command = "chord_node.py --port 2000 --connect {}:2000 --filename b{}".format(a[1], b[0])
	print server_command
	print client_command
	p1 = subprocess.Popen(['lxc-execute', '-n', a[0], '--', sys.executable] + server_command.split(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=location)
	#print p1.stdout.read()
	p2 = subprocess.Popen(['lxc-execute', '-n', b[0], '--', sys.executable] + client_command.split(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=location)
#def main():
#	for i in xrange(0, total):
#		name = "{}{:03d}".format(prec, i)
#		run_script = "lxc-create -n {0} -f lxc_config/{0}.conf".format(name)
#		#subprocess.call(run_script, shell=True)
#		print run_script

