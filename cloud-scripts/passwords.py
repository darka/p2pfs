import flexiapi
import sys
import pickle

numbers = range(1, 32)

out = open('ips.txt', 'w')

d = {}
for n in numbers:
  name = 'Node {}'.format(n)
  try:
    server = flexiapi.findServerByName(name)
    ip = server.nics[0].ipAddresses[0].ipAddress
  except TypeError:
    print 'ERROR: {}'.format(name)
    continue
  s = '{} # {}'.format(ip, name)
  print s
  out.write(s + '\n')
  password = server.initialPassword
  d[str(ip)] = str(password)

out.close()

f = open('passwords.pickle', 'w')
pickle.dump(d, f)
f.close()
