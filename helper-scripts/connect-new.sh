#!/bin/bash
/usr/bin/pypy /home/ubuntu/p2pfs/src/share_node.py \
--port 2000 \
--connect 109.231.124.122:2000 \
--key /home/ubuntu/p2pfs/src/keys/key1 \
--db /home/ubuntu/p2pfs/work/dball \
--log /home/ubuntu/p2pfs/log-node \
--dir /home/ubuntu/p2pfs/work/res \
--newdb
