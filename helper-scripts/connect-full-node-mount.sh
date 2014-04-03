#!/bin/bash
KEY=/home/ubuntu/p2pfs/work/key
if [ ! -f $KEY ]; then
    ssh-keygen -q -N "" -f $KEY
fi
/usr/bin/pypy /home/ubuntu/p2pfs/src/share_node.py \
--port 2000 \
--connect 109.231.124.122:2000 \
--key $KEY \
--db /home/ubuntu/p2pfs/work/db${RANDOM} \
--log /home/ubuntu/p2pfs/log-node \
--dir /home/ubuntu/p2pfs/work/res \
--newdb \
--fs testfs 
