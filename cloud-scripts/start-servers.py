import flexiapi
import sys
import suds

numbers = range(1, 32)
for n in numbers:
  name = 'Node {}'.format(n)
  print name
  try:
    flexiapi.changeServerStatus(name, 'RUNNING')
  except suds.WebFault:
    print 'Already Running?'
    continue
  except TypeError:
    print 'ERROR!'
    continue
