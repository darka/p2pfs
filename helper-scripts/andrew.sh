#!/bin/bash
cd testfs
echo Mkdir
time -f "\t%E real,\t%U user,\t%S sys" sh -c 'mkdir ed-1.9;mkdir ed-1.9/doc;mkdir ed-1.9/testsuite' >> /dev/null
echo Copy
time -f "\t%E real,\t%U user,\t%S sys" cp -r ~/tmp/ed-1.9 . >> /dev/null
echo List
time -f "\t%E real,\t%U user,\t%S sys" ls -Rla ed-1.9 >> /dev/null
echo Search
time -f "\t%E real,\t%U user,\t%S sys" grep -R "next" ed-1.9 >> /dev/null
cd ed-1.9
echo Compile
time -f "\t%E real,\t%U user,\t%S sys" sh -c './configure; make' >> /dev/null
