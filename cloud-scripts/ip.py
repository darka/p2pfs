import flexiapi
import sys

numbers = range(1, 32)

for n in numbers:
  name = 'Node {}'.format(n)
  print '{} # {}'.format(flexiapi.getIP(name), name)
