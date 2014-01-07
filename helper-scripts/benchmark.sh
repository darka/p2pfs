cd test
echo Copy
time -f "\t%E real,\t%U user,\t%S sys" cp -r ~/tmp/irssi-0.8.16-rc1 . >> /dev/null
echo List
time -f "\t%E real,\t%U user,\t%S sys" ls -Rla irssi-0.8.16-rc1 >> /dev/null
echo Search
time -f "\t%E real,\t%U user,\t%S sys" grep -R "next" irssi-0.8.16-rc1 >> /dev/null
