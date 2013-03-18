import netaddr
import os
import copy

default_keys = [
  "lxc.utsname",
  "lxc.network.type",
  "lxc.network.flags", 
  "lxc.network.link", 
  "lxc.network.hwaddr",
  "lxc.network.ipv4",
  "lxc.network.name"
]

default_values = [
  "vps0" ,
  "veth",
  "up", 
  "br0", 
  "00:30:6E:08:EC:80",
  "192.168.1.10",
  "eth0"
]

default_options = {}
for key, value in zip(default_keys, default_values):
	default_options[key] = value

starting_address = netaddr.IPAddress("192.168.1.10")
directory = "lxc_config"
total = 10

def write_config(f, options):
	for key in default_keys:
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
		options["lxc.network.ipv4"] = str(current_address)
		current_address += 1
		f = open(os.path.join(directory, "{}.conf".format(name)), "w")
		write_config(f, options)
		f.close()
			
			

		

if __name__ == "__main__":
	main()
