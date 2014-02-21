#!/bin/bash
HOST=$1
scp server-setup.py ubuntu@${HOST}:~/
ssh -t ubuntu@${HOST} sudo python server-setup.py
ssh -t ubuntu@${HOST} sudo dpkg-reconfigure grub-pc

