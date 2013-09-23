#!/usr/bin/python
import subprocess

prec = "cont"
directory = "lxc_config"
total = 10

def main():
	for i in xrange(0, total):
		name = "{}{:03d}".format(prec, i)
		run_script = "lxc-create -n {0} -f lxc_config/{0}.conf".format(name)
		subprocess.call(run_script, shell=True)

if __name__ == "__main__":
	main()
