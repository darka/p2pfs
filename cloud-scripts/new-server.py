import flexiapi
import sys

numbers = range(1, 32)

for n in numbers:
  name = 'Node {}'.format(n)
  print 'Creating: {}'.format(name)
  flexiapi.createServer(name)
