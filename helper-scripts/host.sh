#!/bin/bash
/usr/bin/pypy /home/ubuntu/p2pfs/src/share_node.py \
--port 2000 \
--key /home/ubuntu/p2pfs/src/keys/key0 \
--db /home/ubuntu/p2pfs/work/dbhost \
--log /home/ubuntu/p2pfs/log-host \
--dir /home/ubuntu/p2pfs/work/res \
--newdb
