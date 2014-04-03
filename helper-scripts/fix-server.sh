#!/bin/bash
HOST=$1
scp -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no server-setup.py ubuntu@${HOST}:~/
ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -t ubuntu@${HOST} bash -c "'
sudo python server-setup.py
sudo grub-install /dev/vda
sudo update-grub
'"
