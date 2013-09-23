#!/usr/bin/python
import netaddr
import os
import virtinst.util
import copy

default_config = [
  ("lxc.utsname",        "vps0"),
  ("lxc.network.type",   "veth"),
  ("lxc.network.flags",  "up"), 
  ("lxc.network.link",   "br0"), 
  ("lxc.network.hwaddr", "00:30:6E:08:EC:80"),
  ("lxc.network.ipv4",   "192.168.1.10"),
  ("lxc.network.name",   "eth0")
]

default_options = {}
for key, value in default_config:
	default_options[key] = value

starting_address = netaddr.IPAddress("192.168.1.10")
directory = "lxc_config"
total = 100

def write_config(f, options):
	for key in (pair[0] for pair in default_config):
		f.write("{} = {}\n".format(key, options[key]))

def main():
	current_address = copy.copy(starting_address)
	prec = "cont"
	if not os.path.exists(directory):
	    os.makedirs(directory)
	for i in xrange(0, total):
		name = "{}{:03d}".format(prec, i)
		options = default_options.copy()
		options["lxc.utsname"] = name
		options["lxc.network.hwaddr"] = virtinst.util.randomMAC().upper()
		options["lxc.network.ipv4"] = str(current_address) + '/24'
		current_address += 1
		f = open(os.path.join(directory, "{}.conf".format(name)), "w")
		write_config(f, options)
		f.close()
			
if __name__ == "__main__":
	main()
