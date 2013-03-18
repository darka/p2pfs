import netaddr
import os
import copy

default_options = {
  "lxc.utsname" : "vps0" ,
  "lxc.network.type" : "veth",
  "lxc.network.flags" : "up", 
  "lxc.network.link" : "br0", 
  "lxc.network.hwaddr" : "00:30:6E:08:EC:80",
  "lxc.network.ipv4" : "192.168.1.10",
  "lxc.network.name" : "eth0"
}

starting_address = netaddr.IPAddress("192.168.1.10")
directory = "lxc_config"
total = 10

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
		for key, value in options.iteritems():
			f.write("{} = {}\n".format(key, value))
		f.close()
			
			

		

if __name__ == "__main__":
	main()
