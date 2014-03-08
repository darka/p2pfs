cd testfs
echo Copy
time -f "\t%E real,\t%U user,\t%S sys" cp -r ~/tmp/ed-1.9 . >> /dev/null
echo List
time -f "\t%E real,\t%U user,\t%S sys" ls -Rla ed-1.9 >> /dev/null
echo Search
time -f "\t%E real,\t%U user,\t%S sys" grep -R "next" ed-1.9 >> /dev/null
