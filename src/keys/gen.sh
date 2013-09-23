#!/bin/bash

for i in {0..100}
do 
  ssh-keygen -q -N "" -f key$i
done
