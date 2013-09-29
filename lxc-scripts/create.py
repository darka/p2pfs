#!/usr/bin/python
import subprocess
import sys

prec = "cont"
directory = "lxc_config"

def main():
    if len(sys.argv) != 2:
        print("Please specify container count")
        sys.exit(1)
    total = int(sys.argv[1])
    for i in xrange(0, total):
        name = "{}{:03d}".format(prec, i)
        run_script = "lxc-create -n {0} -f lxc_config/{0}.conf".format(name)
        subprocess.call(run_script, shell=True)

if __name__ == "__main__":
	main()
