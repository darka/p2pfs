#!/bin/bash
HOST=$1
scp -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no server-setup.py ubuntu@${HOST}:~/
ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -t ubuntu@${HOST} bash -c "'
mkdir -p ~/.ssh
echo ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCzYVatpTuKyUB0aQlUXxAW0rIVbAh/yluy0ljWFevba0Otz4kMWIfAcEpMmchEfp9+PgqT2E3JRVy+pDsmNp/Xf0JQQnHImHEeWjAx1UqEGLYIp75cOb2p2/wmA0M8bixgQQ86FUNnxVLWyQf4w42RAzROl/G53tj+ieMbpa+MSgGCgildnvv+brfpIYANFWPD0FAAqdkSUn0rldScEqInSs+/lC+UQSuJUTeL/eRTOT1uo0R3BDtksy3S9NfhNQPJpn57fIRKdif/wgOo3hwrsey1JR7CxUhCLd0pF8fiRawIdURQ86t+QOSzaheB1FISS1xZ2oJVZKz4dNsn+2Tz ubuntu@ubuntu-VirtualBox > ~/.ssh/authorized_keys
chmod 664 ~/.ssh/authorized_keys
sudo python server-setup.py
sudo grub-install /dev/vda
sudo update-grub
'"
