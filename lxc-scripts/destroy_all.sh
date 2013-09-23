#!/bin/bash
nodes=`lxc-ls`
for node in $nodes
do
  echo 'stopping...'
  sudo lxc-stop -n $node
  echo 'destroying...'
  sudo lxc-destroy -n $node
done
