#!/usr/bin/python

import subprocess

output = subprocess.check_output("blkid").strip().split()
assert(output[1][:4] == 'UUID')
uuid = output[1].split("=")[1].strip("\"")

f = open("/boot/grub/load.cfg", 'w')
f.write("""\
search.fs_uuid {} root 
set prefix=($root)/grub
""".format(uuid))
f.close()
