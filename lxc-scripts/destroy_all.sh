#!/bin/bash
nodes=`lxc-ls`
for node in $nodes
do
  echo destroying $node
  sudo lxc-stop -n $node
  sudo lxc-destroy -n $node
done
